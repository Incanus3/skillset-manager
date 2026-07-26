# Initialization-Recovery Simplification Implementation Plan

> **For agentic workers:** Use `subagent-driven-development` or
> `executing-plans` one task at a time. Stop after each task for operator
> review.

> **Status:** Completed — implementation was verified and independently
> reviewed. The durable policy and completion record are in
> `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md` and
> `docs/guides/local-cli-reliability.md`.

**Goal:** Remove configured-initialization tests that enforce behavior against
concurrent creation or replacement while retaining serial rollback and recovery
coverage.

**Architecture:** This is a test-only classification batch. The live
`operations.py` rollback implementation already handles ordinary `OSError` and
Ctrl+C failures without a specialized adversarial protocol, so it remains
unchanged. Delete five fault-injection contracts that rely on another process
mutating the configured link or target after preflight; retain serial failure,
staging, malformed-layout, and incomplete-rollback diagnostics.

**Tech Stack:** Python standard library, `unittest`, GitButler workspace.

## Global Constraints

- Read `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md`
  and `docs/guides/local-cli-reliability.md` before editing.
- `skillset` is a trusted local CLI: support normal serial commands, ordinary
  I/O errors, and proportionate Ctrl+C recovery; concurrent mutation is best
  effort only.
- Do not modify `lib/skillset/operations.py`, `lib/skillset/layout.py`, command
  behavior, or the archived review handoff.
- Retain normal configured initialization, pre-existing collision, ordinary
  rollback, incomplete-rollback diagnostics, stale-staging, and malformed
  configured-layout coverage.
- Do not add dependencies, `ctypes`, direct syscall bindings, or `renameat*`.
- Do not commit, push, merge, publish, or delete handoffs without explicit
  operator authorization.

## Scope Classification

| Classification | Included work | Reason |
| --- | --- | --- |
| High-confidence adversarial hardening | Five configured-init tests that inject concurrent target creation or link replacement after preflight. | Concurrency is best effort and the tests impose a dedicated hostile/racing-process contract. |
| Functional reliability retained | Existing configured-init rollback, interrupted init, incomplete rollback, stale staging, and malformed-config tests. | They preserve data or report useful recovery actions during ordinary serial failures. |
| Out of scope | Production rollback and configured-link validation. | No separate adversarial protocol remains to remove; these checks also serve normal layout coherence. |

## File Map

- Modify: `tests/test_skillset.py` — delete five concurrent-mutation test
  methods only.
- Modify: `docs/plans/2026-07-26-initialization-recovery-simplification-implementation.md`
  — track this approved plan.

---

### Task 1: Preserve the serial recovery baseline

**Files:**
- Test: `tests/test_skillset.py:4968-4988,5109-5172,5390-5403,6599-6705`

**Interfaces:**
- Consumes: `SkillsetTests.run_cli()`, `fault_environment()`, and filesystem
  snapshot assertions.
- Produces: evidence that normal configured rollback, stale staging, and
  incomplete-rollback diagnostics are green before race-only coverage changes.

- [x] **Step 1: Run retained recovery controls**

Run:

````sh
python -m unittest -v \
  tests.test_skillset.SkillsetTests.test_configured_init_rolls_back_owned_link_and_set_after_interruptions \
  tests.test_skillset.SkillsetTests.test_configured_init_rejects_stale_create_staging_without_mutation \
  tests.test_skillset.SkillsetTests.test_init_rejects_stale_active_staging_without_mutation \
  tests.test_skillset.SkillsetTests.test_init_rolls_back_after_keyboard_interrupt \
  tests.test_skillset.SkillsetTests.test_init_rolls_back_after_recoverable_alias_failure \
  tests.test_skillset.SkillsetTests.test_init_rollback_failure_reports_concrete_recovery_paths
````

Expected: all six tests pass. Do not change production code if a failure occurs;
classify it against the approved serial-recovery contract before proceeding.

### Task 2: Delete concurrent-mutation test contracts

**Files:**
- Modify: `tests/test_skillset.py:4887-4925,4927-4966,5174-5211,5213-5256,5258-5303`

**Interfaces:**
- Consumes: the approved classification in the authoritative reliability design.
- Produces: no fault-injection test that demands configured initialization
  preserve a target or link created/replaced by a concurrent actor.

- [x] **Step 1: Remove the target-creation race contract**

Delete the complete `test_configured_init_preserves_a_set_created_after_preflight`
method at lines 4887-4925. It patches `Path.mkdir()` to create `external/default`
after preflight and asserts that the competing content is preserved.

- [x] **Step 2: Remove the link-and-target creation race contract**

Delete the complete
`test_configured_init_preserves_a_link_and_set_created_after_preflight` method
at lines 4927-4966. It patches `os.symlink()` to create both the configured
link and its target between initialization operations.

- [x] **Step 3: Remove configured-link replacement contracts**

Delete these complete methods, preserving the adjacent serial tests unchanged:

- `test_configured_init_rollback_never_traverses_a_replaced_link` at
  lines 5174-5211;
- `test_configured_init_refuses_a_link_replaced_after_creation` at
  lines 5213-5256; and
- `test_configured_init_refuses_a_link_replaced_during_alias_creation` at
  lines 5258-5303.

Each method patches `os.symlink()` to replace `root/skillsets` with a separate
victim link during rollback or alias creation. Do not replace them with tests
for post-syscall timing, hostile replacement, or concurrent process behavior.

- [x] **Step 4: Confirm only the classified contracts are absent**

Run:

````sh
if grep -nE 'test_configured_init_preserves_a_(set|link_and_set)_created_after_preflight|test_configured_init_(rollback_never_traverses_a_replaced_link|refuses_a_link_replaced_after_creation|refuses_a_link_replaced_during_alias_creation)' tests/test_skillset.py; then exit 1; fi
````

Expected: exit `0` with no output. The neighboring
`test_configured_init_rejects_stale_create_staging_without_mutation` and
`test_configured_init_rolls_back_owned_link_and_set_after_interruptions` remain
collected.

### Task 3: Verify the narrow test-only boundary and stop for review

**Files:**
- Modify: `tests/test_skillset.py` only, apart from this plan and active
  handoff tracking.

**Interfaces:**
- Consumes: the five deleted concurrent-mutation contracts and retained serial
  recovery controls.
- Produces: verification evidence for a test-only simplification batch.

- [x] **Step 1: Re-run focused serial recovery tests**

Run the exact six-test command from Task 1.

Expected: all six tests pass; their assertions still cover rollback of created
aliases, restored original data, retained stale staging, and concrete
incomplete-recovery guidance.

- [x] **Step 2: Run syntax and full regression checks**

Run:

````sh
python -m compileall -q bin lib tests
python -m unittest discover -s tests
````

Expected: both commands exit `0`. Classify any failure before changing code or
unrelated tests.

- [x] **Step 3: Inspect scope and record evidence**

Run `but diff`. Expected: only the five deleted test methods in
`tests/test_skillset.py`, this plan, the authoritative design classification,
and active handoff/index tracking changes are present. Record the commands and
results in the active handoff, then stop for operator review; do not begin the
activation/rename recovery classification.