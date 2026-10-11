"""Shared Git project identity and collection registration."""

import json
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .errors import OperationalError
from .layout import validate_layout, validate_name, validate_set


REGISTRATION_NAME = "project-skillsets.json"
HOOK_COMMAND = (
    'skillset_project_hook() { '
    'if skillset _project-hook "$@"; then :; else '
    "printf '%s\\n' 'skillset: project hook failed; rerun project enable or inspect project list' >&2; "
    'fi; return 0; }; skillset_project_hook'
)
_HOOK_PREFIX = "hook.skillset-project."
_OWNED_CONFIG = {
    _HOOK_PREFIX + "command": HOOK_COMMAND,
    _HOOK_PREFIX + "event": "post-checkout",
}


@dataclass(frozen=True)
class GitProject:
    common_dir: Path
    current_root: Path
    worktrees: tuple


def _git(cwd, *arguments, env=None, allowed=(0,)):
    command = ["git", "-C", os.fspath(cwd), *arguments]
    try:
        result = subprocess.run(command, env=env, capture_output=True, check=False)
    except OSError as error:
        raise OperationalError(f"could not execute Git in {cwd}: {error}") from error
    if result.returncode not in allowed:
        reason = os.fsdecode(result.stderr).rstrip("\n")
        raise OperationalError(reason or f"Git exited {result.returncode} in {cwd}")
    return result.stdout


def _require_git_version():
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, check=False)
    except OSError as error:
        raise OperationalError(f"project scope requires Git 2.54 or newer: {error}") from error
    match = re.match(rb"git version (\d+)\.(\d+)(?:\.|\s|$)", result.stdout)
    if result.returncode or not match or tuple(map(int, match.groups())) < (2, 54):
        raise OperationalError("project scope requires Git 2.54 or newer")
    return tuple(map(int, match.groups()))


def _git_path(cwd, *arguments, env=None):
    serialized = _git(cwd, "rev-parse", *arguments, env=env).removesuffix(b"\n")
    path = Path(os.fsdecode(serialized))
    if not path.is_absolute():
        path = cwd / path
    return path.resolve()


def _identity(cwd, *, env=None):
    if _git(cwd, "rev-parse", "--is-inside-work-tree", env=env) != b"true\n":
        raise OperationalError("project scope requires a Git worktree")
    common = _git_path(cwd, "--path-format=absolute", "--git-common-dir", env=env)
    root = _git_path(cwd, "--show-toplevel", env=env)
    return common, root


def _worktree_paths(contents):
    paths = []
    for record in contents.split(b"\0\0"):
        if not record:
            continue
        fields = record.split(b"\0")
        if not fields[0].startswith(b"worktree "):
            raise OperationalError("cannot inspect Git worktree inventory: missing worktree path")
        if b"bare" not in fields:
            paths.append(Path(os.fsdecode(fields[0][len(b"worktree "):])).resolve())
    return tuple(sorted(paths))


def discover(cwd: Path, *, required=True, inventory=True):
    """Resolve this clone and, for required discovery, validate its worktrees.

    Optional overview discovery needs neither a version floor nor inventory.
    """
    cwd = Path(cwd).resolve()
    if required:
        _require_git_version()
    try:
        common, root = _identity(cwd)
    except OperationalError as error:
        if not required:
            return None
        raise OperationalError(f"project scope requires a Git worktree: {error}") from error
    if not required or not inventory:
        return GitProject(common, root, ())
    context, errors = _inspect_worktrees(GitProject(common, root, ()), cwd=cwd)
    if errors:
        raise OperationalError("\n".join(errors))
    return context


def _inspect_worktrees(context, *, cwd):
    """Collect accessible roots and every ordinary inventory error."""
    common = context.common_dir
    worktrees = _worktree_paths(_git(cwd, "worktree", "list", "--porcelain", "-z"))
    child_env = os.environ.copy()
    for name in _git(cwd, "rev-parse", "--local-env-vars").splitlines():
        child_env.pop(os.fsdecode(name), None)
    checked = []
    errors = []
    for worktree in worktrees:
        try:
            # Submodule inventory names its main Git directory; core.worktree
            # lets Git resolve the actual checkout, including from linked trees.
            if worktree == common:
                worktree = _git_path(worktree, "--show-toplevel", env=child_env)
            sibling_common, sibling_root = _identity(worktree, env=child_env)
            if sibling_common != common:
                raise OperationalError(f"common directory differs from {common}")
            if sibling_root != worktree:
                raise OperationalError(f"worktree root differs from {worktree}")
            checked.append(worktree)
        except OperationalError as error:
            errors.append(f"cannot inspect registered worktree {worktree}: {error}")
    return GitProject(common, context.current_root, tuple(sorted(checked))), tuple(errors)


