# Codex project enablement implementation plan

For agentic workers: use the subagent-driven-development skill after plan approval and resumption, unless the operator chooses inline execution through executing-plans. Checkboxes track implementation; none are completed by writing this plan.

**Status:** Approved by the operator; implementation verified after resumption; remaining acceptance disposition is recorded below. Tasks 1–6 are implemented and independently reviewed within the recorded acceptance limits. Final review product corrections are committed at `71b0587` and scoped re-review addressed all three findings. The test-only Git 2.55 guard correction is at `5254e50`; direct verifier confirmation passed; no review findings remain. Unmodified Orca service HOME/PATH acceptance remains unmet.

**Goal:** Enable selected skillsets once for a clone and discover them through Codex in existing and future worktrees.

**Architecture:** One harness-neutral `project.py` owns Git discovery, `project-skillsets.json`, the shared named hook, operation ordering and inspection. `codex.py` owns explicit-root link projection. The public project options are Codex-only; the hidden top-level hook dispatches to the current Codex reconciler.

**Tech stack:** Linux, Python 3 standard library, Git 2.54+ for project operations, existing unittest and native shell-completion probes.

**Spec:** [Approved design](../specs/2026-10-11-codex-project-enablement-design.md). Read it completely before executing this plan. It governs behavior where this plan supplies implementation detail.

## Global constraints

- Preserve global enable/disable defaults and exact-current-directory `--local`, including non-Git use.
- Only Codex enable/disable/list acquire `--project`, with no short alias. Scope conflicts exit 2 before mutation.
- Registration is `<git-common-dir>/project-skillsets.json`, exactly `{"version": 1, "names": [...]}`; one sorted, unique, nonempty list shared by future harness integrations.
- Own only `hook.skillset-project.command` and `hook.skillset-project.event = post-checkout`, in repository-local common config.
- Invoke hidden top-level `skillset _project-hook OLD NEW FLAG` using inherited `HOME` and standard `PATH` precedence. Record neither home nor executable.
- Native hook ordinary failures warn to stderr and return zero to Git; another hook's status remains visible.
- Unscoped list groups are global `[g]`, project `[p]`, local `[l]`, each sorted. Registration and physical links can both produce rows for one name.
- Preflight known errors; retain completed changes and registration after partial failures. Registration removal is last; no rollback journal or origin ledger.
- Preserve unrelated entries, traditional hooks, `core.hooksPath`, ignore files and unrelated runtime metadata. Containers remain real directories and are never removed.
- Use existing stable-home and non-creating discovery locks for all project paths, including cleanup and the internal hook. No non-Git discovery side effects in `.agents`.
- No dependencies beyond the standard library; no other harness integration, global project index, path cache, watcher, persistent launcher, adversarial filesystem protocol or concurrency matrix.
- Use isolated temporary homes/clones. Do not change this checkout's live hooks/config or `~/.agents` during implementation tests.

## Review focus

1. Git location variables inherited by hooks can redirect inspection of sibling worktrees; clear only Git-reported local variables in those child environments (Tasks 1 and 6).
2. A later worktree collision must not record requested names or create earlier links (Task 4).
3. Failed last-name disable and failed disable with other names differ: absent hook versus possible checkout recreation (Task 4).
4. Missing sources must remain visible, cleanable and unable to create new dangling links; other valid sources still reconcile (Tasks 3 and 5).
5. Traditional-hook self-removal/restoration and effective disabled/inherited named-hook settings must preserve ownership and diagnosis (Tasks 3 and 6).

## Repository baseline and file boundaries

Planning inspected base `bb7e9152fe6c9f7976586380cd2956b9bf6e92c1` with design commit `6eda5ed4399e` and subsequent reviewed documentation changes. No product code has changed. GitButler is initialized; use `but` for workspace version-control changes. Unrelated Beads recovery state must stay outside feature commits.

| File | Responsibility and existing entry points |
| --- | --- |
| New `lib/skillset/project.py` | Shared Git subprocess boundary, registration, hook config, operations, inspection and hidden-hook dispatcher |
| `lib/skillset/codex.py` | Existing `expected_target`, `codex_skills_directory`, `canonical_link`, `enable`, `disable`, `enabled_names`, `list_enabled`; add explicit-worktree primitives and project bridges |
| `lib/skillset/cli.py` | `parser`, `add_scope_options`, `dispatch_locked_command`, `run_managed_command`; Codex-only scope support, hidden top-level hook, non-creating lock routing and return-code propagation |
| `lib/skillset/metadata.py` | Existing row tuples/renderers; narrowly support invalid registered sources and project scope rows |
| `lib/skillset/completions.py` | Existing Bash/Zsh/Fish scripts; public Codex grammar only, scope mutual exclusion |
| `tests/test_skillset.py` | Existing `SkillsetTests`, temporary homes, CLI helpers, filesystem snapshots, shell probes; add focused project test classes without moving unrelated tests |
| `README.md` | Public examples and operational dependencies/recovery/ignore guidance |
| Design, research and handoff artifacts | Acceptance evidence and continuation state; no planning labels in product surfaces |

