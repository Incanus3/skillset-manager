# Auggie Skills Table Output Design

**Date:** 2026-07-25
**Status:** Implemented and verified

## Summary

Format normal `skillset augment skills list` output as a three-column table
and apply terminal-aware color. Keep `--verbose` as its existing diagnostic
layout, but colorize its first line without adding a table or header.

## Normal-output contract

Normal output has bold headers and aligned columns:

```text
SKILL | SOURCE         | DIRECTORY
------|----------------|------------------------
alpha | ~/.augment     | ~/.agents/.../alpha
```

The table has no leading indentation: unlike `skillset list -v`, it has no
selected-item marker to reserve space for.

The columns are `SKILL`, `SOURCE`, and `DIRECTORY`. `SOURCE` uses concise
discovery-root labels such as `~/.augment`, `./.claude`, and `~/.agents`;
table rows do not wrap those labels in brackets. Rows sort first by concise
source label, then by resolved directory. Display formatting and
candidate/precedence semantics remain unchanged.

Column widths use the repository's display-width handling so escaped controls,
combining characters, and wide characters align correctly. As in `skillset
list -v`, a TTY separator may be capped to terminal width but data rows remain
complete.

## Color contract

Use the existing `metadata.color_enabled(output)` policy: colors are emitted
only to TTY output when `NO_COLOR` is absent and `TERM` is not `dumb`.

- headers: bold;
- divider and separator: dim;
- skill name: cyan (`\x1b[36m`);
- `~/...` source: cyan (`\x1b[36m`), matching existing global `[g]`;
- `./...` source: green (`\x1b[32m`), matching existing local `[l]`.

Captured output and opted-out TTY output remain byte-for-byte plain text.

## Verbose-output contract

`augment skills list --verbose` retains its non-tabular multi-line blocks and
does not print a header. Its first line keeps the existing skill, bracketed
source-label, and directory shape, but uses concise labels such as
`[~/.augment]` and `[./.agents]`. In eligible TTY output, color the skill name
cyan and color the bracketed `~/...` source label cyan or `./...` label green.
Resolved-directory and resolved-`SKILL.md` diagnostic lines are unchanged.

## Boundaries and verification

Implement focused formatting helpers in `lib/skillset/augment_discovery.py`,
reusing metadata styling and display-width utilities rather than duplicating
terminal policy. Update black-box tests for exact plain tables, eligible-TTY
styles, color opt-outs, verbose non-tabular layout, source colors, controls,
and read-only snapshots. Update README to describe columns, color policy, and
the distinct verbose layout. Use test-first development, run focused tests,
the complete unittest suite, and `git diff --check`; do not add dependencies,
mutate discovery roots, or commit without authorization.

## Implementation evidence

Implemented in `lib/skillset/augment_discovery.py` with black-box coverage in
`tests/test_skillset.py` and documentation in `README.md`. The additional
read-only advisory-lock safety follow-up uses descriptor-relative no-follow
locking for an existing managed root while preserving discovery without a
managed layout. Main-session verification on 2026-07-25 passed 21 focused
discovery-list tests, 237 complete unittest tests with 2 expected skips, and
`git diff --check`.