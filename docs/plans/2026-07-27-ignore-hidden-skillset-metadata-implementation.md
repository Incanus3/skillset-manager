# Ignore Hidden Skillset Metadata Implementation Plan

> **For agentic workers:** Execute the task in a TDD cycle. Track each step
> with its checkbox.

**Goal:** Allow hidden user metadata in `skillsets/` without listing or
validating it as a skillset.

**Architecture:** Keep the existing visible-name contract. During container
enumeration, preserve the explicit stale-create-staging error and skip every
other dot-prefixed entry. Both validation and listing apply that boundary.

**Tech Stack:** Python standard library and `unittest`.

## Global Constraints

- Hidden names remain invalid in explicit skillset-name arguments.
- `.skillset-create-<name>.staging` remains a recovery error.
- Do not add dependencies.
- Do not commit without explicit user authorization.

---

### Task 1: Ignore hidden user metadata during enumeration

**Files:**
- Modify: `tests/test_skillset.py: existing layout/list tests near 4825`
- Modify: `lib/skillset/layout.py:214-223`
- Modify: `lib/skillset/doctor.py:244-261`
- Modify: `lib/skillset/metadata.py:391-394`

**Interfaces:**
- Consumes: `validate_skillset_entries(skillsets)` and `list_sets(root, verbose)`.
- Produces: successful layout validation and list output when a hidden metadata
  directory is present, while explicit hidden names remain rejected.

- [ ] **Step 1: Write the failing regression test**

Add a test adjacent to `test_invalid_names_are_operational_errors_and_cannot_escape_skillsets`:

```python
def test_hidden_skillset_metadata_is_ignored(self):
    self.initialize()
    self.make_set(self.root, "extra")
    (self.root / "skillsets" / ".git").mkdir()

    for arguments in (("doctor",), ("list",), ("list", "--verbose")):
        result = self.run_cli(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(".git", result.stdout)
```

Extend the invalid-name test with a rename case:

```python
renamed = self.run_cli("rename", "default", ".hidden")
self.assert_refused(renamed)
self.assertTrue((self.root / "skillsets" / "default").is_dir())
self.assertFalse(os.path.lexists(self.root / "skillsets" / ".hidden"))
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `python3 -m unittest tests.test_skillset.SkillsetTests.test_hidden_skillset_metadata_is_ignored`

Expected: failure containing `invalid skillset name '.git'` before the
implementation change.

- [ ] **Step 3: Implement the minimum enumeration filters**

In `validate_skillset_entries` and `doctor_skillset_entries`, retain the
stale-create condition first, then skip other hidden entries:

```python
if entry.name.startswith(".skillset-create-") and entry.name.endswith(".staging"):
    raise OperationalError(f"stale create staging path must be recovered: {entry}")
if entry.name.startswith("."):
    continue
validate_name(entry.name)
skillset_mode(entry)
```

The doctor scan uses `continue` after the same `entry.name.startswith(".")`
condition, before it records invalid-name findings or calls `doctor_set`.

In `list_sets`, filter dot-prefixed names before passing them to
`list_named_sets`:

```python
names = sorted(
    entry.name for entry in skillsets.iterdir() if not entry.name.startswith(".")
)
```

- [ ] **Step 4: Run focused tests and confirm they pass**

Run: `python3 -m unittest tests.test_skillset.SkillsetTests.test_hidden_skillset_metadata_is_ignored tests.test_skillset.SkillsetTests.test_invalid_names_are_operational_errors_and_cannot_escape_skillsets tests.test_skillset.SkillsetTests.test_doctor_aggregates_partial_and_structurally_invalid_state`

Expected: both tests pass; `.skillset-create-*.staging` coverage remains
unchanged.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m unittest tests/test_skillset.py`

Expected: all tests pass.

- [ ] **Step 6: Commit if authorized**

Create one commit containing the specification, plan, tests, and two minimal
enumeration changes only after receiving explicit user authorization.