Use [local CLI reliability](../guides/local-cli-reliability.md) and [in-process/subprocess selection](../guides/in-process-cli-test-selection.md). `run_cli_in_process` restores environment/cwd/streams and is appropriate for ordinary CLI validation. Native hooks, `PATH` selection, interrupts and shell grammar require real processes. Retain lazy dispatch imports; `completions` and help must not import project machinery unnecessarily. Add all new test methods/helpers inside existing `SkillsetTests`; task-specific prefixes select focused runs without inheriting and rerunning unrelated suites. Project subprocess and in-process CLI cases pass `extra_environment=self.git_environment()` to isolate Git config and supply the hook executable through PATH; cases proving another environment override it deliberately.

Execute Tasks 1–6 in order. They share interfaces and files; do not implement them concurrently. Each task has its own red/green and bounded review gate. A working internal layer is a valid early deliverable before its public CLI bridge exists.

### Task 1: Shared Git identity and names-only registration

**Files:** Create `lib/skillset/project.py`; modify `tests/test_skillset.py` with Git helper methods and tests prefixed `test_project_state_` inside existing `SkillsetTests`.

**Interfaces produced:**

```python
@dataclass(frozen=True)
class GitProject:
    common_dir: Path
    current_root: Path
    worktrees: tuple  # sorted Path values; empty when inventory=False

```

| Function | Return/behavior |
| --- | --- |
| `discover(cwd: Path, *, required=True, inventory=True)` | `GitProject` or `None` for optional non-Git/unavailable discovery; required mode enforces Git 2.54/non-bare invocation |
| `read_names(common_dir: Path)` | `None` when absent, otherwise validated sorted tuple of names |
| `write_names(common_dir: Path, names: tuple)` | Atomic nonempty write; empty tuple unlinks registration |

These are interface contracts, not implementation stubs. Use private helpers for Git execution, parsing and schema validation. Import `Path`, `dataclass`, and existing `OperationalError`/name validation.

- [x] Add these Git helper methods inside existing `SkillsetTests`; do not subclass that test class or inherit its unrelated tests into new suites. Its Git operations are confined to disposable resources; raw Git here is the tool under test, not workspace version control.

```python
def git_environment(self, extra=None):
    env = self.environment(extra={
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Skillset Test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "Skillset Test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
        "PATH": str(SKILLSET.parent) + os.pathsep + os.environ.get("PATH", ""),
    })
    if extra:
        env.update(extra)
    return env

def git(self, cwd, *args, check=True, extra=None):
    if shutil.which("git") is None:
        self.skipTest("Git is unavailable")
    result = subprocess.run(
        ["git", "-C", str(cwd), *args], env=self.git_environment(extra),
        text=True, capture_output=True, check=False, timeout=10,
    )
    if check:
        self.assertEqual(result.returncode, 0, result.stderr)
    return result

def new_repository(self, name="repo"):
    path = self.sandbox / name
    path.mkdir()
    self.git(path, "init", "-q")
    (path / "seed").write_text("seed\n")
    self.git(path, "add", "seed")
    self.git(path, "commit", "-qm", "seed")
    return path
```

- [x] Add a registration round-trip and rejection test before the production module exists:

```python
def test_project_state_registration_round_trip_and_schema_refusal(self):
    from skillset import project
    common = self.sandbox / "metadata"
    common.mkdir()
    self.assertIsNone(project.read_names(common))
    project.write_names(common, ("default", "personal"))
    state = common / "project-skillsets.json"
    self.assertEqual(json.loads(state.read_text()),
                     {"version": 1, "names": ["default", "personal"]})
    self.assertEqual(project.read_names(common), ("default", "personal"))
    for value in (
        {"version": True, "names": ["default"]},
        {"version": 2, "names": ["default"]},
        {"version": 1, "names": []},
        {"version": 1, "names": ["default", "default"]},
        {"version": 1, "names": ["personal", "default"]},
        {"version": 1, "names": ["../default"]},
        {"version": 1, "names": ["default"], "home": "/tmp"},
    ):
        with self.subTest(value=value):
            state.write_text(json.dumps(value))
            before = state.read_bytes()
            with self.assertRaises(OperationalError):
                project.read_names(common)
            self.assertEqual(state.read_bytes(), before)
```

