# Manual Sentinel Permission Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `subagent-driven-development` (recommended) or `executing-plans` to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** Completed — implementation was verified and independently
> reviewed. The durable policy and completion record are in
> `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md` and
> `docs/guides/local-cli-reliability.md`.

**Goal:** Accept canonical non-writable manual empty-lock sentinels while
continuing to create and repair them with mode `0444`.

**Architecture:** Keep `validate_manual_sentinel()` as the single authority for
the shared sentinel's real-file, permission, and canonical-content invariants.
Replace its exact-mode comparison with a write-bit check. Add a black-box
manual-mode contract that is red under the current exact-`0444` rule.

**Tech Stack:** Python 3 standard library; `unittest`; GitButler (`but`).

## Global Constraints

- Read `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md`
  and `docs/guides/local-cli-reliability.md` before editing.
- `skillset` is a trusted local CLI: preserve normal serial recovery and do not
  add replacement-race, TOCTOU, descriptor-identity, or syscall timing logic.
- Retain real-regular-file validation, canonical empty-lock JSON validation,
  the active manual-mode alias, ordinary I/O errors, and writable-sentinel
  refusal.
- New and repaired sentinels must still have mode `0444`.
- Do not add dependencies, commit, push, publish, or merge without explicit
  operator authorization.

---

## File Map

- Modify `tests/test_skillset.py` — add black-box coverage for accepted
  non-writable modes and rejected writable modes; retain existing creation and
  repair checks for `0444`.
- Modify `lib/skillset/layout.py` — accept any mode without write bits in
  `validate_manual_sentinel(root) -> Path`.

### Task 1: Define the manual-sentinel permission contract

**Files:**
- Modify: `tests/test_skillset.py:4910-4960`

**Interfaces:**
- Consumes: `SkillsetTests.initialize()`, `SkillsetTests.run_cli()`,
  `SkillsetTests.assert_refused()`, and `self.home`.
- Produces: a black-box test proving that `0400` is usable and `0644` is
  rejected while a manual skillset is active.

- [x] **Step 1: Add the failing test beside the existing manual lifecycle test**

````python
def test_manual_sentinel_accepts_nonwritable_modes_and_refuses_writable_mode(self):
    self.initialize()
    self.assertEqual(self.run_cli("create", "--manual", "personal").returncode, 0)
    self.assertEqual(self.run_cli("use", "personal").returncode, 0)
    sentinel = self.home / ".skillset-manual-empty-lock.json"
    sentinel.chmod(0o400)
    accepted = self.run_cli("list")
    self.assertEqual(accepted.returncode, 0, accepted.stderr)
    self.assertEqual(accepted.stdout, "default\n* personal [m]\n")
    sentinel.chmod(0o644)
    rejected = self.run_cli("list")
    self.assert_refused(rejected)
    self.assertIn("manual empty-lock sentinel must be read-only", rejected.stderr)
````

- [x] **Step 2: Run the new test and verify it is red**

Run:

````sh
python -m unittest -v tests.test_skillset.SkillsetTests.test_manual_sentinel_accepts_nonwritable_modes_and_refuses_writable_mode
````

Expected: failure at the `0400` `list` invocation; stderr reports that the
sentinel must be read-only with exact mode `0444`.

### Task 2: Relax validation without weakening the read-only invariant

**Files:**
- Modify: `lib/skillset/layout.py:240-253`
- Test: `tests/test_skillset.py:4910-4960`

**Interfaces:**
- Consumes: `stat.S_IMODE(path.stat().st_mode)` in
  `validate_manual_sentinel(root) -> Path`.
- Produces: acceptance for a canonical sentinel with no owner, group, or other
  write bit; existing callers continue to receive `OperationalError` for a
  writable sentinel.

- [x] **Step 1: Replace exact-mode validation with a write-bit check**

````python
mode = stat.S_IMODE(path.stat().st_mode)
if mode & 0o222:
    raise OperationalError(
        f"manual empty-lock sentinel must be read-only: {path}"
    )
value = read_lockfile(path)
````

Keep `ensure_manual_sentinel()` unchanged: its `chmod(0o444)` remains the
creation and repair contract.

- [x] **Step 2: Run the focused manual-sentinel contracts**

Run:

````sh
python -m unittest -v tests.test_skillset.SkillsetTests.test_manual_skillset_creation_activation_and_display tests.test_skillset.SkillsetTests.test_manual_sentinel_accepts_nonwritable_modes_and_refuses_writable_mode
````

Expected: PASS. The existing lifecycle test proves creation and repair remain
`0444`; the new test proves `0400` is accepted and `0644` is refused.

### Task 3: Verify the narrow boundary and stop for review

**Files:**
- Modify: `lib/skillset/layout.py`, `tests/test_skillset.py` only.

**Interfaces:**
- Consumes: the existing manual lifecycle, activation, and doctor repair paths.
- Produces: verification that only the approved permission rule changed.

- [x] **Step 1: Confirm the exact-mode rule is absent and the retained creator remains**

Run:

````sh
if rg -n 'mode != 0o444' lib/skillset/layout.py; then exit 1; fi
rg -n 'mode & 0o222|chmod\(0o444\)' lib/skillset/layout.py
````

Expected: the first command emits no matches; the second reports the write-bit
validation and unchanged `chmod(0o444)` creation call.

- [x] **Step 2: Run syntax and full regression verification**

Run:

````sh
python -m compileall -q bin lib tests
python -m unittest discover -s tests
````

Expected: both commands exit `0`.

- [x] **Step 3: Inspect the complete change and stop for independent review**

Run:

````sh
but diff
````

Expected: only the focused test, write-bit validation, approved design addition,
handoff checkpoint, and this plan are present. Do not commit or publish unless the operator
explicitly authorizes it.