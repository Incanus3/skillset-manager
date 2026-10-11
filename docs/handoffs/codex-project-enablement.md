# Codex project enablement

Status: active
Updated: 2026-10-11
Resume: `$resume codex-project-enablement`

## Objective and checkpoint

Enable selected Codex skillsets across existing and future worktrees of one
clone, including ordinary Orca creation without setup scripts. Independent
clones remain independent. The approved design and six-task plan have been
implemented after the clean-session boundary with separate implementation and
verification agents. Do not restart implementation or request another boundary.

Implementation branch: `codex-project-enablement`, checkpoint `5254e50` (product fixes at `71b0587`, followed by a test-only guard).
Design/documentation branch: `codex-project-enablement-design`, checkpoint
`827647a` plus final evidence/handoff updates. Preserve the independent stacks;
no push, merge, publication or live hook installation is authorized.

Task reviews are complete within their evidence limits. Final feature review
identified three defects: first-enable event-wide disable preflight, ordinary
link/container inspection failure recovery, and hidden invalid registered rows
in unscoped list. One combined fix wave at `71b0587` corrected all three with
regressions; scoped independent re-review found all three product defects addressed.
A residual test-only event-control guard now requires Git 2.55; simulated 2.54
skips before fixture mutation and four installed-2.56 tests pass. Direct
verifier confirmation passed; no review findings remain. Fresh amended-code checks
passed 123 focused tests and all 331 suite tests, with no skips. Native
Bash/Fish/Zsh completion checks and nine real-Git compatibility cases passed.

## Authorities and evidence

- [Approved specification](../specs/2026-10-11-codex-project-enablement-design.md): exact behavior, accepted decisions and constraints.
- [Implementation plan](../plans/2026-10-11-codex-project-enablement-implementation.md): completed sequence, clarified invalid-source rendering contract and remaining gate.
- [Compatibility research](../research/codex-worktree-hook-compatibility.md): exact commands, Git findings, hook lifecycle tests, Orca adapter/cleanup evidence and verification limits.
- [Local CLI reliability policy](../guides/local-cli-reliability.md): ordinary serial reliability; no adversarial filesystem protocol.
- Execution recovery: `.superpowers/sdd/2026-10-11-codex-project-enablement-implementation/progress.md`, `final-review.md`, `final-fix-report.md`, and `final-rereview.md`.

Installed Orca 1.4.224 with setup skipped triggered the native hook and actual
dispatcher/projection through a disclosed temporary HOME/PATH fixture adapter.
Probe worktrees/setup were removed through Orca and verified absent. Unmodified
Orca service HOME/PATH acceptance remains unmet: CLI exposes no override and
live runtime access was excluded. Actual Git 2.54 execution, sparse/prepared
Orca, SSH and WSL remain unverified; versioned sources support the Git floor.

Runtime state belongs to `~/.agents`; tests used disposable layouts. Keep the
unrelated Beads recovery separate: no open task was found and sync still
reported newer JSONL/import recommended. No explicit import/export or task
mutation was performed. Preserve the operator's existing spec/review-companion
and Beads changes.

## Continue in order

1. Obtain operator disposition of the unmodified Orca service HOME/PATH
   acceptance gap. Product and test review findings are resolved; implementation
   is verified within the recorded limits.
2. Any further live-runtime testing, publication, merging or live hook
   installation requires separate authorization. Preserve the independent
   implementation/documentation branches and existing unrelated changes.
3. Keep this handoff until the operator explicitly confirms the workstream is
   complete. If accepted, capture remaining decisions before retiring it.
