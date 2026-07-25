"""Manage flattened skillset projections discovered by Auggie."""

import os
import stat
import uuid
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from errno import EINVAL
from pathlib import Path

from .errors import ClaudeInterrupted, ManualRecoveryError, OperationalError
from .layout import (
    NAME_PATTERN,
    lexists,
    real_kind,
    set_path,
    validate_layout,
    validate_name,
    validate_set,
)
from .metadata import list_named_sets, list_scoped_sets


DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
REMOVAL_PREFIX = ".skillset-removal-"
REMOVAL_ENTRY = "entry"


@dataclass(frozen=True)
class GlobalRegistrationBlocker:
    path: Path
    enabled: bool
    incomplete_projection: bool = False


def expected_target(root, name):
    try:
        return os.fspath((set_path(root, name) / "skills").resolve(strict=False))
    except (OSError, RuntimeError) as error:
        raise OperationalError(
            f"could not resolve Auggie skillset target for {name!r}: {error}"
        ) from error


def scope_paths(root, scope):
    augment = (
        root.parent / ".augment" if scope == "global" else Path.cwd() / ".augment"
    )
    return augment, augment / "skills", augment / ".skillsets"


def scope_option(scope):
    return "" if scope == "global" else " --local"


def opposite_scope(scope):
    return "local" if scope == "global" else "global"


def validate_projection_root(source_path, scope):
    if scope != "local":
        return
    projection_root = Path.cwd() / ".augment"
    try:
        resolved_source = source_path.resolve(strict=True)
        resolved_projection = projection_root.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise OperationalError(
            "could not resolve Auggie local projection containment: "
            f"{error}"
        ) from error
    if (
        resolved_source == resolved_projection
        or resolved_source in resolved_projection.parents
    ):
        raise OperationalError(
            "Auggie local projection must not be rooted inside its "
            f"skill source: {projection_root} is inside {source_path}"
        )


def canonical_target(target, expected):
    return os.path.isabs(target) and target.rstrip("/") == expected


def canonical_link_at(directory_fd, name, target):
    try:
        metadata = os.stat(
            name, dir_fd=directory_fd, follow_symlinks=False
        )
    except FileNotFoundError:
        return False
    except OSError as error:
        raise OperationalError(
            f"could not inspect Auggie entry {name!r}: {error}"
        ) from error
    if not stat.S_ISLNK(metadata.st_mode):
        return False
    try:
        link_target = os.readlink(name, dir_fd=directory_fd)
    except FileNotFoundError:
        return False
    except OSError as error:
        if error.errno == EINVAL:
            return False
        raise OperationalError(
            f"could not inspect Auggie entry {name!r}: {error}"
        ) from error
    try:
        current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise OperationalError(
            f"could not inspect Auggie entry {name!r}: {error}"
        ) from error
    if not stat.S_ISLNK(current.st_mode) or (
        current.st_dev,
        current.st_ino,
    ) != (metadata.st_dev, metadata.st_ino):
        return False
    return canonical_target(link_target, target)


def owned_link_at(directory_fd, name, registered_target):
    if Path(name).name != name:
        return False
    return canonical_link_at(
        directory_fd, name, os.path.join(registered_target, name)
    )


def _container_error(path):
    raise OperationalError(
        f"Auggie container must be a real directory: {path}"
    )


def validate_scope_containers(root, scope):
    augment, skills, registrations = scope_paths(root, scope)
    if not lexists(augment):
        return augment, skills, registrations
    if not real_kind(augment, stat.S_ISDIR):
        _container_error(augment)
    quarantine = removal_quarantine(augment)
    if quarantine is not None:
        raise OperationalError(
            "Auggie removal quarantine requires manual recovery: "
            f"{quarantine}"
        )
    for directory in (skills, registrations):
        if lexists(directory) and not real_kind(directory, stat.S_ISDIR):
            _container_error(directory)
    return augment, skills, registrations


def removal_quarantine(augment):
    try:
        entries = sorted(augment.iterdir(), key=lambda entry: entry.name)
    except OSError as error:
        raise OperationalError(
            f"could not inspect Auggie container {augment}: {error}"
        ) from error
    for entry in entries:
        if entry.name.startswith(REMOVAL_PREFIX):
            return entry
    return None


@contextmanager
def open_directory(path):
    try:
        descriptor = os.open(path, DIRECTORY_FLAGS)
    except OSError as error:
        raise OperationalError(
            f"could not open real directory {path}: {error}"
        ) from error
    try:
        yield descriptor
    finally:
        os.close(descriptor)


def _identity(metadata):
    return metadata.st_dev, metadata.st_ino


def directory_binding_problem(path, descriptor):
    try:
        public_metadata = os.stat(path, follow_symlinks=False)
        opened_metadata = os.fstat(descriptor)
    except OSError as error:
        return f"directory changed during synchronization: {path}: {error}"
    if (
        not stat.S_ISDIR(public_metadata.st_mode)
        or _identity(public_metadata) != _identity(opened_metadata)
    ):
        return f"directory changed during synchronization: {path}"
    return None