def _registration_error(path, reason):
    return OperationalError(f"invalid project registration {path}: {reason}")


def _validated_names(value, path):
    if not isinstance(value, dict) or set(value) != {"version", "names"}:
        raise _registration_error(path, "expected exactly 'version' and 'names'")
    if type(value["version"]) is not int or value["version"] != 1:
        raise _registration_error(path, "expected integer version 1")
    names = value["names"]
    if not isinstance(names, list) or not names:
        raise _registration_error(path, "names must be a nonempty list")
    for name in names:
        if not isinstance(name, str):
            raise _registration_error(path, "names must contain strings")
        try:
            validate_name(name)
        except OperationalError as error:
            raise _registration_error(path, str(error)) from error
    if names != sorted(set(names)):
        raise _registration_error(path, "names must be sorted and unique")
    return tuple(names)


def read_names(common_dir: Path):
    """Read valid clone registration without changing malformed state."""
    path = common_dir / REGISTRATION_NAME
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    except OSError as error:
        raise _registration_error(path, str(error)) from error
    if not stat.S_ISREG(mode):
        raise _registration_error(path, "must be a real regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise _registration_error(path, str(error)) from error
    return _validated_names(value, path)


def write_names(common_dir: Path, names: tuple):
    """Atomically replace registration, or remove it for an empty selection."""
    path = common_dir / REGISTRATION_NAME
    read_names(common_dir)
    staging = None
    try:
        if not names:
            path.unlink(missing_ok=True)
            return
        value = {"version": 1, "names": list(names)}
        _validated_names(value, path)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=common_dir,
            prefix=f".{REGISTRATION_NAME}.", delete=False,
        ) as output:
            staging = Path(output.name)
            json.dump(value, output, indent=2)
            output.write("\n")
        os.replace(staging, path)
    except OSError as error:
        raise OperationalError(f"could not write project registration {path}: {error}") from error
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)


def _config_entries(worktree, *, env=None):
    """Read scopes and origins without losing duplicate keys or multiline values."""
    contents = _git(worktree, "config", "--null", "--list", "--show-scope",
                    "--show-origin", env=env)
    fields = contents.split(b"\0")
    entries = []
    for offset in range(0, len(fields) - 1, 3):
        scope, origin, setting = map(os.fsdecode, fields[offset:offset + 3])
        key, separator, value = setting.partition("\n")
        entries.append((scope, origin, key, value if separator else None))
    return entries


def _common_config_entry(context, worktree, scope, origin):
    if scope != "local" or not origin.startswith("file:"):
        return False
    path = Path(origin[len("file:"):])
    if not path.is_absolute():
        # Git reports auto-discovered origins from the worktree root even
        # when invoked below it; explicit repository paths yield absolute origins.
        path = worktree / path
    return path.resolve() == context.common_dir / "config"


def _hook_listed(worktree, *, env=None):
    listing = _git(worktree, "hook", "list", "-z", "--show-scope",
                   "post-checkout", env=env, allowed=(0, 1))
    return b"local\tskillset-project" in listing.split(b"\0")


def _config_disabled(worktree, key, *, env=None):
    return _git(worktree, "config", "--type=bool", "--get", key,
                env=env, allowed=(0, 1)) == b"false\n"


