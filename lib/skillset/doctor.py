import os
import stat
import sys
import json

from .errors import OperationalError
from .layout import (
    NAME_PATTERN,
    configured_skillsets_directory,
    doctor_operation_lock,
    ensure_manual_sentinel,
    lexists,
    MANUAL_MARKER,
    MANUAL_SENTINEL,
    manual_sentinel_path,
    operation_lock,
    read_lockfile,
    real_kind,
    set_mode,
    skillset_mode,
    USE_STAGING,
    validate_manual_sentinel,
    validate_skillsets_directory,
    write_empty_lock,
)
from .metadata import parse_frontmatter, printable_text, read_skill_text


def doctor_alias(path, target, errors):
    if not lexists(path):
        errors.append(f"managed alias is missing: {path}")
        return
    if not path.is_symlink():
        errors.append(f"managed alias must be a symlink: {path} -> {target}")
        return
    try:
        actual = os.readlink(path)
    except OSError as error:
        errors.append(f"could not read managed alias {path}: {error}")
        return
    if actual != target:
        errors.append(
            f"managed alias is noncanonical: {path} -> {actual}; expected {target}"
        )


def inspect_lockfile_entry(path, errors):
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        errors.append(f"lockfile is missing: {path}")
        return False
    except OSError as error:
        errors.append(f"could not inspect lockfile {path}: {error}")
        return False
    if stat.S_ISLNK(mode):
        errors.append(f"lockfile symlink is not allowed: {path}")
        return False
    if not stat.S_ISREG(mode):
        errors.append(f"lockfile must be a real regular file: {path}")
        return False
    return True


def doctor_lockfile(path, errors):
    if not inspect_lockfile_entry(path, errors):
        return None
    try:
        return read_lockfile(path)
    except OperationalError as error:
        errors.append(str(error))
        return None
    except Exception as error:
        errors.append(f"could not read lockfile {path}: {error}")
        return None


def doctor_manual_marker(path, errors):
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return False
    except OSError as error:
        errors.append(f"could not inspect manual marker {path}: {error}")
        return False
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        errors.append(f"manual marker must be a real empty regular file: {path}")
        return False
    try:
        if path.stat().st_size != 0:
            errors.append(f"manual marker must be empty: {path}")
            return False
    except OSError as error:
        errors.append(f"could not inspect manual marker {path}: {error}")
        return False
    return True


def classify_skill_entry(candidate, set_name, errors):
    try:
        mode = candidate.lstat().st_mode
    except OSError as error:
        errors.append(f"could not inspect skill {candidate}: {error}")
        return None
    if stat.S_ISREG(mode):
        return None
    if stat.S_ISLNK(mode):
        errors.append(
            f"skill directory symlink is not allowed in {set_name!r}: {candidate}"
        )
        return None
    if not stat.S_ISDIR(mode):
        errors.append(f"unsupported skill entry type in {set_name!r}: {candidate}")
        return None
    return candidate


def inspect_skill_metadata(candidate, set_name, errors):
    try:
        text, reason = read_skill_text(candidate)
        if reason is None:
            _metadata, reason = parse_frontmatter(text)
    except Exception as error:
        errors.append(f"could not inspect skill metadata {candidate}: {error}")
        return
    if reason is not None:
        errors.append(f"invalid skill metadata in {set_name!r}/{candidate.name}: {reason}")


def doctor_skills(skills, set_name, errors):
    installed = set()
    try:
        candidates = sorted(skills.iterdir(), key=lambda path: path.name)
    except OSError as error:
        errors.append(f"could not inspect skills directory {skills}: {error}")
        return None
    for candidate in candidates:
        directory = classify_skill_entry(candidate, set_name, errors)
        if directory is None:
            continue
        installed.add(directory.name)
        inspect_skill_metadata(directory, set_name, errors)
    return installed


