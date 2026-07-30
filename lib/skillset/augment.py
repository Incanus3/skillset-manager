"""Manage flattened skillset projections discovered by Auggie."""

import os
import stat
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from errno import EINVAL
from pathlib import Path

from .errors import ClaudeInterrupted, OperationalError
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


DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY


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
    for directory in (skills, registrations):
        if lexists(directory) and not real_kind(directory, stat.S_ISDIR):
            _container_error(directory)
    return augment, skills, registrations


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


@dataclass(frozen=True)
class ScopeState:
    augment_path: Path
    skills_path: Path
    registrations_path: Path
    augment_fd: int | None
    skills_fd: int | None
    registrations_fd: int | None


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


def same_list_scope_directory(root):
    global_root, _global_skills, _global_registrations = scope_paths(root, "global")
    local_root, _local_skills, _local_registrations = scope_paths(root, "local")
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
    set_name,
    created_directories,
):
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
    inventory = set()
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
            inventory.add(name)
    return inventory


def open_source(root, name, stack):
    source_path = validate_set(root, name) / "skills"
    source_fd = stack.enter_context(open_directory(source_path))
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


def unlink_link(
    directory_fd,
    name,
    path,
    target,
    root,
    set_name,
    scope,
    action,
):
    if not canonical_link_at(directory_fd, name, target):
        if _entry_missing(directory_fd, name):
            return
        raise OperationalError(f"refused to remove changed Auggie entry: {path}")
    try:
        os.unlink(name, dir_fd=directory_fd)
    except KeyboardInterrupt:
        state = "link was removed" if _entry_missing(directory_fd, name) else "link was not removed"
        _interrupted(root, set_name, scope, action, f"{path}: {state}")
    except OSError as error:
        if _entry_missing(directory_fd, name):
            return
        raise OperationalError(f"could not remove Auggie link {path}: {error}") from error


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
    return None


def enable(root, name, scope):
    validate_name(name)
    validate_layout(root)
    target = expected_target(root, name)
    registration_created = False
    created_directories = set()
    with ExitStack() as stack:
        source_path, source_fd, inventory = open_source(root, name, stack)
        validate_projection_root(source_path, scope)
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
            for skill_name in inventory:
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
        except OperationalError as error:
            raise OperationalError(
                _recovery_message(root, name, scope, "disable", error)
            ) from error


def registered_names(root, scope):
    augment, _skills, registrations = scope_paths(root, scope)
    if not lexists(augment):
        return []
    if not real_kind(augment, stat.S_ISDIR):
        _container_error(augment)
    if not lexists(registrations):
        return []
    if not real_kind(registrations, stat.S_ISDIR):
        _container_error(registrations)
    label = "global" if scope == "global" else "local"
    try:
        entries = sorted(registrations.iterdir(), key=lambda path: path.name)
    except OSError as error:
        raise OperationalError(
            f"could not inspect Auggie registrations in {label} "
            f"scope at {registrations}: {error}"
        ) from error
    return [entry.name for entry in entries if NAME_PATTERN.fullmatch(entry.name)]


def synchronized_names(root, scope):
    if not registered_names(root, scope):
        return []
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


def list_enabled(root, verbose, scope):
    validate_layout(root)
    if scope == "all":
        global_names = synchronized_names(root, "global")
        local_names = (
            []
            if same_list_scope_directory(root)
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
    try:
        skills_metadata = os.stat(
            "skills", dir_fd=augment_fd, follow_symlinks=False
        )
    except FileNotFoundError:
        return None
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
        try:
            names = owned_names(skills_fd, target)
        except OperationalError:
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
    return target


def lifecycle_container_blocker_path(root, scope):
    augment, skills, registrations = scope_paths(root, scope)
    if not lexists(augment) or not real_kind(augment, stat.S_ISDIR):
        return augment
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
            return orphaned_projection_blocker(
                augment, augment_fd, _skills, target
            )
        except OSError:
            return GlobalRegistrationBlocker(augment, False)
        stack.callback(os.close, registrations_fd)
        registration = registrations / name
        inspected_target = inspected_link_target_at(registrations_fd, name)
        if inspected_target is None:
            return orphaned_projection_blocker(
                augment, augment_fd, _skills, target
            )
        if inspected_target is False:
            return GlobalRegistrationBlocker(registration, False)
        return GlobalRegistrationBlocker(
            registration, canonical_target(inspected_target, target)
        )