def hook_config_errors(context: GitProject, *, registered: bool, enabling: bool, cwd=None):
    """Validate owned keys everywhere; disabling controls remain operator-owned.

    Enable accepts missing owned keys so it can repair an interrupted install.
    Disable accepts supported enabled controls, without changing their values.
    The invoking reads retain cwd so relative inherited Git variables keep
    their meaning; sibling reads use sanitized environments.
    """
    cwd = context.current_root if cwd is None else Path(cwd)
    child_env = os.environ.copy()
    for name in _git(cwd, "rev-parse", "--local-env-vars").splitlines():
        child_env.pop(os.fsdecode(name), None)
    errors = []
    for worktree in context.worktrees or (context.current_root,):
        # Keep the invoking worktree's command-scope configuration. Git's
        # local-env-vars includes GIT_CONFIG_COUNT as well as location vars.
        invoking = worktree == context.current_root
        inspection_cwd = cwd if invoking else worktree
        inspection_env = None if invoking else child_env
        try:
            entries = _config_entries(inspection_cwd, env=inspection_env)
            owned = {key: [] for key in _OWNED_CONFIG}
            for scope, origin, key, value in entries:
                if not key.startswith(_HOOK_PREFIX):
                    continue
                if registered and key == _HOOK_PREFIX + "enabled":
                    continue
                if key in owned:
                    owned[key].append(value)
                if (not registered or key not in _OWNED_CONFIG
                    or not _common_config_entry(context, worktree, scope, origin)
                    or value != _OWNED_CONFIG[key]):
                    errors.append(f"project hook configuration conflicts: {key}: {worktree}: {origin}")
            for key, values in owned.items():
                if len(values) > 1:
                    errors.append(f"project hook configuration conflicts: {key}: duplicate values in {worktree}")
            if enabling:
                controls = [_HOOK_PREFIX + "enabled"] if registered else []
                # Event-wide controls arrived after the minimum native-hook version.
                if any(key == "hook.post-checkout.enabled" for _, _, key, _ in entries):
                    if _require_git_version() >= (2, 55):
                        controls.append("hook.post-checkout.enabled")
                for key in controls:
                    if _config_disabled(inspection_cwd, key, env=inspection_env):
                        errors.append(f"project hook is disabled: {key}: {worktree}")
                if all(owned[key] == [value] for key, value in _OWNED_CONFIG.items()):
                    if not _hook_listed(inspection_cwd, env=inspection_env):
                        errors.append(f"project hook is not enabled in effective hook listing: {worktree}")
        except OperationalError as error:
            errors.append(f"cannot inspect project hook in {worktree}: {error}")
    return tuple(dict.fromkeys(errors))


def hook_is_complete(context: GitProject, *, cwd=None):
    """Read whether the invoking worktree has both owned keys and an active hook.

    Call after hook_config_errors to distinguish allowed installation recovery
    state from healthy configuration during read-only project inspection.
    """
    cwd = context.current_root if cwd is None else Path(cwd)
    entries = _config_entries(cwd)
    for key, value in _OWNED_CONFIG.items():
        values = [setting for scope, origin, candidate, setting in entries
                  if candidate == key and _common_config_entry(
                      context, context.current_root, scope, origin)]
        if values != [value]:
            return False
    return _hook_listed(cwd)


def install_hook(context: GitProject, *, cwd=None):
    """Install command before event in repository-local common config."""
    cwd = context.current_root if cwd is None else Path(cwd)
    for key, value in _OWNED_CONFIG.items():
        _git(cwd, "config", "--local", key, value)


def remove_hook(context: GitProject, *, cwd=None):
    """Stop invocation before removing command; absent owned keys are accepted."""
    cwd = context.current_root if cwd is None else Path(cwd)
    for key in reversed(_OWNED_CONFIG):
        _git(cwd, "config", "--local", "--unset-all", key,
             allowed=(0, 5))


def enable(root: Path, name: str, cwd: Path):
    """Record desired clone-wide enablement after all known checks pass."""
    validate_name(name)
    context = discover(cwd)
    validate_layout(root)
    validate_set(root, name)
    names = read_names(context.common_dir)
    errors = hook_config_errors(context, registered=names is not None, enabling=True, cwd=cwd)
    if errors:
        raise OperationalError("\n".join(errors))
    desired = tuple(sorted(set(names or ()) | {name}))
    from . import codex

    for desired_name in desired:
        validate_set(root, desired_name)
    for worktree in context.worktrees:
        codex.preflight_at(root, desired, worktree)
    write_names(context.common_dir, desired)
    install_hook(context, cwd=cwd)
    errors = []
    for worktree in context.worktrees:
        errors.extend(codex.reconcile_at(root, desired, worktree))
    return tuple(errors)