def directory_at_binding_problem(parent_fd, name, path, descriptor):
    try:
        public_metadata = os.stat(
            name, dir_fd=parent_fd, follow_symlinks=False
        )
        opened_metadata = os.fstat(descriptor)
    except OSError as error:
        return f"directory changed during synchronization: {path}: {error}"
    if (
        not stat.S_ISDIR(public_metadata.st_mode)
        or _identity(public_metadata) != _identity(opened_metadata)
    ):
        return f"directory changed during synchronization: {path}"
    return None


@dataclass(frozen=True)
class ScopeState:
    augment_path: Path
    skills_path: Path
    registrations_path: Path
    augment_fd: int | None
    skills_fd: int | None
    registrations_fd: int | None

    def verify_bindings(self):
        for path, descriptor in (
            (self.augment_path, self.augment_fd),
            (self.skills_path, self.skills_fd),
            (self.registrations_path, self.registrations_fd),
        ):
            if descriptor is not None:
                problem = directory_binding_problem(path, descriptor)
                if problem is not None:
                    return problem
                continue
            try:
                os.stat(path, follow_symlinks=False)
            except FileNotFoundError:
                continue
            except OSError as error:
                return (
                    f"directory changed during synchronization: {path}: "
                    f"{error}"
                )
            return f"directory changed during synchronization: {path}"
        return None


def same_directory(first, second):
    try:
        first_metadata = os.stat(first, follow_symlinks=False)
        second_metadata = os.stat(second, follow_symlinks=False)
        return _identity(first_metadata) == _identity(second_metadata)
    except FileNotFoundError:
        try:
            return first.resolve(strict=False) == second.resolve(strict=False)
        except (OSError, RuntimeError) as error:
            raise OperationalError(
                f"could not compare Auggie scope roots: {error}"
            ) from error
    except OSError as error:
        raise OperationalError(
            f"could not compare Auggie scope roots: {error}"
        ) from error


def same_scope_directory(root):
    global_root, _global_skills, _global_registrations = (
        validate_scope_containers(root, "global")
    )
    local_root, _local_skills, _local_registrations = (
        validate_scope_containers(root, "local")
    )
    return same_directory(global_root, local_root)


def create_scope_directory(
    path,
    create,
    root,
    set_name,
    scope,
    created_directories,
):
    try:
        create()
    except FileExistsError:
        return
    except KeyboardInterrupt as interrupt:
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            raise interrupt
        except OSError as error:
            _interrupted(
                root,
                set_name,
                scope,
                "enable",
                f"{path}: directory creation could not be verified: {error}",
            )
        created_directories.add(path)
        state = (
            "directory was created"
            if stat.S_ISDIR(metadata.st_mode)
            and not stat.S_ISLNK(metadata.st_mode)
            else "path changed during directory creation"
        )
        _interrupted(root, set_name, scope, "enable", f"{path}: {state}")
    except Exception as error:
        if real_kind(path, stat.S_ISDIR):
            created_directories.add(path)
            return
        raise OperationalError(
            f"could not create Auggie container {path}: {error}"
        ) from error
    created_directories.add(path)


def ensure_scope_directories(
    root,
    scope,
    stack,
    initial_state,
    set_name,
    created_directories,
):
    problem = initial_state.verify_bindings()
    if problem is not None:
        raise OperationalError(problem)
    augment, skills, registrations = validate_scope_containers(root, scope)
    if not lexists(augment):
        create_scope_directory(
            augment,
            augment.mkdir,
            root,
            set_name,
            scope,
            created_directories,
        )
    augment_fd = stack.enter_context(open_directory(augment))
    if (
        initial_state.augment_fd is not None
        and _identity(os.fstat(augment_fd))
        != _identity(os.fstat(initial_state.augment_fd))
    ):
        raise OperationalError(
            f"Auggie container changed during inspection: {augment}"
        )
    for name, path in (("skills", skills), (".skillsets", registrations)):
        try:
            metadata = os.stat(
                name, dir_fd=augment_fd, follow_symlinks=False
            )
        except FileNotFoundError:
            create_scope_directory(
                path,
                lambda name=name: os.mkdir(name, dir_fd=augment_fd),
                root,
                set_name,
                scope,
                created_directories,
            )
        except OSError as error:
            raise OperationalError(
                f"could not inspect Auggie container {path}: {error}"
            ) from error
        else:
            if not stat.S_ISDIR(metadata.st_mode):
                _container_error(path)
        try:
            descriptor = os.open(name, DIRECTORY_FLAGS, dir_fd=augment_fd)
        except OSError as error:
            raise OperationalError(
                f"could not open Auggie container {path}: {error}"
            ) from error
        stack.callback(os.close, descriptor)
        accepted_descriptor = (
            initial_state.skills_fd
            if name == "skills"
            else initial_state.registrations_fd
        )
        if (
            accepted_descriptor is not None
            and _identity(os.fstat(descriptor))
            != _identity(os.fstat(accepted_descriptor))
        ):
            raise OperationalError(
                f"Auggie container changed during inspection: {path}"
            )
        if name == "skills":
            skills_fd = descriptor
        else:
            registrations_fd = descriptor
    return ScopeState(
        augment,
        skills,
        registrations,
        augment_fd,
        skills_fd,
        registrations_fd,
    )


