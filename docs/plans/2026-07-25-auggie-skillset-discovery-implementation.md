# Auggie Skillset Discovery Implementation Plan

> **Status:** Historical pre-implementation plan. The described feature is
> implemented.

**Goal:** Add safe managed Auggie skillset projections and a read-only command
that lists the effective skills from all Auggie discovery locations.

**Architecture:** Copy Claude Code's hardened flat-projection transaction into
an Auggie-specific module that owns only `.augment` roots and registrations.
Keep six-root read-only discovery in a separate module so scanning compatible
`.claude` and `.agents` locations cannot create ownership or mutation paths.

**Tech Stack:** Linux; Python 3 standard library; `argparse`; `unittest`; Bash,
Zsh, and Fish generated completions.

## Global Constraints

- Follow `docs/specs/2026-07-24-auggie-skillset-discovery-design.md` exactly.
- Do not add dependencies or use a YAML package.
- Only `augment enable` and `augment disable` may mutate `.augment` roots.
- Never mutate, repair, block on, or acquire ownership of compatible `.claude`
  or `.agents` roots.
- Keep `skillsets/always-on/.skill-lock.json` untouched.
- Use test-first development and preserve the existing `ClaudeInterrupted`
  recovery behavior.
- Do not commit unless the user explicitly asks; stop after each bead.

---

## File boundaries

| File | Responsibility |
| --- | --- |
| `lib/skillset/augment.py` | Managed `.augment` registration, direct-link projection, recovery, and global lifecycle blocker. |
| `lib/skillset/augment_discovery.py` | Read-only six-root scan, precedence resolution, scope filtering, and rendering. |
| `lib/skillset/cli.py` | Auggie nested parsers, command dispatch, and inspection-lock classification. |
| `lib/skillset/operations.py` | Refuse rename/removal while a global Auggie registration is enabled or malformed. |
| `lib/skillset/completions.py` | Bash, Zsh, and Fish completion trees for Auggie commands. |
| `tests/test_skillset.py` | Black-box CLI, filesystem safety, discovery, help, and completion coverage. |
| `README.md` | User-facing managed and discovery command documentation. |

### Task 1: Managed Auggie flat-projection integration

**Files:**
- Create: `lib/skillset/augment.py`
- Modify: `lib/skillset/cli.py:7-20, 107-143, 198-265`
- Modify: `lib/skillset/operations.py:7-9, 449-481`
- Modify: `tests/test_skillset.py:1964-3290, 3987-4076, 4414-4460`

**Interfaces:**
- Produces `enable(root, name, scope)`, `disable(root, name, scope)`,
  `list_enabled(root, verbose, scope)`, and
  `global_registration_blocker(root, name)` from `skillset.augment`.
- `scope_paths(root, scope)` returns `(augment_root, skills_dir,
  registrations_dir)` using `root.parent / ".augment"` globally and
  `Path.cwd() / ".augment"` locally.
- CLI parses `skillset augment <enable|disable|list>` with `augment_scope` and
  invokes the corresponding interface.

- [ ] **Step 1: Add focused black-box tests before adding the command.**

  Mirror `test_claude_global_enable_flattens_skills_and_registers_the_set` as
  `test_augment_global_enable_flattens_skills_and_registers_the_set`. Assert
  that enabling `personal` creates the following links and no collection link
  under the public skills directory:

  ```python
  augment = self.home / ".augment"
  self.assertEqual(os.readlink(augment / ".skillsets" / "personal"), str(skills))
  self.assertEqual(os.readlink(augment / "skills" / "alpha-directory"), str(alpha))
  self.assertFalse(os.path.lexists(augment / "skills" / "personal"))
  self.assertEqual(listed.stdout, "[g] personal [m]\n")
  ```

  Add parser-negative cases for a missing Auggie subcommand, an unknown
  subcommand, missing enable/disable names, extra list arguments, unknown
  options, and simultaneous `--global --local`.

- [ ] **Step 2: Run the focused test to establish the red state.**

  Run:

  ```sh
  python -m unittest tests.test_skillset.SkillsetTests.test_augment_global_enable_flattens_skills_and_registers_the_set
  ```

  Expected: exit 2 because `augment` is not yet a recognized command.

