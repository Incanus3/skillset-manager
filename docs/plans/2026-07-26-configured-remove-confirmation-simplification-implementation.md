# Configured Remove Confirmation Simplification Implementation Plan

> **For agentic workers:** Execute this one task with a fresh review checkpoint.
> Steps use checkbox syntax for tracking.

> **Status:** Completed — implementation was verified and independently
> reviewed. The durable policy and completion record are in
> `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md` and
> `docs/guides/local-cli-reliability.md`.

**Goal:** Remove the configured-link replacement race protocol from `skillset remove`.

**Architecture:** `remove()` retains its pre-prompt validation and the advisory
lock held across confirmation. Remove only its post-confirmation managed-link
revalidation, which exists to detect a second actor replacing the configured
`skillsets` link while stdin waits, and delete the test that requires that
behavior.

**Tech Stack:** Python standard library, `unittest`, GitButler workspace.

## Global Constraints

- Read `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md`
  and `docs/guides/local-cli-reliability.md` in full before editing.
- Retain pre-prompt name, layout, selected-set, active-set, and enabled-lifecycle
  validation, advisory locking, confirmation behavior, and direct deletion
  errors.
- Delete only the post-confirmation revalidation and its dedicated replacement
  race test. Do not add another timing or replacement test.
- Do not change initialization, lock implementation, recovery, public commands,
  or the archived review handoff.
- Do not add dependencies, `ctypes`, direct syscall bindings, or `renameat*`.
- Do not commit, push, merge, publish, or delete handoffs without explicit
  operator authorization.

---

### Task 1: Remove the configured-link timing contract

**Files:**
- Modify: `lib/skillset/operations.py:542-557`
- Modify: `tests/test_skillset.py:4580-4624`

**Interfaces:**
- Consumes: `remove(root, name, confirmed)`, which has already called
  `validate_layout(root)`, `validate_set(root, name)`, and lifecycle guards.
- Produces: the same serial remove workflow without a post-confirmation
  `validate_skillsets_directory(root)` call.

- [x] **Step 1: Run the retained serial removal baseline**

Run:

````sh
python -m unittest -v \
  tests.test_skillset.SkillsetTests.test_remove_decline_empty_invalid_and_eof_cancel_without_mutation \
  tests.test_skillset.SkillsetTests.test_remove_refuses_missing_invalid_symlink_and_invalid_layout_before_prompt \
  tests.test_skillset.SkillsetTests.test_remove_nested_tree_succeeds_without_following_external_links \
  tests.test_skillset.SkillsetTests.test_remove_confirmation_waits_while_holding_advisory_lock
````

Expected: all four tests pass. They define retained confirmation, pre-prompt
validation, normal external-link preservation, and cooperating-command locking.

- [x] **Step 2: Delete the dedicated replacement-race test**

Delete the complete
`test_configured_remove_refuses_a_replaced_managed_link_after_confirmation`
method. It swaps `root / "skillsets"` from `sys.stdin.readline()` and asserts
the command refuses after confirmation; it has no normal serial contract.

- [x] **Step 3: Remove the post-confirmation revalidation**

In `remove()`, preserve the confirmation call and delete only this subsequent
line:

````python
validate_skillsets_directory(root)
````

The resulting branch must proceed directly from a successful
`confirm_removal(name)` call to the existing `shutil.rmtree(target)` block.
Do not alter how `target` is computed before the prompt or how deletion errors
are wrapped.

- [x] **Step 4: Verify the focused boundary**

Run:

````sh
if rg -n 'test_configured_remove_refuses_a_replaced_managed_link_after_confirmation' tests/test_skillset.py; then exit 1; fi
python -m unittest -v \
  tests.test_skillset.SkillsetTests.test_remove_decline_empty_invalid_and_eof_cancel_without_mutation \
  tests.test_skillset.SkillsetTests.test_remove_refuses_missing_invalid_symlink_and_invalid_layout_before_prompt \
  tests.test_skillset.SkillsetTests.test_remove_nested_tree_succeeds_without_following_external_links \
  tests.test_skillset.SkillsetTests.test_remove_confirmation_waits_while_holding_advisory_lock
````

Expected: the absence check prints nothing, and all four retained tests pass.

- [x] **Step 5: Run syntax and regression checks**

Run:

````sh
python -m compileall -q bin lib tests
python -m unittest discover -s tests
if rg -n 'ctypes|renameat|renameat2|RENAME_NOREPLACE' lib tests; then exit 1; fi
but diff
````

Expected: compilation and the full suite exit `0`; the forbidden-binding check
prints nothing; and the diff is limited to this removal, its test deletion, the
authoritative design update, this plan, and active handoff tracking.

- [x] **Step 6: Stop for independent review**

Record exact verification evidence in the active handoff. Request review of the
single removal boundary before any publication or another candidate inventory.