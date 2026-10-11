"""Parse and dispatch skillset CLI commands."""

import argparse
import sys
from pathlib import Path

from .errors import ClaudeInterrupted, OperationalError


class SkillsetArgumentParser(argparse.ArgumentParser):
    """Let domain validation handle option-like skillset names."""

    def _parse_optional(self, argument):
        parsed = super()._parse_optional(argument)
        if parsed is not None:
            candidates = parsed if isinstance(parsed, list) else [parsed]
            if candidates and all(candidate[0] is None for candidate in candidates):
                return None
        return parsed


def parser():
    command_parser = SkillsetArgumentParser(prog="skillset")
    commands = command_parser.add_subparsers(dest="command", required=True)
    init_parser = commands.add_parser("init", help="adopt existing global skills")
    init_parser.add_argument("name")
    create_parser = commands.add_parser("create", help="create a skillset")
    create_parser.add_argument("name")
    source_group = create_parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "-f",
        "--from",
        dest="source",
        metavar="SOURCE",
        help="clone from an existing skillset",
    )
    source_group.add_argument(
        "--manual",
        action="store_true",
        help="create a hand-managed skillset without upstream lock metadata",
    )
    create_parser.add_argument(
        "--use",
        dest="activate",
        action="store_true",
        help="activate the created skillset",
    )
    use_parser = commands.add_parser("use", help="activate a skillset")
    use_parser.add_argument("name")
    rename_parser = commands.add_parser("rename", help="rename a skillset")
    rename_parser.add_argument("old")
    rename_parser.add_argument("new")
    remove_parser = commands.add_parser("remove", help="remove an inactive skillset")
    remove_parser.add_argument("name")
    remove_parser.add_argument("--yes", action="store_true")
    list_parser = commands.add_parser("list", help="list managed skillsets")
    list_parser.add_argument("-v", "--verbose", action="store_true")
    codex_parser = commands.add_parser(
        "codex", help="manage Codex-enabled skillsets"
    )
    codex_commands = codex_parser.add_subparsers(
        dest="codex_command", required=True
    )
    codex_enable_parser = codex_commands.add_parser(
        "enable", help="enable a skillset for Codex"
    )
    codex_enable_parser.add_argument("name")
    add_scope_options(
        codex_enable_parser,
        dest="codex_scope",
        product="Codex",
        directory=".codex",
        project_help="manage Codex skills across this clone's worktrees",
    )
    codex_disable_parser = codex_commands.add_parser(
        "disable", help="disable a skillset for Codex"
    )
    codex_disable_parser.add_argument("name")
    add_scope_options(
        codex_disable_parser,
        dest="codex_scope",
        product="Codex",
        directory=".codex",
        project_help="manage Codex skills across this clone's worktrees",
    )
    codex_list_parser = codex_commands.add_parser(
        "list", help="list Codex-enabled skillsets"
    )
    codex_list_parser.add_argument("-v", "--verbose", action="store_true")
    add_scope_options(
        codex_list_parser,
        dest="codex_scope",
        product="Codex",
        directory=".codex",
        default="all",
        project_help="inspect Codex skills across this clone's worktrees",
    )
    claude_parser = commands.add_parser(
        "claude", help="manage Claude Code-enabled skillsets"
    )
    claude_commands = claude_parser.add_subparsers(
        dest="claude_command", required=True
    )
    claude_enable_parser = claude_commands.add_parser(
        "enable", help="enable a skillset for Claude Code"
    )
    claude_enable_parser.add_argument("name")
    add_scope_options(
        claude_enable_parser,
        dest="claude_scope",
        product="Claude Code",
        directory=".claude",
    )
    claude_disable_parser = claude_commands.add_parser(
        "disable", help="disable a skillset for Claude Code"
    )
    claude_disable_parser.add_argument("name")
    add_scope_options(
        claude_disable_parser,
        dest="claude_scope",
        product="Claude Code",
        directory=".claude",
    )
    claude_list_parser = claude_commands.add_parser(
        "list", help="list Claude Code-enabled skillsets"
    )
    claude_list_parser.add_argument("-v", "--verbose", action="store_true")
    add_scope_options(
        claude_list_parser,
        dest="claude_scope",
        product="Claude Code",
        directory=".claude",
        default="all",
    )
    augment_parser = commands.add_parser(
        "augment", help="manage Auggie-enabled skillsets"
    )
    augment_commands = augment_parser.add_subparsers(
        dest="augment_command", required=True
    )
    augment_enable_parser = augment_commands.add_parser(
        "enable", help="enable a skillset for Auggie"
    )
    augment_enable_parser.add_argument("name")
    add_scope_options(
        augment_enable_parser,
        dest="augment_scope",
        product="Auggie",
        directory=".augment",
    )
    augment_disable_parser = augment_commands.add_parser(
        "disable", help="disable a skillset for Auggie"
    )
    augment_disable_parser.add_argument("name")
    add_scope_options(
        augment_disable_parser,
        dest="augment_scope",
        product="Auggie",
        directory=".augment",
    )
    augment_list_parser = augment_commands.add_parser(
        "list", help="list Auggie-enabled skillsets"
    )
    augment_list_parser.add_argument("-v", "--verbose", action="store_true")
    add_scope_options(
        augment_list_parser,
        dest="augment_scope",
        product="Auggie",
        directory=".augment",
        default="all",
    )
    augment_skills_parser = augment_commands.add_parser(
        "skills", help="list effective Auggie skills"
    )
    augment_skills_commands = augment_skills_parser.add_subparsers(
        dest="augment_skills_command", required=True
    )
    augment_skills_list_parser = augment_skills_commands.add_parser(
        "list", help="list effective Auggie skills"
    )
    augment_skills_list_parser.add_argument("-v", "--verbose", action="store_true")
    add_scope_options(
        augment_skills_list_parser,
        dest="augment_skills_scope",
        product="Auggie",
        directory=".augment",
        default="all",
        global_help="filter effective winners from all User roots",
        local_help="filter effective winners from all Workspace roots",
    )
    commands.add_parser("current", help="print the active skillset name")
    show_parser = commands.add_parser("show", help="show skills in a skillset")
    show_parser.add_argument("name", nargs="?")
    doctor_parser = commands.add_parser("doctor", help="diagnose the managed layout")
    doctor_parser.add_argument(
        "--fix",
        action="store_true",
        help="create safe missing replacement files after confirmation",
    )
    completions_parser = commands.add_parser(
        "completions", help="emit a shell completion script"
    )
    completions_parser.add_argument("shell", choices=("bash", "zsh", "fish"))
    skills_parser = commands.add_parser(
        "skills", help="run managed upstream skills", add_help=False
    )
    skills_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    # No help pseudo-action is registered, and an explicit metavar keeps the
    # hidden command out of argparse's generated public choice list.
    commands.metavar = "{" + ",".join(commands.choices) + "}"
    hook_parser = commands.add_parser("_project-hook")
    hook_parser.add_argument("old")
    hook_parser.add_argument("new")
    hook_parser.add_argument("flag")
    return command_parser