def doctor_skills_directory(path, name, errors):
    skills = path / "skills"
    try:
        skills_mode = skills.lstat().st_mode
    except FileNotFoundError:
        errors.append(f"skills directory is missing: {skills}")
    except OSError as error:
        errors.append(f"could not inspect skills directory {skills}: {error}")
    else:
        if stat.S_ISLNK(skills_mode):
            errors.append(f"skills directory symlink is not allowed: {skills}")
        elif not stat.S_ISDIR(skills_mode):
            errors.append(f"skills must be a real directory: {skills}")
        else:
            return doctor_skills(skills, name, errors)
    return None


def doctor_skill_inventory(name, installed, lock, warnings):
    locked = set(lock["skills"])
    for skill_name in sorted(installed - locked):
        warnings.append(
            f"installed skill directory {skill_name!r} in {name!r} is missing from the lockfile"
        )
    for skill_name in sorted(locked - installed):
        warnings.append(
            f"lockfile skill {skill_name!r} in {name!r} has no real direct skill directory"
        )


def doctor_set(path, name, errors, warnings):
    try:
        mode = path.lstat().st_mode
    except OSError as error:
        errors.append(f"could not inspect skillset {name!r} at {path}: {error}")
        return None
    if stat.S_ISLNK(mode):
        errors.append(f"skillset directory symlink is not allowed: {path}")
        return None
    if not stat.S_ISDIR(mode):
        errors.append(f"skillset must be a real directory: {path}")
        return None

    installed = doctor_skills_directory(path, name, errors)
    marker = path / MANUAL_MARKER
    lockfile = path / ".skill-lock.json"
    marker_exists = lexists(marker)
    if marker_exists:
        marker_valid = doctor_manual_marker(marker, errors)
        if lexists(lockfile):
            errors.append(f"manual skillset must not contain a lockfile: {lockfile}")
        if installed is None or not marker_valid or lexists(lockfile):
            return None
        return "manual"
    lock = doctor_lockfile(lockfile, errors)
    if installed is None or lock is None:
        return None
    doctor_skill_inventory(name, installed, lock, warnings)
    return "managed"


def doctor_skillsets_directory(root, errors):
    try:
        return validate_skillsets_directory(root)
    except OperationalError as error:
        errors.append(str(error))
        return None


def doctor_active_alias(active, skillsets, skillsets_valid, errors):
    if not lexists(active):
        errors.append(f"managed active alias is missing: {active}")
        return None
    elif not active.is_symlink():
        errors.append(f"managed active alias must be a symlink: {active}")
        return None
    else:
        try:
            target = os.readlink(active)
        except OSError as error:
            errors.append(f"could not read managed active alias {active}: {error}")
            return None
        else:
            prefix = "skillsets/"
            candidate = target[len(prefix) :] if target.startswith(prefix) else ""
            if not NAME_PATTERN.fullmatch(candidate) or target != prefix + candidate:
                errors.append(
                    f"active alias has a noncanonical target; expected skillsets/NAME: {target}"
                )
                return None
            elif skillsets_valid and not lexists(skillsets / candidate):
                errors.append(f"active target is missing: {active} -> {target}")
                return None
            elif not skillsets_valid:
                return None
            else:
                return candidate
    return None


def doctor_skillset_entries(skillsets, errors, warnings):
    try:
        entries = sorted(skillsets.iterdir(), key=lambda path: path.name)
    except OSError as error:
        errors.append(f"could not inspect skillsets directory {skillsets}: {error}")
        return
    for entry in entries:
        if entry.name.startswith(".skillset-create-") and entry.name.endswith(
            ".staging"
        ):
            errors.append(f"stale create staging path must be recovered: {entry}")
            continue
        if entry.name.startswith("."):
            continue
        if not NAME_PATTERN.fullmatch(entry.name):
            errors.append(
                f"invalid skillset name {entry.name!r} at {entry}; "
                "use lowercase letters, digits, '_' or '-'"
            )
        doctor_set(entry, entry.name, errors, warnings)


def canonical_use_record(record):
    return json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"


def valid_active_target(target):
    prefix = "skillsets/"
    name = target[len(prefix) :] if isinstance(target, str) and target.startswith(prefix) else ""
    return target == prefix + name and bool(NAME_PATTERN.fullmatch(name))


