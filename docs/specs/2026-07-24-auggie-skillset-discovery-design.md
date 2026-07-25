# Auggie Skillset Discovery Design

**Date:** 2026-07-24
**Status:** Implemented; review follow-up in progress

## Summary

Add managed Auggie skillsets and an independent read-only view of the
effective individual skills that Auggie discovers. Auggie discovers only direct
child skill directories containing `SKILL.md`, so the managed integration must
flatten a skillset into one link per direct source skill, like the existing
Claude Code integration rather than the Codex collection-link integration.

```text
skillset augment enable NAME [-g|--global|-l|--local]
skillset augment disable NAME [-g|--global|-l|--local]
skillset augment list [-v|--verbose] [-g|--global|-l|--local]
skillset augment skills list [-v|--verbose] [-g|--global|-l|--local]
```

`augment enable`, `disable`, and `list` have the same registration semantics as
their Claude Code counterparts: `enable` and `disable` default to global scope,
and an unscoped `list` combines global and exact-current-directory managed
registrations. `--global` and `--local` filter that view and are mutually
exclusive for every command.

`augment skills list` is deliberately a different view. It prints effective
individual skills rather than managed skillsets, along with each winning skill
directory's source location. It resolves all documented discovery roots before
applying its optional scope filter.

## Environment and evidence

- The workspace is `/home/jakub/.agents`, a normal checkout; the user chose
  to work in place.
- `skillsets/always-on/.skill-lock.json` already has an unrelated user
  modification and must remain untouched.
- The CLI is Linux-only standard-library Python. `bin/skillset` is the
  executable; implementation is under `lib/skillset`; its black-box suite is
  `tests/test_skillset.py`.
- `lib/skillset/claude.py` already implements a complete, security-sensitive
  flat-projection state machine. `lib/skillset/codex.py` instead links a whole
  collection and is unsuitable for Auggie.
- The official Auggie documentation enumerates discovery roots and direct
  skills at <https://docs.augmentcode.com/cli/skills#skill-locations>. The Agent Skills
  client guidance likewise specifies scanning direct subdirectories containing
  `SKILL.md`: <https://agentskills.io/client-implementation/adding-skills-support>.

## Scope and filesystem contract

The managed commands own Auggie-specific roots only. They do not manage
Auggie's compatible `.claude/skills` or `.agents/skills` roots.

| Scope | Product root | Projected skill directory | Registration directory |
| --- | --- | --- | --- |
| Global | `~/.augment` | `~/.augment/skills` | `~/.augment/.skillsets` |
| Local | `$PWD/.augment` | `$PWD/.augment/skills` | `$PWD/.augment/.skillsets` |

For a source at `~/.agents/skillsets/personal/skills`, enabling creates an
absolute registration link `.augment/.skillsets/personal` to that `skills`
directory and one absolute direct skill link per source child directory beneath
`.augment/skills`. The registration is deliberately outside the public skills
directory so Auggie cannot discover it as a skill.

All ownership and destructive-operation rules follow the existing Claude Code
implementation:

- only direct real source directories are projected; direct source symlinks are
  refused and direct non-directories are ignored;
- an owned projected link must have the same basename as its target and point
  to exactly `<registered-source>/<basename>` with an absolute canonical target;
- unrelated links, aliases, files, and directories are never replaced or
  removed;
- existing containers must be real directories; links, regular files, and
  other malformed containers fail without mutation;
- registration state provides recovery intent. Re-running `enable` reconciles
  direct source additions and removals; `disable` removes owned projection
  links first and the registration last;
- final removal of a staged link or an empty private removal quarantine has an
  unavoidable portable POSIX name-based interval after identity validation.
  The mode-700 random quarantine isolates other users; exploiting that interval
  requires a hostile same-UID actor able to modify the owner's `.augment`
  namespace. Eliminating it requires platform-specific primitives or a
  preserve-only policy that leaves empty markers to block further mutation;
- collisions across effective global and exact-local projections are rejected
  unless the existing link has the exact same canonical target;
- global enabled or malformed Auggie registration state blocks rename and
  removal of the affected skillset, preventing stale links.

