# Auggie Skills Resolved-Path Ordering Design

**Date:** 2026-07-25
**Status:** Implemented and verified

## Summary

Change `skillset augment skills list` from name-order output to lexicographic
order by each effective skill's canonical absolute directory. This order uses
the physical resolved target, not the symlink discovery entry or the path's
`~`-abbreviated display form.

## Current behavior

`effective_skills()` selects the first effective winner for each skill name and
returns winners in name order. `list_effective_skills()` then filters those
winners by scope and resolves each directory only while rendering it. The
previous display-path work makes the standard output show resolved locations,
but does not change its name-based ordering.

## Required behavior

For every scope-filtered effective winner:

1. Resolve the directory once with `Path.resolve()`.
2. Sort the retained entries first by concise source label, then
   lexicographically by canonical absolute directory path.
3. Render the already-resolved directory with the existing home-relative `~`
   display formatter.

The later table-output design supersedes this design's original
directory-only ordering. Source-label ordering groups the table by the displayed
source, while the canonical resolved directory remains the sole ordering key
within each source group.

Discovery precedence, candidate eligibility, source labels, scope filtering,
error handling, printable-text escaping, and verbose resolved-directory and
`SKILL.md` detail lines remain unchanged. The command remains read-only.

## Implementation boundaries

- `lib/skillset/augment_discovery.py` owns rendering-time scope filtering,
  resolution, ordering, and display formatting. Leave `effective_skills()` in
  its existing name-based discovery contract.
- `tests/test_skillset.py` replaces the name-order assertion with a black-box
  directory-order assertion whose skill names intentionally oppose their
  resolved target directory order.
- `README.md` states that effective skills print in lexicographic canonical
  resolved-directory order.

## Verification

Test-first development was used: the focused ordering test was observed failing
under the name-order implementation before rendering-time ordering was added.
The focused four-test discovery regression group then passed. The full
`python -m unittest discover -s tests` suite passed 229 tests with 2 expected
skips. The tests verify source labels, canonical displayed paths, and read-only
filesystem snapshots.

## Constraints and rejected approaches

Sorting the `effective_skills()` return value was rejected because it changes a
discovery helper before scope filtering rather than the CLI output contract.
Sorting the `~`-abbreviated display text was rejected because it would not order
by the selected canonical physical path. Do not add dependencies, commits, or
filesystem mutations.