def read_use_staging(root, errors=None):
    path = root / USE_STAGING
    if not real_kind(path, stat.S_ISREG):
        if errors is not None:
            errors.append(f"stale activation staging record must be a real regular file: {path}")
        return None
    try:
        contents = path.read_text(encoding="utf-8")
        record = json.loads(contents)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        if errors is not None:
            errors.append(f"stale activation staging record is invalid {path}: {error}")
        return None
    if (
        not isinstance(record, dict)
        or record.get("version") != 1
        or set(record) != {"version", "old", "new"}
        or not all(isinstance(record.get(key), dict) and set(record[key]) == {"active", "lock"}
                   for key in ("old", "new"))
        or any(not isinstance(record[key][field], str)
               for key in ("old", "new") for field in ("active", "lock"))
        or contents != canonical_use_record(record)
    ):
        if errors is not None:
            errors.append(f"stale activation staging record is malformed or noncanonical: {path}")
        return None
    for side in ("old", "new"):
        active = record[side]["active"]
        lock = record[side]["lock"]
        if not valid_active_target(active) or lock not in {"active/.skill-lock.json", MANUAL_SENTINEL}:
            if errors is not None:
                errors.append(f"stale activation staging record is malformed or noncanonical: {path}")
            return None
        name = active[len("skillsets/") :]
        try:
            expected_lock = MANUAL_SENTINEL if set_mode(root, name) == "manual" else "active/.skill-lock.json"
        except OperationalError as error:
            if errors is not None:
                errors.append(f"stale activation staging target is invalid for {name!r}: {error}")
            return None
        if lock != expected_lock:
            if errors is not None:
                errors.append(f"stale activation staging record has a mode-mismatched lock target: {path}")
            return None
    for alias, field in ((root / "active", "active"), (root / ".skill-lock.json", "lock")):
        if not alias.is_symlink():
            if errors is not None:
                errors.append(f"stale activation staging cannot recover non-symlink alias: {alias}")
            return None
        try:
            actual = os.readlink(alias)
        except OSError as error:
            if errors is not None:
                errors.append(f"could not read stale activation alias {alias}: {error}")
            return None
        if actual not in {record["old"][field], record["new"][field]}:
            if errors is not None:
                errors.append(f"stale activation staging has an unknown alias target: {alias} -> {actual}")
            return None
    return record


def replace_recovery_alias(root, name, target):
    destination = root / name
    temporary = root / f".{name.lstrip('.')}.skillset-recovery-link.staging"
    try:
        os.symlink(target, temporary)
        os.replace(temporary, destination)
    finally:
        if lexists(temporary):
            try:
                temporary.unlink()
            except OSError:
                pass


def recover_staged_use(root):
    errors = []
    record = read_use_staging(root, errors)
    if record is None:
        raise OperationalError("; ".join(errors))
    try:
        if record["new"]["lock"] == MANUAL_SENTINEL:
            validate_manual_sentinel(root)
        replace_recovery_alias(root, "active", record["new"]["active"])
        replace_recovery_alias(root, ".skill-lock.json", record["new"]["lock"])
        active = root / "active"
        lock = root / ".skill-lock.json"
        if not (
            active.is_symlink()
            and lock.is_symlink()
            and os.readlink(active) == record["new"]["active"]
            and os.readlink(lock) == record["new"]["lock"]
        ):
            raise OperationalError("activation aliases did not reach their intended targets")
        (root / USE_STAGING).unlink()
    except OperationalError:
        raise
    except Exception as error:
        raise OperationalError(
            f"could not complete interrupted activation; staging was retained at {root / USE_STAGING}: {error}"
        ) from error