- [x] Run `python3 -m unittest discover -s tests -p test_skillset.py -k registration_round_trip -v`; require a missing-module/interface failure before implementation.
- [x] Implement schema parsing with exact keys/types (`type(version) is int`), a real regular UTF-8 JSON file, name grammar and order checks. Missing file returns `None`; malformed state raises a path/reason diagnostic unchanged. Write via same-directory `tempfile` and `os.replace`; remove staging after ordinary errors, preserve the old file when replacement fails.
- [x] Implement Git discovery using argument arrays and byte-mode NUL inventory parsing. Resolve current root/common directory dynamically. Inspect all sorted non-bare entries including locked/detached worktrees; verify identity with sibling `git -C` calls using a copied environment minus `git rev-parse --local-env-vars`. Do not clear the caller's environment or prune/unlock inventory.
- [x] Add `test_project_state_` cases: JSON root/non-list/string names, invalid UTF-8, symlink/directory state; ordinary replacement error and staging cleanup; version 2.53 refusal/2.54 acceptance/suffixed Git version parsing; non-Git and unavailable optional discovery; subdirectory, detached, linked worktrees, bare-root refusal, non-bare linked worktree of bare common repo, independent clone, submodule identity; paths containing newline/space via NUL parsing; missing worktree and mismatched identity. Assert optional discovery uses no inventory or version-floor requirement, since the unscoped overview must not acquire a Git dependency.
- [x] Pin Review Focus 1 with a test setting `GIT_DIR`/`GIT_WORK_TREE` for the invoking checkout, inspecting a sibling correctly, and asserting the parent `os.environ` stays unchanged. Use the fixture's real Git processes; stub only version/read-error boundaries.
- [x] Run `python3 -m unittest discover -s tests -p test_skillset.py -k test_project_state_ -v`; expect all cases green. Capture a bounded diff for review, then make a local checkpoint commit containing only this task's files using the commit procedure below.

### Task 2: Codex projection at explicit worktree roots

**Files:** Modify `lib/skillset/codex.py`, `tests/test_skillset.py`; add `test_codex_projection_` methods inside existing `SkillsetTests`.

**Consumes:** Existing `expected_target(root, name)`, layout/name validation. This layer does not discover Git, mutate registration or install hooks.

**Interfaces produced:**

| Function | Return/behavior |
| --- | --- |
| `skills_directory_at(worktree: Path, *, create=False)` | Path or None; real `.codex`/`skills` containers only |
| `canonical_link_at(root: Path, name: str, worktree: Path)` | bool; absolute normalized target match even if target is missing |
| `preflight_at(root: Path, names: tuple, worktree: Path, *, removing=False)` | No mutation; enable rejects unrelated entries, removal preserves them |
| `reconcile_at(root: Path, names: tuple, worktree: Path, *, removing=False)` | Tuple of ordinary path-specific errors; continue across names |


- [x] Write the failing characterization of canonical pre-existing removal:

```python
def test_codex_projection_preserves_then_removes_preexisting_canonical_link(self):
    from skillset import codex
    self.make_managed_layout(self.home)
    worktree = self.sandbox / "checkout"
    (worktree / ".codex" / "skills").mkdir(parents=True)
    link = worktree / ".codex" / "skills" / "default"
    target = str(self.root / "skillsets" / "default" / "skills")
    link.symlink_to(target + "/")
    codex.preflight_at(self.root, ("default",), worktree)
    self.assertEqual(codex.reconcile_at(self.root, ("default",), worktree), ())
    self.assertEqual(os.readlink(link), target + "/")
    self.assertEqual(codex.reconcile_at(
        self.root, ("default",), worktree, removing=True), ())
    self.assertFalse(os.path.lexists(link))
    self.assertTrue(link.parent.is_dir())
```

- [x] Run `python3 -m unittest discover -s tests -p test_skillset.py -k projection_preserves -v`; expect missing explicit-root interface.
- [x] Extract the existing real-container/target comparisons into these explicit-root primitives. Keep `codex_skills_directory` and global/local wrappers selecting exactly their previous destinations. Preflight must not create containers. Reconciliation creates missing containers for enable only; removal treats absent/unrelated entries as cleared and never removes containers. Reuse existing `OperationalError` wording for Codex container/entry failures.
- [x] Add cases for relative/different-target links, directory/file entries, symlinked containers, missing containers, normalized absolute target, dangling canonical cleanup, nested local links left alone, ordinary unlink/create error with continuation to another name. Assert source validation belongs to callers: removal does not require the source/layout to exist.
- [x] Run `python3 -m unittest discover -s tests -p test_skillset.py -k test_codex_projection_ -v` and `python3 -m unittest discover -s tests -p test_skillset.py -k test_codex -v`; expect unchanged existing scope tests and new projection tests green. Review and commit this bounded extraction with its tests.

### Task 3: Shared hook config and real invocation boundary

**Files:** Modify `project.py`, `cli.py`, `tests/test_skillset.py`; add `test_project_hook_` methods inside existing `SkillsetTests`.

