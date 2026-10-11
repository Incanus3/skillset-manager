# Codex worktree hook compatibility

Evidence recorded 2026-10-11 on Linux: prior Orca 1.4.223 traditional-hook
probe, real Git 2.56.0 acceptance tests, and Orca 1.4.224 native-hook probe
with an explicitly isolated fixture environment.

## Orca checkout trigger

A disposable traditional-hook probe on Orca 1.4.223 showed that ordinary
worktree creation with `--setup skip` runs `post-checkout` at the final
worktree root. The hook created a canonical Codex link before creation
returned, without an Orca setup script. This established the trigger; the
native-hook probe below exercised the implemented dispatcher separately.

## Source inspection

The separately checked-out Orca source corroborates the mechanism:

- `src/main/git/worktree-add.ts`: ordinary creation executes `git worktree add`.
- `src/main/git/worktree-sparse-add.ts`: creation starts with `--no-checkout`
  but finishes with `git checkout <branch>`.
- `src/main/git/worktree-create-preparation.ts`: preparation uses reset without
  checkout hooks; finalization moves the checkout to its final path and executes
  `git checkout --no-track -b <branch> <commit>`.

These paths were inspected in `/home/jakub/orca/projects/orca`; that source
checkout was not established as identical to the installed runtime. Sparse and
prepared paths were not separately exercised through the runtime probe.

Git documents hook execution after checkout/switch and worktree add, with an
exception for `worktree add --no-checkout`:
https://git-scm.com/docs/githooks#_post_checkout

## Native config-based hooks offer a coexistence path

