# Skillset Module Extraction Design

## Purpose

Refactor the 1,154-line `bin/skillset` executable into focused private library modules while keeping the executable as a
minimal entry point. This is an internal, behavior-preserving change: the supported interface remains the `skillset` CLI,
not a new Python API.

## Repository state and context

- The implementation is currently contained entirely in `bin/skillset`.
- `tests/test_skillset.py` is a black-box `unittest` suite that invokes the executable under temporary `HOME`
  directories with `PYTHONPATH` removed.
- The repository is itself expected to live at `~/.agents`; the README adds `~/.agents/bin` directly to `PATH`.
- The CLI is Linux-only, uses Python 3 and the standard library, and relies on `fcntl`, Linux file-opening flags,
  symlinks, and process replacement.
- Historical designs included transactional filesystem hardening. The current
  local-CLI policy is `docs/guides/local-cli-reliability.md`; it supersedes that
  adversarial guidance while retaining ordinary functional recovery.
- The working copy was clean before this design was written. The parent commit was
  `a7d28ad1071a Add skillset diagnostics and hardening`.
- The earlier named-skillsets specification assigned every implementation responsibility to `bin/skillset`. This design
  supersedes only that file-boundary decision; all behavioral requirements remain unchanged.

## Requirements

1. Preserve commands, arguments, help behavior, standard streams, output text, exit statuses, filesystem effects,
   locking, rollback, interrupt handling, diagnostics, and upstream delegation exactly.
2. Keep `bin/skillset` as a directly executable script and reduce it to bootstrap/import/exit responsibilities.
3. Put implementation modules in a private `lib/skillset/` package organized by coherent responsibility.
4. Keep the implementation standard-library-only and avoid introducing packaging or installation metadata.
5. Ensure execution works from any current working directory with `PYTHONPATH` unset.
6. Preserve clear ownership of locks, file descriptors, staging paths, rollback, and delegated process lifetime.
7. Avoid cyclic imports and avoid exposing a supported Python API.
8. Do not combine the extraction with unrelated behavior changes or general cleanup.

## Architecture

### Entry point

`bin/skillset` will contain only:

- the Python shebang;
- resolution of the repository-relative `lib` directory from the real executable file path;
- insertion of that directory into `sys.path`;
- import of `skillset.cli.main`; and
- `sys.exit(main())` under the normal script guard.

Resolving the script path makes the bootstrap independent of the caller's working directory. The implementation remains
repository-relative, matching the documented installation model in which `~/.agents/bin` is on `PATH`.

### Private package

`lib/skillset/__init__.py`

- Marks the private package.
- Does not re-export an API.

`lib/skillset/errors.py`

- Defines `OperationalError`, the shared user-correctable failure type.

`lib/skillset/layout.py`

- Owns shared constants for names and empty lockfiles.
- Validates names, paths, lockfiles, sets, aliases, and complete managed layouts.
- Provides low-level real-entry and canonical-alias checks.
- Owns stable HOME locking, managed operation locking, and doctor-safe lock acquisition.
- Writes an empty lockfile.

`lib/skillset/operations.py`

- Implements `init`, `create`, `use`, `rename`, and `remove`.
- Keeps initialization rollback and active-rename recovery beside the transactions they protect.
- Owns canonical staging cleanup decisions for those operations.
- Depends only on `errors.py`, `layout.py`, and standard-library facilities.

`lib/skillset/metadata.py`

- Reads real `SKILL.md` files without following symlinks.
- Parses the currently supported frontmatter scalar subset.
- Inspects direct skill directories and provides terminal-safe printable text.
- Implements the read-only `list`, `current`, and `show` behavior.
- Does not mutate managed state.

`lib/skillset/doctor.py`

- Performs best-effort, non-mutating diagnostic traversal.
- Collects and sorts errors and warnings while continuing after local failures.
- Reuses layout lockfile validation and metadata inspection without weakening doctor's error aggregation.
- Returns the existing diagnostic status code and preserves exact finding formatting.

`lib/skillset/delegate.py`

- Validates the managed layout before delegation.
- Applies the documented global-scope rules without consuming upstream arguments.
- Prepares the copied child environment and transfers inherited locks to `npx skills` via `execvpe`.

`lib/skillset/cli.py`

- Defines the custom argument parser and all subcommands.
- Selects inspection versus mutation lock behavior.
- Dispatches parsed commands to feature modules.
- Owns top-level handling for operational errors, interrupts, unexpected failures, and final status codes.

### Dependency direction

Imports must flow toward `cli.py`:

- `errors.py` has no package dependencies.
- `layout.py` may import `errors.py`.
- `operations.py`, `metadata.py`, and `delegate.py` may import foundational modules.
- `doctor.py` may import `errors.py`, `layout.py`, and `metadata.py`.
- `cli.py` may import all feature modules.
- Feature modules must not import `cli.py`, and no import cycle is permitted.

## Safety and error semantics

The extraction moves existing code without redesigning transaction boundaries. Context managers in `layout.py` continue
to own lock acquisition and release. `cli.py` continues to hold the stable HOME lock around every command and the
managed lock around every command except doctor; doctor retains its special best-effort acquisition path. Delegation
continues to inherit both descriptors through process replacement.

Rollback and recovery helpers remain in `operations.py` so state transitions and their recovery logic can be reviewed as
one unit. No staging marker may be removed unless its type, location, and target meet the existing canonical checks.
Exception messages and `KeyboardInterrupt` behavior are copied without semantic edits.

## Testing and verification

The existing black-box suite is the primary contract because it exercises the real executable and does not depend on
implementation symbols. It already removes `PYTHONPATH` and invokes from temporary working directories, covering the
new bootstrap path under realistic conditions.

Verification command:

    python3 -m unittest tests.test_skillset

After extraction, also run a syntax/import check over the entry point and package if the repository has no existing
equivalent. Add a focused regression test only if implementation reveals a bootstrap case not exercised by the current
suite. Do not add tests that freeze exact module sizes or private function placement.

Success requires the complete suite to pass with no changed black-box expectations and a review of the final diff for
accidental behavior edits.

## Alternatives rejected

- A three-module split (`core`, `inspection`, `cli`) leaves a large core module mixing validation, locking, and mutation.
- A command-per-module split fragments shared transaction and recovery logic and produces excessive cross-module
  coupling.
- Introducing an installable Python distribution adds packaging machinery that the documented repository-relative tool
  does not need.
- Publishing a Python API creates an unnecessary compatibility surface; only CLI behavior is supported.

## Implementation checklist

1. Add the private package and foundational modules.
2. Move metadata, diagnostics, operations, delegation, and CLI orchestration without semantic edits.
3. Replace `bin/skillset` with the minimal repository-relative bootstrap.
4. Run the full black-box suite and syntax/import checks.
5. Review imports, resource ownership, exception paths, and the final diff for behavior drift.