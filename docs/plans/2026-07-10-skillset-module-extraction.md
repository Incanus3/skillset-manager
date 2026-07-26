# Skillset Module Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans`
> to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the monolithic `bin/skillset` implementation with a minimal executable backed by focused private
modules under `lib/skillset/`, without changing CLI behavior.

**Architecture:** Extract one responsibility at a time and immediately wire the executable to the extracted module, so
the existing black-box suite exercises each boundary. Dependencies flow from shared errors and layout primitives through
operations, metadata, diagnostics, and delegation into CLI orchestration.

**Tech Stack:** Linux, Python 3 standard library, `unittest`, Jujutsu.

**Implementation status:** Completed on 2026-07-10. All five extraction tasks passed task-scoped review, and the final
whole-change review found no production issues. Final verification is recorded in the associated bead and working-copy
history.

## Global Constraints

- Preserve commands, arguments, help behavior, standard streams, output text, exit statuses, filesystem effects,
  locking, rollback, interrupt handling, diagnostics, and upstream delegation exactly.
- Keep the implementation standard-library-only; do not add packaging metadata or dependencies.
- Treat modules under `lib/skillset/` as private implementation details, not a supported Python API.
- Keep lock ownership, descriptor inheritance, staging checks, and recovery behavior unchanged.
- Run from any current working directory with `PYTHONPATH` unset.
- Do not combine extraction with unrelated cleanup.
- Do not commit unless the user explicitly authorizes it. If authorized, use `jj commit` and wrap commit-message lines at
  100 characters.
- This completed extraction plan predates the current local-CLI policy. For
  later maintenance, read `docs/guides/local-cli-reliability.md` rather than
  restoring its former transactional-hardening constraints.

## File map

- Create `lib/skillset/__init__.py`: private package marker with no re-exports.
- Create `lib/skillset/errors.py`: `OperationalError`.
- Create `lib/skillset/layout.py`: shared constants, path/layout validation, lock contexts, and empty-lock writing.
- Create `lib/skillset/operations.py`: lifecycle mutations and their rollback/recovery helpers.
- Create `lib/skillset/metadata.py`: safe skill metadata parsing, inspection, display, and read-only commands.
- Create `lib/skillset/doctor.py`: best-effort diagnostics and finding emission.
- Create `lib/skillset/delegate.py`: upstream argument policy and `execvpe` delegation.
- Create `lib/skillset/cli.py`: parser, dispatch, lock orchestration, and top-level error handling.
- Modify `bin/skillset`: first load extracted modules, then become the minimal executable bootstrap.
- Test with `tests/test_skillset.py`: retain black-box expectations; add no private-structure assertions.

---

### Task 1: Extract errors and managed-layout primitives

**Files:**
- Create: `lib/skillset/__init__.py`
- Create: `lib/skillset/errors.py`
- Create: `lib/skillset/layout.py`
- Modify: `bin/skillset`
- Test: `tests/test_skillset.py`

**Interfaces:**
- Produces: `OperationalError`; constants `EMPTY_LOCK`, `NAME_PATTERN`; functions `lexists(path)`,
  `real_kind(path, expected)`, `validate_name(name)`, `set_path(root, name)`, `read_lockfile(path)`,
  `validate_lockfile(path)`, `validate_set(root, name)`, `require_alias(path, target)`, `validate_layout(root)`,
  `canonical_alias(path, target)`, `stable_home_lock(root)`, `operation_lock(root, create=True)`,
  `doctor_operation_lock(root, errors)`, and `write_empty_lock(path)`.
- Consumers: all later package modules and the transitional executable.

- [ ] **Step 1: Record the clean baseline**

Run: `python3 -m unittest tests.test_skillset`

Expected: exit 0 with the complete existing suite passing. Stop and investigate if the baseline is not green.

- [ ] **Step 2: Add the package marker and shared error**

Create an empty `lib/skillset/__init__.py`. Create `lib/skillset/errors.py` with the existing exception unchanged:

    class OperationalError(Exception):
        """A user-correctable filesystem or validation failure."""

- [ ] **Step 3: Move layout primitives without semantic edits**

Move the named constants and functions from `bin/skillset` into `lib/skillset/layout.py`. Use these imports:

    import fcntl
    import json
    import os
    import re
    import stat
    from contextlib import contextmanager
    from .errors import OperationalError

Include `canonical_alias` with the other alias helpers even though it appears later in the current executable. Preserve
all function signatures, open flags, lock modes, validation order, exception text, and context-manager cleanup.

- [ ] **Step 4: Wire the transitional executable to the package**

Near the top of `bin/skillset`, derive the sibling library directory before package imports:

    LIB_DIRECTORY = Path(__file__).resolve().parents[1] / "lib"
    sys.path.insert(0, os.fspath(LIB_DIRECTORY))

Import every interface listed above from `skillset.layout` and `OperationalError` from `skillset.errors`. Remove only the
now-duplicated definitions and imports. Keep `Path`, `os`, and `sys` because the transitional executable still uses them.