def doctor_inspection(root, errors, warnings):
    skillsets = doctor_skillsets_directory(root, errors)
    skillsets_valid = skillsets is not None
    if skillsets is None:
        skillsets = root / "skillsets"

    doctor_alias(root / "skills", "active/skills", errors)
    active_name = doctor_active_alias(root / "active", skillsets, skillsets_valid, errors)
    if active_name is None:
        doctor_alias(root / ".skill-lock.json", "active/.skill-lock.json", errors)
    else:
        active_path = skillsets / active_name
        manual = lexists(active_path / MANUAL_MARKER)
        lock_target = MANUAL_SENTINEL if manual else "active/.skill-lock.json"
        doctor_alias(root / ".skill-lock.json", lock_target, errors)
        if manual:
            try:
                validate_manual_sentinel(root)
            except OperationalError as error:
                errors.append(str(error))

    use_staging = root / USE_STAGING
    if lexists(use_staging):
        staging_errors = []
        if read_use_staging(root, staging_errors) is None:
            errors.extend(staging_errors)
        else:
            errors.append(f"interrupted activation must be completed: {use_staging}")

    if skillsets_valid:
        doctor_skillset_entries(skillsets, errors, warnings)


def doctor_findings(root):
    errors = []
    warnings = []
    try:
        root_mode = root.lstat().st_mode
    except FileNotFoundError:
        root_mode = None
    except OSError as error:
        errors.append(f"could not inspect managed root {root}: {error}")
        root_mode = False
    if root_mode is not None and (
        root_mode is False
        or stat.S_ISLNK(root_mode)
        or not stat.S_ISDIR(root_mode)
    ):
        if root_mode is not False:
            errors.append(f"managed root must be a real directory: {root}")
    else:
        with doctor_operation_lock(root, errors):
            doctor_inspection(root, errors, warnings)
    return errors, warnings


def repairable_active_names(root):
    """Return valid configured skillsets that can be selected interactively."""
    try:
        skillsets = configured_skillsets_directory(root)
    except OperationalError:
        return []
    if skillsets is None:
        return []
    link = root / "skillsets"
    if lexists(link):
        try:
            validate_skillsets_directory(root)
        except OperationalError:
            return []
    try:
        entries = sorted(skillsets.iterdir(), key=lambda path: path.name)
    except OSError:
        return []
    names = []
    for entry in entries:
        if not NAME_PATTERN.fullmatch(entry.name):
            continue
        try:
            skillset_mode(entry)
        except OperationalError:
            continue
        names.append(entry.name)
    return names


def select_active_repair(root):
    names = repairable_active_names(root)
    if not names:
        return None
    print("Select the active skillset to restore:", file=sys.stderr)
    for name in names:
        print(f"  {name}", file=sys.stderr)
    print("Active skillset (blank to cancel): ", end="", file=sys.stderr, flush=True)
    selected = sys.stdin.readline().strip()
    return selected if selected in names else None


def safe_repair_candidates(root, active_name=None):
    """Return missing entries that can be recreated without guessing metadata."""
    if not real_kind(root, stat.S_ISDIR):
        return []

    advisory_lock = root / ".skillset.lock"
    if lexists(advisory_lock) and not real_kind(advisory_lock, stat.S_ISREG):
        return []

    candidates = []
    if not lexists(advisory_lock):
        candidates.append((advisory_lock, None))

    skillsets_link = root / "skillsets"
    try:
        configured = configured_skillsets_directory(root)
    except OperationalError:
        return candidates
    if configured is not None and not lexists(skillsets_link):
        skillsets = configured
        candidates.append((skillsets_link, os.fspath(configured)))
    else:
        try:
            skillsets = validate_skillsets_directory(root)
        except OperationalError:
            return candidates
    try:
        entries = sorted(skillsets.iterdir(), key=lambda path: path.name)
    except OSError:
        return candidates
    active = root / "active"
    if active_name is None and active.is_symlink():
        try:
            target = os.readlink(active)
            prefix = "skillsets/"
            active_name = target[len(prefix) :] if target.startswith(prefix) else ""
            if target == prefix + active_name and NAME_PATTERN.fullmatch(active_name):
                skillset_mode(skillsets / active_name)
        except (OSError, OperationalError):
            active_name = None
    if active_name is not None:
        try:
            mode = skillset_mode(skillsets / active_name)
        except OperationalError:
            active_name = None
        else:
            if not lexists(active):
                candidates.append((active, f"skillsets/{active_name}"))
            skills_alias = root / "skills"
            if not lexists(skills_alias):
                candidates.append((skills_alias, "active/skills"))
            lock_alias = root / ".skill-lock.json"
            lock_target = MANUAL_SENTINEL if mode == "manual" else "active/.skill-lock.json"
            if not lexists(lock_alias):
                candidates.append((lock_alias, lock_target))
            if mode == "manual":
                sentinel = manual_sentinel_path(root)
                if not lexists(sentinel):
                    candidates.append((sentinel, None))
    for entry in entries:
        if not NAME_PATTERN.fullmatch(entry.name) or not real_kind(entry, stat.S_ISDIR):
            continue
        skills = entry / "skills"
        marker = entry / MANUAL_MARKER
        lockfile = entry / ".skill-lock.json"
        if (
            not real_kind(skills, stat.S_ISDIR)
            or lexists(marker)
            or lexists(lockfile)
        ):
            continue
        try:
            if any(skills.iterdir()):
                continue
        except OSError:
            continue
        candidates.append((lockfile, None))
    return candidates


