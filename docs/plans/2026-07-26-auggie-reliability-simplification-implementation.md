# Auggie Reliability Simplification Implementation Plan

> **For agentic workers:** Use `subagent-driven-development` or
> `executing-plans` to implement one task at a time. Steps use checkbox syntax
> for tracking. Stop after each task for operator approval.

> **Status:** Completed — implementation was verified and independently
> reviewed. The durable policy and completion record are in
> `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md` and
> `docs/guides/local-cli-reliability.md`.

**Goal:** Remove Auggie's hostile-replacement, quarantine, and descriptor-
identity protocol while retaining normal serial enable, disable, reconciliation,
layout validation, and interruption recovery.

**Architecture:** Keep the current fd-relative operations and normal canonical
link checks, but treat concurrent replacement as outside the contract. Replace
the quarantine move/delete protocol with a direct owned-link unlink. Remove
repeated inode comparisons and binding revalidation, while retaining ordinary
malformed-layout and I/O-error reporting.

**Tech Stack:** Python standard library, `unittest`, GitButler workspace.

## Global Constraints

- Read `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md`
  and `docs/guides/local-cli-reliability.md` in full before editing.
- Preserve normal serial Auggie enable, disable, stale-projection reconciliation,
  registration checks, malformed-layout errors, and useful Ctrl+C recovery.
- Concurrency is best effort. Do not retain or add hostile replacement, TOCTOU,
  descriptor identity, quarantine, or syscall-timing protocols.
- Do not add dependencies, `ctypes`, direct syscall bindings, or `renameat*`.
- Do not modify documentation, `layout.py`, or the advisory-lock/FIFO tests in
  this batch.
- Do not commit, push, merge, publish, or delete handoffs without explicit
  operator authorization.

## Scope classification

| Classification | Included work | Reason |
| --- | --- | --- |
| High-confidence adversarial | Auggie link/directory/source replacement checks, removal quarantine, and their fault-injection tests. | They exist only to reject a racing replacement or preserve its quarantine. |
| Functional reliability | Serial link ownership, normal stale-link removal, malformed-container checks, registration reconciliation, and Ctrl+C recovery. | These define normal command behavior or proportionate recovery. |
| Deferred mixed work | `layout.py` lock/no-follow behavior and tests at `tests/test_skillset.py:4388-4463,9933-9971`. | Advisory-lock semantics require their own later classification. |

## File map

- Modify: `lib/skillset/augment.py` — replace the quarantine/identity protocol
  with direct serial operations.
- Modify: `tests/test_skillset.py` — remove hostile fault tests and retarget
  retained interruption tests to direct unlink/create behavior.

---

### Task 1: Replace adversarial Auggie tests with serial behavior contracts

**Files:**
- Modify: `tests/test_skillset.py:7266-7405,7494-8035,8280-8352,8463-8527,8610-9145`

**Interfaces:**
- Consumes: existing `SkillsetTests.run_cli()`, `fault_environment()`, and
  `assert_refused()` helpers.
- Produces: coverage for direct serial unlink/recovery and no tests that require
  a hostile process to replace a path, directory, registration, or quarantine.

- [x] **Step 1: Delete only the hostile-replacement and quarantine test methods**

Remove these complete methods, including their injected `os.rename`, `os.stat`,
`os.open`, `os.readlink`, and `os.mkdir` replacements:

````text
test_augment_enable_revalidates_public_directory_bindings
test_augment_disable_revalidates_public_directory_bindings
test_augment_refuses_links_replaced_after_ownership_inspection
test_augment_quarantines_links_replaced_before_removal
test_augment_refuses_leftover_removal_quarantine_without_mutation
test_augment_preserves_quarantine_when_interrupted_after_move
test_augment_reports_manual_recovery_after_post_mkdir_interrupt
test_augment_refuses_replaced_removal_quarantine_during_creation
test_augment_removes_empty_quarantine_after_open_failure
test_augment_preserves_post_mkdir_quarantine_failures_with_recovery_path
test_augment_reports_pre_mkdir_quarantine_failure_without_marker
test_augment_refuses_replaced_removal_quarantine_during_cleanup
test_augment_lifecycle_refuses_removal_quarantine_without_mutation
test_augment_lifecycle_refuses_replaced_orphaned_projection
test_augment_lifecycle_refuses_skills_replaced_before_orphan_open
test_augment_lifecycle_refuses_replaced_parent_before_orphan_return
test_augment_lifecycle_refuses_orphan_created_after_missing_lookup
test_augment_lifecycle_refuses_parent_replaced_after_missing_lookup
test_augment_lifecycle_refuses_replaced_registration_during_inspection
test_augment_lifecycle_refuses_removed_registration_during_inspection
````

Do not delete adjacent functional tests: `test_augment_ownership_requires_matching_basename_and_preserves_aliases`, `test_augment_disable_recovers_dangling_links_after_source_removal`, `test_orphaned_augment_projections_block_lifecycle`, malformed-container tests, or ordinary inaccessible-I/O tests.

