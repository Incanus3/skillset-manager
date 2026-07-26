# Advisory-Lock Descriptor Simplification Implementation Plan

> **For agentic workers:** Use `subagent-driven-development` or `executing-plans` one task at a time. Stop after each task for operator review.

> **Status:** Completed — implementation was verified and independently
> reviewed. The durable policy and completion record are in
> `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md` and
> `docs/guides/local-cli-reliability.md`.

**Goal:** Remove advisory-lock replacement identity hardening while preserving read-only Auggie discovery when an optional lock is unavailable.

**Architecture:** The advisory lock stays a standard-library, best-effort optimization. Discovery continues without it after a normal acquisition error. Preserve serial malformed-lock validation, and remove only `st_dev`/`st_ino` replacement detection plus its hostile-race contract.

**Tech Stack:** Python standard library, `unittest`, GitButler workspace.

## Global Constraints

- Read `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md` and `docs/guides/local-cli-reliability.md` before editing.
- Preserve read-only `skillset augment skills list` output and no-mutation behavior for missing, malformed, unreadable, non-regular, FIFO, and acquisition-failed optional locks.
- Retain `O_NOFOLLOW`, `O_NONBLOCK`, regular-file checks, descriptor cleanup, and blocking locks for mutating managed commands.
- Do not retain or add inode identity comparisons, hostile-replacement tests, TOCTOU protocols, or fail-closed behavior justified only by racing actors.
- Do not add dependencies, `ctypes`, direct syscall bindings, or `renameat*`.
- Do not modify `lib/skillset/augment.py`, mutating lock behavior, recovery logic, or the archived review handoff.
- Do not commit, push, merge, publish, or delete handoffs without explicit operator authorization.

## Scope Classification

| Classification | Included work | Reason |
| --- | --- | --- |
| High-confidence adversarial hardening | The `st_dev`/`st_ino` comparison and lock-replacement test. | They detect a hostile/racing replacement and have no serial contract. |
| Functional reliability | Fallback after `flock()` acquisition failure. | Read-only discovery has no need for an optional lock. |
| Functional reliability retained | No-follow, nonblocking FIFO, regular-file, cleanup, and mutating-lock behavior. | They prevent malformed state or a hung command without promising race-free operation. |

## File Map

- Modify: `lib/skillset/layout.py` — reduce doctor lock validation to kind checks and make optional discovery `flock()` failures fall back.
- Modify: `tests/test_skillset.py` — delete the replacement race and add an acquisition-failure black-box contract.

---

### Task 1: Specify optional-lock acquisition fallback

**Files:**
- Modify: `tests/test_skillset.py:4388-4463,8624-8772`

**Interfaces:**
- Consumes: `SkillsetTests.fault_environment()` and `run_cli()`.
- Produces: a black-box contract that discovery succeeds without mutation when `fcntl.flock()` fails for its optional lock.

- [x] **Step 1: Delete the hostile replacement method**

Delete the complete `test_augment_skills_list_falls_back_when_advisory_lock_is_replaced` method. It patches `os.open` to install a replacement symlink and asserts the replacement is neither opened nor locked. Do not change `test_each_inspection_command_waits_for_the_advisory_lock_without_blind_sleep`; it covers ordinary serial waiting rather than a replacement race.

- [x] **Step 2: Add the focused failing acquisition case**

Append `"lock-flock-error"` to the `cases` tuple in `test_augment_skills_list_falls_back_from_unavailable_managed_locks_without_mutation`. The existing setup creates a real empty lock for this case. Add this fault branch next to `lock-open-error` and `lock-fstat-error`:

````python
elif case == "lock-flock-error":
    fault = self.fault_environment(
        """
        import errno, fcntl, os
        lock_descriptor = None
        original_open, original_flock = os.open, fcntl.flock
        def track_advisory_lock_open(name, *args, **kwargs):
            global lock_descriptor
            descriptor = original_open(name, *args, **kwargs)
            if name == ".skillset.lock" and kwargs.get("dir_fd") is not None:
                lock_descriptor = descriptor
            return descriptor
        def fail_advisory_lock_flock(descriptor, operation):
            if descriptor == lock_descriptor and operation & fcntl.LOCK_EX:
                raise OSError(errno.ENOLCK, os.strerror(errno.ENOLCK))
            return original_flock(descriptor, operation)
        os.open, fcntl.flock = track_advisory_lock_open, fail_advisory_lock_flock
        """
    )
````

Keep the existing expected table, empty stderr, real-lock, and home/project snapshot assertions; they define the functional fallback contract.