def add_scope_options(
    command_parser,
    *,
    dest,
    product,
    directory,
    default="global",
    global_help=None,
    local_help=None,
    project_help=None,
):
    scope = command_parser.add_mutually_exclusive_group()
    if global_help is None:
        global_help = f"manage the global ~/{directory} directory"
        if default == "global":
            global_help += " (default)"
    if local_help is None:
        local_help = (
            f"manage the current directory's {directory} directory for {product}"
        )
    scope.add_argument(
        "-g",
        "--global",
        dest=dest,
        action="store_const",
        const="global",
        help=global_help,
    )
    scope.add_argument(
        "-l",
        "--local",
        dest=dest,
        action="store_const",
        const="local",
        help=local_help,
    )
    if project_help is not None:
        scope.add_argument(
            "--project", dest=dest, action="store_const", const="project",
            help=project_help,
        )
    command_parser.set_defaults(**{dest: default})


def dispatch_locked_command(root, arguments, home_lock, lock_file, command_parser):
    if arguments.command == "_project-hook":
        from .project import run_hook

        errors = run_hook(root, arguments.old, arguments.new, arguments.flag)
        return report_command_errors(arguments.command, errors)
    elif arguments.command == "init":
        from .operations import init

        init(root, arguments.name)
    elif arguments.command == "create":
        from .operations import create, use

        create(root, arguments.name, arguments.source, arguments.manual)
        if arguments.activate:
            use(root, arguments.name)
    elif arguments.command == "use":
        from .operations import use

        use(root, arguments.name)
    elif arguments.command == "rename":
        from .operations import rename

        rename(root, arguments.old, arguments.new)
    elif arguments.command == "remove":
        from .operations import remove

        remove(root, arguments.name, arguments.yes)
    elif arguments.command == "list":
        from .metadata import list_sets

        list_sets(root, arguments.verbose)
    elif arguments.command == "codex":
        from . import codex

        if arguments.codex_command == "enable":
            errors = codex.enable(root, arguments.name, arguments.codex_scope)
            return report_command_errors(arguments.command, errors)
        elif arguments.codex_command == "disable":
            errors = codex.disable(root, arguments.name, arguments.codex_scope)
            return report_command_errors(arguments.command, errors)
        elif arguments.codex_command == "list":
            errors = codex.list_enabled(root, arguments.verbose, arguments.codex_scope)
            return report_command_errors(arguments.command, errors)
        else:
            raise OperationalError(
                f"unsupported Codex command: {arguments.codex_command}"
            )
    elif arguments.command == "claude":
        from . import claude

        if arguments.claude_command == "enable":
            claude.enable(root, arguments.name, arguments.claude_scope)
        elif arguments.claude_command == "disable":
            claude.disable(root, arguments.name, arguments.claude_scope)
        elif arguments.claude_command == "list":
            claude.list_enabled(root, arguments.verbose, arguments.claude_scope)
        else:
            raise OperationalError(
                f"unsupported Claude Code command: {arguments.claude_command}"
            )
    elif arguments.command == "augment":
        if arguments.augment_command == "enable":
            from .augment import enable

            enable(root, arguments.name, arguments.augment_scope)
        elif arguments.augment_command == "disable":
            from .augment import disable

            disable(root, arguments.name, arguments.augment_scope)
        elif arguments.augment_command == "list":
            from .augment import list_enabled

            list_enabled(root, arguments.verbose, arguments.augment_scope)
        elif arguments.augment_command == "skills":
            if arguments.augment_skills_command == "list":
                from .augment_discovery import list_effective_skills

                list_effective_skills(
                    root,
                    arguments.verbose,
                    arguments.augment_skills_scope,
                )
            else:
                raise OperationalError(
                    "unsupported Auggie skills command: "
                    f"{arguments.augment_skills_command}"
                )
        else:
            raise OperationalError(
                f"unsupported Auggie command: {arguments.augment_command}"
            )
    elif arguments.command == "current":
        from .metadata import current

        current(root)
    elif arguments.command == "show":
        from .metadata import show

        show(root, arguments.name)
    elif arguments.command == "skills":
        from .delegate import delegate_skills

        delegate_skills(
            root,
            arguments.arguments,
            home_lock,
            lock_file,
            command_parser,
        )
    else:
        raise OperationalError(f"unsupported command: {arguments.command}")


