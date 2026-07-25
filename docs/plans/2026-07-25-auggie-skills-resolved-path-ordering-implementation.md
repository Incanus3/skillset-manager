# Auggie Skills Resolved-Path Ordering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `subagent-driven-development` (recommended) or `executing-plans` to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Order `skillset augment skills list` output lexicographically by each
effective skill's canonical absolute resolved directory.

**Architecture:** Keep effective-winner discovery name-ordered and unchanged.
At rendering time, collect scope-filtered winners with their once-resolved
directories, sort only by the canonical directory string, and render the stored
directory through the existing `~` formatter. Reuse that stored directory for
the verbose resolved-directory detail.

**Tech Stack:** Python 3 standard library (`pathlib`, `unittest`); existing
black-box CLI test harness.

## Global Constraints

- Follow `docs/specs/2026-07-25-auggie-skills-resolved-path-ordering-design.md`.
- Do not add dependencies, commits, or filesystem mutations.
- Preserve discovery precedence, candidate eligibility, source labels, scope
  filtering, error behavior, printable-text escaping, and verbose `SKILL.md`
  details.
- This historical plan is superseded by the table-output design for final row
  ordering: sort first by concise source label, then by canonical resolved
  directory.
- Use test-first development and leave unrelated workspace changes untouched.

---

## File boundaries

| File | Responsibility |
| --- | --- |
| `lib/skillset/augment_discovery.py` | Collect, sort, and render resolved effective-skill directories. |
| `tests/test_skillset.py` | Black-box regression that separates names from resolved-directory order. |
| `README.md` | State the canonical resolved-directory output ordering. |

### Task 1: Render effective skills in resolved-directory order

**Files:**
- Modify: `tests/test_skillset.py:8014-8038`
- Modify: `lib/skillset/augment_discovery.py:100-123`
- Modify: `README.md:593-598`

**Interfaces:**
- `effective_skills(root)` continues to return effective winners in name order.
- `list_effective_skills(root, verbose, scope, output=None)` collects
  `(skill, directory)` pairs where `directory` is `skill.path.resolve()`.
- The later table renderer sorts entries by concise source label and then by
  resolved directory; this plan's original directory-only sort is superseded.

- [x] **Step 1: Replace the name-order test with a failing resolved-directory-order test.**

  Rename `test_augment_skills_list_emits_effective_skills_in_name_order` to
  `test_augment_skills_list_orders_effective_skills_by_resolved_directory`.
  Create external target directories at `targets / "alpha-directory"` and
  `targets / "zulu-directory"`, each containing a valid `SKILL.md`. Link
  `.augment/skills/zulu` to `alpha-directory` and `.augment/skills/alpha` to
  `zulu-directory`. Assert that normal output is target-directory order, not
  name order:

  ```python
  expected = "".join(
      (
          f"zulu [User/.augment] {targets / 'alpha-directory'}\\n",
          f"alpha [User/.augment] {targets / 'zulu-directory'}\\n",
      )
  )
  self.assertEqual(first.stdout, expected)
  self.assertEqual(second.stdout, expected)
  ```

  Preserve return-code and filesystem-snapshot assertions for the test home,
  project, and target directory.

- [x] **Step 2: Run the focused test and confirm the red state.**

  Run:

  ```sh
  python -m unittest tests.test_skillset.SkillsetTests.test_augment_skills_list_orders_effective_skills_by_resolved_directory
  ```

  Observed: the intended test failed because the renderer emitted `alpha` before
  `zulu` from `effective_skills()` name order.

- [x] **Step 3: Collect and sort resolved render entries.**

  Replace the direct `for skill in effective_skills(root)` renderer loop with:

  ```python
  skills = [
      (skill, skill.path.resolve())
      for skill in effective_skills(root)
      if scope == "all" or skill.source.scope == scope
  ]
  for skill, directory in sorted(skills, key=lambda item: str(item[1])):
      skill_file = skill.path / "SKILL.md"
      displayed_directory = display_skill_path(directory, root.parent.resolve())
  ```

  Keep the existing normal output expression. In verbose output, replace
  `skill.path.resolve()` with the stored `directory`; retain
  `skill_file.resolve()` for the `SKILL.md` detail.

- [x] **Step 4: Run focused discovery coverage and confirm the green state.**

  Run:

  ```sh
  python -m unittest \
    tests.test_skillset.SkillsetTests.test_augment_skills_list_orders_effective_skills_by_resolved_directory \
    tests.test_skillset.SkillsetTests.test_augment_skills_list_displays_resolved_directories_and_abbreviates_home \
    tests.test_skillset.SkillsetTests.test_augment_skills_list_filters_resolved_winners_without_mutation \
    tests.test_skillset.SkillsetTests.test_augment_skills_list_gives_each_higher_root_precedence_over_every_lower_root
  ```

  Observed: exit 0. The four-test group confirmed physical resolved-target
  ordering while presentation, precedence, scope filtering, and read-only
  snapshots remained unchanged.

- [x] **Step 5: Document resolved-directory ordering.**

  In `README.md` after the description of winning skills, state that the list
  is ordered lexicographically by canonical resolved skill-directory path. Keep
  the existing explanation that home descendants display with `~` and external
  paths display absolutely.

- [x] **Step 6: Run complete verification and inspect scope.**

  Run:

  ```sh
  python -m unittest discover -s tests
  git diff --check
  ```

  Observed: `python -m unittest discover -s tests` passed 229 tests with 2
  expected skips.
  Inspect `but diff` and confirm that only the three implementation files plus
  this approved design and plan changed for this feature; do not revert or
  stage unrelated workspace changes.

- [x] **Step 7: Complete review checkpoint.**

  The new test was observed failing before production code. The focused
  four-test group passed, and the full suite passed 229 tests with 2 expected
  skips. Do not commit without explicit user authorization.