- [x] **Step 3: Verify the new contract is red**

Run: `python -m unittest -v tests.test_skillset.SkillsetTests.test_augment_skills_list_falls_back_from_unavailable_managed_locks_without_mutation`

Expected: FAIL only for `lock-flock-error`, because the current `discovery_operation_lock()` lets its injected `OSError` escape. The deleted replacement test must no longer be collected.

### Task 2: Remove identity binding and add discovery fallback

**Files:**
- Modify: `lib/skillset/layout.py:403-450`
- Test: the focused unavailable-lock method from Task 1

**Interfaces:**
- Consumes: `inspect_advisory_lock_entry(lock_path, errors)` and `discovery_operation_lock(root)`.
- Produces: kind-only doctor inspection and optional discovery locking that yields `None` on `OSError` from `flock()`.

- [x] **Step 1: Reduce doctor validation to serial kind checks**

Keep `inspect_advisory_lock_entry()`'s missing, symlink, and regular-file diagnostics, but make its successful return value `True`, not `lstat` metadata. Use it in `doctor_operation_lock()` as a predicate:

````python
if not inspect_advisory_lock_entry(lock_path, errors):
    yield None
    return
````

After opening with the existing `os.O_RDONLY | os.O_NOFOLLOW`, retain one `os.fstat()` regular-file check. For a non-regular descriptor, append `advisory lock must be a real regular file: {lock_path}`, yield `None`, and return. Remove the `st_dev`/`st_ino` comparison and `advisory lock changed during inspection` diagnostic. Preserve existing lock release and descriptor-close behavior.

- [x] **Step 2: Make acquisition failure fall back without the lock**

In `discovery_operation_lock()`, catch only `OSError` from acquisition, before setting `locked = True`:

````python
locked = False
try:
    fcntl.flock(lock_descriptor, fcntl.LOCK_EX)
except OSError:
    yield None
    return
locked = True
try:
    yield lock_descriptor
finally:
    if locked:
        fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
````

Do not catch lock-release or cleanup errors and do not change open, `fstat`, `O_NOFOLLOW`, or `O_NONBLOCK` behavior.

- [x] **Step 3: Run focused contracts until green**

Run: `python -m unittest -v tests.test_skillset.SkillsetTests.test_augment_skills_list_falls_back_from_unavailable_managed_locks_without_mutation tests.test_skillset.SkillsetTests.test_augment_skills_list_falls_back_from_fifo_lock_without_mutation tests.test_skillset.SkillsetTests.test_successful_inspection_commands_are_strictly_read_only tests.test_skillset.SkillsetTests.test_doctor_accepts_healthy_state_without_mutation_or_findings tests.test_skillset.SkillsetTests.test_doctor_waits_for_advisory_lock_without_blind_sleep`

Expected: PASS. The injected `ENOLCK` case prints the normal table, produces no stderr, and leaves the lock, home, and project snapshots unchanged. The doctor checks retain healthy no-mutation diagnosis and normal serial lock waiting.

### Task 3: Verify the narrow boundary and stop for review

**Files:**
- Modify: `lib/skillset/layout.py`, `tests/test_skillset.py` only

**Interfaces:**
- Consumes: reduced doctor validation and direct optional-lock fallback.
- Produces: verification evidence without changing mutating locks or recovery.

- [x] **Step 1: Check removed and retained behavior**

Run: `if grep -n 'test_augment_skills_list_falls_back_when_advisory_lock_is_replaced' tests/test_skillset.py; then exit 1; fi; grep -nE 'O_NOFOLLOW|O_NONBLOCK|S_ISREG|fcntl\.flock' lib/skillset/layout.py`

Expected: no replacement-test output. The remaining output shows no-follow, nonblocking FIFO, regular-file, and advisory-lock operations. The doctor lock code has no `st_ino`, `st_dev`, or changed-during-inspection text.

- [x] **Step 2: Run compilation, regression, and binding checks**

Run: `python -m compileall -q bin lib tests && python -m unittest discover -s tests && ! grep -RInE 'ctypes|renameat|renameat2|RENAME_NOREPLACE' lib tests`

Expected: compilation and the suite exit `0`; the search prints no matches. Classify any failure before altering implementation.

- [x] **Step 3: Inspect scope and request review**

Run `but diff`. Expected: implementation changes are limited to `lib/skillset/layout.py` and `tests/test_skillset.py`, with plan and handoff tracking as expected. Record verification in the active handoff and stop for operator review. Do not commit, push, merge, or begin mixed recovery work without explicit authorization.