def run_managed_command(root, arguments, command_parser):
    augment_discovery = (
        arguments.command == "augment"
        and arguments.augment_command == "skills"
        and arguments.augment_skills_command == "list"
    )
    inspection = arguments.command in {"list", "current", "show"} or (
        arguments.command == "codex" and arguments.codex_command == "list"
    ) or (
        arguments.command == "claude" and arguments.claude_command == "list"
    ) or (
        arguments.command == "augment" and arguments.augment_command == "list"
    ) or augment_discovery
    from .layout import (
        discovery_operation_lock,
        operation_lock,
        stable_home_lock,
    )

    with stable_home_lock(root) as home_lock:
        if arguments.command == "doctor":
            from .doctor import doctor

            return doctor(root, fix=arguments.fix)
        project_scope = (
            arguments.command == "codex" and (
                arguments.codex_scope == "project" or (
                    arguments.codex_command == "list" and arguments.codex_scope == "all"
                )
            )
        )
        if augment_discovery or project_scope or arguments.command == "_project-hook":
            with discovery_operation_lock(root) as lock_file:
                status = dispatch_locked_command(
                    root, arguments, home_lock, lock_file, command_parser
                )
            return 0 if status is None else status
        with operation_lock(root, create=not inspection) as lock_file:
            status = dispatch_locked_command(
                root, arguments, home_lock, lock_file, command_parser
            )
    return 0 if status is None else status


def report_command_errors(command, errors):
    for error in errors or ():
        print(format_command_error(command, error), file=sys.stderr)
    return 1 if errors else 0


def format_command_error(command, error, unexpected=False):
    from .metadata import printable_text

    if command == "doctor":
        message = f"doctor inspection failed: {error}" if unexpected else error
        return f"skillset: error: {printable_text(message)}"
    prefix = "operation failed: " if unexpected else ""
    return f"skillset: {prefix}{printable_text(error)}"


def main():
    command_parser = parser()
    arguments = command_parser.parse_args()
    if arguments.command == "completions":
        from .completions import emit_completions

        emit_completions(arguments.shell)
        return 0
    root = Path.home() / ".agents"
    try:
        return run_managed_command(root, arguments, command_parser)
    except ClaudeInterrupted as error:
        from .metadata import printable_text

        print(
            f"skillset: interrupted: {printable_text(error.message)}",
            file=sys.stderr,
        )
        return 130
    except OperationalError as error:
        print(format_command_error(arguments.command, error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("skillset: interrupted", file=sys.stderr)
        return 130
    except Exception as error:
        print(
            format_command_error(arguments.command, error, unexpected=True),
            file=sys.stderr,
        )
        return 1