def open_existing_scope(root, scope, stack):
    augment, skills, registrations = validate_scope_containers(root, scope)
    if not lexists(augment):
        return ScopeState(
            augment, skills, registrations, None, None, None
        )
    augment_fd = stack.enter_context(open_directory(augment))
    descriptors = []
    for name, path in (("skills", skills), (".skillsets", registrations)):
        try:
            descriptor = os.open(name, DIRECTORY_FLAGS, dir_fd=augment_fd)
        except FileNotFoundError:
            descriptor = None
        except OSError as error:
            raise OperationalError(
                f"could not open Auggie container {path}: {error}"
            ) from error
        if descriptor is not None:
            stack.callback(os.close, descriptor)
        descriptors.append(descriptor)
    return ScopeState(
        augment, skills, registrations, augment_fd, *descriptors
    )


def source_inventory(source_fd, source_path):
    inventory = {}
    try:
        names = sorted(os.listdir(source_fd))
    except OSError as error:
        raise OperationalError(
            f"could not inspect Auggie skill source {source_path}: {error}"
        ) from error
    for name in names:
        try:
            metadata = os.stat(
                name, dir_fd=source_fd, follow_symlinks=False
            )
        except OSError as error:
            raise OperationalError(
                f"could not inspect Auggie skill source {source_path / name}: {error}"
            ) from error
        if stat.S_ISLNK(metadata.st_mode):
            raise OperationalError(
                f"Auggie skill source must not be a symlink: {source_path / name}"
            )
        if stat.S_ISDIR(metadata.st_mode):
            inventory[name] = (metadata.st_dev, metadata.st_ino)
    return inventory


def open_source(root, name, stack):
    source_path = validate_set(root, name) / "skills"
    try:
        accepted = source_path.lstat()
    except OSError as error:
        raise OperationalError(
            f"could not inspect Auggie skill source {source_path}: {error}"
        ) from error
    source_fd = stack.enter_context(open_directory(source_path))
    opened = os.fstat(source_fd)
    if (accepted.st_dev, accepted.st_ino) != (opened.st_dev, opened.st_ino):
        raise OperationalError(
            f"Auggie skill source changed during inspection: {source_path}"
        )
    return source_path, source_fd, source_inventory(source_fd, source_path)


def _entry_missing(directory_fd, name):
    try:
        os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def _recovery_message(root, name, scope, action, detail):
    _augment, skills, registrations = scope_paths(root, scope)
    source = set_path(root, name) / "skills"
    option = scope_option(scope)
    return (
        f"Auggie {action} for {name!r} is incomplete ({detail}). "
        f"Registration: {registrations / name}; source: {source}; "
        f"projection: {skills}. Rerun `skillset augment {action} {name}{option}` "
        f"to recover"
    )


def _interrupted(root, name, scope, action, detail):
    raise ClaudeInterrupted(
        _recovery_message(root, name, scope, action, detail)
    )


def _manual_recovery_message(root, name, scope, action, quarantine, detail):
    option = scope_option(scope)
    return (
        f"Auggie {action} for {name!r} requires manual recovery ({detail}). "
        f"Preserved removal quarantine: {quarantine}. Inspect and recover it "
        "manually before running further Auggie commands; do not rerun "
        f"`skillset augment {action} {name}{option}` first"
    )


def _manual_recovery_error(root, name, scope, action, quarantine, detail):
    return ManualRecoveryError(
        _manual_recovery_message(
            root, name, scope, action, quarantine, detail
        )
    )


def _manual_recovery_interrupted(root, name, scope, action, quarantine, detail):
    raise ClaudeInterrupted(
        _manual_recovery_message(
            root, name, scope, action, quarantine, detail
        )
    )


def create_link(
    directory_fd, name, target, path, root, set_name, scope, action
):
    if canonical_link_at(directory_fd, name, target):
        return
    if not _entry_missing(directory_fd, name):
        raise OperationalError(f"Auggie entry already exists: {path}")
    try:
        os.symlink(target, name, dir_fd=directory_fd)
    except KeyboardInterrupt:
        state = "link was created" if canonical_link_at(
            directory_fd, name, target
        ) else "link was not created"
        _interrupted(root, set_name, scope, action, f"{path}: {state}")
    except Exception as error:
        if canonical_link_at(directory_fd, name, target):
            return
        raise OperationalError(
            f"could not create Auggie link {path}: {error}"
        ) from error


