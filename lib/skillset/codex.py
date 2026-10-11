"""Manage named skillset links discovered by Codex."""

import os
import stat
from pathlib import Path

from .errors import OperationalError
from .layout import (
    NAME_PATTERN,
    lexists,
    real_kind,
    set_path,
    validate_layout,
    validate_name,
    validate_set,
)
from .metadata import list_named_sets, list_project_sources, list_scoped_sets


def expected_target(root, name):
    validate_name(name)
    return os.fspath((root / "skillsets" / name / "skills").absolute())


def _inspection_mode(path):
    """Distinguish absent project entries from ordinary inspection failures."""
    try:
        return path.lstat().st_mode
    except FileNotFoundError:
        return None
    except OSError as error:
        raise OperationalError(f"could not inspect Codex path {path}: {error}") from error


def skills_directory_at(worktree: Path, *, create=False, strict=False):
    """Find or create real Codex containers at the supplied directory."""
    codex = worktree / ".codex"
    skills = codex / "skills"
    for directory in (codex, skills):
        mode = _inspection_mode(directory) if strict else None
        exists = mode is not None if strict else lexists(directory)
        if exists:
            is_directory = stat.S_ISDIR(mode) if strict else real_kind(directory, stat.S_ISDIR)
            if not is_directory:
                raise OperationalError(
                    f"Codex skills container must be a real directory: {directory}"
                )
            continue
        if not create:
            return None
        try:
            directory.mkdir()
        except OSError as error:
            raise OperationalError(
                f"could not create Codex skills container {directory}: {error}"
            ) from error
    return skills


def _scope_directory(root, scope):
    return root.parent if scope == "global" else Path.cwd()


def codex_skills_directory(root, scope, create):
    return skills_directory_at(_scope_directory(root, scope), create=create)


def canonical_link_at(root: Path, name: str, worktree: Path, *, strict=False):
    skills = skills_directory_at(worktree, strict=strict)
    if skills is None:
        return False
    link = skills / name
    if strict:
        mode = _inspection_mode(link)
        if mode is None or not stat.S_ISLNK(mode):
            return False
    try:
        target = os.readlink(link)
        return (
            (strict or link.is_symlink())
            and os.path.isabs(target)
            and os.path.normpath(target) == expected_target(root, name)
        )
    except OSError as error:
        if strict:
            raise OperationalError(f"could not inspect Codex link {link}: {error}") from error
        return False


def canonical_link(root, name, scope="global"):
    return canonical_link_at(root, name, _scope_directory(root, scope))


def preflight_at(root: Path, names: tuple, worktree: Path, *, removing=False):
    """Check destination shapes without validating sources or creating paths."""
    for name in names:
        validate_name(name)
    skills = skills_directory_at(worktree, strict=True)
    if skills is None or removing:
        return
    for name in names:
        link = skills / name
        if lexists(link) and not canonical_link_at(root, name, worktree):
            raise OperationalError(f"Codex skillset entry already exists: {link}")


def reconcile_at(root: Path, names: tuple, worktree: Path, *, removing=False):
    """Reconcile named links, retaining completed work after ordinary errors.

    Source/layout validation belongs to callers so removal also works after
    a collection has disappeared. Returned messages identify affected paths.
    """
    for name in names:
        validate_name(name)
    try:
        skills = skills_directory_at(worktree, create=not removing, strict=True)
    except OperationalError as error:
        return (str(error),)
    if skills is None:
        return ()
    errors = []
    for name in names:
        link = skills / name
        if removing:
            try:
                if not canonical_link_at(root, name, worktree, strict=True):
                    continue
                link.unlink()
            except OperationalError as error:
                errors.append(str(error))
            except OSError as error:
                errors.append(
                    f"could not disable Codex skillset {name!r}: {link}: {error}"
                )
        else:
            if lexists(link):
                if not canonical_link_at(root, name, worktree):
                    errors.append(f"Codex skillset entry already exists: {link}")
                continue
            try:
                os.symlink(expected_target(root, name), link)
            except OSError as error:
                errors.append(
                    f"could not enable Codex skillset {name!r}: {link}: {error}"
                )
    return tuple(errors)


def enable(root, name, scope):
    if scope == "project":
        from . import project

        return project.enable(root, name, Path.cwd())
    validate_name(name)
    validate_layout(root)
    validate_set(root, name)
    skills = codex_skills_directory(root, scope, create=True)
    link = skills / name
    target = expected_target(root, name)
    if lexists(link):
        if canonical_link(root, name, scope):
            return
        raise OperationalError(f"Codex skillset entry already exists: {link}")
    try:
        os.symlink(target, link)
    except OSError as error:
        raise OperationalError(
            f"could not enable Codex skillset {name!r}: {error}"
        ) from error


def disable(root, name, scope):
    if scope == "project":
        from . import project

        return project.disable(root, name, Path.cwd())
    validate_name(name)
    validate_layout(root)
    skills = codex_skills_directory(root, scope, create=False)
    link = None if skills is None else skills / name
    if link is None or not canonical_link(root, name, scope):
        raise OperationalError(f"skillset is not Codex-enabled: {name!r}")
    try:
        link.unlink()
    except OSError as error:
        raise OperationalError(
            f"could not disable Codex skillset {name!r}: {error}"
        ) from error


def enabled_names(root, scope):
    skills = codex_skills_directory(root, scope, create=False)
    if skills is None:
        return []
    names = []
    for entry in skills.iterdir():
        if not NAME_PATTERN.fullmatch(entry.name) or not canonical_link(
            root, entry.name, scope
        ):
            continue
        try:
            validate_set(root, entry.name)
        except OperationalError:
            continue
        names.append(entry.name)
    return sorted(names)


def list_enabled(root, verbose, scope):
    if scope == "project":
        from .project import inspect

        inspection = inspect(root, Path.cwd(), full=True)
        if inspection.sources:
            list_named_sets(
                root, (), verbose, mark_active=False, sources=inspection.sources
            )
        return inspection.errors
    try:
        validate_layout(root)
    except OperationalError as error:
        if scope != "all":
            raise
        from .project import inspect

        inspection = inspect(root, Path.cwd())
        if inspection.sources:
            list_project_sources(inspection.sources, verbose, scoped=True)
        return (str(error), *inspection.errors)
    if scope == "all":
        global_skills = codex_skills_directory(root, "global", create=False)
        local_skills = codex_skills_directory(root, "local", create=False)
        local_names = (
            []
            if global_skills is not None and global_skills == local_skills
            else enabled_names(root, "local")
        )
        from .project import inspect

        inspection = inspect(root, Path.cwd())
        project_names = {source.name for source in inspection.sources}
        list_scoped_sets(
            root,
            (("g", enabled_names(root, "global")),
             ("p", [source.name for source in inspection.sources]),
             ("l", [name for name in local_names if name not in project_names])),
            verbose,
            sources=inspection.sources,
        )
        return inspection.errors
    return list_named_sets(
        root,
        enabled_names(root, scope),
        verbose,
        mark_active=False,
    )