**Consumes:** `discover`, `read_names`, `preflight_at`/`reconcile_at`.

**Interfaces produced:**

| Function | Return/behavior |
| --- | --- |
| `hook_config_errors(context: GitProject, *, registered: bool, enabling: bool)` | Tuple of config/disabled-state errors across all worktrees |
| `install_hook(context: GitProject)` | Write local command then event; preflight belongs to caller |
| `remove_hook(context: GitProject)` | Remove event then command; absent owned keys accepted |
| `run_hook(root: Path, old: str, new: str, flag: str)` | Tuple of reconciliation errors; never change registration/config |


- [x] Add a failing executable test of hidden-command validation, using `self.run_cli("_project-hook", "old", "new", "invalid")`; assert return 1 and an unchanged temporary home. Assert root and Codex `--help` output omit `_project-hook` (including argparse's generated choice list). Keep malformed-argument coverage separate from valid flag-0 no-op and missing-registration quiet no-op.

```python
def test_project_hook_invalid_flag_is_noncreating_and_hidden(self):
    before = self.filesystem_snapshot(self.home)
    result = self.run_cli("_project-hook", "old", "new", "invalid",
                          extra_environment=self.git_environment())
    self.assertEqual(result.returncode, 1)
    self.assertEqual(self.filesystem_snapshot(self.home), before)
    for args in (("--help",), ("codex", "--help")):
        help_result = self.run_cli(*args)
        self.assertEqual(help_result.returncode, 0)
        self.assertNotIn("_project-hook", help_result.stdout)
```
- [x] Run `python3 -m unittest discover -s tests -p test_skillset.py -k test_project_hook_ -v`; expect failures from the missing hidden command/config behavior.
- [x] Build this fixed single-line command in `project.py`, with no embedded paths or harness selector:

```python
HOOK_COMMAND = (
    'skillset_project_hook() { '
    'if skillset _project-hook "$@"; then :; else '
    "printf '%s\\n' 'skillset: project hook failed; rerun project enable or inspect project list' >&2; "
    'fi; return 0; }; skillset_project_hook'
)
```

- [x] Inspect config using origin/scope-aware Git output rather than rewriting files. Without valid registration, every reserved-subsection occurrence conflicts. With registration, only one matching owned command and one matching event may exist in local common config; missing keys are recovery state. Unknown keys, duplicates, inherited/worktree settings and changed values conflict. Inspect `git hook list --show-scope post-checkout` and supported named/event enabled controls; diagnose disabled effective hook state for enable/list, but let disable remove owned keys without touching disabling controls. Use Git 2.54 documentation as the minimum; installed 2.56 event-wide controls cannot become a minimum-version dependency.
- [x] Add the hidden top-level parser/dispatch route with three positional arguments and no scope/name flags. Suppress it from all user-facing help and completions. Route it under `stable_home_lock` plus `discovery_operation_lock`, not creating `operation_lock`; dispatch imports remain lazy. `run_hook` validates flag 0/1, returns immediately on 0, reads current clone state afresh, validates each source independently, projects valid names in the invoking worktree only and accumulates failures.
- [x] Add real-process invocation evidence without waiting for public enable: use `discover`/`write_names`/`install_hook` to register the disposable clone, then `git worktree add` with the fixture environment. Assert the new root link before Git returns and unchanged registration bytes. Record old/new/flag with a test executable named `skillset` placed earlier in `PATH`; assert the three appended arguments arrive intact and the inherited temporary `HOME` matches. A second earlier executable must win standard PATH precedence.
- [x] Cover missing executable with an isolated hook environment where Git can run but `skillset` cannot be found; assert checkout succeeds and stderr has the wrapper warning. Use paths with spaces, apostrophes, dollar signs and semicolons; assert no shell expansion artifacts. Test missing source plus another valid source (Review Focus 4), registration malformed, collision, file checkout no-op and another failing named hook retaining its exit status. Skip native invocation tests with a clear reason when installed Git is below 2.54; state/schema/parser tests must still run.
- [x] For Review Focus 5, add config matrices for missing keys, duplicate command/event, extra reserved key, changed command, inherited subsection, worktree-specific subsection, named disable, and supported event-wide disable. Verify refusal leaves exact config bytes/values unchanged. Actual file self-removal/restoration integration is Task 6.
- [x] Run `python3 -m unittest discover -s tests -p test_skillset.py -k test_project_hook_ -v`; expect green and no mutations outside the sandbox. Review and commit this hook boundary with its tests.

### Task 4: Explicit project enable/disable and repeat-command recovery

**Files:** Modify `project.py`, `codex.py`, `cli.py`, `tests/test_skillset.py`; add `test_codex_project_operation_` methods inside existing `SkillsetTests`.

**Consumes:** Tasks 1–3 interfaces, `validate_layout` and `validate_set`.

**Interfaces produced:**

| Function | Return/behavior |
| --- | --- |
| `enable(root: Path, name: str, cwd: Path)` | Tuple of ordinary errors after intent/changes remain |
| `disable(root: Path, name: str, cwd: Path)` | Tuple of ordinary errors; remove registration last; absent name raises OperationalError |


Validation failures raise existing `OperationalError`. Operations return tuples of detailed messages only when continuing after ordinary per-worktree errors. The CLI prints each through `format_command_error` and returns 1; success is silent 0. KeyboardInterrupt propagates to the existing explicit-command exit-130 handler.

- [x] Add the failing public lifecycle test:

```python
def test_codex_project_operation_enable_from_subdirectory_and_disable_matching_links(self):
    self.make_managed_layout(self.home)
    repo = self.new_repository()
    sibling = self.sandbox / "linked"
    self.git(repo, "worktree", "add", "--detach", str(sibling))
    subdir = repo / "src"
    subdir.mkdir()
    local = self.run_cli_in_process("codex", "enable", "default", "--local", cwd=repo)
    self.assertEqual(local.returncode, 0, local.stderr)
    enabled = self.run_cli_in_process("codex", "enable", "default", "--project", cwd=subdir)
    self.assertEqual(enabled.returncode, 0, enabled.stderr)
    self.assertEqual(enabled.stdout, "")
    for checkout in (repo, sibling):
        self.assertTrue((checkout / ".codex/skills/default").is_symlink())
    self.assertFalse((subdir / ".codex").exists())
    disabled = self.run_cli_in_process("codex", "disable", "default", "--project", cwd=sibling)
    self.assertEqual(disabled.returncode, 0, disabled.stderr)
    for checkout in (repo, sibling):
        self.assertFalse(os.path.lexists(checkout / ".codex/skills/default"))
    common = Path(self.git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
    self.assertFalse((common / "project-skillsets.json").exists())
```

- [x] Run `python3 -m unittest discover -s tests -p test_skillset.py -k project_operation_enable_from_subdirectory -v`; expect argparse's unsupported-option failure before implementation.
- [x] Add `project_help=None` to `add_scope_options`; append `--project` to the same mutually exclusive group only when supplied by Codex parser callers. Keep all other groups/defaults intact. Route `codex_scope == "project"` before Codex global/local source/layout assumptions. All project operations use the non-creating discovery-lock path; invalid Git/source/config cannot create `.agents` or its lock. Propagate `dispatch_locked_command` status through `run_managed_command` while retaining 0 for existing `None` dispatch results. Print accumulated project failures individually and safely on stderr.
- [x] Implement enable exactly in specification order: validate Git/layout/source/state/config; build sorted desired union; preflight all desired sources and all destinations; write registration; command key; event key; all-worktree projection with ordinary failures accumulated. Repeat enable repairs missing owned keys and links, retaining external conflicts as refusals.

The central ordering after validation uses the earlier interfaces directly:

```python
desired = tuple(sorted(set(read_names(context.common_dir) or ()) | {name}))
for desired_name in desired:
    validate_set(root, desired_name)
for worktree in context.worktrees:
    codex.preflight_at(root, desired, worktree)
write_names(context.common_dir, desired)
install_hook(context)
errors = []
for worktree in context.worktrees:
    errors.extend(codex.reconcile_at(root, desired, worktree))
return tuple(errors)
```

Here `context` is the validated `discover(cwd)` result, and `root`/`name` are the operation arguments. This fragment belongs inside `project.enable`; import the Codex reconciler locally to avoid module-import cycles with its public bridge.
- [x] Implement disable without source/layout validity requirements: validate registered name/inventory/containers/ownership; last name removes event then command first; unlink canonical entries across roots; only after every cleanup succeeds remove name/file. Unrelated destination entries are cleared for removal purposes and retained physically. Missing requested name returns 1 without deleting arbitrary links.
- [x] Pin Review Focus 2 with a collision only in the last sorted worktree, asserting no new registration, config, earlier link or container; repeat with an existing registration and a newly requested name to assert old registration bytes remain. Add multiple names, repeated enable repair, outside Git/missing managed root, missing worktree, foreign common-dir inventory, bare-linked repo, independent clone, exact-directory nested local links and scope-conflict snapshots.
- [x] Pin Review Focus 3 using ordinary `unittest.mock.patch` failures at registration replacement, hook config command, link creation/unlink and final registration removal. No syscall/timing matrix. Last-name unlink failure retains registration with keys absent; repeat disable finishes; repeat enable reinstalls keys/links. With another name active, failed disable keeps the hook; a real later checkout recreates the name before successful retry. Verify continuation reports every failed path and does not remove another name.
- [x] Add a real interrupt boundary: patch a deterministic operation point to raise `KeyboardInterrupt` in-process to prove state ordering/130, plus a disposable subprocess that signals SIGINT after observed registration creation; confirm retained registration is recoverable. Keep signal tests bounded with explicit timeouts and cleanup.
- [x] Run `python3 -m unittest discover -s tests -p test_skillset.py -k test_codex_project_operation_ -v` and the existing `-k test_codex` coverage; expect green. Review and commit project operations/CLI bridges with their tests.

### Task 5: Ordered listing, invalid sources and native completions

**Files:** Modify `project.py`, `codex.py`, `metadata.py`, `completions.py`, `tests/test_skillset.py`; add `test_codex_project_inspection_` methods inside existing `SkillsetTests` and extend existing completion probes.

**Interfaces produced:**

```python
@dataclass(frozen=True)
class SourceView:
    name: str
    manual: bool
    entries: tuple  # existing skill-entry triples for healthy sources
    error: object  # None or detailed source-validation string

@dataclass(frozen=True)
class ProjectInspection:
    sources: tuple  # SourceView values in registration order
    errors: tuple  # printable diagnostics, without the skillset: prefix

```

`inspect(root: Path, cwd: Path, *, full=False) -> ProjectInspection` returns optional registration/source overview when `full=False`; `full=True` requires project discovery and checks sources, effective hook and all projections.

Keep optional project overview separate from full inventory. Extend rendering narrowly so supplied `SourceView` values can bypass layout/source assumptions for invalid registered sources; retain existing row shape and rendering conventions for other callers. Project-scoped list renders first and reports every health error after stdout; the CLI returns 1 if errors exist. Metadata annotations such as missing descriptions retain their existing meaning and do not alone cause project health failure.

- [x] Add the failing row-order test:

```python
def test_codex_project_inspection_combined_listing_orders_global_project_local_and_keeps_registration(self):
    self.make_managed_layout(self.home)
    repo = self.new_repository()
    self.assertEqual(self.run_cli_in_process("codex", "enable", "default").returncode, 0)
    self.assertEqual(self.run_cli_in_process("codex", "enable", "default", "--project", cwd=repo).returncode, 0)
    listed = self.run_cli_in_process("codex", "list", cwd=repo)
    self.assertEqual(listed.stdout, "[g] default\n[p] default\n[l] default\n")
    self.assertEqual(self.run_cli_in_process("codex", "disable", "default", "--local", cwd=repo).returncode, 0)
    overview = self.run_cli_in_process("codex", "list", cwd=repo)
    self.assertEqual(overview.stdout, "[g] default\n[p] default\n")
    self.assertEqual(overview.returncode, 0, overview.stderr)
    checked = self.run_cli_in_process("codex", "list", "--project", cwd=repo)
    self.assertEqual(checked.stdout, "default\n")
    self.assertEqual(checked.returncode, 1)
    self.assertIn("project link is missing", checked.stderr)
```

- [x] Run `python3 -m unittest discover -s tests -p test_skillset.py -k combined_listing_orders -v`; require a missing `[p]` row or missing inspection interface failure.
- [x] Implement optional overview with `discover(..., required=False, inventory=False)`; print global/project/local groups without deduplicating between scopes. Outside Git, bare-root cwd or missing Git omit project rows. Malformed/unreadable registration reports 1 while available global/local rows still render. Explicit global/local listing does not invoke Git. Preserve existing global/local layout refusal and error status in unscoped listing, while rendering available project SourceViews even when layout validation fails. This supersedes the original abort-before-render interpretation, which hid invalid registered sources contrary to the binding specification. Project-only inspection uses non-creating discovery and can render missing inactive sources without a healthy layout.
- [x] Implement full inspection with required Git discovery, registration rendering, source validity, effective hook ownership/enabled status and every root destination. Missing/orphan state follows the specification. Never repair or create state; snapshot filesystem/config before and after list. Use safe path escaping and preserve sorted names despite invalid sources.
- [x] Add cases for manual sources, missing metadata/source/skills directory, dangling canonical links, root unavailable, real directory collision, hook incomplete/disabled/conflicting, no registration/no config, orphan reserved config, malformed file, `[p]` from subdirectory without `[l]`, duplicate rows across all scopes, lexical name order and independent clone. A source removed after registration remains named in brief/verbose output and can still be disabled (Review Focus 4). Healthy inventory annotations must not become project errors. TTY rendering must retain `[g]`/`[l]` colors, readable textual `[p]`, no active marker, and terminal-width behavior.
- [x] Extend Bash's shared command branch to offer `--project` only when `subcommand == codex`; treat it as a no-value scope flag and suppress all scope alternatives once any scope is present. Update Codex Zsh exclusion groups to include `--project`. Add Codex-only Fish conditions suppressing all other scopes once one is selected, preserving name positions, partial flags and `--` termination.
- [x] Extend existing Bash/Fish/Zsh native probes for Codex enable/disable/list, selected `--project`/global/local mutual exclusion, flags before/after names, and no `_project-hook` completion. Confirm Claude/Augment contexts never suggest `--project`. Parser help must include only public Codex project scope.
- [x] Run `python3 -m unittest discover -s tests -p test_skillset.py -k test_codex_project_inspection_ -v`, then `-k completion -v` and `-k test_codex -v` with the same discover invocation. Require available native shell syntax/behavior checks green, record genuinely unavailable shell skips. Review and commit ordered listing/completions with their tests.

### Task 6: Compatibility acceptance and operator documentation

**Files:** Modify `tests/test_skillset.py`, `README.md`, compatibility research and workstream handoff. Add `test_project_compatibility_` methods inside existing `SkillsetTests`.

**Consumes:** All public project commands, shared hook and inspection contracts. No new product API or move/remove handlers are introduced.

- [x] Add a failing compatibility test for ordinary `worktree add`, then `--no-checkout` followed by later checkout: ordinary creation has links before Git returns; bare no-checkout creation has none; later checkout creates them. Repeat project enable also repairs the no-checkout worktree. Verify both cases against actual Git processes, not direct dispatcher calls.

```python
def test_project_compatibility_checkout_and_no_checkout_creation(self):
    self.make_managed_layout(self.home)
    repo = self.new_repository()
    enabled = self.run_cli("codex", "enable", "default", "--project", cwd=repo,
                           extra_environment=self.git_environment())
    self.assertEqual(enabled.returncode, 0, enabled.stderr)
    ordinary = self.sandbox / "ordinary"
    self.git(repo, "worktree", "add", "--detach", str(ordinary))
    self.assertTrue((ordinary / ".codex/skills/default").is_symlink())
    prepared = self.sandbox / "prepared"
    self.git(repo, "worktree", "add", "--detach", "--no-checkout", str(prepared))
    self.assertFalse(os.path.lexists(prepared / ".codex/skills/default"))
    self.git(prepared, "checkout", "--detach", "HEAD")
    self.assertTrue((prepared / ".codex/skills/default").is_symlink())
```
- [x] Run `python3 -m unittest discover -s tests -p test_skillset.py -k test_project_compatibility_ -v`; new compatibility assertions must fail before any required fixes. If behavior already passes from Tasks 1–5, retain this as additional acceptance evidence without changing working production code merely to manufacture a red test.
- [x] Exercise locked/detached worktrees, linked worktree of a bare clone, submodule independence, manual moved/missing inventory refusal and no implicit prune/unlock. Use real `git worktree move`/`remove` and clone-directory relocation to prove dynamic discovery and absence of embedded paths. These operations need compatibility tests, not product handlers. Worktree removal may require the test to delete its generated untracked links or deliberately pass `--force` on disposable resources; do not infer production cleanup logic from fixture cleanup.
- [x] Verify traditional hook plus separate `core.hooksPath`: log arguments/invocation in a disposable hook, install shared hook, create a worktree and compare existing hook/config bytes. Reproduce the inspected GitButler-managed post-checkout restoration/removal lifecycle in a disposable clone using its observed marker/chaining behavior; prove named hook still works after the traditional file changes. Repeat with a second named hook failing to preserve Git's result (Review Focus 5).
- [x] Include Review Focus 1 in a real hook run with Git-exported location variables; assert only invoking root reconciles and independent clone remains unchanged. Compare snapshots of source lock/metadata, active aliases and ignore files before/after project operations. Prove no lifecycle blockers/global index were added: after removal of a registered inactive collection, list diagnoses it and disable cleans links without repairing registration implicitly.
- [x] Add README content under Codex scope documentation, using these exact examples:

```sh
skillset codex enable obra --project
skillset codex list
skillset codex list --project --verbose
skillset codex disable obra --project
git rev-parse --git-path info/exclude
```

Explain global/project/local ordering, duplicate local/project rows, exact-directory local scope, pre-existing canonical-link removal (including tracked canonical links), local disable recreation, no-checkout, Git 2.54/Python/PATH/HOME requirements, warning-only hook failure and repeat-command recovery. Describe `project-skillsets.json`/shared keys as machine-local clone metadata and generated links as uncommitted runtime. Offer narrow operator-owned `/.codex/skills/obra` exclusion; no automatic ignore edits. Explain disable-before-rename/remove in every known clone and inaccessible-worktree repair through Git. Do not document `_project-hook` as a user command or imply other harnesses now support project scope.
- [x] Run focused compatibility, project operation/inspection/hook/state/projection and native-shell checks, then the required full suite:

```sh
python3 -m unittest discover -s tests -v
rg -n 'Task [0-9]|milestone|phase [0-9]|bead|ticket|codex-project-enablement' lib/skillset bin README.md tests/test_skillset.py
```

The terminology search is a review aid: existing unrelated matches are not instructions to rewrite them. Remove planning labels introduced by this feature. Require full-suite success; investigate failures under systematic-debugging without broadening scope to unrelated cleanup.
- [x] Run an installed-Orca native-hook acceptance probe only in a disposable clone/worktree, following the existing [compatibility research](../research/codex-worktree-hook-compatibility.md) reproduction and orca-cli skill. Existing evidence proves traditional-hook triggering with setup skipped, not this native-hook implementation. Confirm ordinary Orca creation with setup skipped creates links before completion and record tool/Git versions. Remove only created probe resources through their owning tools. If the runtime cannot be exercised, record it as an unmet acceptance check rather than claiming complete compatibility. Sparse/prepared paths, SSH and WSL remain explicitly unverified unless separately exercised within agreed scope.
- [x] Record focused/full test commands, native-hook/Orca results and genuine skips/limits in research/handoff; preserve accepted source decisions. Review the feature's current-session changes and their interactions, not the entire pre-existing branch. Use distinct implementer/verifier agents under the delegation policy after approval; no reviewer that authored the implementation counts as independent verification.
- [x] Review and commit the acceptance tests/docs as a local checkpoint. Do not push, merge, install live project hooks or retire the handoff without the relevant operator authorization.

## Checkpoint commits and reviews

Before each local checkpoint, run `but diff` and inspect the exact files/hunks for that task. Select their fresh IDs, including only intended feature changes; leave Beads recovery state and unrelated changes alone. Use `but commit -b codex-project-enablement` with a concise task-specific message and the selected IDs. Do not copy IDs from this plan or stage everything implicitly. If the branch does not exist, `but commit -b` creates it. Preserve the current workspace's stack relationships; do not rewrite pushed history or use raw Git workspace mutations.

Suggested chronological messages: `feat: add shared project registration`, `refactor: reconcile Codex links at explicit roots`, `feat: install shared checkout hook`, `feat: enable Codex skillsets across worktrees`, `feat: inspect project skillsets in scope order`, `docs: explain project skillset recovery`.

## Specification coverage and approval gate

| Design contract | Implementation/test owner |
| --- | --- |
| Git identity, version floor, schema, ordinary writes, no path cache | Task 1 |
| Ordinary canonical links, pre-existing removal, containers, unrelated/nested preservation | Task 2 |
| Shared native keys, top-level dispatcher, environment lookup, conflicts, warning-only failures | Task 3 |
| CLI scopes/locks, all-worktree preflight, union registration, partial enable/disable and interrupt recovery | Task 4 |
| `[g]`/`[p]`/`[l]` order, invalid names visible, full read-only health, completions | Task 5 |
| Traditional-hook lifecycle, no-checkout, move/remove/relocation, lifecycle/ignore constraints, Orca and full-suite evidence | Task 6 |

No product tests or implementation have been performed by preparing this plan. Planning verification is source/interface review, executable test-snippet syntax checks, artifact link checks and design coverage mapping.

The operator approved this plan. Follow the repository's clean-session boundary once; default to delegated task execution on resumption unless the operator chooses inline execution. The clean-session boundary and execution have occurred. Continue from operator disposition of the remaining acceptance gap; do not restart Task 1 or request another clean-session boundary. No full-branch review, publication or live installation is authorized by this plan.

## Execution evidence and remaining gate

All six tasks were executed after resumption with separate implementer and verifier agents. Task 5 review found relative Git-cwd and dropped-row defects; its first fix round passed scoped re-review. Final feature review found first-enable event-wide disable preflight, ordinary destination-inspection failure recovery, and unscoped invalid-source visibility defects. A combined fix wave at `71b0587` added regressions; 123 focused tests and the full 331-test suite passed with no skips. Scoped re-review addressed all three product findings. A residual event-control test guard was corrected at `5254e50`: the runtime assertion requires Git 2.55, while the separate 2.54/2.55 boundary test remains. A simulated 2.54 probe skips before fixture mutation and all four installed-2.56 first-enable tests pass. Direct verifier confirmation passed; no review findings remain.

The [compatibility research](../research/codex-worktree-hook-compatibility.md) owns exact commands and probe limits. Installed Orca 1.4.224 native-trigger/dispatcher/projection acceptance passed with an explicit temporary HOME/PATH fixture adapter and setup skipped. Unmodified service HOME/PATH acceptance remains unmet; Git 2.54 runtime, sparse/prepared Orca, SSH and WSL remain unverified. Local implementation and design documentation remain on independent GitButler branches. No publication, merge or live installation occurred or is authorized.
