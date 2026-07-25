"""Read effective Auggie skills without managing their source roots."""

import stat
import sys
from dataclasses import dataclass
from pathlib import Path

from . import metadata
from .errors import OperationalError


@dataclass(frozen=True)
class DiscoveryRoot:
    label: str
    scope: str
    path: Path


@dataclass(frozen=True)
class EffectiveSkill:
    name: str
    source: DiscoveryRoot
    path: Path


def discovery_roots(root):
    home = root.parent
    workspace = Path.cwd()
    return (
        DiscoveryRoot("User/.augment", "global", home / ".augment" / "skills"),
        DiscoveryRoot(
            "Workspace/.augment", "local", workspace / ".augment" / "skills"
        ),
        DiscoveryRoot("User/.claude", "global", home / ".claude" / "skills"),
        DiscoveryRoot(
            "Workspace/.claude", "local", workspace / ".claude" / "skills"
        ),
        DiscoveryRoot("User/.agents", "global", home / ".agents" / "skills"),
        DiscoveryRoot(
            "Workspace/.agents", "local", workspace / ".agents" / "skills"
        ),
    )


def skill_candidates(source):
    try:
        source.path.lstat()
    except FileNotFoundError:
        return ()
    except OSError as error:
        raise OperationalError(
            f"could not inspect Auggie skill root {source.path}: {error}"
        ) from error
    try:
        entries = sorted(source.path.iterdir(), key=lambda entry: entry.name)
    except OSError as error:
        raise OperationalError(
            f"could not inspect Auggie skill root {source.path}: {error}"
        ) from error
    candidates = []
    for entry in entries:
        try:
            metadata = entry.stat()
        except OSError as error:
            raise OperationalError(
                f"could not inspect Auggie skill candidate {entry}: {error}"
            ) from error
        if not stat.S_ISDIR(metadata.st_mode):
            continue
        skill_file = entry / "SKILL.md"
        try:
            skill_metadata = skill_file.stat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise OperationalError(
                f"could not inspect Auggie skill candidate {skill_file}: {error}"
            ) from error
        if stat.S_ISREG(skill_metadata.st_mode):
            candidates.append(EffectiveSkill(entry.name, source, entry))
    return tuple(candidates)


def effective_skills(root):
    winners = {}
    for source in discovery_roots(root):
        for candidate in skill_candidates(source):
            winners.setdefault(candidate.name, candidate)
    return tuple(winners[name] for name in sorted(winners))


def display_skill_path(path: Path, home: Path) -> Path | str:
    try:
        relative = path.relative_to(home)
    except ValueError:
        return path
    return Path("~") / relative if relative.parts else "~"


def display_source_label(label):
    if label.startswith("User/"):
        return "~/" + label.removeprefix("User/")
    if label.startswith("Workspace/"):
        return "./" + label.removeprefix("Workspace/")
    return label


def source_color(source):
    label = source.removeprefix("[")
    if label.startswith("~/"):
        return metadata.CYAN
    if label.startswith("./"):
        return metadata.GREEN
    return None


def style_source(source, colored):
    color = source_color(source)
    if color is None:
        return source
    return metadata.styled(source, color, colored)


def render_skill_table(rows, output):
    if not rows:
        return
    headers = ("SKILL", "SOURCE", "DIRECTORY")
    widths = tuple(
        max(
            metadata.display_width(header),
            *(metadata.display_width(row[index]) for row in rows),
        )
        for index, header in enumerate(headers)
    )
    colored = metadata.color_enabled(output)
    divider = metadata.styled("|", metadata.DIM, colored)
    plain_header = " | ".join(
        metadata.pad_display(header, width)
        for header, width in zip(headers, widths)
    )
    header_cells = tuple(
        metadata.styled(header, metadata.BOLD, colored)
        + metadata.pad_display("", width - metadata.display_width(header))
        for header, width in zip(headers, widths)
    )
    print(f" {divider} ".join(header_cells), file=output)
    separator = "".join("|" if character == "|" else "-" for character in plain_header)
    terminal_width = metadata.terminal_width(output)
    if terminal_width is not None:
        separator = separator[:terminal_width]
    print(metadata.styled(separator, metadata.DIM, colored), file=output)
    for skill, source, directory in rows:
        skill_cell = metadata.styled(skill, metadata.CYAN, colored)
        skill_cell += metadata.pad_display(
            "", widths[0] - metadata.display_width(skill)
        )
        source_cell = style_source(source, colored)
        source_cell += metadata.pad_display(
            "", widths[1] - metadata.display_width(source)
        )
        print(f"{skill_cell} {divider} {source_cell} {divider} {directory}", file=output)


def render_verbose_skill_line(skill, source, directory, colored):
    source_label = f"[{source}]"
    return (
        f"{metadata.styled(skill, metadata.CYAN, colored)} "
        f"{style_source(source_label, colored)} {directory}"
    )


def list_effective_skills(root, verbose, scope, output=None):
    output = sys.stdout if output is None else output
    skills = [
        (skill, skill.path.resolve())
        for skill in effective_skills(root)
        if scope == "all" or skill.source.scope == scope
    ]
    home = root.parent.resolve()
    rows = []
    for skill, directory in sorted(
        skills,
        key=lambda item: (display_source_label(item[0].source.label), str(item[1])),
    ):
        skill_file = skill.path / "SKILL.md"
        displayed_directory = display_skill_path(directory, home)
        rows.append(
            (
                metadata.printable_text(skill.name),
                display_source_label(skill.source.label),
                metadata.printable_text(displayed_directory),
                directory,
                skill_file,
            )
        )
    if not verbose:
        render_skill_table(tuple(row[:3] for row in rows), output)
        return
    colored = metadata.color_enabled(output)
    for skill, source, displayed_directory, directory, skill_file in rows:
        print(
            render_verbose_skill_line(skill, source, displayed_directory, colored),
            file=output,
        )
        print(
            f"  resolved directory: {metadata.printable_text(directory)}",
            file=output,
        )
        print(
            f"  resolved SKILL.md: {metadata.printable_text(skill_file.resolve())}",
            file=output,
        )