# Resolved Auggie Skill Paths Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `subagent-driven-development` (recommended) or `executing-plans` to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `skillset augment skills list` display every effective skill's
canonical directory, abbreviated with `~` when it is within the configured
home directory.

**Architecture:** Preserve discovered entries and all winner-selection logic.
At render time, resolve both the winner path and configured home, format the
winner relative to that canonical home only when `Path.relative_to()` proves
containment, and use that formatted path for standard output. Verbose
resolution details retain their current absolute-path contract.

**Tech Stack:** Python 3 standard library (`pathlib`, `unittest`); existing
black-box CLI test harness.

## Global Constraints

- Follow `docs/specs/2026-07-25-resolved-auggie-skill-paths-design.md` exactly.
- Do not add dependencies or mutate any discovery root.
- Do not alter precedence, candidate eligibility, source labels, scope
  filtering, exception behavior, or verbose resolved-detail lines.
- Use test-first development; observe the new test fail before production code.
- Do not modify unrelated workspace changes or commit without explicit user
  authorization.

---

## File boundaries

| File | Responsibility |
| --- | --- |
| `lib/skillset/augment_discovery.py` | Resolve and safely format a winner directory for standard-list rendering. |
| `tests/test_skillset.py` | Black-box regression coverage and adjusted output expectations. |
| `README.md` | Describe the printed path as the resolved skill directory. |

### Task 1: Render canonical effective-skill directories

**Files:**
- Modify: `tests/test_skillset.py:7930-8252`
- Modify: `lib/skillset/augment_discovery.py:92-113`
- Modify: `README.md:575-596`

**Interfaces:**
- Produce `display_skill_path(path: Path, home: Path) -> Path | str` in
  `skillset.augment_discovery`.
- `list_effective_skills(root, verbose, scope, output=None)` calls
  `display_skill_path(skill.path.resolve(), root.parent.resolve())` for its
  standard output directory.
- `display_skill_path` returns `"~"` for the home directory itself,
  `Path("~") / relative` for descendants, and the resolved absolute `path`
  for paths outside home.

- [x] **Step 1: Add the failing regression test and revise direct-path expectations.**

  In `SkillsetTests`, add
  `test_augment_skills_list_displays_resolved_directories_and_abbreviates_home`.
  Initialize the managed layout, create a project, write a skill at
  `self.root / "skillsets" / "personal" / "skills" / "managed"`, and create
  the projected `self.home / ".augment" / "skills" / "managed"` symlink to
  it. Also write a direct global skill named `direct`, and an external skill
  outside `self.home` named `external` linked from `.augment/skills`.

  Assert the normal CLI output equals:

  ```python
  self.assertEqual(
      result.stdout,
      "".join(
          (
              f"direct [User/.augment] ~/.augment/skills/direct\\n",
              f"external [User/.augment] {external}\\n",
              "managed [User/.augment] "
              "~/.agents/skillsets/personal/skills/managed\\n",
          )
      ),
  )
  ```

  Keep the existing snapshot assertions. Update all nearby normal-output
  expectations for direct children under `self.home` from sandbox absolute
  paths to `~/.augment/...`; preserve verbose assertions, which explicitly
  verify the absolute resolved values.

- [x] **Step 2: Run the new test and confirm the intended red state.**

  Run:

  ```sh
  python -m unittest tests.test_skillset.SkillsetTests.test_augment_skills_list_displays_resolved_directories_and_abbreviates_home
  ```

  Expected: failure because standard output still contains the `.augment`
  projection link rather than the `~/.agents/skillsets/.../managed` target.

- [x] **Step 3: Add the minimal safe formatter and use it in normal output.**

  In `lib/skillset/augment_discovery.py`, add the helper before
  `list_effective_skills`:

  ```python
  def display_skill_path(path, home):
      try:
          relative = path.relative_to(home)
      except ValueError:
          return path
      return Path("~") / relative if relative.parts else "~"
  ```

  In the loop, compute the resolved directory once for normal output:

  ```python
  directory = skill.path.resolve()
  displayed_directory = display_skill_path(directory, root.parent.resolve())
  ```

  Pass `displayed_directory` to `metadata.printable_text` in the first line.
  Keep the verbose directory and `SKILL.md` calls as `skill.path.resolve()` and
  `skill_file.resolve()` so their values and output labels stay unchanged.

- [x] **Step 4: Run focused discovery coverage and confirm the green state.**

  Run:

  ```sh
  python -m unittest \
    tests.test_skillset.SkillsetTests.test_augment_skills_list_displays_resolved_directories_and_abbreviates_home \
    tests.test_skillset.SkillsetTests.test_augment_skills_list_emits_effective_skills_in_name_order \
    tests.test_skillset.SkillsetTests.test_augment_skills_list_escapes_control_characters_without_mutation \
    tests.test_skillset.SkillsetTests.test_augment_skills_list_filters_resolved_winners_without_mutation
  ```

  Expected: exit 0. The first line uses resolved, home-abbreviated paths; the
  verbose resolved-detail lines, precedence, deterministic ordering, escaping,
  scope filtering, and read-only snapshots still pass.

- [x] **Step 5: Update the user documentation.**

  In the `Inspect effective Auggie discovery` section of `README.md`, replace
  “discovered directory path” with “resolved skill-directory path.” Add that
  paths under the configured home directory use `~`; paths outside it remain
  absolute. Replace “`--verbose` adds resolved paths” with language explaining
  it additionally prints resolved directory and `SKILL.md` details.

- [x] **Step 6: Run complete regression verification.**

  Run:

  ```sh
  python -m unittest discover -s tests
  ```

  Expected: exit 0. Then inspect the focused diff with `but diff`; verify this
  work changes only the three implementation files plus its approved design and
  plan artifacts, and do not revert or stage unrelated workspace changes.

- [x] **Step 7: Review the completion checkpoint.**

  Confirm the output for a managed link is
  `~/.agents/skillsets/personal/skills/<name>`, no user-facing planning terms
  appear in code or README, and verification evidence is recorded in the final
  report. Ask the user whether they want a commit; do not create one otherwise.