- [x] **Step 2: Retarget the retained interruption tests to the direct operations**

In `test_augment_interrupted_after_registration_reports_recovery_paths`, replace
the `os.stat` second-source-check fault with an `os.symlink` fault that raises
`KeyboardInterrupt` immediately after the `alpha` projection link is created.
It must still assert exit `130`, the recovery command, an existing registration,
an existing projection, and successful rerun.

In `test_augment_interrupted_projected_unlink_reports_and_recovers`, make the
patched `os.unlink` raise after `name == "alpha"`, rather than after the removed
quarantine entry name. In
`test_augment_disable_recovers_after_registration_unlink`, count calls whose
names are `"alpha"` or `"default"` and interrupt after the second direct unlink.
Keep their existing assertions that the rerun completes cleanup.

- [x] **Step 3: Run the new focused recovery contract and confirm it is red**

Run:

````sh
python -m unittest -v \
  tests.test_skillset.SkillsetTests.test_augment_interrupted_projected_unlink_reports_and_recovers \
  tests.test_skillset.SkillsetTests.test_augment_disable_recovers_after_registration_unlink
````

Expected: both tests fail while `augment.py` still removes through the
`REMOVAL_ENTRY` quarantine protocol. The failure establishes that retained
interruption recovery is now specified against direct unlinking.

- [x] **Step 4: Run unaffected functional controls before implementation**

Run:

````sh
python -m unittest -v \
  tests.test_skillset.SkillsetTests.test_augment_ownership_requires_matching_basename_and_preserves_aliases \
  tests.test_skillset.SkillsetTests.test_augment_disable_recovers_dangling_links_after_source_removal \
  tests.test_skillset.SkillsetTests.test_augment_interrupted_registration_creation_reports_and_recovers \
  tests.test_skillset.SkillsetTests.test_orphaned_augment_projections_block_lifecycle
````

Expected: all controls pass before the implementation change.

### Task 2: Simplify Auggie to direct serial operations

**Files:**
- Modify: `lib/skillset/augment.py:3-26,86-122,139-248,322-472,503-776,829-896,958-1128,1194-1222,1254-1411`
- Test: `tests/test_skillset.py` focused methods from Task 1

**Interfaces:**
- Consumes: `canonical_link_at(directory_fd, name, target) -> bool`,
  `ScopeState` file descriptors, and existing recovery-message helpers.
- Produces: `unlink_link(directory_fd, name, path, target, root, set_name,
  scope, action)` that performs direct owned-link deletion and reports ordinary
  errors or recoverable interruption without creating persistent state.

- [x] **Step 1: Remove quarantine state and descriptor-binding helpers**

Delete `uuid`, `ManualRecoveryError`, `REMOVAL_PREFIX`, `REMOVAL_ENTRY`,
`removal_quarantine`, `_manual_recovery_message`, `_manual_recovery_error`,
`_manual_recovery_interrupted`, `directory_binding_problem`,
`directory_at_binding_problem`, `ScopeState.verify_bindings`,
`create_removal_quarantine`, `remove_created_empty_quarantine`, and
`remove_empty_quarantine`.

Remove the corresponding quarantine scans from `validate_scope_containers()` and
`lifecycle_container_blocker_path()`. Remove each call to binding verification
from `ensure_scope_directories()`, `verify_enabled()`, `enable()`, `disable()`,
`validate_names_against_other_scope()`, `orphaned_projection_blocker()`, and
`global_registration_blocker()`.

Keep `_identity()` only for `same_directory()`, which compares configured global
and local roots during normal serial setup.

- [x] **Step 2: Replace repeated identity protocols with normal checks**

Change `DIRECTORY_FLAGS` to `os.O_RDONLY | os.O_DIRECTORY`; the preceding
ordinary layout checks still reject malformed containers in serial use, while
`os.O_NOFOLLOW` only narrows a concurrent-path-substitution window.

Make `canonical_link_at()` inspect once, read the target, and decide canonicality
without its second `os.stat`/inode comparison:

````python
def canonical_link_at(directory_fd, name, target):
    try:
        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise OperationalError(
            f"could not inspect Auggie entry {name!r}: {error}"
        ) from error
    if not stat.S_ISLNK(metadata.st_mode):
        return False
    try:
        link_target = os.readlink(name, dir_fd=directory_fd)
    except FileNotFoundError:
        return False
    except OSError as error:
        if error.errno == EINVAL:
            return False
        raise OperationalError(
            f"could not inspect Auggie entry {name!r}: {error}"
        ) from error
    return canonical_target(link_target, target)
````

Make `source_inventory()` return a `set[str]` of direct real-directory names;
remove `verify_source_child()` and iterate `for skill_name in inventory` in
`enable()`. In `open_source()` remove the lstat/fstat identity comparison after
opening the validated source. In `ensure_scope_directories()`,
`orphaned_projection_blocker()`, and `global_registration_blocker()`, retain
their ordinary `stat`, directory-kind, open-error, and owned-link checks but
remove only descriptor/public-path identity comparisons. In
`inspected_link_target_at()`, return the result of its single successful
`os.readlink()` without restatting for inode identity.