def create_removal_quarantine(
    augment_fd, augment_path, root, set_name, scope, action
):
    for _attempt in range(100):
        name = f"{REMOVAL_PREFIX}{uuid.uuid4().hex}"
        path = augment_path / name
        created_metadata = None
        try:
            os.mkdir(name, 0o700, dir_fd=augment_fd)
        except FileExistsError:
            continue
        except KeyboardInterrupt:
            if not _entry_missing(augment_fd, name):
                _manual_recovery_interrupted(
                    root,
                    set_name,
                    scope,
                    action,
                    path,
                    "interrupted while creating the removal quarantine",
                )
            raise
        except OSError as error:
            if not _entry_missing(augment_fd, name):
                raise _manual_recovery_error(
                    root,
                    set_name,
                    scope,
                    action,
                    path,
                    f"could not create the removal quarantine: {error}",
                ) from error
            raise OperationalError(
                f"could not create Auggie removal quarantine in {augment_path}: "
                f"{error}"
            ) from error
        descriptor = None
        try:
            created_metadata = os.stat(
                name, dir_fd=augment_fd, follow_symlinks=False
            )
            descriptor = os.open(name, DIRECTORY_FLAGS, dir_fd=augment_fd)
            opened_metadata = os.fstat(descriptor)
        except KeyboardInterrupt:
            if descriptor is not None:
                os.close(descriptor)
            _manual_recovery_interrupted(
                root,
                set_name,
                scope,
                action,
                path,
                "interrupted while verifying the newly created removal quarantine",
            )
        except OSError as error:
            if descriptor is not None:
                os.close(descriptor)
            if not remove_created_empty_quarantine(
                augment_fd, name, created_metadata
            ):
                raise _manual_recovery_error(
                    root,
                    set_name,
                    scope,
                    action,
                    path,
                    f"could not verify the removal quarantine: {error}",
                ) from error
            raise OperationalError(
                f"could not open Auggie removal quarantine {path}: {error}"
            ) from error
        if (
            not stat.S_ISDIR(created_metadata.st_mode)
            or _identity(created_metadata) != _identity(opened_metadata)
        ):
            os.close(descriptor)
            raise _manual_recovery_error(
                root,
                set_name,
                scope,
                action,
                path,
                "the removal quarantine changed during creation",
            )
        return name, path, descriptor
    raise OperationalError(
        f"could not create a unique Auggie removal quarantine in {augment_path}"
    )


def remove_created_empty_quarantine(augment_fd, name, created_metadata):
    if created_metadata is None:
        return False
    try:
        current = os.stat(name, dir_fd=augment_fd, follow_symlinks=False)
    except OSError:
        return False
    if (
        not stat.S_ISDIR(current.st_mode)
        or _identity(current) != _identity(created_metadata)
    ):
        return False
    try:
        os.rmdir(name, dir_fd=augment_fd)
    except OSError:
        return False
    return True


def remove_empty_quarantine(augment_fd, name, path, descriptor):
    problem = directory_at_binding_problem(
        augment_fd, name, path, descriptor
    )
    if problem is not None:
        raise ManualRecoveryError(
            f"Auggie removal quarantine requires manual recovery: {path}; {problem}"
        )
    try:
        os.rmdir(name, dir_fd=augment_fd)
    except OSError as error:
        raise ManualRecoveryError(
            f"Auggie removal quarantine requires manual recovery: {path}; "
            f"could not remove the empty quarantine: {error}"
        ) from error


