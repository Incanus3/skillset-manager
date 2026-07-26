# Claude Descriptor-Binding Simplification Implementation Plan

> **For agentic workers:** Use `subagent-driven-development` or
> `executing-plans` one task at a time. Steps use checkbox syntax for tracking.
> Stop after each task for operator review.

> **Status:** Completed — implementation was verified and independently
> reviewed. The durable policy and completion record are in
> `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md` and
> `docs/guides/local-cli-reliability.md`.

**Goal:** Remove Claude Code's descriptor/public-path identity protocol and
replacement-race tests while retaining normal serial enable, disable,
validation, and Ctrl+C recovery.

**Architecture:** Keep preflight checks and direct fd-relative link operations.
Treat directory and source-child replacement after inspection as outside the
best-effort concurrency contract. Remove repeated inode comparisons and binding
rechecks, while retaining ordinary I/O errors, malformed-container diagnostics,
and the scope-root comparison needed for normal global/local configuration.

**Tech Stack:** Python standard library, `unittest`, GitButler workspace.

## Global Constraints

- Read `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md`
  and `docs/guides/local-cli-reliability.md` in full before editing.
- Preserve normal serial Claude enable, disable, reconciliation, ownership,
  collision, malformed-container, ordinary-I/O, and Ctrl+C behavior.
- Concurrency is best effort. Do not retain or add descriptor identity,
  TOCTOU, hostile replacement, or syscall-timing protocols.
- Retain `_identity()` only for `same_directory()` and do not change
  `DIRECTORY_FLAGS`, `O_NOFOLLOW`, or general symlink validation in this batch.
- Do not add dependencies, `ctypes`, direct syscall bindings, or `renameat*`.
- Do not modify `layout.py`, `augment.py`, or `metadata.py`.
- Do not commit, push, merge, publish, or delete handoffs without explicit
  operator authorization.

## Scope Classification

| Classification | Included work | Reason |
| --- | --- | --- |
| High-confidence adversarial hardening | Claude descriptor/public-path and source-child inode checks; three directory-replacement race tests. | They detect a second actor changing a path after inspection. |
| Functional reliability retained | Preflight kind/collision checks, fd-relative link operations, source inventory, normal I/O diagnostics, idempotency, and Ctrl+C recovery. | They define supported serial command behavior and proportionate recovery. |
| Deferred mixed work | Claude `O_NOFOLLOW` flags and general symlink validation. | Their serial malformed-layout contract needs a separate classification. |

## File Map

- Modify: `lib/skillset/claude.py` — remove identity binding/revalidation while
  retaining direct serial operations.
- Modify: `tests/test_skillset.py` — remove only dedicated directory
  replacement-race contracts.

---

### Task 1: Remove Claude directory-replacement race contracts

**Files:**
- Modify: `tests/test_skillset.py:2684-2884`

**Interfaces:**
- Consumes: `SkillsetTests.run_cli()`, `fault_environment()`, and
  `assert_refused()`.
- Produces: focused test coverage only for normal serial behavior and recovery;
  no test requires a second process to move or recreate a directory mid-command.

- [x] **Step 1: Delete only the three dedicated race methods**

Delete these complete methods and their fault-injected `os.rename`, `os.mkdir`,
`os.symlink`, `os.unlink`, and `os.stat` replacements:

````text
test_claude_enable_revalidates_public_directory_bindings
test_claude_disable_revalidates_public_directory_bindings
test_claude_disable_detects_initially_absent_containers_appearing
````

Keep adjacent functional tests for source collisions, exact canonical-link
adoption, dangling-link cleanup, idempotency, directory-creation interrupts,
interrupted link creation/removal, and malformed containers.

- [x] **Step 2: Run retained functional controls before implementation**

Run:

````sh
python -m unittest -v \
  tests.test_skillset.SkillsetTests.test_claude_local_enable_is_exact_scoped_idempotent_and_reconciles \
  tests.test_skillset.SkillsetTests.test_claude_enable_refuses_source_symlinks_and_collisions_before_mutation \
  tests.test_skillset.SkillsetTests.test_claude_disable_recovers_dangling_links_after_source_removal \
  tests.test_skillset.SkillsetTests.test_claude_first_enable_classifies_directory_creation_interrupts \
  tests.test_skillset.SkillsetTests.test_claude_interrupted_registration_creation_reports_and_recovers \
  tests.test_skillset.SkillsetTests.test_claude_interrupted_scope_repair_reports_and_recovers \
  tests.test_skillset.SkillsetTests.test_claude_interrupted_projected_unlink_reports_and_recovers \
  tests.test_skillset.SkillsetTests.test_claude_disable_recovers_after_registration_unlink