- [x] **Step 3: Replace quarantine removal with direct unlinking**

Replace the existing `unlink_link()` with this complete implementation and
update both `enable()` and `disable()` callers to remove their `augment_fd` and
`augment_path` arguments:

````python
def unlink_link(directory_fd, name, path, target, root, set_name, scope, action):
    if not canonical_link_at(directory_fd, name, target):
        if _entry_missing(directory_fd, name):
            return
        raise OperationalError(f"refused to remove changed Auggie entry: {path}")
    try:
        os.unlink(name, dir_fd=directory_fd)
    except KeyboardInterrupt:
        state = "link was removed" if _entry_missing(directory_fd, name) else "link was not removed"
        _interrupted(root, set_name, scope, action, f"{path}: {state}")
    except OSError as error:
        if _entry_missing(directory_fd, name):
            return
        raise OperationalError(f"could not remove Auggie link {path}: {error}") from error
````

The direct `os.unlink` retains the normal serial guarantee of removing only a
canonical owned link. A racing replacement is outside the supported contract;
do not add a post-unlink identity check, quarantine directory, or manual
recovery branch.

- [x] **Step 4: Run the focused tests until green**

Run the Task 1 recovery command plus:

````sh
python -m unittest -v \
  tests.test_skillset.SkillsetTests.test_augment_ownership_requires_matching_basename_and_preserves_aliases \
  tests.test_skillset.SkillsetTests.test_augment_disable_recovers_dangling_links_after_source_removal \
  tests.test_skillset.SkillsetTests.test_augment_interrupted_after_registration_reports_recovery_paths \
  tests.test_skillset.SkillsetTests.test_augment_disable_interrupt_between_unlinks_reports_recovery \
  tests.test_skillset.SkillsetTests.test_orphaned_augment_projections_block_lifecycle
````

Expected: all selected tests pass. If a normal serial behavior fails, preserve
the smallest direct behavior needed for that test; do not restore an identity,
replacement, or quarantine protocol.

#### Approved Task 2 extension: remove remaining race-only rechecks

**Decision:** The operator approved this extension after independent review
identified two residual concurrent-mutation contracts. Both are
high-confidence adversarial/TOCTOU hardening, not normal serial reliability,
best-effort advisory locking, ordinary I/O handling, or Ctrl+C recovery.

- [x] Delete `test_augment_disable_detects_initially_absent_containers_appearing`
  and `test_augment_enable_rechecks_opposite_scope_created_during_sync` from
  `tests/test_skillset.py`.
- [x] Remove the post-synchronization `other_state = open_existing_scope(...)`,
  `cross_scope_collision(...)`, and former binding-verification block from
  `enable()` in `lib/skillset/augment.py`. Keep the initial cross-scope
  collision preflight before any mutation; it protects normal serial setup.
- [x] Do not change `disable()`: its former final binding recheck was already
  removed by Task 2, so its remaining race-only contract is test-only. Retain
  direct owned-link removal and Ctrl+C recovery.
- [x] Re-run the Task 2 focused suite and review this extension before Task 3.

### Task 3: Verify the narrow batch and stop for review

**Files:**
- Modify: `lib/skillset/augment.py`, `tests/test_skillset.py` only

**Interfaces:**
- Consumes: the completed direct-operation implementation and retained
  black-box behavior tests.
- Produces: verified evidence for this batch; no expansion into lock,
  descriptor/no-follow, staging, rollback, or documentation work.

- [x] **Step 1: Check removed protocol terms and deferred boundaries**

Run:

````sh
grep -nE 'REMOVAL_PREFIX|REMOVAL_ENTRY|removal_quarantine|ManualRecoveryError|directory_binding_problem|directory_at_binding_problem|verify_bindings|verify_source_child' lib/skillset/augment.py tests/test_skillset.py
grep -n 'test_augment_skills_list_falls_back_when_advisory_lock_is_replaced' tests/test_skillset.py
grep -n 'test_augment_skills_list_falls_back_from_fifo_lock_without_mutation' tests/test_skillset.py
````

Expected: the first command has no output and exits `1`; the two deferred
advisory-lock test names remain present. Treat the first command's exit `1` as
the expected successful absence check.

- [x] **Step 2: Run syntax, full regression, and forbidden-binding checks**

Run:

````sh
python -m compileall -q bin lib tests
python -m unittest discover -s tests
grep -RInE 'ctypes|renameat|renameat2|RENAME_NOREPLACE' lib tests || true
````

Expected: compilation and the full suite exit `0`; the final search prints no
implementation or test references. Classify any unexpected test failure before
changing code.

- [x] **Step 3: Inspect scope and stop**

Run:

````sh
but diff
````

Expected: apart from this plan and tracking state, implementation changes are
limited to `lib/skillset/augment.py` and `tests/test_skillset.py`. The diff
removes high-confidence adversarial protocol and retains direct serial
workflows. Record the commands and results in the active handoff, then stop for
operator review before planning advisory-lock/no-follow or mixed recovery work.