def unlink_link(
    directory_fd,
    name,
    path,
    target,
    augment_fd,
    augment_path,
    root,
    set_name,
    scope,
    action,
):
    if not canonical_link_at(directory_fd, name, target):
        if _entry_missing(directory_fd, name):
            return
        raise OperationalError(
            f"refused to remove changed Auggie entry: {path}"
        )
    quarantine_name, quarantine_path, quarantine_fd = create_removal_quarantine(
        augment_fd, augment_path, root, set_name, scope, action
    )
    quarantined_path = quarantine_path / REMOVAL_ENTRY
    try:
        try:
            problem = directory_at_binding_problem(
                augment_fd, quarantine_name, quarantine_path, quarantine_fd
            )
            if problem is not None:
                raise OperationalError(problem)
            os.rename(
                name,
                REMOVAL_ENTRY,
                src_dir_fd=directory_fd,
                dst_dir_fd=quarantine_fd,
            )
        except OSError as error:
            if os.path.lexists(quarantined_path):
                raise _manual_recovery_error(
                    root,
                    set_name,
                    scope,
                    action,
                    quarantine_path,
                    f"could not move {path}; entry remains at {quarantined_path}: "
                    f"{error}",
                ) from error
            remove_empty_quarantine(
                augment_fd, quarantine_name, quarantine_path, quarantine_fd
            )
            raise OperationalError(
                f"could not move Auggie entry {path}: {error}"
            ) from error
        if not canonical_link_at(quarantine_fd, REMOVAL_ENTRY, target):
            raise _manual_recovery_error(
                root,
                set_name,
                scope,
                action,
                quarantine_path,
                f"refused to remove changed entry {path}; it remains at "
                f"{quarantined_path}",
            )
        os.unlink(REMOVAL_ENTRY, dir_fd=quarantine_fd)
    except KeyboardInterrupt:
        if _entry_missing(quarantine_fd, REMOVAL_ENTRY):
            remove_empty_quarantine(
                augment_fd, quarantine_name, quarantine_path, quarantine_fd
            )
            state = "link was removed"
        else:
            _manual_recovery_interrupted(
                root,
                set_name,
                scope,
                action,
                quarantine_path,
                f"interrupted after moving {path}; entry remains at "
                f"{quarantined_path}",
            )
        _interrupted(root, set_name, scope, action, f"{path}: {state}")
    except OSError as error:
        if not _entry_missing(quarantine_fd, REMOVAL_ENTRY):
            raise _manual_recovery_error(
                root,
                set_name,
                scope,
                action,
                quarantine_path,
                f"could not remove {path}; entry remains at {quarantined_path}: "
                f"{error}",
            ) from error
        raise OperationalError(
            f"could not remove Auggie link {path}: {error}"
        ) from error
    else:
        remove_empty_quarantine(
            augment_fd, quarantine_name, quarantine_path, quarantine_fd
        )
    finally:
        os.close(quarantine_fd)


def preflight_projection(
    source_inventory_value,
    skills_fd,
    skills_path,
    registrations_fd,
    registration_path,
    target,
):
    if registrations_fd is not None and not _entry_missing(
        registrations_fd, registration_path.name
    ):
        if not canonical_link_at(
            registrations_fd, registration_path.name, target
        ):
            raise OperationalError(
                f"Auggie skillset registration already exists: {registration_path}"
            )
    if skills_fd is None:
        return
    for skill_name in source_inventory_value:
        skill_target = os.path.join(target, skill_name)
        if canonical_link_at(skills_fd, skill_name, skill_target):
            continue
        if not _entry_missing(skills_fd, skill_name):
            raise OperationalError(
                f"Auggie skill entry already exists: {skills_path / skill_name}"
            )


def cross_scope_collision(
    source_inventory_value,
    target,
    other_skills_fd,
    other_skills_path,
):
    if other_skills_fd is None:
        return None
    for skill_name in source_inventory_value:
        skill_target = os.path.join(target, skill_name)
        if canonical_link_at(other_skills_fd, skill_name, skill_target):
            continue
        if not _entry_missing(other_skills_fd, skill_name):
            return (
                f"Auggie skill name {skill_name!r} conflicts across "
                "global and local scopes at "
                f"{other_skills_path / skill_name}"
            )
    return None


def verify_source_child(source_fd, source_path, name, identity):
    try:
        metadata = os.stat(
            name, dir_fd=source_fd, follow_symlinks=False
        )
    except OSError as error:
        raise OperationalError(
            f"Auggie skill source changed during enable: {source_path / name}: {error}"
        ) from error
    if not stat.S_ISDIR(metadata.st_mode) or (
        metadata.st_dev,
        metadata.st_ino,
    ) != identity:
        raise OperationalError(
            f"Auggie skill source changed during enable: {source_path / name}"
        )


def owned_names(skills_fd, registered_target):
    if skills_fd is None:
        return []
    try:
        names = os.listdir(skills_fd)
    except OSError as error:
        raise OperationalError(
            f"could not inspect Auggie projection for {registered_target}: {error}"
        ) from error
    return sorted(
        name
        for name in names
        if owned_link_at(skills_fd, name, registered_target)
    )


def verify_enabled(
    source_fd,
    source_path,
    scope_state,
    registration_path,
    target,
):
    current = source_inventory(source_fd, source_path)
    if scope_state.registrations_fd is None or not canonical_link_at(
        scope_state.registrations_fd, registration_path.name, target
    ):
        return f"registration is missing or noncanonical: {registration_path}"
    if scope_state.skills_fd is None:
        return f"projection directory is missing: {scope_state.skills_path}"
    for skill_name in current:
        if not canonical_link_at(
            scope_state.skills_fd,
            skill_name,
            os.path.join(target, skill_name),
        ):
            return (
                "projected skill is missing or colliding: "
                f"{scope_state.skills_path / skill_name}"
            )
    stale = set(owned_names(scope_state.skills_fd, target)) - set(current)
    if stale:
        return (
            "stale projected skill remains: "
            f"{scope_state.skills_path / sorted(stale)[0]}"
        )
    problem = directory_binding_problem(source_path, source_fd)
    if problem is not None:
        return problem
    return scope_state.verify_bindings()