````

Expected: all controls pass before the implementation change.

### Task 2: Remove Claude descriptor identity and binding rechecks

**Files:**
- Modify: `lib/skillset/claude.py:147-191,265-335,375-415,549-616,619-938`
- Test: retained focused methods from Task 1.

**Interfaces:**
- Consumes: `ScopeState` path and file-descriptor fields,
  `same_directory(first, second) -> bool`, and existing direct link helpers.
- Produces: normal serial Claude operations without a descriptor/public-path
  binding protocol or source-child identity tokens.

- [x] **Step 1: Delete the path-binding protocol and its call sites**

Delete `directory_binding_problem()` and `ScopeState.verify_bindings()`. Remove
their calls from `ensure_scope_directories()`, `verify_enabled()`, `enable()`,
`disable()`, and `validate_names_against_other_scope()`.

In `ensure_scope_directories()`, remove both opened-descriptor `fstat()`
identity comparisons with the initial descriptors. Keep opening the validated
container and existing `stat.S_ISDIR` and `OSError` handling.
Keep the `ScopeState` descriptor fields because downstream serial link
operations use them. Keep `_identity()` and `same_directory()` unchanged.

- [x] **Step 2: Remove source identity tokens and per-child revalidation**

Make `source_inventory()` return direct real-directory names rather than inode
tuples, remove `verify_source_child()`, and iterate names directly in `enable()`:

In `source_inventory()`:

````python
inventory = set()
# After the existing real-directory test:
inventory.add(name)
````

In `enable()`:

````python
for skill_name in inventory:
    create_link(
        scope_state.skills_fd,
        skill_name,
        os.path.join(target, skill_name),
        scope_state.skills_path / skill_name,
        root,
        name,
        scope,
        "enable",
    )
````

In `open_source()`, remove the preliminary `lstat()` and the post-open
`fstat()` identity comparison. Keep `validate_set()`, `open_directory()`, and
`source_inventory()` so malformed sources and ordinary open/list/stat failures
still report normally.

- [x] **Step 3: Run the focused contracts until green**

Run the Task 1 focused command again.

Expected: all selected tests pass. If a normal serial test fails, retain the
smallest direct validation or recovery behavior needed for it; do not restore
an identity comparison or replacement-race check.

### Task 3: Verify the narrow boundary and stop for review

**Files:**
- Modify: `lib/skillset/claude.py`, `tests/test_skillset.py` only

**Interfaces:**
- Consumes: the direct serial Claude implementation from Task 2.
- Produces: verified evidence without modifying no-follow behavior, other
  integrations, staging, rollback, or layout locks.

- [x] **Step 1: Check removed protocol and retained scope comparison**

Run:

````sh
if rg -n 'directory_binding_problem|verify_bindings|verify_source_child|directory changed during synchronization' lib/skillset/claude.py tests/test_skillset.py; then exit 1; fi
if rg -n 'test_claude_(enable_revalidates_public_directory_bindings|disable_revalidates_public_directory_bindings|disable_detects_initially_absent_containers_appearing)' tests/test_skillset.py; then exit 1; fi
rg -n 'def _identity|def same_directory|DIRECTORY_FLAGS' lib/skillset/claude.py
````

Expected: both absence checks print nothing and exit `0`; the final command
shows `_identity()`, `same_directory()`, and the unchanged deferred directory
flags.

- [x] **Step 2: Run compilation, regression, and forbidden-binding checks**

Run:

````sh
python -m compileall -q bin lib tests
python -m unittest discover -s tests
if rg -n 'ctypes|renameat|renameat2|RENAME_NOREPLACE' lib tests; then exit 1; fi
````

Expected: every command exits `0`. Classify any unexpected test failure before
altering implementation.

- [x] **Step 3: Inspect scope and request review**

Run `but diff`.

Expected: apart from this plan and tracking state, implementation changes are
limited to `lib/skillset/claude.py` and `tests/test_skillset.py`. Record
verification in the active handoff and stop for operator review before planning
the deferred Claude no-follow behavior or another candidate area.