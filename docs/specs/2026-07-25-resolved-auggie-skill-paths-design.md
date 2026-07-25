# Resolved Auggie Skill Paths Design

**Date:** 2026-07-25
**Status:** Implemented and verified

## Summary

Make `skillset augment skills list` show each effective skill's canonical
directory instead of the discovery entry. This makes managed flat projections
useful to inspect: a skill discovered through
`~/.augment/skills/<name>` reports its physical skillset directory, such as
`~/.agents/skillsets/personal/skills/<name>`.

The command remains read-only. Discovery precedence, candidate eligibility,
source labels, scope filtering, and error behavior are unchanged.

## Observed behavior

`lib/skillset/augment_discovery.py` currently keeps a discovered child entry
in `EffectiveSkill.path`. Standard output prints that path, which is often a
managed projection symlink. Verbose output separately calls `Path.resolve()`
for the directory and its `SKILL.md` file.

The existing focused test in `tests/test_skillset.py` creates a managed skill
symlink and confirms that only verbose output shows its target. `README.md`
currently describes the standard output as a discovered directory path.

## Required behavior

For every effective winner that passes the optional scope filter:

1. Resolve its directory with the existing `Path.resolve()` behavior.
2. Display the resolved directory in the standard output line after the
   unchanged skill name and source label.
3. If the resolved directory is within the configured home directory, render
   it with a leading `~`, preserving its relative suffix. For example,
   `/home/jakub/.agents/skillsets/personal/skills/characterization-test`
   becomes `~/.agents/skillsets/personal/skills/characterization-test`.
4. Display resolved directories outside home as absolute paths.
5. Continue escaping non-printable text with `metadata.printable_text`.

`--verbose` continues to include explicit resolved-directory and resolved
`SKILL.md` lines. Its first line follows the same normal-output contract, so
the directory line is intentionally redundant but remains a compatible verbose
detail.

## Boundaries and alternatives

Resolution occurs at rendering time rather than during discovery. This retains
the discovered entry for the source label and candidate handling while changing
only the presentation contract. A dedicated display helper should own
home-relative formatting so that containment checks do not use unsafe string
prefix matching.

Resolving only managed links was rejected because compatible discovery roots
may also contain symlinks. Storing resolved paths in `EffectiveSkill` was
rejected because it unnecessarily changes the discovery data model.

Expected changes are limited to:

- `lib/skillset/augment_discovery.py` for resolved-directory formatting and
  normal output;
- `tests/test_skillset.py` for the regression contract; and
- `README.md` to describe displayed directories as resolved paths.

## Verification strategy

Use test-first development. Add a focused test that creates a managed
projection symlink and expects normal output to contain the home-abbreviated
target. Run it before production changes and confirm it fails because the link
path is still shown. Then implement the minimal formatter and run the focused
test again.

The regression coverage must also establish that source labels and precedence
do not change, a path outside home remains absolute, verbose output keeps its
existing details, and the read-only command leaves its filesystem snapshots
unchanged. Run the narrow discovery tests followed by the full unittest suite.

## Implementation checklist

1. Read this design before changing code.
2. Add and run the focused failing test.
3. Implement only the display-time resolution and safe home abbreviation.
4. Update README language and adjust affected expectations.
5. Run focused and complete test suites; inspect the diff without altering
   unrelated workspace changes.