def enable(root, name, scope):
    validate_name(name)
    validate_layout(root)
    target = expected_target(root, name)
    registration_created = False
    created_directories = set()
    with ExitStack() as stack:
        source_path, source_fd, inventory = open_source(root, name, stack)
        validate_projection_root(source_path, scope)
        other_state = None
        if not same_scope_directory(root):
            other_state = open_existing_scope(
                root, opposite_scope(scope), stack
            )
            problem = cross_scope_collision(
                inventory,
                target,
                other_state.skills_fd,
                other_state.skills_path,
            )
            if problem is not None:
                raise OperationalError(problem)
        initial_state = open_existing_scope(root, scope, stack)
        registration_path = initial_state.registrations_path / name
        preflight_projection(
            inventory,
            initial_state.skills_fd,
            initial_state.skills_path,
            initial_state.registrations_fd,
            registration_path,
            target,
        )
        was_registered = (
            initial_state.registrations_fd is not None
            and canonical_link_at(
                initial_state.registrations_fd, name, target
            )
        )
        scope_state = initial_state
        try:
            scope_state = ensure_scope_directories(
                root,
                scope,
                stack,
                initial_state,
                name,
                created_directories,
            )
            registration_path = scope_state.registrations_path / name
            create_link(
                scope_state.registrations_fd,
                name,
                target,
                registration_path,
                root,
                name,
                scope,
                "enable",
            )
            registration_created = not was_registered
            for skill_name, identity in inventory.items():
                verify_source_child(
                    source_fd, source_path, skill_name, identity
                )
                create_link(
                    scope_state.skills_fd,
                    skill_name,
                    os.path.join(target, skill_name),
                    scope_state.skills_path / skill_name,
                    root,
                    name,
                    scope,
                    "enable",
                )
            for stale_name in (
                set(owned_names(scope_state.skills_fd, target))
                - set(inventory)
            ):
                stale_path = scope_state.skills_path / stale_name
                unlink_link(
                    scope_state.skills_fd,
                    stale_name,
                    stale_path,
                    os.path.join(target, stale_name),
                    scope_state.augment_fd,
                    scope_state.augment_path,
                    root,
                    name,
                    scope,
                    "enable",
                )
            problem = verify_enabled(
                source_fd,
                source_path,
                scope_state,
                registration_path,
                target,
            )
            if problem is not None:
                raise OperationalError(problem)
            if other_state is not None:
                if other_state.skills_fd is None:
                    other_state = open_existing_scope(
                        root, opposite_scope(scope), stack
                    )
                problem = cross_scope_collision(
                    inventory,
                    target,
                    other_state.skills_fd,
                    other_state.skills_path,
                )
                if problem is not None:
                    raise OperationalError(problem)
                problem = other_state.verify_bindings()
                if problem is not None:
                    raise OperationalError(problem)
        except ClaudeInterrupted:
            raise
        except KeyboardInterrupt:
            if (
                was_registered
                or registration_created
                or created_directories
                or (
                    scope_state.registrations_fd is not None
                    and canonical_link_at(
                        scope_state.registrations_fd, name, target
                    )
                )
            ):
                _interrupted(
                    root,
                    name,
                    scope,
                    "enable",
                    "scope or registration changed and projection may be incomplete",
                )
            raise
        except ManualRecoveryError:
            raise
        except OperationalError as error:
            if (
                was_registered
                or registration_created
                or created_directories
                or (
                    scope_state.registrations_fd is not None
                    and canonical_link_at(
                        scope_state.registrations_fd, name, target
                    )
                )
            ):
                raise OperationalError(
                    _recovery_message(root, name, scope, "enable", error)
                ) from error
            raise


def disable(root, name, scope):
    validate_name(name)
    validate_layout(root)
    target = expected_target(root, name)
    with ExitStack() as stack:
        scope_state = open_existing_scope(root, scope, stack)
        registration_path = scope_state.registrations_path / name
        registration_missing = (
            scope_state.registrations_fd is None
            or _entry_missing(scope_state.registrations_fd, name)
        )
        if not registration_missing and not canonical_link_at(
            scope_state.registrations_fd, name, target
        ):
            raise OperationalError(
                f"skillset is not Auggie-enabled: {name!r}"
            )
        try:
            for skill_name in owned_names(scope_state.skills_fd, target):
                skill_path = scope_state.skills_path / skill_name
                unlink_link(
                    scope_state.skills_fd,
                    skill_name,
                    skill_path,
                    os.path.join(target, skill_name),
                    scope_state.augment_fd,
                    scope_state.augment_path,
                    root,
                    name,
                    scope,
                    "disable",
                )
            if scope_state.registrations_fd is not None:
                unlink_link(
                    scope_state.registrations_fd,
                    name,
                    registration_path,
                    target,
                    scope_state.augment_fd,
                    scope_state.augment_path,
                    root,
                    name,
                    scope,
                    "disable",
                )
            remaining = owned_names(scope_state.skills_fd, target)
            registration_remains = (
                scope_state.registrations_fd is not None
                and not _entry_missing(scope_state.registrations_fd, name)
            )
            if remaining or registration_remains:
                path = (
                    scope_state.skills_path / remaining[0]
                    if remaining
                    else registration_path
                )
                raise OperationalError(f"managed entry remains: {path}")
            problem = scope_state.verify_bindings()
            if problem is not None:
                raise OperationalError(problem)
        except ClaudeInterrupted:
            raise
        except KeyboardInterrupt:
            _interrupted(
                root,
                name,
                scope,
                "disable",
                "registration and projection may be incomplete",
            )
        except ManualRecoveryError:
            raise
        except OperationalError as error:
            raise OperationalError(
                _recovery_message(root, name, scope, "disable", error)
            ) from error