- [ ] **Step 5: Verify extracted primitives through the real CLI**

Run: `python3 -c 'import ast, pathlib; [ast.parse(p.read_text()) for p in [pathlib.Path("bin/skillset"), *pathlib.Path("lib/skillset").glob("*.py")]]'`

Expected: exit 0 with no output.

Run: `python3 -m unittest tests.test_skillset`

Expected: exit 0 with the same test count and all tests passing.

- [ ] **Step 6: Optional authorized checkpoint commit**

If and only if the user has authorized commits, run:

    jj commit -m "Extract skillset layout primitives"

### Task 2: Extract lifecycle transactions

**Files:**
- Create: `lib/skillset/operations.py`
- Modify: `bin/skillset`
- Test: `tests/test_skillset.py`

**Interfaces:**
- Consumes: `OperationalError` and layout primitives from Task 1.
- Produces: `init(root, name)`, `create(root, name, source)`, `use(root, name)`,
  `rename(root, old_name, new_name)`, and `remove(root, name, confirmed)`.

- [ ] **Step 1: Move complete mutation and recovery units**

Move `preflight_init`, `rollback_init`, `init`, `create`, `use`, `cleanup_rename_staging`, `set_is_valid`,
`incomplete_active_rename`, `recover_active_rename`, `rename`, and `remove` into `lib/skillset/operations.py`. Use standard
library imports `os`, `shutil`, and `sys`; import the exact required names from `.errors` and `.layout`.

Do not split rollback or active-rename recovery into another file. Preserve `Exception` versus `KeyboardInterrupt`
handling, operation ordering, canonical staging checks, recovery text, prompt streams, and flush behavior.

- [ ] **Step 2: Replace local functions with operation imports**

In `bin/skillset`, import the five public operation functions from `skillset.operations`. Remove the moved definitions and
now-unused `shutil` import. Do not alter parser or dispatch branches.

- [ ] **Step 3: Verify lifecycle behavior**

Run: `python3 -c 'import ast, pathlib; [ast.parse(p.read_text()) for p in [pathlib.Path("bin/skillset"), *pathlib.Path("lib/skillset").glob("*.py")]]'`

Expected: exit 0 with no output.

Run: `python3 -m unittest tests.test_skillset`

Expected: exit 0 with all initialization, creation, activation, rename, removal, rollback, and interrupt tests passing.

- [ ] **Step 4: Optional authorized checkpoint commit**

If authorized, run: `jj commit -m "Extract skillset lifecycle operations"`

### Task 3: Extract metadata inspection and read-only commands

**Files:**
- Create: `lib/skillset/metadata.py`
- Modify: `bin/skillset`
- Test: `tests/test_skillset.py`

**Interfaces:**
- Consumes: `set_path`, `validate_layout`, and `validate_set` from `layout.py`.
- Produces: `parse_frontmatter(text)`, `read_skill_text(directory)`, `inspect_skills(skills)`,
  `printable_text(value)`, `list_sets(root, verbose)`, `current(root)`, and `show(root, name)`.

- [ ] **Step 1: Move metadata parsing as one coherent unit**

Move `TARGET_FIELD_PATTERN` and functions `normalize_scalar` through `inspect_skills`, plus `printable_text`, `list_sets`,
`current`, and `show`, into `lib/skillset/metadata.py`. Use standard-library imports `json`, `os`, `re`, `stat`, and
`unicodedata`; import the three layout interfaces listed above.

Preserve the supported scalar grammar, direct-entry ordering, no-follow file access, UTF-8 handling, invalid-candidate
reasons, terminal escaping, sorting, separators, and output formatting exactly.

- [ ] **Step 2: Replace local metadata code with imports**

Import all produced interfaces still needed by transitional doctor code, dispatch, and top-level error handling into
`bin/skillset`. Remove the moved definitions and now-unused metadata-specific imports. Do not change call sites.

- [ ] **Step 3: Verify metadata behavior**

Run: `python3 -c 'import ast, pathlib; [ast.parse(p.read_text()) for p in [pathlib.Path("bin/skillset"), *pathlib.Path("lib/skillset").glob("*.py")]]'`

Expected: exit 0 with no output.

Run: `python3 -m unittest tests.test_skillset`

Expected: exit 0, including all `list`, `show`, frontmatter, no-follow, Unicode, and printable-finding tests.

- [ ] **Step 4: Optional authorized checkpoint commit**

If authorized, run: `jj commit -m "Extract skillset metadata inspection"`

### Task 4: Extract diagnostics and transparent delegation

**Files:**
- Create: `lib/skillset/doctor.py`
- Create: `lib/skillset/delegate.py`
- Modify: `bin/skillset`
- Test: `tests/test_skillset.py`