def confirm_repairs(candidates):
    print("Create these safe replacement files?", file=sys.stderr)
    for candidate, _target in candidates:
        print(f"  {candidate}", file=sys.stderr)
    print("Proceed? [y/N] ", end="", file=sys.stderr, flush=True)
    return sys.stdin.readline().strip().lower() in {"y", "yes"}


def repair_candidates(root, active_name):
    repaired = []
    for candidate, target in safe_repair_candidates(root, active_name):
        if target is not None:
            try:
                os.symlink(target, candidate)
            except FileExistsError:
                continue
            except OSError as error:
                raise OperationalError(
                    f"could not create replacement alias {candidate}: {error}"
                ) from error
            repaired.append(candidate)
            continue
        if candidate == manual_sentinel_path(root):
            try:
                ensure_manual_sentinel(root)
            except OperationalError:
                raise
            repaired.append(candidate)
            continue
        if candidate.name != ".skill-lock.json":
            continue
        try:
            write_empty_lock(candidate)
        except FileExistsError:
            continue
        except OSError as error:
            raise OperationalError(
                f"could not create replacement lockfile {candidate}: {error}"
            ) from error
        repaired.append(candidate)
    return repaired


def emit_findings(errors, warnings):
    for message in sorted(errors):
        print(f"skillset: error: {printable_text(message)}", file=sys.stderr)
    for message in sorted(warnings):
        print(f"skillset: warning: {printable_text(message)}", file=sys.stderr)


def doctor(root, fix=False):
    errors, warnings = doctor_findings(root)
    if not fix:
        emit_findings(errors, warnings)
        return 1 if errors else 0

    staged_errors = []
    staged = read_use_staging(root, staged_errors) if lexists(root / USE_STAGING) else None
    if staged is not None:
        print("Complete the verified interrupted activation? [y/N] ", end="", file=sys.stderr, flush=True)
        if sys.stdin.readline().strip().lower() not in {"y", "yes"}:
            emit_findings(errors, warnings)
            return 1
        with operation_lock(root, create=False):
            recover_staged_use(root)
        errors, warnings = doctor_findings(root)

    active_name = None
    if not lexists(root / "active"):
        active_name = select_active_repair(root)
        if active_name is None:
            emit_findings(errors, warnings)
            return 1 if errors else 0

    candidates = safe_repair_candidates(root, active_name)
    if not candidates or not confirm_repairs(candidates):
        emit_findings(errors, warnings)
        return 1 if errors else 0

    advisory_lock = root / ".skillset.lock"
    advisory_was_missing = any(candidate == advisory_lock for candidate, _ in candidates)
    with operation_lock(root, create=True):
        repaired = repair_candidates(root, active_name)
        errors = []
        warnings = []
        doctor_inspection(root, errors, warnings)
    if advisory_was_missing and real_kind(advisory_lock, stat.S_ISREG):
        repaired.insert(0, advisory_lock)
    for candidate in repaired:
        print(f"skillset: repaired: created {candidate}", file=sys.stderr)
    emit_findings(errors, warnings)
    return 1 if errors else 0
