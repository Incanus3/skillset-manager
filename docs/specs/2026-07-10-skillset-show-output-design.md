# Friendlier `skillset show` Design

## Purpose

Make `skillset show` convenient for interactive use without making redirected output unsafe or unpredictable. The command
will default to the active skillset, render a real two-column table, and add restrained terminal color.

This specification extends the inspection contract in `docs/specs/2026-07-10-named-skillsets-cli-design.md`.

## Repository context

- The CLI is a dependency-free Python program dispatched by `lib/skillset/cli.py`.
- `lib/skillset/metadata.py` validates the layout, inspects direct skill directories, sanitizes terminal controls with
  `printable_text`, and currently prints `<name> — <description>` lines.
- `validate_layout(root)` returns the active skillset name; `validate_set(root, name)` validates an explicit set.
- Existing integration coverage is in `tests/test_skillset.py` and captures stdout by default, so its normal output is
  non-interactive.
- At design time, Jujutsu's working copy has an unrelated added `skillsets/minimal/.skill-lock.json`. This work must not
  modify or remove that user change.
- Bead `agents-zgu` tracks this change.

No external research is needed; the design relies on Python and established terminal conventions.

## Command semantics

The accepted forms are:

- `skillset show`: inspect the active skillset.
- `skillset show NAME`: inspect `NAME`, whether active or inactive.

The `name` positional argument is optional in argparse and appears as `[name]` in command help. When omitted, `show`
uses the name returned by the existing full-layout validation. An explicit name continues through existing set
validation. Invalid layouts, missing sets, unsafe names, locking, exit statuses, stderr behavior, and read-only behavior
remain unchanged.

## Plain output contract

A non-empty set is printed as a borderless table with an inner `|` delimiter and a header separator:

```text
SKILL       | DESCRIPTION
------------|-------------------------------
alpha       | First skill
longer-name | Second skill
broken      | [invalid: missing description]
```

There is no left or right outer border. The left and right column widths are the maximum display widths of their header
and cell values. Header and data rows contain one space on each side of `|`. The separator contains enough dashes to
cover those spaces, so its `|` aligns with the row delimiters. Rows do not gain trailing whitespace after the final
cell.

Rows retain the current lexical ordering by their sanitized displayed skill or directory name. Valid rows use the
declared skill name and normalized description. Invalid rows use the directory name and the unchanged
`[invalid: REASON]` description.

On a TTY, the separator alone is capped to the current positive terminal-column count to prevent its dashes from
wrapping. Detect the width immediately before rendering and truncate the unstyled ASCII separator from the right;
headers, skill names, descriptions, and data rows remain complete and may wrap naturally. Apply dim styling after the
cap when color is enabled. The cap also applies when `NO_COLOR` is set or `TERM=dumb`; pipes, redirects, unsupported
width detection, and nonpositive widths retain the complete separator.

An empty set prints exactly:

```text
No skills installed.
```

It does not print table headers. Every successful output ends with a newline. Redirected, piped, and captured output
contains no ANSI escapes.

## Width calculation

Alignment is calculated before styling and against sanitized display text. A small standard-library helper calculates
terminal cell width:

- combining characters contribute zero cells;
- Unicode East Asian `W` and `F` characters contribute two cells;
- other printable characters contribute one cell.

Padding uses the difference between the target cell width and the measured cell width. This handles common combining
and wide-character names without a dependency. Exact grapheme width for every emoji sequence is out of scope.

## Interactive color contract

Color is enabled only when all of these conditions hold:

- stdout reports that it is a TTY;
- `NO_COLOR` is absent from the environment;
- `TERM` is not `dumb`.

No `--color` or `--no-color` option is added. Generated ANSI escapes are applied only after all user-controlled text has
passed through `printable_text`, preserving the existing terminal-injection protection.

When color is enabled:

- both header cells are bold;
- valid skill names are cyan;
- `[invalid: missing description]` is yellow;
- every other invalid description is red;
- every row's `|` delimiter is dim;
- the complete header separator line is dim;
- `No skills installed.` is dim.

Styles must reset at cell boundaries so they cannot leak into padding, adjacent cells, or following terminal output.
Color changes presentation only. In particular, a missing description remains textually invalid, and `skillset doctor`
classification and exit behavior do not change.

## Implementation boundaries

Expected changes are limited to:

- `lib/skillset/cli.py`: make the `show` positional optional and pass the absent value through dispatch.
- `lib/skillset/metadata.py`: resolve an omitted name, build structured rows, measure display width, format the table,
  and apply optional output styling.
- `tests/test_skillset.py`: update output contracts and add omitted-name, alignment, color, and empty-state coverage.
- `README.md`: document optional `NAME`, the table, empty state, and automatic color behavior.
- `docs/specs/2026-07-10-named-skillsets-cli-design.md`: update the superseded one-line `show` output contract.

No package or runtime dependency is introduced. Existing metadata parsing and filesystem traversal should not be
refactored beyond what the formatter needs.

## Verification strategy

Tests must establish:

1. `skillset show` selects the active set before and after `skillset use`.
2. `skillset show NAME` still selects an explicitly named inactive set.
3. Help presents `name` as optional.
4. Valid and invalid rows have aligned delimiters and the exact header separator.
5. Common wide and combining Unicode names align by display cells.
6. An empty set prints only `No skills installed.`.
7. Captured stdout remains plain and contains no ANSI escapes.
8. A pseudo-terminal receives the specified ANSI styles, including dim delimiters.
9. `NO_COLOR` and `TERM=dumb` independently suppress ANSI styles in a pseudo-terminal.
10. Missing descriptions are yellow while all other invalid reasons are red.
11. Existing control-character escaping and symlink-safety tests continue to pass.

Run the smallest show-focused tests while iterating, then the complete test file. The final verification commands and
their exit codes belong in the implementation report.

## Rejected alternatives and trade-offs

- A third-party table or color library would improve advanced grapheme and terminal-width handling, but adds dependency
  and packaging overhead disproportionate to this fixed two-column output.
- Tabs are simpler but depend on terminal tab stops and do not align predictably for long or wide names.
- Always emitting color would contaminate pipes, files, and command substitutions.
- Header-only empty output is structurally consistent but less explanatory; completely empty output preserves the old
  contract but is not user-friendly.
- A `+` header junction is conventional but visually disconnects from the `|` delimiters above and below. The approved
  separator therefore uses `|` at the junction.
- Outer borders add visual noise and are intentionally omitted.

## Implementation checklist

1. Add or update tests first, including red tests for omitted `NAME`, exact plain output, and TTY styling.
2. Implement optional active-set resolution without weakening layout validation.
3. Add structured formatting and display-cell width calculation.
4. Add post-sanitization, TTY-aware styling and environment opt-outs.
5. Update README and the original inspection contract.
6. Run focused tests and the full test file; inspect the final diff without disturbing unrelated working-copy changes.