Git's [2.54 release notes](https://github.com/git/git/blob/v2.54.0/Documentation/RelNotes/2.54.0.adoc)
establish that config-defined hook commands and multiple commands per event
were introduced in that version. The [hook manual](https://git-scm.com/docs/git-hook)
documents `hook.<name>.command` and `hook.<name>.event`; configured hooks run
before the traditional hook from the hook directory. This offers a way to add
clone-local `post-checkout` reconciliation without replacing a hook file or
changing `core.hooksPath`.

Project scope requires Git 2.54+. Older Git would need a separate integration
mechanism. Runtime verification used Git 2.56.0; an actual Git 2.54 binary
was not exercised.

## Git discovery and effective config

Real Git submodule discovery exposed a compatibility detail:
`git worktree list --porcelain -z` can report the primary entry as
`<parent>/.git/modules/<module>`, while `git rev-parse --show-toplevel`
reports the actual submodule checkout. Discovery resolves only an inventory
entry equal to the common directory through Git's own `--show-toplevel`, then
checks the resulting checkout's root and common-directory identity normally.
Real tests cover invocation from both the main submodule and its linked worktree.
Ordinary missing worktrees still produce errors without automatic maintenance.

Git's reported local environment variables include `GIT_CONFIG_COUNT` and
`GIT_CONFIG_PARAMETERS`. Config inspection keeps the invoking checkout's inherited
environment and clears these variables only in sibling-inspection children;
otherwise a command-scope disabling control can disappear from inspection.

The [tagged Git 2.54 config reference](https://raw.githubusercontent.com/git/git/v2.54.0/Documentation/config/hook.adoc)
defines named `enabled` controls. The
[tagged Git 2.55 reference](https://raw.githubusercontent.com/git/git/v2.55.0/Documentation/config/hook.adoc)
adds event-wide controls; inspection gates those controls on Git 2.55 or newer.
Actual execution on a Git 2.54 binary remains unverified; the minimum-version
contract has source evidence and version-boundary tests.

### Existing GitButler hook ownership

Read-only inspection on 2026-10-11 in `skillset-manager` found no configured
`core.hooksPath` and an executable `.git/hooks/post-checkout` marked
`GITBUTLER_MANAGED_HOOK_V1`. It invokes an executable `post-checkout-user`
when present. When leaving `gitbutler/workspace`, it can restore that user
hook over itself or remove itself. This is observed local hook source behavior,
not a runtime test of hook coexistence.

Design implication: preserving only an existing hook's invocation is
insufficient if that hook also manages the hook file. Any wrapper or chaining
proposal would have to explain its behavior with this lifecycle. The accepted
native named-hook direction avoids owning that file. The disposable lifecycle
reproduction below verifies coexistence without operating GitButler itself.
The [approved specification](../specs/2026-10-11-codex-project-enablement-design.md)
owns the current integration contract. Inspection did not modify hooks or Git config.

## Public-command compatibility acceptance

Nine `test_project_compatibility_` tests exercise actual Git processes and
public project commands using isolated temporary homes.

- Ordinary worktree creation links before Git returns. `--no-checkout` leaves
  no link; later checkout and repeat project enable each reconcile it.
- Locked/detached worktrees and non-bare worktrees of a bare clone participate;
  the lock reason is unchanged and the bare root is excluded.
- Submodule registration and its future linked worktree remain independent
  of both parent repository and source clone.
- Actual `git worktree move` and `remove --force` use current inventory.
  Relocating a clone with no remaining linked worktrees preserves registration
  and creates links in its next worktree; the hook contains no cached paths.
- Manual moves and missing locked worktrees refuse enable/disable without
  changing inventory, locks, config or registration. Operator `worktree repair`
  recovers the manual-move case without implicit unlocking.
- Traditional hook bytes, arguments, invocation and `core.hooksPath` survive
  enable/add/disable. The traditional hook observes the link already present.
- A disposable shell fixture reproduces the inspected GitButler managed marker,
  branch detection, `post-checkout-user` chaining, restoration and self-removal.
  The named hook continues after either lifecycle transition, and a second
  named hook's exit 7 remains Git's result. This reproduces observed file
  behavior; it does not run a GitButler application lifecycle.
- A real checkout with explicit Git location options exports `GIT_DIR` and
  `GIT_WORK_TREE=.` to hooks. Only the invoking linked root is repaired; the
  primary checkout and independent clone remain unchanged. Runtime snapshots
  preserve source metadata/lock, active aliases, existing advisory lock and
  unrelated metadata. Repository/global ignore bytes remain unchanged.
- Removing a registered inactive collection through ordinary lifecycle commands
  remains allowed; project list diagnoses the unchanged registration and
  project disable clears canonical dangling links. A tracked pre-existing
  canonical local link is also removed on project disable, as specified.

Ordinary worktree add does not export `GIT_DIR` on Git 2.56; explicit Git
location options do, and Git normalizes the worktree to `.` before invoking
hooks. Tests must use that real environment rather than assuming an absolute
worktree spelling.

## Installed Orca native-hook probe with isolated environment

The installed app was already running at version **1.4.224**. The selected CLI
was `/home/jakub/.config/orca/linux-orca-cli-shim/orca`; its version-matched
`orca-cli` guide and command help were read. Git reported **2.56.0** and Python
reported **3.14.8**. Repo add, setup update and worktree create expose no HOME
or environment override; the service inherits the operator's real home.
Running the unmodified product command there would access live `~/.agents`,
which this acceptance work explicitly excludes.

A disposable fixture under `/tmp/skillset-orca-native-j35v2b2j` contained an
isolated managed home, empty healthy `obra` collection and repository on `main`.
Public `codex enable obra --project` ran with that temporary HOME and configured
the actual product registration and hook. Only the disposable command value
was then adapted to supply the temporary environment to an inner shell. The
exact recorded command was:

```sh
skillset_probe() { printf '%s\n' "$PWD" > /tmp/skillset-orca-native-j35v2b2j/native-trigger; env HOME=/tmp/skillset-orca-native-j35v2b2j/home PATH=/home/jakub/orca/projects/skillset-manager/bin:/usr/bin:/bin GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null sh -c 'skillset_project_hook() { if skillset _project-hook "$@"; then :; else printf '"'"'%s\n'"'"' '"'"'skillset: project hook failed; rerun project enable or inspect project list'"'"' >&2; fi; return 0; }; skillset_project_hook "$@"' -- "$@"; }; skillset_probe
```

The inner shell executes the unchanged generated hook command with forwarded
arguments appended, as Git normally appends them. Omitting that append causes
argument parsing to fail. This is fixture-only config, not a product launcher
or installation recommendation.

Commands used (each `orca` below means the selected absolute CLI above):

```sh
orca repo add --path /tmp/skillset-orca-native-j35v2b2j/repo --json
orca project setup-update --setup f7fe574b-2203-4c82-909f-ce139f59ffed --worktree-base-path /tmp/skillset-orca-native-j35v2b2j/worktrees --json
orca worktree create --repo id:f7fe574b-2203-4c82-909f-ce139f59ffed --name skillset-native-hook-probe-fixed --base-branch main --no-parent --setup skip --json
```

Create returned exit 0, `ok: true`, `warnings: []`. Before any subsequent
skillset operation, the trigger log contained the returned final worktree root
`/tmp/skillset-orca-native-j35v2b2j/worktrees/repo/skillset-native-hook-probe-fixed`,
and `.codex/skills/obra` was an absolute symlink to
`/tmp/skillset-orca-native-j35v2b2j/home/.agents/skillsets/obra/skills`.
No traditional `post-checkout` file or Orca setup script existed. Restoring the
exact owned command, then running `codex list --project --verbose` under the
temporary environment returned exit 0, an `obra | (no skills)` row and empty
stderr.

Cleanup used `orca worktree rm --worktree id:<returned-full-id> --force --json`
for each created probe worktree and
`orca project setup-delete --setup f7fe574b-2203-4c82-909f-ce139f59ffed --json`.
Read-only repo/setup lists confirmed those records absent; Git inventory
contained only the main checkout and both worktree paths were absent before
the disposable filesystem was removed. No live hook/config/runtime or app
restart was involved.

**Evidence boundary:** ordinary installed-Orca creation with setup skipped
triggers a native named hook and the real dispatcher creates links under an
isolated fixture environment before creation completes. The **unmodified Orca
service HOME/PATH variant remains an unmet acceptance check**. The adapter
does not establish that environment's dependency availability or home targets.
Sparse/prepared Orca paths, SSH, WSL and an actual Git 2.54 binary remain
unverified; the latter retains primary-source and version-boundary evidence.

## Reliability findings

Regression coverage protects three ordinary serial failure cases:

- Effective event-wide hook disable controls must be checked before first
  enable, even when no project registration exists.
- Ordinary container or link inspection errors must remain errors rather than
  being treated as absence; disable retains registration for retry.
- Unscoped list must retain invalid registered project rows when global/local
  layout validation fails. Global/local rendering still refuses that layout
  and returns an error; project rows provide partial read-only evidence.

These findings clarify the implementation of the
[listing and recovery contracts](../specs/2026-10-11-codex-project-enablement-design.md).

## Verification baseline

Commands ran on Linux with Git 2.56.0 on 2026-10-11.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p test_skillset.py -k test_project_compatibility_ -v` | 9 real-Git compatibility tests passed |
| `python3 -m unittest discover -s tests -p test_skillset.py -k completion -v` | 13 tests passed; native Bash/Fish/Zsh behavior and syntax checked |
| `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v -k codex -k project -k completion` | 123 focused tests passed |
| `uv run --no-project --python <version> python -m unittest discover -s tests` | 331 tests passed without skips on each of Python 3.11, 3.12, 3.13 and 3.14 |

Event-wide runtime tests require Git 2.55; separate version-boundary tests
cover the Git 2.54/2.55 distinction. A simulated Git 2.54 run skipped event-wide
runtime coverage before fixture mutation. This does not replace execution
against an actual Git 2.54 binary.

## Python filesystem mock portability

[CI run 38157910213](https://github.com/Incanus3/skillset-manager/actions/runs/38157910213)
failed the four subcases of
`test_codex_project_operation_container_inspection_failure_is_not_absence`
on Python 3.11, 3.12 and 3.13. The expected inspection error was never injected:
those interpreters implement `Path.lstat()` through
`os.stat(..., follow_symlinks=False)`, while local Python 3.14 delegates to
`os.lstat()`. This was confirmed by inspecting the installed interpreter
implementations and reproducing all four failures locally on Python 3.13.

The test now patches `Path.lstat()` with autospec, preserving real filesystem
inspection for other paths. Its exit-status, diagnostic, unchanged-state and
retry assertions remain intact. Production code is unchanged. The focused
Python 3.13 run passes after the correction.

[CI run 38158339548](https://github.com/Incanus3/skillset-manager/actions/runs/38158339548)
passed the Python 3.11–3.13 matrix after this test-only correction.

## Evidence limits at closure

The operator closed the workstream on 2026-10-11. Unmodified Orca service
HOME/PATH, Git 2.54 runtime, sparse/prepared Orca, SSH and WSL coverage remain
unverified. Closure adds no runtime evidence.

## Review corrections (2026-10-11)

Project inspection now reports stale or inaccessible inventory entries only
when the clone has registration. An unregistered clone returns an empty,
successful project listing despite a stale worktree; accessible worktrees
still participate in orphan-hook detection. A regression test covers plain
and verbose listing, read-only preservation and orphan configuration refusal.
It failed before the correction and passed afterward. Registered-clone health
and existing empty/orphan-state tests also passed.

Tests requiring project success now use the existing Git 2.54 version guard.
Version-refusal, schema, optional-discovery and argument-validation coverage
remain runnable on older Git. The optional-discovery test supplies a supported
version for its non-worktree refusal assertion so the version check cannot
mask the behavior it tests.

An executable Git shim reporting 2.53.0, while delegating other operations to
installed Git 2.56.0, ran `python3 -m unittest discover -s tests -k project -q`:
103 tests selected, 72 skipped, no failures. This verifies version gating;
it does not establish runtime compatibility with an actual older Git binary.

The complete suite passed all 332 tests on Python 3.14.8 / Git 2.56.0 using
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q`.
The two final test-only adjustments also passed in a focused run. No new
Git 2.54 runtime or unmodified Orca service evidence was added.
