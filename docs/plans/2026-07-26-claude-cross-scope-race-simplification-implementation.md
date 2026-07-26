# Claude Cross-Scope Race Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `subagent-driven-development` (recommended) or `executing-plans` to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** Completed — retained as a historical implementation plan. The
> durable policy and completion record are in
> `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md` and
> `docs/guides/local-cli-reliability.md`.

**Goal:** Remove Claude's post-synchronization collision protocol that detects
a conflicting entry created by a second actor, while retaining normal serial
cross-scope collision prevention.

**Architecture:** `enable()` keeps the existing preflight
`cross_scope_collision()` call before it creates Claude registrations or
projected links. Delete only the later call after `verify_enabled()`, which
re-inspects the other scope solely to catch a concurrent mutation. Remove its
dedicated fault-injected test; retain the ordinary serial collision contract.

**Tech Stack:** Python standard library, `unittest`, GitButler workspace.

## Global Constraints

- Read `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md`
  and `docs/guides/local-cli-reliability.md` in full before editing.
- Preserve the pre-mutation `cross_scope_collision()` validation in
  `enable()`, all no-follow and symlink-validation behavior, ordinary I/O
  errors, idempotency, and Ctrl+C recovery.
- Concurrent mutation after preflight is out of contract; do not replace the
  removed recheck with another post-synchronization collision protocol.
- Do not modify `DIRECTORY_FLAGS`, `O_NOFOLLOW`, source inventory,
  `same_directory()`, other integrations, staging, rollback, or layout locks.
- Do not add dependencies, `ctypes`, direct syscall bindings, or `renameat*`.
- Do not commit, push, merge, publish, or delete handoffs without explicit
  operator authorization.

## File Map

- Modify: `tests/test_skillset.py` — remove the single injected second-actor
  contract.
- Modify: `lib/skillset/claude.py` — remove the matching late recheck.
- Reference: `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md`
  and `docs/guides/local-cli-reliability.md` — durable policy and completion
  context; no active handoff remains.

---

### Task 1: Remove the dedicated second-actor contract

**Files:**
- Modify: `tests/test_skillset.py:2457-2514`

**Interfaces:**
- Consumes: `SkillsetTests.run_cli()`, `fault_environment()`, and the existing
  preflight collision contract.
- Produces: no test that requires a second actor to create a conflicting
  opposite-scope entry after synchronization has begun.

- [x] **Step 1: Establish the retained serial collision baseline**

Run:

````sh
python -m unittest -v \
  tests.test_skillset.SkillsetTests.test_claude_enable_refuses_cross_scope_skill_name_collisions
````

Expected: pass. It verifies that enabling a conflicting global or local
skillset refuses before creating its target scope.

- [x] **Step 2: Delete only the race-only test method**

Delete the complete `test_claude_enable_rechecks_opposite_scope_created_during_sync`
method. It patches `os.symlink()` to create the opposite-scope collision after
the first projected link is created, which is a concurrent-mutation contract.

Keep `test_claude_enable_refuses_cross_scope_skill_name_collisions` and
`test_claude_list_rejects_cross_scope_masking`; they cover normal serial
collision behavior without an injected second actor.

### Task 2: Remove the matching post-synchronization recheck

**Files:**
- Modify: `lib/skillset/claude.py:621-632`
- Test: `tests/test_skillset.py` retained methods from Task 1.

**Interfaces:**
- Consumes: the initial `other_state` and preflight `cross_scope_collision()`
  call at `enable()` lines 535-546.
- Produces: `enable()` creates a projection after successful preflight without
  re-opening the other scope to detect a later concurrent collision.

- [x] **Step 1: Delete the late conditional exactly**

Immediately after the existing `verify_enabled()` error handling, delete this
entire block and nothing else:

````python
if other_state is not None:
    if other_state.skills_fd is None:
        other_state = open_existing_scope(root, opposite_scope(scope), stack)
    problem = cross_scope_collision(
        inventory, target, other_state.skills_fd, other_state.skills_path
    )
    if problem is not None:
        raise OperationalError(problem)
````

Retain the preflight `other_state` block before `initial_state` is opened.

- [x] **Step 2: Run the retained focused contracts**

Run:

````sh
python -m unittest -v \
  tests.test_skillset.SkillsetTests.test_claude_enable_refuses_cross_scope_skill_name_collisions \
  tests.test_skillset.SkillsetTests.test_claude_list_rejects_cross_scope_masking \
  tests.test_skillset.SkillsetTests.test_claude_local_enable_is_exact_scoped_idempotent_and_reconciles
````

Expected: all pass. If a failure exposes a normal serial regression, preserve
the smallest pre-mutation validation or recovery behavior needed; do not
restore a late concurrent-mutation recheck.

### Task 3: Verify the boundary and stop for review

**Files:**
- Modify: `lib/skillset/claude.py`, `tests/test_skillset.py`, and active
  tracking only.

**Interfaces:**
- Consumes: the direct preflight-only `enable()` flow from Task 2.
- Produces: evidence that the race protocol is absent and all retained serial
  behavior remains covered.

- [x] **Step 1: Check the removed contract and retained preflight call**

Run:

````sh
if rg -n 'test_claude_enable_rechecks_opposite_scope_created_during_sync' tests/test_skillset.py; then exit 1; fi
if rg -n -U 'if other_state is not None:\n                if other_state.skills_fd is None:' lib/skillset/claude.py; then exit 1; fi
rg -n -C 5 'problem = cross_scope_collision' lib/skillset/claude.py
````

Expected: both absence checks print nothing and exit `0`; the final command
shows the pre-mutation `enable()` collision check before `initial_state` is
opened. Its separate unchanged list-validation call may also appear.

- [x] **Step 2: Run compilation, regression, and forbidden-binding checks**

Run:

````sh
python -m compileall -q bin lib tests
python -m unittest discover -s tests
if rg -n 'ctypes|renameat|renameat2|RENAME_NOREPLACE' lib tests; then exit 1; fi
````

Expected: every command exits `0`. Classify any unexpected failure before
altering implementation.

- [x] **Step 3: Inspect scope and request review**

Run `but diff`.

Expected: implementation changes are limited to the one late recheck and its
dedicated test, plus active tracking. The completed branch is recorded in the
durable design; no active handoff remains.