- [ ] **Step 3: Create the Auggie transaction module by copying the complete Claude transaction, then substitute only product-specific values.**

  Copy `lib/skillset/claude.py` into `lib/skillset/augment.py`. Rename every
  module-level Claude identity, diagnostic, and recovery command to Auggie, and
  change only the product root in `scope_paths`:

  ```python
  def scope_paths(root, scope):
      augment = (
          root.parent / ".augment"
          if scope == "global"
          else Path.cwd() / ".augment"
      )
      return augment, augment / "skills", augment / ".skillsets"
  ```

  Retain descriptor-based `O_NOFOLLOW` checks, preflight, canonical absolute
  links, direct-real-source-child inventory, cross-scope collision detection,
  rollback diagnostics, interruption injection points, synchronization
  verification, and registration-last deletion. Do not parameterize or weaken
  the Claude module.

- [ ] **Step 4: Wire the managed Auggie parser, dispatch, inspection lock, and lifecycle blocker.**

  Add an `augment` parser with the same `enable`, `disable`, and `list`
  structure as `claude`; pass `directory=".augment"` to `add_scope_options`.
  Import the four Auggie interfaces, dispatch them using `augment_scope`, and
  classify `augment list` as inspection. In `refuse_enabled_lifecycle`, combine
  Codex, Claude Code, and Auggie blockers; describe the actual malformed
  registration/container and require its repair before rename or removal.

- [ ] **Step 5: Run focused tests for managed behavior.**

  Run:

  ```sh
  python -m unittest tests.test_skillset.SkillsetTests.test_augment_global_enable_flattens_skills_and_registers_the_set
  python -m unittest tests.test_skillset.SkillsetTests.test_augment_local_enable_is_exact_scoped_idempotent_and_reconciles
  python -m unittest tests.test_skillset.SkillsetTests.test_augment_enable_refuses_cross_scope_skill_name_collisions
  python -m unittest tests.test_skillset.SkillsetTests.test_augment_global_registration_and_malformed_containers_block_lifecycle
  ```

  Expected: all pass after renaming and adapting the corresponding Claude tests.

- [ ] **Step 6: Mirror all remaining Claude projection safety tests under the Auggie command and paths.**

  Adapt every `test_claude_...` case through the final registration/lifecycle
  cases: alias and symlink refusal, malformed containers, source containment,
  binding changes, preflight collisions, stale reconciliation, dangling-source
  disable, interrupt recovery, list synchronization, and filesystem snapshots.
  Keep assertions product-specific so a regression cannot accidentally execute
  Claude code. Run the contiguous Auggie test selection and require no failures.

- [ ] **Step 7: Review the bead boundary.**

  Inspect the diff and run `git diff --check` (or `jj diff --check` if
  available). Verify the unrelated lock file is absent. Ask the user to review
  or commit before starting the next bead.

### Task 2: Effective Auggie skills discovery

**Files:**
- Create: `lib/skillset/augment_discovery.py`
- Modify: `lib/skillset/cli.py:7-20, 107-143, 198-265`
- Modify: `tests/test_skillset.py` near the Auggie integration tests

**Interfaces:**
- `discovery_roots(root)` returns ordered records for the six documented roots
  with `label`, `scope`, and `path` fields.
- `effective_skills(root)` returns one record per first-seen directory name.
- `list_effective_skills(root, verbose, scope, output=None)` renders winners,
  applying scope filtering only after all roots have been resolved.

- [ ] **Step 1: Write a six-root precedence test.**

  Create all six roots beneath the test home and a project directory. Add a
  distinct direct `SKILL.md` child to each and the same `shared` child to at
  least three roots. Require the unscoped command to include each distinct
  child, include only the `User/.augment` `shared` winner, and print its source
  label plus discovered directory path:

  ```python
  result = self.run_cli("augment", "skills", "list", cwd=project)
  self.assertEqual(result.returncode, 0, result.stderr)
  self.assertIn("shared [User/.augment]", result.stdout)
  self.assertNotIn(str(project / ".agents" / "skills" / "shared"), result.stdout)
  ```

- [ ] **Step 2: Run the new test and confirm the nested command is red.**

  Run:

  ```sh
  python -m unittest tests.test_skillset.SkillsetTests.test_augment_skills_list_uses_documented_precedence
  ```

  Expected: exit 2 because `augment skills list` does not yet parse.

- [ ] **Step 3: Implement read-only root scanning and resolution.**

  Define immutable records for roots and winners. For each existing root,
  enumerate only immediate entries in deterministic name order; accept an entry
  when `entry.is_dir()` and `(entry / "SKILL.md").is_file()` are true, allowing
  managed directory symlinks. Treat missing roots as empty. Raise
  `OperationalError` with the relevant root or candidate path when enumeration
  or inspection raises `OSError`. Never use `mkdir`, `unlink`, `symlink`, or
  registration functions in this module.