def synchronized_names(root, scope):
    with ExitStack() as stack:
        scope_state = open_existing_scope(root, scope, stack)
        if scope_state.registrations_fd is None:
            return []
        names = []
        label = "global" if scope == "global" else "local"
        try:
            registration_names = sorted(
                os.listdir(scope_state.registrations_fd)
            )
        except OSError as error:
            raise OperationalError(
                f"could not inspect Auggie registrations in {label} "
                f"scope at {scope_state.registrations_path}: {error}"
            ) from error
        for name in registration_names:
            if not NAME_PATTERN.fullmatch(name):
                continue
            target = expected_target(root, name)
            registration_path = scope_state.registrations_path / name
            if not canonical_link_at(
                scope_state.registrations_fd, name, target
            ):
                raise OperationalError(
                    f"noncanonical Auggie registration in {label} scope: "
                    f"{registration_path}; repair it manually or run "
                    f"`skillset augment disable {name}{scope_option(scope)}` "
                    "after restoring the canonical link"
                )
            with ExitStack() as source_stack:
                try:
                    source_path, source_fd, _inventory = open_source(
                        root, name, source_stack
                    )
                except OperationalError as error:
                    raise OperationalError(
                        f"invalid Auggie registration in {label} scope: "
                        f"{registration_path}: {error}; restore the source or "
                        f"run `skillset augment disable {name}{scope_option(scope)}`"
                    ) from error
                problem = verify_enabled(
                    source_fd,
                    source_path,
                    scope_state,
                    registration_path,
                    target,
                )
            if problem is not None:
                raise OperationalError(
                    f"incomplete Auggie projection in {label} scope for "
                    f"{name!r}: {problem}; rerun "
                    f"`skillset augment enable {name}{scope_option(scope)}` "
                    f"or `skillset augment disable {name}{scope_option(scope)}`"
                )
            names.append(name)
        return names


def validate_names_against_other_scope(root, scope, names):
    if not names:
        return
    if same_scope_directory(root):
        return
    other_scope_name = opposite_scope(scope)
    with ExitStack() as stack:
        other_state = open_existing_scope(root, other_scope_name, stack)
        if other_state.skills_fd is None:
            return
        for name in names:
            with ExitStack() as source_stack:
                source_path, source_fd, inventory = open_source(
                    root, name, source_stack
                )
                problem = cross_scope_collision(
                    inventory,
                    expected_target(root, name),
                    other_state.skills_fd,
                    other_state.skills_path,
                )
                if problem is not None:
                    raise OperationalError(problem)
                problem = directory_binding_problem(source_path, source_fd)
                if problem is not None:
                    raise OperationalError(problem)
        problem = other_state.verify_bindings()
        if problem is not None:
            raise OperationalError(problem)


def list_enabled(root, verbose, scope):
    validate_layout(root)
    if scope == "all":
        global_names = synchronized_names(root, "global")
        local_names = (
            []
            if same_scope_directory(root)
            else synchronized_names(root, "local")
        )
        validate_names_against_other_scope(root, "global", global_names)
        validate_names_against_other_scope(root, "local", local_names)
        return list_scoped_sets(
            root,
            (
                ("g", global_names),
                ("l", local_names),
            ),
            verbose,
        )
    names = synchronized_names(root, scope)
    validate_names_against_other_scope(root, scope, names)
    return list_named_sets(
        root,
        names,
        verbose,
        mark_active=False,
    )