**Interfaces:**
- Diagnostic consumers: layout validation/locking and metadata inspection interfaces.
- Diagnostic output: `doctor(root) -> int`.
- Delegation consumers: `OperationalError`, `validate_layout`, inherited HOME lock descriptor, managed lock file, parser.
- Delegation output: `delegate_skills(root, arguments, home_lock, lock_file, command_parser)`; successful calls replace
  the process and do not return.

- [ ] **Step 1: Move doctor traversal and emission**

Move `doctor_alias`, `doctor_lockfile`, `doctor_skills`, `doctor_set`, `doctor_inspection`, and `doctor` into
`lib/skillset/doctor.py`. Import `os`, `stat`, and `sys`; import `OperationalError`; import `NAME_PATTERN`,
`doctor_operation_lock`, `lexists`, and `read_lockfile` from `.layout`; import `parse_frontmatter`, `printable_text`, and
`read_skill_text` from `.metadata`.

Preserve best-effort continuation, non-mutating behavior, finding categories, sorting, formatting, and status selection.

- [ ] **Step 2: Move delegation policy and process replacement**

Move `SCOPED_SKILLS_COMMANDS`, `SCOPE_FREE_SKILLS_COMMANDS`, and `delegate_skills` into `lib/skillset/delegate.py`.
Import `os` and `sys`, plus `OperationalError` and `validate_layout`.

Preserve token order, `--` handling, global-scope injection, project-scope refusal, unknown-command warning, environment
copying, `XDG_STATE_HOME` removal, descriptor inheritance, `execvpe`, and failed-exec error text.

- [ ] **Step 3: Wire both modules into the transitional executable**

Import `doctor` and `delegate_skills` into `bin/skillset`; remove their prior definitions, constants, and unused imports.
Keep parser, dispatch, and lock nesting unchanged.

- [ ] **Step 4: Verify diagnostics and delegation**

Run: `python3 -c 'import ast, pathlib; [ast.parse(p.read_text()) for p in [pathlib.Path("bin/skillset"), *pathlib.Path("lib/skillset").glob("*.py")]]'`

Expected: exit 0 with no output.

Run: `python3 -m unittest tests.test_skillset`

Expected: exit 0, including all malformed-layout aggregation, lock, fake-`npx`, argument, environment, and descriptor
lifetime tests.

- [ ] **Step 5: Optional authorized checkpoint commit**

If authorized, run: `jj commit -m "Extract skillset diagnostics and delegation"`

### Task 5: Extract CLI orchestration and minimize the executable

**Files:**
- Create: `lib/skillset/cli.py`
- Modify: `bin/skillset`
- Test: `tests/test_skillset.py`

**Interfaces:**
- Consumes: every command function, `OperationalError`, `stable_home_lock`, `operation_lock`, and `printable_text`.
- Produces: `parser() -> argparse.ArgumentParser` and `main() -> int`.
- Entry-point contract: `bin/skillset` exits with `main()`'s status.

- [ ] **Step 1: Move parser and orchestration together**

Move `SkillsetArgumentParser`, `parser`, and `main` into `lib/skillset/cli.py`. Import `argparse`, `sys`, and `Path`, then
import the exact command and shared interfaces from sibling package modules.

Preserve parser construction order, help strings, remainder parsing, root derivation, inspection command selection, lock
nesting, command dispatch, doctor-specific prefixes, interrupt status 130, unexpected-error wording, and return values.

- [ ] **Step 2: Replace the executable with the minimal bootstrap**

Reduce `bin/skillset` to this responsibility-equivalent form:

    #!/usr/bin/env python3
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
    from skillset.cli import main
    if __name__ == "__main__":
        sys.exit(main())

Keep the executable bit. A blank line and import grouping may be added, but no command implementation remains in `bin/`.

- [ ] **Step 3: Verify syntax, executable shape, and permissions**

Run: `python3 -c 'import ast, pathlib; [ast.parse(p.read_text()) for p in [pathlib.Path("bin/skillset"), *pathlib.Path("lib/skillset").glob("*.py")]]'`

Expected: exit 0 with no output.

Run: `test -x bin/skillset && test "$(wc -l < bin/skillset)" -le 12`

Expected: exit 0 with no output.

Run: `grep -R "from .*cli" -n lib/skillset --exclude=cli.py`

Expected: exit 1 with no output, demonstrating that feature modules do not import CLI orchestration.

- [ ] **Step 4: Run the full behavioral regression suite**

Run: `python3 -m unittest tests.test_skillset`

Expected: exit 0 with the same test count as the baseline and all tests passing.

- [ ] **Step 5: Review the final diff for behavior drift**

Run: `jj diff --stat && git diff --check`

Expected: eight new package files, one reduced executable, planning/specification files already present, and no whitespace
errors. Compare moved function bodies against the original parent with `jj file show -r @- bin/skillset`; every behavioral
change must be either absent or explicitly justified before completion.

- [ ] **Step 6: Optional authorized final commit**

If authorized and earlier checkpoint commits were skipped, run:

    jj commit -m "Extract skillset implementation into focused modules"

If checkpoint commits were created, do not squash or rewrite them without separate user direction.