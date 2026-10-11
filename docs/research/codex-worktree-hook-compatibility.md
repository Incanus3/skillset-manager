# Codex worktree hook compatibility

Evidence recorded 2026-10-11 on Linux: prior Orca 1.4.223 traditional-hook
probe, real Git 2.56.0 acceptance tests, and Orca 1.4.224 native-hook probe
with an explicitly isolated fixture environment.

## Prior trigger probe

A clone-local Git `post-checkout` hook runs during ordinary worktree creation
through Orca, even when Orca setup scripts are explicitly skipped. The hook
can create canonical `.codex/skills/<name>` links before worktree creation returns.
This verifies the proposed trigger, not a completed shared-registration implementation.

## Reproduction and evidence

1. Create an isolated repository with branch `main` and an empty initial commit.
2. Install an executable `.git/hooks/post-checkout` that records `$PWD` in the
   shared Git directory and creates `.codex/skills/obra` pointing to
   `/home/jakub/.agents/skillsets/obra/skills`.
3. Register the disposable repository with `orca-ide repo add --path <repo> --json`.
4. Run `orca-ide worktree create --repo id:<repo-id> --name skillset-hook-probe
   --base-branch main --no-parent --setup skip --json`.
5. Inspect the hook log and link, then run `skillset codex list --local`
   from the new worktree.

The hook log contained the final worktree path; the link had the expected
absolute target; the local listing returned `obra`. Worktree creation returned
success with no warnings. The hook itself performed the link operation; no
Orca setup script or `skillset enable` call was involved.

Cleanup removed the probe worktree through Orca, removed its registered project
host setup, verified the worktree path was absent and only the main checkout
remained registered in Git, then deleted the disposable repository.

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

On 2026-10-11, `git --version` in this workspace reported 2.56.0.
`git hook list --show-scope post-checkout` reported `hook from hookdir`, and
`git config --show-origin --get-regexp '^hook\.'` found no named hook settings.
These are read-only inventory results, not a runtime coexistence test. The
operator accepted requiring Git 2.54+ for project scope and using native
config-based hooks on 2026-10-11. Older Git support would need a separate
integration mechanism and is outside the accepted direction.

## Implementation findings

### Implementation evidence after resumption

The first three implementation tasks are locally committed and independently
reviewed through `bf35f40`. Focused verification passed 14 registration/discovery
tests, 6 projection tests, and 22 hook tests; a combined project/Codex/help/import
run passed 53 tests. Native invocation used disposable repositories and temporary
homes on Git 2.56.0. It exercised ordinary worktree creation, argument forwarding,
HOME/PATH precedence, shell-metacharacter paths, file-checkout no-op, missing
executable warnings, source-error continuation and another named hook's exit
status. Public operations and inspection were subsequently implemented and
independently reviewed through `bdcf2da`; final acceptance evidence follows below.

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

The operator prefers shared clone registration plus a Git hook and rejects
calling `skillset` from Orca setup scripts. Existing hooks and `core.hooksPath`
must be preserved. Use the shared Git directory as clone identity, not remote
URL or a primary-checkout path. Existing worktrees need explicit reconciliation
when registration changes. Bare `--no-checkout` creation without a later
checkout does not trigger this mechanism. SSH/WSL hosts remain unverified.
Traditional hooks and `core.hooksPath` now have disposable runtime tests.
The operator accepted a new `--project`
scope while preserving exact-directory/worktree-local `--local` and the global
default on 2026-10-11.

## Public-command compatibility acceptance

Nine `test_project_compatibility_` tests exercise actual Git processes and
public project commands using isolated temporary homes. Existing production
behavior passed the added assertions; no product changes were required.

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

Initial fixture failures concerned Git's environment spelling and the ordinary
remove confirmation, rather than production behavior. Ordinary worktree add
does not export `GIT_DIR` on this Git version; explicit Git location options do,
and Git normalizes the worktree to `.` before invoking hooks. The tests record
that real environment rather than assuming an absolute worktree spelling.

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
arguments appended, as Git normally appends them. This is fixture-only config,
not a product launcher or installation recommendation. An initial adapter
omitted that argument append: Git triggered it, but parsing failed. The first
worktree was removed through Orca and the adapter corrected before the successful
probe; no product code changed.

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

## Verification commands

All commands ran from the implementation checkout on 2026-10-11:

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p test_skillset.py -k test_project_compatibility_ -v` | 9 tests, 4.854s, OK, no skips |
| `python3 -m unittest discover -s tests -p test_skillset.py -k project -v` | 96 tests, 22.012s, OK, no skips; includes project operations/inspection/hooks/state/projection |
| `python3 -m unittest discover -s tests -p test_skillset.py -k codex_projection -v` | 6 tests, 0.008s, OK |
| `python3 -m unittest discover -s tests -p test_skillset.py -k completion -v` | 13 tests, 8.800s, OK, no skips; Bash/Fish/Zsh behavior and syntax |
| `python3 -m unittest discover -s tests -v` | 325 tests, 71.560s, OK, no skips |

The full-suite output was captured with `> /tmp/skillset-task6-full-suite.log 2>&1`.
The terminology review command returned exit 1 with no matches:

```sh
rg -n 'Task [0-9]|milestone|phase [0-9]|bead|ticket|codex-project-enablement' lib/skillset bin README.md tests/test_skillset.py
```

## Final review corrections and refreshed verification

Final current-session review identified three ordinary serial reliability gaps. The combined correction at `71b0587` checks effective event-wide disable controls before first enable, distinguishes project destination inspection errors from absent/unrelated entries, and retains invalid registered project rows when unscoped layout validation fails. The global/local layout refusal and exit status remain; project rows provide partial read-only evidence. This clarifies and supersedes the plan's abort-before-render interpretation in favor of the binding listing specification.

Each correction has failing-before/passing-after regression evidence. Fresh amended-code verification passed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v -k codex -k project -k completion
# 123 tests in 36.586s; OK
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
# 331 tests in 77.829s; OK; no skips
```

The earlier 325-test result describes the acceptance checkpoint before these six additional regression methods. Independent scoped re-review found all three product findings addressed. A residual test-only guard correction at `5254e50` gates event-wide runtime coverage on Git 2.55; the separate 2.54/2.55 boundary test remains. A deterministic simulated-2.54 probe verified skipping before fixture mutation, and all four first-enable tests passed on installed Git 2.56. Production code is unchanged from the 331-test run. Direct verifier confirmation passed; no review findings remain. The Orca adapter evidence and unmodified service-environment gap above are unchanged; no additional live-runtime test was run.