Compatible-root skills are unmanaged external state. `augment enable` and
`disable` must never create, modify, validate, remove, or register entries in
the compatible roots. A same-name compatible skill does not block an Auggie
projection: Auggie's documented precedence decides which skill wins. The
managed integration does continue to reject collisions between global and
exact-local `.augment` projections, because a different-target managed local
link would otherwise be unreachable.

The command leaves created containers in place when empty. Auggie loading or
session reloads are outside scope. Project-local generated links and
registrations contain machine-specific absolute paths and documentation must
advise against committing them.

## Effective-skill discovery contract

`skillset augment skills list` is read-only and independent of the managed
registration ledger. It scans these roots in the exact precedence order
documented by Auggie:

| Order | Source label | Root |
| --- | --- | --- |
| 1 | `User/.augment` | `~/.augment/skills` |
| 2 | `Workspace/.augment` | `$PWD/.augment/skills` |
| 3 | `User/.claude` | `~/.claude/skills` |
| 4 | `Workspace/.claude` | `$PWD/.claude/skills` |
| 5 | `User/.agents` | `~/.agents/skills` |
| 6 | `Workspace/.agents` | `$PWD/.agents/skills` |

This inspection does not require, validate, or create the managed
`~/.agents` layout or its advisory lock. It remains available when skillset
management has not been initialized.

For every existing root, inspect only direct children. A child is a candidate
when it is a directory, including a projected managed symlink, with a
`SKILL.md` file. The first candidate for a directory-name skill identifier is
effective; lower-precedence same-name candidates are omitted. This command must
not reimplement Auggie's frontmatter validation or mutate any root. Missing
roots contribute no candidates. Existing roots or candidate entries that cannot
be inspected fail with a diagnostic rather than silently omitting a possibly
effective skill.

Normal output prints effective skills in a `SKILL | SOURCE | DIRECTORY` table.
The directory is the resolved skill-directory path, and rows sort first by
concise source label and then by resolved directory. `--verbose` retains
non-tabular diagnostic blocks with resolved directory and `SKILL.md` paths
while remaining limited to effective skills; it is not a shadowed-candidate
debugger.

Resolution always evaluates all six roots. Only after resolving winners do the
scope flags filter results: `--global` retains winners from User roots and
`--local` retains winners from Workspace roots. A workspace skill shadowed by a
User skill must not be reported as effective by `--local`.

## Implementation boundaries

- Create `lib/skillset/augment.py` as a narrow Auggie-specific copy of the
  existing hardened Claude projection implementation. Preserve its filesystem
  algorithm, validation, recovery, and interruption behavior; substitute only
  product identity, `.augment` paths, and diagnostics.
- Create a small read-only Auggie discovery component that owns the six-root
  precedence scan, effective-name de-duplication, scope filtering, and output.
  Keep it separate from the transaction-sensitive projection implementation so
  compatible-root inspection cannot acquire ownership of external state.
- Update `lib/skillset/cli.py` for parsing, dispatch, and read-only inspection
  lock detection, including the nested `augment skills list` command.
- Update `lib/skillset/operations.py` so global Auggie registrations participate
  in lifecycle safety checks alongside Codex and Claude Code.
- Update all Bash, Zsh, and Fish source strings in `lib/skillset/completions.py`.
- Update `README.md` with the managed command surface, flat-link layout,
  reconciliation, scopes, local runtime-state warning, and the distinct
  effective-skill discovery view and source labels.
- Extend `tests/test_skillset.py` by mirroring the full existing Claude Code
  behavioral coverage with Auggie-specific paths, commands, and diagnostics.
  Add focused discovery tests for all six roots, every relevant precedence
  pair, post-resolution scope filtering, managed projection symlinks, missing
  roots, inspection failures, and absence of filesystem mutation.

## Verification

Use test-first development: add a focused Auggie behavior test, run it and
observe failure because the command is absent, add only the required production
implementation, and re-run it. Mirror all Claude safety tests before claiming
completion. Run discovery-specific tests, then the complete unittest suite and
generated-completion tests. Inspect the final diff to confirm the unrelated
`.skill-lock.json` is not part of this feature.