def disable(root: Path, name: str, cwd: Path):
    """Clear canonical links before removing the registered name."""
    validate_name(name)
    context = discover(cwd)
    names = read_names(context.common_dir)
    if names is None or name not in names:
        raise OperationalError(f"skillset is not project-enabled: {name!r}")
    errors = hook_config_errors(context, registered=True, enabling=False, cwd=cwd)
    if errors:
        raise OperationalError("\n".join(errors))
    from . import codex

    for worktree in context.worktrees:
        codex.preflight_at(root, (name,), worktree, removing=True)
    remaining = tuple(candidate for candidate in names if candidate != name)
    if not remaining:
        remove_hook(context, cwd=cwd)
    errors = []
    for worktree in context.worktrees:
        errors.extend(codex.reconcile_at(root, (name,), worktree, removing=True))
    if not errors:
        write_names(context.common_dir, remaining)
    return tuple(errors)


def run_hook(root: Path, old: str, new: str, flag: str):
    """Reconcile current desired sources only in the invoking worktree."""
    if flag not in {"0", "1"}:
        raise OperationalError(f"invalid project checkout flag: {flag!r}; expected 0 or 1")
    if flag == "0":
        return ()
    context = discover(Path.cwd(), inventory=False)
    names = read_names(context.common_dir)
    if names is None:
        return ()
    from .codex import preflight_at, reconcile_at
    from .layout import validate_set

    errors = []
    for name in names:
        try:
            validate_set(root, name)
            preflight_at(root, (name,), context.current_root)
            errors.extend(reconcile_at(root, (name,), context.current_root))
        except OperationalError as error:
            errors.append(str(error))
    return tuple(errors)


@dataclass(frozen=True)
class SourceView:
    name: str
    manual: bool
    entries: tuple
    error: object


@dataclass(frozen=True)
class ProjectInspection:
    sources: tuple
    errors: tuple


def inspect(root: Path, cwd: Path, *, full=False) -> ProjectInspection:
    """Inspect desired names and optionally every projection, without repair."""
    from . import codex
    from .layout import lexists, set_mode, validate_skillsets_directory
    from .metadata import printable_text, verbose_skill_entries

    context = discover(cwd, required=full, inventory=False)
    if context is None:
        return ProjectInspection((), ())
    errors = []
    try:
        names = read_names(context.common_dir)
    except OperationalError as error:
        return ProjectInspection((), (printable_text(error),))
    sources = []
    for name in names or ():
        try:
            validate_skillsets_directory(root)
            path = validate_set(root, name)
            manual = set_mode(root, name) == "manual"
            entries = tuple(verbose_skill_entries(path / "skills"))
            sources.append(SourceView(name, manual, entries, None))
        except (OperationalError, OSError) as error:
            reason = printable_text(error)
            sources.append(SourceView(name, False, (), reason))
            # Brief overview carries the invalid annotation. Health is explicit.
            if full:
                errors.append(f"invalid project source {name!r}: {reason}")
    if full:
        try:
            context, inventory_errors = _inspect_worktrees(context, cwd=cwd)
            # Accessible siblings still need orphan-hook inspection, but stale
            # inventory cannot make an unregistered clone unhealthy.
            if names is not None:
                errors.extend(inventory_errors)
        except OperationalError as error:
            errors.append(str(error))
        try:
            errors.extend(hook_config_errors(
                context, registered=names is not None, enabling=True, cwd=cwd
            ))
        except OperationalError as error:
            errors.append(f"cannot inspect project hook: {error}")
        if names is not None:
            try:
                if not hook_is_complete(context, cwd=cwd):
                    errors.append("project hook is incomplete; rerun project enable")
            except OperationalError as error:
                errors.append(f"cannot inspect project hook: {error}")
            for worktree in context.worktrees or (context.current_root,):
                try:
                    skills = codex.skills_directory_at(worktree, strict=True)
                except OperationalError as error:
                    errors.append(str(error))
                    continue
                for name in names:
                    link = worktree / ".codex" / "skills" / name
                    try:
                        if codex.canonical_link_at(root, name, worktree, strict=True):
                            continue
                    except OperationalError as error:
                        errors.append(str(error))
                        continue
                    if skills is not None and lexists(link):
                        errors.append(f"Codex skillset entry already exists: {link}")
                    else:
                        errors.append(f"project link is missing: {link}")
    return ProjectInspection(tuple(sources), tuple(printable_text(error) for error in errors))
