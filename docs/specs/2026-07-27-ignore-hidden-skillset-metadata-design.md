# Ignore hidden skillset-container metadata

## Context

`skillset` stores managed skillsets as direct children of the runtime's
`skillsets/` directory. The container may also be version controlled, which
creates hidden metadata such as `.git/`. Current enumeration validates every
entry as a skillset name, so `skillset list` and layout validation reject such
metadata with an invalid-name error.

## Goal

Permit user-managed hidden metadata under `skillsets/` without treating it as a
skillset or displaying it in command output.

## Non-goals

- Hidden names do not become valid skillset names for `init`, `create`, `use`,
  `rename`, `remove`, or other explicit name-taking commands.
- The change does not alter validation of visible entries.
- The change does not suppress tool-owned stale staging recovery errors.

## Design

Container enumeration distinguishes two categories of dot-prefixed entries:

1. A `.skillset-create-<name>.staging` entry is an internal interrupted-create
   artifact. It remains an operational error that requires recovery.
2. Every other dot-prefixed entry is user metadata. Validation and listings
   skip it without reading or validating its contents.

Visible entries retain the current name validation and managed/manual-set
validation behavior. Therefore, user metadata cannot shadow, activate, or be
addressed as a skillset.

## Implementation boundary

- `lib/skillset/layout.py`: retain the stale-create check, then omit other
  hidden entries from `validate_skillset_entries`.
- `lib/skillset/doctor.py`: retain the stale-create finding, then omit other
  hidden entries from diagnostic enumeration.
- `lib/skillset/metadata.py`: omit hidden entries when `list_sets` gathers
  names for normal and verbose output.
- `tests/test_skillset.py`: add focused coverage for hidden metadata during
  `doctor` and both list modes; preserve existing stale-create coverage.

## Acceptance criteria

- A `skillsets/.git/` directory does not make `skillset doctor` fail.
- `skillset list` and `skillset list --verbose` succeed and omit `.git`.
- A visible valid skillset remains listed and active as before.
- A `.skillset-create-<name>.staging` entry continues to make validation fail.
- Creating a dot-prefixed skillset or renaming a skillset to one fails name
  validation.

## Verification

Run the focused hidden-metadata and stale-create tests, followed by
`python3 -m unittest tests/test_skillset.py`.