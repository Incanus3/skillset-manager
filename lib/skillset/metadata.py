import json
import os
import re
import stat
import sys
import unicodedata

from .layout import (
    set_mode,
    set_path,
    validate_layout,
    validate_set,
    validate_skillsets_directory,
)


TARGET_FIELD_PATTERN = re.compile(r"(name|description):[ \t]*(.*)\Z")
BLOCK_SCALAR_MARKERS = {"|", ">", "|-", "|+", ">-", ">+"}


def normalize_scalar(value):
    return " ".join(value.split())


def parse_single_quoted(field, value):
    decoded = []
    index = 1
    while index < len(value):
        character = value[index]
        if character != "'":
            decoded.append(character)
            index += 1
        elif index + 1 < len(value) and value[index + 1] == "'":
            decoded.append("'")
            index += 2
        else:
            trailing = value[index + 1 :].strip()
            if trailing and not trailing.startswith("#"):
                return None, f"unsupported single-quoted {field}"
            return "".join(decoded), None
    return None, f"unterminated single-quoted {field}"


def closing_double_quote(value):
    escaped = False
    for index, character in enumerate(value[1:], start=1):
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == '"':
            return index
    return None


def parse_double_quoted(field, value):
    closing = closing_double_quote(value)
    if closing is None:
        return None, f"unterminated double-quoted {field}"
    trailing = value[closing + 1 :].strip()
    if trailing and not trailing.startswith("#"):
        return None, f"unsupported double-quoted {field}"
    encoded = value[: closing + 1]
    encoded = encoded.replace("\r", "\\r").replace("\n", "\\n")
    encoded = encoded.replace("\t", "\\t")
    try:
        decoded = json.loads(encoded)
    except json.JSONDecodeError:
        return None, f"unsupported double-quoted {field}"
    if not isinstance(decoded, str):
        return None, f"unsupported double-quoted {field}"
    return decoded, None


def strip_plain_comments(value):
    lines = []
    for line in value.splitlines():
        for index, character in enumerate(line):
            if character == "#" and (index == 0 or line[index - 1].isspace()):
                line = line[:index]
                break
        lines.append(line)
    return "\n".join(lines)


def parse_inline_scalar(field, raw):
    value = raw.strip()
    if not value:
        return None, f"empty {field}"
    if value.startswith("'"):
        value, reason = parse_single_quoted(field, value)
        if reason is not None:
            return None, reason
    elif value.startswith('"'):
        value, reason = parse_double_quoted(field, value)
        if reason is not None:
            return None, reason
    else:
        if value[0] in "[{&*!|>":
            return None, f"unsupported {field} scalar"
        value = strip_plain_comments(value)
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return None, f"unsupported unicode {field}"
    value = normalize_scalar(value)
    if not value:
        return None, f"empty {field}"
    return value, None


def collect_target_fields(lines):
    fields = {"name": [], "description": []}
    index = 0
    while index < len(lines):
        match = TARGET_FIELD_PATTERN.fullmatch(lines[index])
        index += 1
        if match is None:
            continue
        field, raw = match.groups()
        continuation = []
        while index < len(lines):
            line = lines[index]
            if line and not line[0].isspace():
                break
            continuation.append(line)
            index += 1
        if raw in BLOCK_SCALAR_MARKERS:
            fields[field].append(("block", "\n".join(continuation)))
        else:
            fields[field].append(("inline", "\n".join([raw, *continuation])))
    return fields


def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None, "invalid frontmatter opening delimiter"
    try:
        closing = lines.index("---", 1)
    except ValueError:
        return None, "invalid frontmatter: missing closing delimiter"
    fields = collect_target_fields(lines[1:closing])
    for field in ("name", "description"):
        if not fields[field]:
            return None, f"missing {field}"
        if len(fields[field]) != 1:
            return None, f"duplicate {field}"
    metadata = {}
    for field in ("name", "description"):
        form, raw = fields[field][0]
        if form == "block":
            value = normalize_scalar(raw)
            reason = None if value else f"empty {field}"
        else:
            value, reason = parse_inline_scalar(field, raw)
        if reason is not None:
            return None, reason
        metadata[field] = value
    return metadata, None


