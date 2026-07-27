import fcntl
import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path

from .errors import OperationalError


EMPTY_LOCK = {"version": 3, "skills": {}, "dismissed": {}}
NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*\Z")
CONFIG_NAME = "config.json"
CONFIG_VERSION = 1
CONFIG_KEYS = {"version", "skillsets_directory"}
MANUAL_MARKER = ".skillset-manual"
MANUAL_SENTINEL_NAME = ".skillset-manual-empty-lock.json"
MANUAL_SENTINEL = f"../{MANUAL_SENTINEL_NAME}"
USE_STAGING = ".skillset-use.staging"


def lexists(path):
    return os.path.lexists(path)


def real_kind(path, expected):
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    if stat.S_ISLNK(mode):
        return False
    return expected(mode)


def validate_name(name):
    if not NAME_PATTERN.fullmatch(name):
        raise OperationalError(
            f"invalid skillset name {name!r}; use lowercase letters, digits, '_' or '-'"
        )


def configured_skillsets_directory(root):
    """Return the configured external skillsets directory, or None."""
    config = root / CONFIG_NAME
    if not lexists(config):
        return None
    if not real_kind(config, stat.S_ISREG):
        raise OperationalError(f"config must be a real regular file: {config}")
    try:
        contents = config.read_text(encoding="utf-8")
        value = json.loads(contents)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise OperationalError(f"invalid config {config}: {error}") from error
    if not isinstance(value, dict) or set(value) != CONFIG_KEYS:
        raise OperationalError(
            f"config must contain exactly 'version' and "
            f"'skillsets_directory': {config}"
        )
    if type(value["version"]) is not int or value["version"] != CONFIG_VERSION:
        raise OperationalError(
            f"config must use integer version {CONFIG_VERSION}: {config}"
        )
    serialized = value["skillsets_directory"]
    if not isinstance(serialized, str) or not serialized or "\0" in serialized:
        raise OperationalError(
            f"configured skillsets directory must be a nonempty absolute path: {config}"
        )
    normalized = os.path.normpath(serialized)
    if not os.path.isabs(serialized) or serialized != normalized:
        raise OperationalError(
            f"configured skillsets directory must be a normalized absolute path: {config}"
        )
    source = Path(normalized)
    managed_root = Path(os.path.normpath(os.fspath(root)))
    if source == managed_root or managed_root in source.parents:
        raise OperationalError(
            f"configured skillsets directory must be outside the managed root: {source}"
        )
    if not real_kind(source, stat.S_ISDIR):
        raise OperationalError(
            f"configured skillsets directory must be an existing real directory: {source}"
        )
    try:
        resolved_source = source.resolve(strict=True)
        resolved_root = managed_root.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise OperationalError(
            f"could not resolve configured skillsets directory {source}: {error}"
        ) from error
    if resolved_source == resolved_root or resolved_root in resolved_source.parents:
        raise OperationalError(
            f"configured skillsets directory must resolve outside the managed root: {source}"
        )
    return source


def validate_skillsets_directory(root):
    """Validate the managed container and return its real storage directory."""
    skillsets = root / "skillsets"
    configured = configured_skillsets_directory(root)
    if configured is None:
        try:
            mode = skillsets.lstat().st_mode
        except FileNotFoundError as error:
            raise OperationalError(
                f"skillsets directory is missing: {skillsets}"
            ) from error
        except OSError as error:
            raise OperationalError(
                f"could not inspect skillsets directory {skillsets}: {error}"
            ) from error
        if stat.S_ISLNK(mode):
            raise OperationalError(
                f"skillsets directory symlink is not allowed: {skillsets}"
            )
        if not stat.S_ISDIR(mode):
            raise OperationalError(
                f"skillsets must be a real directory: {skillsets}"
            )
        return skillsets
    try:
        mode = skillsets.lstat().st_mode
    except FileNotFoundError as error:
        raise OperationalError(
            f"configured skillsets link is missing: {skillsets} -> {configured}"
        ) from error
    except OSError as error:
        raise OperationalError(
            f"could not inspect skillsets directory {skillsets}: {error}"
        ) from error
    if not stat.S_ISLNK(mode):
        raise OperationalError(
            f"configured skillsets link must be a symlink: {skillsets} -> {configured}"
        )
    try:
        target = os.readlink(skillsets)
    except OSError as error:
        raise OperationalError(
            f"could not read configured skillsets link {skillsets}: {error}"
        ) from error
    if target != os.fspath(configured):
        raise OperationalError(
            f"configured skillsets link is noncanonical: {skillsets} -> {target}; "
            f"expected {configured}"
        )
    return configured


