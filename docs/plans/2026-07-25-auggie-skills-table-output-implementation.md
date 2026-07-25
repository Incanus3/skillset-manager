# Auggie Skills Table Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `subagent-driven-development` (recommended) or `executing-plans` to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render normal Auggie skill discovery as a colored table while keeping
verbose discovery diagnostics non-tabular and color-aware.

**Architecture:** Add a small rendering layer in `augment_discovery.py` that
uses existing `metadata` display-width and styling helpers. It receives already
resolved, sorted winners and renders either a normal table or current verbose
blocks, without altering discovery or path semantics.

**Tech Stack:** Python 3 standard library; existing metadata ANSI utilities;
`unittest` black-box CLI tests.

## Global Constraints

- Follow `docs/specs/2026-07-25-auggie-skills-table-output-design.md` exactly.
- Preserve source-then-resolved-directory ordering, discovery precedence, filtering, paths,
  errors, escaping, read-only behavior, and verbose detail lines.
- Normal output uses `SKILL | SOURCE | DIRECTORY` with concise `~/...` and
  `./...` source labels; verbose retains bracketed concise labels and no table.
- Colors appear only through `metadata.color_enabled(output)`; cyan is skill
  and `~/...`, green is `./...`, headers are bold, dividers/separators dim.
- Do not add dependencies, mutate roots, or commit without authorization.

---

### Task 1: Render and test Auggie discovery tables

**Files:**
- Modify: `lib/skillset/augment_discovery.py:92-125`
- Modify: `tests/test_skillset.py:7972-8344`
- Modify: `README.md:575-599`

**Interfaces:**
- Add a source-display helper mapping `User/...` labels to `~/...` and
  `Workspace/...` labels to `./...`.
- Add a renderer for normal table rows and a colored verbose first-line renderer.
- Reuse `metadata.display_width`, `pad_display`, `styled`, `color_enabled`,
  `terminal_width`, `BOLD`, `DIM`, `CYAN`, and `GREEN`.

- [x] **Step 1: Write failing normal-table and TTY-color tests.**

  Add black-box fixtures containing one User and one Workspace winner. Assert
  captured normal output has exactly `SKILL | SOURCE | DIRECTORY` header,
  display-width-aligned separator and rows, source values `~/.augment` and
  `./.agents`, and no ANSI. Run through `run_cli_tty` and assert bold headers,
  dim divider/separator, cyan skill plus `~/.augment`, and green `./.agents`.
  Add `NO_COLOR` and `TERM=dumb` cases equal to plain output. Add verbose tests
  asserting no header/table, concise bracketed labels, first-line colors, and
  unchanged detail lines.

- [x] **Step 2: Establish RED.**

  Run the new focused table and verbose tests with `python -m unittest`.
  Expected: normal output still has unheaded free-form lines and verbose has
  old labels/no ANSI styling.

- [x] **Step 3: Implement normal and verbose renderers.**

  Convert source labels through a prefix-safe helper. For normal mode, build
  printable plain cells, calculate column widths with `metadata.display_width`,
  print a bold header and dim separator, and style individual skill/source
  segments only when color is enabled. Limit only the TTY separator via
  `metadata.terminal_width`. For verbose mode, retain current block order and
  detail strings; replace only the first-line construction with separately
  styled skill and bracketed concise source label.

- [x] **Step 4: Verify focused output behavior.**

  Run the focused normal, TTY, opt-out, verbose, control-character, ordering,
  and snapshot test methods. Expected: all pass with no ANSI in captured output
  and exact approved ANSI codes in eligible TTY output.

- [x] **Step 5: Document the output formats.**

  Update README to describe the normal table columns, concise source labels,
  TTY-only colors, and verbose mode's retained non-tabular diagnostics.

- [x] **Step 6: Complete verification and review.**

  Run `python -m unittest discover -s tests` and `git diff --check`; inspect
  `but diff`. Record RED/GREEN/full-suite evidence, request independent task
  and final reviews, and do not commit without explicit authorization.

## Execution evidence

- RED: the initial focused discovery-list selection failed only on the absent
  table, concise-label, and TTY-style behavior after fixture corrections.
- GREEN: 20 focused Auggie discovery-list tests passed, including TTY colors,
  opt-outs, verbose diagnostics, display width, controls, ordering, snapshots,
  advisory-lock blocking, replacement safety, and unavailable-lock fallback.
- Reviews: the table task and descriptor-safe advisory-lock follow-up both
  received independent review and re-review approval with no remaining
  findings; the final whole-branch review also found no findings.
- Full verification: `python -m unittest discover -s tests` passed 237 tests
  with 2 expected skips; `git diff --check` passed.
- Decision: normal table headers and dividers have no leading spaces because
  the `skillset list -v` indentation is reserved for its selected-item marker.
- No dependencies or discovery roots were mutated. The completed work was
  committed as GitButler change `vtv` on `augment-support`.