def orphaned_projection_blocker(augment, augment_fd, skills, target):
    if directory_binding_problem(augment, augment_fd) is not None:
        return GlobalRegistrationBlocker(augment, False)
    try:
        skills_metadata = os.stat(
            "skills", dir_fd=augment_fd, follow_symlinks=False
        )
    except FileNotFoundError:
        if directory_binding_problem(augment, augment_fd) is not None:
            return GlobalRegistrationBlocker(augment, False)
        try:
            skills_metadata = os.stat(
                "skills", dir_fd=augment_fd, follow_symlinks=False
            )
        except FileNotFoundError:
            if directory_binding_problem(augment, augment_fd) is not None:
                return GlobalRegistrationBlocker(augment, False)
            return None
        except OSError:
            return GlobalRegistrationBlocker(skills, False)
    except OSError:
        return GlobalRegistrationBlocker(skills, False)
    if stat.S_ISLNK(skills_metadata.st_mode) or not stat.S_ISDIR(
        skills_metadata.st_mode
    ):
        return GlobalRegistrationBlocker(skills, False)
    try:
        skills_fd = os.open("skills", DIRECTORY_FLAGS, dir_fd=augment_fd)
    except OSError:
        return GlobalRegistrationBlocker(skills, False)
    try:
        if _identity(skills_metadata) != _identity(os.fstat(skills_fd)):
            return GlobalRegistrationBlocker(skills, False)
        if directory_binding_problem(augment, augment_fd) is not None:
            return GlobalRegistrationBlocker(augment, False)
        if directory_binding_problem(skills, skills_fd) is not None:
            return GlobalRegistrationBlocker(skills, False)
        try:
            names = owned_names(skills_fd, target)
        except OperationalError:
            return GlobalRegistrationBlocker(skills, False)
        if directory_binding_problem(augment, augment_fd) is not None:
            return GlobalRegistrationBlocker(augment, False)
        if directory_binding_problem(skills, skills_fd) is not None:
            return GlobalRegistrationBlocker(skills, False)
    finally:
        os.close(skills_fd)
    if not names:
        return None
    return GlobalRegistrationBlocker(
        skills / names[0], False, incomplete_projection=True
    )


def inspected_link_target_at(directory_fd, name):
    try:
        accepted = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError:
        return False
    if not stat.S_ISLNK(accepted.st_mode):
        return False
    try:
        target = os.readlink(name, dir_fd=directory_fd)
    except OSError:
        return False
    try:
        current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except OSError:
        return False
    if not stat.S_ISLNK(current.st_mode) or _identity(current) != _identity(
        accepted
    ):
        return False
    return target


def lifecycle_container_blocker_path(root, scope):
    augment, skills, registrations = scope_paths(root, scope)
    if not lexists(augment) or not real_kind(augment, stat.S_ISDIR):
        return augment
    try:
        quarantine = removal_quarantine(augment)
    except OperationalError:
        return augment
    if quarantine is not None:
        return quarantine
    for directory in (skills, registrations):
        if lexists(directory) and not real_kind(directory, stat.S_ISDIR):
            return directory
    return augment


def global_registration_blocker(root, name):
    try:
        augment, _skills, registrations = validate_scope_containers(
            root, "global"
        )
    except OperationalError:
        return GlobalRegistrationBlocker(
            lifecycle_container_blocker_path(root, "global"), False
        )
    target = expected_target(root, name)
    try:
        augment_fd = os.open(augment, DIRECTORY_FLAGS)
    except FileNotFoundError:
        return None
    except OSError:
        return GlobalRegistrationBlocker(augment, False)
    with ExitStack() as stack:
        stack.callback(os.close, augment_fd)
        try:
            registrations_metadata = os.stat(
                ".skillsets", dir_fd=augment_fd, follow_symlinks=False
            )
        except FileNotFoundError:
            if directory_binding_problem(augment, augment_fd) is not None:
                return GlobalRegistrationBlocker(augment, False)
            return orphaned_projection_blocker(
                augment, augment_fd, _skills, target
            )
        except OSError:
            return GlobalRegistrationBlocker(augment, False)
        if not stat.S_ISDIR(registrations_metadata.st_mode):
            return GlobalRegistrationBlocker(registrations, False)
        try:
            registrations_fd = os.open(
                ".skillsets", DIRECTORY_FLAGS, dir_fd=augment_fd
            )
        except FileNotFoundError:
            if directory_binding_problem(augment, augment_fd) is not None:
                return GlobalRegistrationBlocker(augment, False)
            return orphaned_projection_blocker(
                augment, augment_fd, _skills, target
            )
        except OSError:
            return GlobalRegistrationBlocker(augment, False)
        stack.callback(os.close, registrations_fd)
        if _identity(registrations_metadata) != _identity(
            os.fstat(registrations_fd)
        ):
            return GlobalRegistrationBlocker(registrations, False)
        registration = registrations / name
        inspected_target = inspected_link_target_at(registrations_fd, name)
        if directory_binding_problem(augment, augment_fd) is not None:
            return GlobalRegistrationBlocker(augment, False)
        if directory_binding_problem(registrations, registrations_fd) is not None:
            return GlobalRegistrationBlocker(registrations, False)
        if inspected_target is None:
            return orphaned_projection_blocker(
                augment, augment_fd, _skills, target
            )
        if inspected_target is False:
            return GlobalRegistrationBlocker(registration, False)
        return GlobalRegistrationBlocker(
            registration, canonical_target(inspected_target, target)
        )
