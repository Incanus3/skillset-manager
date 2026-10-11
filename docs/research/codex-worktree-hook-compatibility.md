# Codex worktree hook compatibility

Verified 2026-10-11 on Linux with the installed Orca 1.4.223 runtime.

## Outcome and scope

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

## Remaining design constraints

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
native named-hook direction avoids owning that file; runtime coexistence remains
unverified. The [proposed specification](../specs/2026-10-11-codex-project-enablement-design.md)
owns the current integration contract. Inspection did not modify hooks or Git config.

The operator prefers shared clone registration plus a Git hook and rejects
calling `skillset` from Orca setup scripts. Existing hooks and `core.hooksPath`
must be preserved. Use the shared Git directory as clone identity, not remote
URL or a primary-checkout path. Existing worktrees need explicit reconciliation
when registration changes. Bare `--no-checkout` creation without a later
checkout does not trigger this mechanism. SSH/WSL hosts and alternate hook
configurations were not runtime-tested. The operator accepted a new `--project`
scope while preserving exact-directory/worktree-local `--local` and the global
default on 2026-10-11.