def set_path(root, name):
    validate_name(name)
    skillsets = validate_skillsets_directory(root)
    path = skillsets / name
    if path.parent != skillsets:
        raise OperationalError(f"unsafe skillset path for {name!r}")
    return path


def read_lockfile(path):
    if not real_kind(path, stat.S_ISREG):
        raise OperationalError(f"lockfile must be a real regular file: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise OperationalError(f"invalid lockfile {path}: {error}") from error
    valid = (
        isinstance(value, dict)
        and type(value.get("version")) is int
        and value.get("version") == 3
        and isinstance(value.get("skills"), dict)
        and isinstance(value.get("dismissed"), dict)
    )
    if not valid:
        raise OperationalError(f"lockfile is not a version-3 global lockfile: {path}")
    return value


def validate_lockfile(path):
    read_lockfile(path)


def validate_manual_marker(path):
    if not real_kind(path, stat.S_ISREG):
        raise OperationalError(f"manual marker must be a real empty regular file: {path}")
    try:
        if path.stat().st_size != 0:
            raise OperationalError(f"manual marker must be empty: {path}")
    except OSError as error:
        raise OperationalError(f"could not inspect manual marker {path}: {error}") from error


def skillset_mode(path):
    """Validate a set path and return its explicit management mode."""
    if not real_kind(path, stat.S_ISDIR):
        raise OperationalError(f"skillset must be a real directory: {path}")
    skills = path / "skills"
    if not real_kind(skills, stat.S_ISDIR):
        raise OperationalError(f"skills must be a real directory: {skills}")
    marker = path / MANUAL_MARKER
    lockfile = path / ".skill-lock.json"
    if lexists(marker):
        validate_manual_marker(marker)
        if lexists(lockfile):
            raise OperationalError(
                f"manual skillset must not contain a lockfile: {lockfile}"
            )
        return "manual"
    validate_lockfile(lockfile)
    return "managed"


def validate_skillset_entries(skillsets):
    for entry in skillsets.iterdir():
        if entry.name.startswith(".skillset-create-") and entry.name.endswith(
            ".staging"
        ):
            raise OperationalError(
                f"stale create staging path must be recovered: {entry}"
            )
        if entry.name.startswith("."):
            continue
        validate_name(entry.name)
        skillset_mode(entry)


def set_mode(root, name):
    """Validate a named set and return its explicit management mode."""
    return skillset_mode(set_path(root, name))


def validate_set(root, name):
    set_mode(root, name)
    return set_path(root, name)


def manual_sentinel_path(root):
    return root.parent / MANUAL_SENTINEL_NAME


def validate_manual_sentinel(root):
    path = manual_sentinel_path(root)
    if not real_kind(path, stat.S_ISREG):
        raise OperationalError(f"manual empty-lock sentinel must be a real regular file: {path}")
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as error:
        raise OperationalError(f"could not inspect manual empty-lock sentinel {path}: {error}") from error
    if mode & 0o222:
        raise OperationalError(f"manual empty-lock sentinel must be read-only: {path}")
    value = read_lockfile(path)
    if value != EMPTY_LOCK:
        raise OperationalError(f"manual empty-lock sentinel is not canonical: {path}")
    return path


def ensure_manual_sentinel(root):
    path = manual_sentinel_path(root)
    if lexists(path):
        validate_manual_sentinel(root)
        return path
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(EMPTY_LOCK, handle)
            handle.write("\n")
        path.chmod(0o444)
    except OSError as error:
        raise OperationalError(f"could not create manual empty-lock sentinel {path}: {error}") from error
    validate_manual_sentinel(root)
    return path


def require_alias(path, target):
    if not path.is_symlink() or os.readlink(path) != target:
        raise OperationalError(f"managed alias must be {path} -> {target}")


def canonical_alias(path, target):
    try:
        return path.is_symlink() and os.readlink(path) == target
    except OSError:
        return False


def validate_active_set(root):
    active = root / "active"
    if not active.is_symlink():
        raise OperationalError(f"managed alias is missing or invalid: {active}")
    target = os.readlink(active)
    if not target.startswith("skillsets/"):
        raise OperationalError(f"active alias has a noncanonical target: {target}")
    active_name = target[len("skillsets/") :]
    validate_name(active_name)
    if target != f"skillsets/{active_name}":
        raise OperationalError(f"active alias has a noncanonical target: {target}")
    set_mode(root, active_name)
    return active_name


def validate_layout(root, repair_missing_manual_sentinel=False):
    skillsets = validate_skillsets_directory(root)
    use_staging = root / USE_STAGING
    if lexists(use_staging):
        raise OperationalError(
            f"stale active staging path must be recovered: {use_staging}"
        )
    require_alias(root / "skills", "active/skills")
    active_name = validate_active_set(root)
    active_mode = set_mode(root, active_name)
    if active_mode == "manual":
        if repair_missing_manual_sentinel and not lexists(manual_sentinel_path(root)):
            ensure_manual_sentinel(root)
        else:
            validate_manual_sentinel(root)
        require_alias(root / ".skill-lock.json", MANUAL_SENTINEL)
    else:
        require_alias(root / ".skill-lock.json", "active/.skill-lock.json")
    validate_skillset_entries(skillsets)
    return active_name


@contextmanager
def stable_home_lock(root):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(root.parent, flags)
    except OSError as error:
        raise OperationalError(
            f"HOME must be an existing real directory: {root.parent}: {error}"
        ) from error
    locked = False
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        locked = True
        yield descriptor
    finally:
        if locked:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


@contextmanager
def discovery_operation_lock(root):
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        root_descriptor = os.open(root, directory_flags)
    except OSError:
        yield None
        return
    try:
        try:
            lock_descriptor = os.open(
                ".skillset.lock",
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=root_descriptor,
            )
        except OSError:
            yield None
            return
        try:
            try:
                if not stat.S_ISREG(os.fstat(lock_descriptor).st_mode):
                    yield None
                    return
            except OSError:
                yield None
                return
            locked = False
            try:
                fcntl.flock(lock_descriptor, fcntl.LOCK_EX)
            except OSError:
                yield None
                return
            locked = True
            try:
                yield lock_descriptor
            finally:
                if locked:
                    fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
        finally:
            os.close(lock_descriptor)
    finally:
        os.close(root_descriptor)


@contextmanager
def operation_lock(root, create=True):
    if lexists(root) and not real_kind(root, stat.S_ISDIR):
        raise OperationalError(f"managed root must be a real directory: {root}")
    if create:
        root.mkdir(parents=True, exist_ok=True)
    elif not real_kind(root, stat.S_ISDIR):
        raise OperationalError(f"managed root must be a real directory: {root}")
    lock_path = root / ".skillset.lock"
    if not create and not real_kind(lock_path, stat.S_ISREG):
        raise OperationalError(f"advisory lock must be a real file: {lock_path}")
    if lexists(lock_path) and not real_kind(lock_path, stat.S_ISREG):
        raise OperationalError(f"advisory lock must be a real file: {lock_path}")
    mode = "a+" if create else "r"
    with lock_path.open(mode) as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield lock_file
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def inspect_advisory_lock_entry(lock_path, errors):
    try:
        metadata = lock_path.lstat()
    except FileNotFoundError:
        errors.append(f"advisory lock is missing: {lock_path}")
        return None
    except OSError as error:
        errors.append(f"could not inspect advisory lock {lock_path}: {error}")
        return None
    if stat.S_ISLNK(metadata.st_mode):
        errors.append(f"advisory lock symlink is not allowed: {lock_path}")
        return None
    if not stat.S_ISREG(metadata.st_mode):
        errors.append(f"advisory lock must be a real regular file: {lock_path}")
        return None
    return True


@contextmanager
def doctor_operation_lock(root, errors):
    lock_path = root / ".skillset.lock"
    if not inspect_advisory_lock_entry(lock_path, errors):
        yield None
        return
    try:
        descriptor = os.open(lock_path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:
        errors.append(f"could not open advisory lock {lock_path}: {error}")
        yield None
        return
    locked = False
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            errors.append(f"advisory lock must be a real regular file: {lock_path}")
            yield None
            return
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        locked = True
        yield descriptor
    finally:
        if locked:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def write_empty_lock(path):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(EMPTY_LOCK, handle)
        handle.write("\n")