- [ ] **Step 4: Render and filter only resolved winners.**

  Make normal output one line per winner in deterministic name order:

  ```text
  <directory-name> [<source-label>] <discovered-directory-path>
  ```

  For verbose output, append the resolved directory and `SKILL.md` paths for
  each same winner. Resolve all six roots first; then include a record only when
  `scope == "all"` or its stored scope matches the requested `global`/`local`.

- [ ] **Step 5: Add the nested parser and read-only locking.**

  Add `augment skills` as a required nested subparser with required `list`,
  `-v/--verbose`, and `add_scope_options(..., default="all")`. Dispatch to
  `list_effective_skills`; use a non-creating discovery lock that acquires the
  existing real advisory lock when available, but falls back without validating
  or creating managed state when that lock is absent or unusable.

- [ ] **Step 6: Add focused behavioral and no-mutation coverage.**

  Cover missing roots, file roots, unreadable/enumeration failures, direct-file
  and missing-`SKILL.md` exclusions, managed `.augment/skills` symlink inclusion,
  all precedence pairs, output sorting, `--global`, `--local`, a local loser
  masked by a global winner, verbose resolution paths, and unchanged filesystem
  snapshots before/after every discovery invocation. Run each focused test and
  then their full Auggie discovery group.

- [ ] **Step 7: Review the bead boundary.**

  Inspect the diff, check it does not add mutation APIs to
  `augment_discovery.py`, and ask the user to review or commit before moving on.

### Task 3: Completion, documentation, and end-to-end regression coverage

**Files:**
- Modify: `lib/skillset/completions.py:6-429`
- Modify: `tests/test_skillset.py:539-665, 3987-4076, 4414-4460`
- Modify: `README.md:441-527`

**Interfaces:**
- All shell completers expose `augment`; its first nested command offers
  `enable`, `disable`, `list`, and `skills`; `skills` then offers only `list`.
- `augment skills list` completes only help, verbose, global, and local flags.

- [ ] **Step 1: Write completion and help tests.**

  Extend Bash and real-Fish probes, plus Zsh assertions when installed, to
  require these candidates:

  ```text
  skillset augment e                 -> enable
  skillset augment skills l          -> list
  skillset augment skills list --v   -> --verbose
  ```

  Extend usage-error cases for incomplete `augment skills`, incomplete
  `augment skills list` arguments, unknown nested commands, and mutually
  exclusive scope flags. Add uninitialized-layout read-only cases for both
  Auggie list forms.

- [ ] **Step 2: Run the focused completion tests and confirm they fail.**

  Run:

  ```sh
  python -m unittest tests.test_skillset.SkillsetTests.test_bash_completion_is_contextual_and_uses_managed_names
  python -m unittest tests.test_skillset.SkillsetTests.test_fish_completion_is_contextual_and_uses_managed_names
  ```

  Expected: assertions fail because Auggie candidates are absent.

- [ ] **Step 3: Update all completion grammars.**

  Add `augment` to `COMMANDS`, the Bash `codex|claude` branch generalized for
  Auggie nesting, the Zsh top-level values and `_arguments` tree, and Fish
  predicates/declarations for both Auggie levels. Preserve completion of
  managed skillset names only for `augment enable` and `augment disable`; never
  invoke discovery while completing.

- [ ] **Step 4: Document both Auggie views and their boundary.**

  Add an Auggie section after Claude Code documentation. Show the flat
  `.augment/.skillsets` plus `.augment/skills` layout, global/local managed
  commands, reconciliation, collisions, and lifecycle restrictions. Separately
  document `augment skills list`, all six sources in precedence order,
  effective-winner filtering, source labels, and the fact that compatible roots
  are read-only external inputs. Warn not to commit local generated `.augment`
  links and registrations.

- [ ] **Step 5: Run generated-completion and full regression verification.**

  Run:

  ```sh
  bin/skillset completions bash >/dev/null
  bin/skillset completions zsh >/dev/null
  bin/skillset completions fish | fish -n
  python -m unittest discover -s tests
  ```

  Expected: generators exit 0, Fish reports no syntax error, and the unittest
  suite exits 0. Zsh-dependent tests may skip only when Zsh is unavailable.

- [ ] **Step 6: Final review checkpoint.**

  Inspect the final diff and status using the available VCS. Search modified
  implementation-facing files for leaked planning terms (`bead`, `ticket`,
  `milestone`, `phase`, `superpowers`). Confirm only intended files changed and
  the unrelated lock file remains absent. Report the verification evidence and
  ask the user whether to commit.