def read_skill_text(directory):
    directory_flags = os.O_RDONLY | os.O_DIRECTORY
    file_flags = os.O_RDONLY
    try:
        directory_fd = os.open(directory, directory_flags)
    except OSError:
        return None, "unsupported skill directory"
    try:
        try:
            metadata = os.stat("SKILL.md", dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None, "missing SKILL.md"
        except OSError:
            return None, "unsupported SKILL.md"
        if stat.S_ISLNK(metadata.st_mode):
            return None, "unsupported SKILL.md symlink"
        if not stat.S_ISREG(metadata.st_mode):
            return None, "unsupported SKILL.md file type"
        try:
            file_fd = os.open("SKILL.md", file_flags, dir_fd=directory_fd)
        except OSError:
            return None, "unsupported SKILL.md"
        try:
            chunks = []
            while True:
                chunk = os.read(file_fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
        except OSError:
            return None, "unsupported SKILL.md read"
        finally:
            os.close(file_fd)
        try:
            return b"".join(chunks).decode("utf-8"), None
        except UnicodeDecodeError:
            return None, "invalid UTF-8 in SKILL.md"
    finally:
        os.close(directory_fd)


def inspect_skill_entry(candidate):
    try:
        mode = candidate.lstat().st_mode
    except OSError:
        return candidate.name, None, None, "unsupported candidate"
    if stat.S_ISREG(mode):
        return None
    if stat.S_ISLNK(mode):
        return candidate.name, None, None, "unsupported skill directory symlink"
    if not stat.S_ISDIR(mode):
        return None
    text, reason = read_skill_text(candidate)
    metadata = None
    if reason is None:
        metadata, reason = parse_frontmatter(text)
    if reason is None:
        return candidate.name, metadata["name"], metadata["description"], None
    return candidate.name, None, None, reason


def inspect_skills(skills):
    inspected = []
    for candidate in sorted(skills.iterdir(), key=lambda path: path.name):
        entry = inspect_skill_entry(candidate)
        if entry is not None:
            inspected.append(entry)
    return inspected


def skill_entry_text(entry):
    display_name, annotation, _reason = entry
    if annotation is None:
        return display_name
    return f"{display_name} {annotation}" if display_name else annotation


def verbose_skill_entries(skills):
    entries = []
    for directory, declared, _description, reason in inspect_skills(skills):
        if reason is None:
            display_name = printable_text(declared)
            annotation = None
        else:
            display_name = printable_text(directory)
            annotation = f"[invalid: {reason}]"
        entries.append((display_name, annotation, reason))
    return sorted(entries, key=lambda entry: (entry[0], skill_entry_text(entry)))


def verbose_list_rows(root, names, active_name):
    return [
        (
            name == active_name,
            printable_text(name),
            set_mode(root, name) == "manual",
            verbose_skill_entries(set_path(root, name) / "skills"),
            None,
        )
        for name in names
    ]


def render_skill_entries(entries, colored):
    if not entries:
        return styled("(no skills)", DIM, colored)
    rendered = []
    for display_name, annotation, reason in entries:
        if rendered:
            rendered.append(", ")
        if reason is None:
            rendered.append(styled(display_name, CYAN, colored))
            continue
        if display_name:
            rendered.append(display_name + " ")
        code = YELLOW if reason == "missing description" else RED
        rendered.append(styled(annotation, code, colored))
    return "".join(rendered)


def verbose_list_column_widths(rows):
    skill_cells = [
        ", ".join(skill_entry_text(entry) for entry in entries)
        if entries
        else "(no skills)"
        for _active, _name, _manual, entries, _scope_label in rows
    ]
    left_width = max(
        [
            display_width("SKILLSET"),
            *(display_width(
                (f"[{scope_label}] {name}" if scope_label is not None else name)
                + (" [m]" if manual else "")
            )
              for _active, name, manual, _entries, scope_label in rows),
        ]
    )
    right_width = max(
        [display_width("SKILLS"), *(display_width(cell) for cell in skill_cells)]
    )
    return left_width, right_width


def render_verbose_list(rows, output):
    colored = color_enabled(output)
    left_width, right_width = verbose_list_column_widths(rows)
    divider = styled("|", DIM, colored)
    header_left = styled("SKILLSET", BOLD, colored)
    header_left += " " * (left_width - display_width("SKILLSET"))
    print(f"  {header_left} {divider} {styled('SKILLS', BOLD, colored)}", file=output)
    separator = "  " + "-" * (left_width + 1) + "|" + "-" * (right_width + 1)
    width = terminal_width(output)
    if width is not None:
        separator = separator[:width]
    print(styled(separator, DIM, colored), file=output)
    for active, name, manual, entries, scope_label in rows:
        displayed_name = f"[{scope_label}] {name}" if scope_label is not None else name
        if active:
            marker = styled("*", BOLD + CYAN, colored) + " "
            left_cell = styled(name, BOLD + CYAN, colored)
        else:
            marker = "  "
            if scope_label is None:
                left_cell = name
            else:
                scope_color = {"g": CYAN, "p": ORANGE, "p-": ORANGE, "l": GREEN}.get(scope_label, "")
                left_cell = (
                    styled(f"[{scope_label}]", scope_color, colored) + " " + name
                )
        if manual:
            left_cell += " " + styled("[m]", YELLOW, colored)
        displayed_name += " [m]" if manual else ""
        left_cell += " " * (left_width - display_width(displayed_name))
        print(
            f"{marker}{left_cell} {divider} {render_skill_entries(entries, colored)}",
            file=output,
        )


def list_named_sets(
    root, names, verbose, output=None, mark_active=True, *, sources=None
):
    output = sys.stdout if output is None else output
    active_name = validate_layout(root) if mark_active else None
    if sources is not None:
        return list_project_sources(sources, verbose, output)
    if not verbose:
        colored = color_enabled(output)
        for name in names:
            if name == active_name and colored:
                marker = styled("*", BOLD + CYAN, True) + " "
                displayed_name = styled(name, BOLD + CYAN, True)
            else:
                marker = "* " if name == active_name else ""
                displayed_name = name
            suffix = " [m]" if set_mode(root, name) == "manual" else ""
            if suffix and colored:
                suffix = " " + styled("[m]", YELLOW, True)
            print(f"{marker}{displayed_name}{suffix}", file=output)
        return
    render_verbose_list(
        verbose_list_rows(root, names, active_name), output
    )


def list_project_sources(sources, verbose, output=None, *, scoped=False):
    """Render inspected registration rows independently of managed layout health."""
    output = sys.stdout if output is None else output
    scope_label = "p" if scoped else None
    if verbose:
        render_verbose_list([_source_row(source, scope_label) for source in sources], output)
    else:
        _render_source_names(sources, output, scope_label=scope_label)


def list_scoped_sets(root, scoped_names, verbose, output=None, *, sources=()):
    output = sys.stdout if output is None else output
    validate_layout(root)
    rows = []
    source_views = {source.name: source for source in sources}
    for scope_label, names in scoped_names:
        for name in sorted(names):
            if scope_label == "p" and name in source_views:
                rows.append(_source_row(source_views[name], scope_label))
                continue
            rows.append(
                (
                    False,
                    printable_text(name),
                    set_mode(root, name) == "manual",
                    verbose_skill_entries(set_path(root, name) / "skills"),
                    scope_label,
                )
            )
    if verbose:
        render_verbose_list(rows, output)
        return
    colored = color_enabled(output)
    for _active, name, manual, _entries, scope_label in rows:
        scope_color = {"g": CYAN, "p": ORANGE, "p-": ORANGE, "l": GREEN}.get(scope_label, "")
        scope = styled(f"[{scope_label}]", scope_color, colored)
        suffix = " [m]" if manual else ""
        if suffix and colored:
            suffix = " " + styled("[m]", YELLOW, True)
        if scope_label in {"p", "p-"} and source_views[name].error is not None:
            suffix += " " + styled(f"[invalid: {source_views[name].error}]", RED, colored)
        print(f"{scope} {name}{suffix}", file=output)


def _source_row(source, scope_label):
    if scope_label == "p" and not source.installed:
        scope_label = "p-"
    entries = source.entries
    if source.error is not None:
        entries = (("", f"[invalid: {source.error}]", source.error),)
    return False, printable_text(source.name), source.manual, entries, scope_label


def _render_source_names(sources, output, *, scope_label=None):
    colored = color_enabled(output)
    for source in sources:
        suffix = " " + styled("[m]", YELLOW, colored) if source.manual else ""
        if source.error is not None:
            suffix += " " + styled(f"[invalid: {source.error}]", RED, colored)
        label = "p-" if scope_label == "p" and not source.installed else scope_label
        prefix = (
            styled(f"[{label}]", ORANGE, colored) + " "
            if scope_label is not None else ""
        )
        print(f"{prefix}{printable_text(source.name)}{suffix}", file=output)


def list_sets(root, verbose, output=None):
    skillsets = validate_skillsets_directory(root)
    names = sorted(
        entry.name for entry in skillsets.iterdir() if not entry.name.startswith(".")
    )
    return list_named_sets(root, names, verbose, output)


def current(root):
    print(validate_layout(root))


RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
CYAN = "\x1b[36m"
YELLOW = "\x1b[33m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
ORANGE = "\x1b[38;5;208m"


def display_width(value):
    width = 0
    for character in value:
        if unicodedata.combining(character):
            continue
        width += 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
    return width


def pad_display(value, width):
    return value + " " * (width - display_width(value))


def color_enabled(output):
    return (
        output.isatty()
        and "NO_COLOR" not in os.environ
        and os.environ.get("TERM") != "dumb"
    )


def terminal_width(output):
    try:
        if not output.isatty():
            return None
        columns = os.get_terminal_size(output.fileno()).columns
    except (AttributeError, OSError, ValueError):
        return None
    return columns if columns > 0 else None


def styled(value, code, enabled):
    return f"{code}{value}{RESET}" if enabled and code else value


def show_skill_rows(skills):
    rows = []
    for directory, declared, description, reason in inspect_skills(skills):
        left = printable_text(declared if reason is None else directory)
        right = printable_text(description) if reason is None else f"[invalid: {reason}]"
        rows.append((left, right, reason))
    return sorted(rows, key=lambda row: (row[0], row[1]))


def show_column_widths(rows):
    left_width = max(display_width("SKILL"), *(display_width(row[0]) for row in rows))
    right_width = max(
        display_width("DESCRIPTION"), *(display_width(row[1]) for row in rows)
    )
    return left_width, right_width


def render_show(rows, output):
    colored = color_enabled(output)
    if not rows:
        print(styled("No skills installed.", DIM, colored), file=output)
        return
    left_width, right_width = show_column_widths(rows)
    header_left = styled("SKILL", BOLD, colored)
    header_left += " " * (left_width - display_width("SKILL"))
    header_right = styled("DESCRIPTION", BOLD, colored)
    divider = styled("|", DIM, colored)
    print(f"{header_left} {divider} {header_right}", file=output)
    separator = "-" * (left_width + 1) + "|" + "-" * (right_width + 1)
    width = terminal_width(output)
    if width is not None:
        separator = separator[:width]
    print(styled(separator, DIM, colored), file=output)
    for left, right, reason in rows:
        left_cell = styled(left, CYAN, colored) if reason is None else left
        left_cell += " " * (left_width - display_width(left))
        if reason == "missing description":
            right_cell = styled(right, YELLOW, colored)
        elif reason is not None:
            right_cell = styled(right, RED, colored)
        else:
            right_cell = right
        print(f"{left_cell} {divider} {right_cell}", file=output)


def show(root, name, output=None):
    output = sys.stdout if output is None else output
    active_name = validate_layout(root)
    selected_name = active_name if name is None else name
    selected_mode = set_mode(root, selected_name)
    skills = validate_set(root, selected_name) / "skills"
    if selected_mode == "manual":
        print("Manual skillset [m]: no upstream lock metadata.", file=output)
    render_show(show_skill_rows(skills), output)


def printable_text(value):
    displayed = []
    for character in str(value):
        codepoint = ord(character)
        if unicodedata.category(character) in {"Cc", "Cf", "Zl", "Zp"}:
            if codepoint <= 0xFF:
                displayed.append(f"\\x{codepoint:02x}")
            elif codepoint <= 0xFFFF:
                displayed.append(f"\\u{codepoint:04x}")
            else:
                displayed.append(f"\\U{codepoint:08x}")
        else:
            displayed.append(character)
    return "".join(displayed).encode(
        "utf-8", "backslashreplace"
    ).decode("utf-8")
