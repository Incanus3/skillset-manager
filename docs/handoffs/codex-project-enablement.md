# Codex project enablement

Status: active
Updated: 2026-10-11
Resume: `$resume codex-project-enablement`

## Objective and checkpoint

Design automatic Codex skillset enablement across existing and future worktrees
of one clone, including Orca-created worktrees without an Orca setup-script
call. Independent clones remain independent.

The [proposed specification](../specs/2026-10-11-codex-project-enablement-design.md)
is now the canonical design and review artifact. No product implementation or
implementation plan exists. The immediate next action is operator review of
its proposed decisions and behavior; implementation is not authorized.

Accepted choices are separate `--project` scope, preserving exact-directory
`--local` and the global default, and Git 2.54+ native clone-local config-based
hooks. For pre-existing local links the operator requested the simpler
solution. D3 therefore proposes no per-link origin ledger and removal of all
matching canonical links on project disable; its specific consequence remains
visible for specification review rather than being recorded as separately
accepted intent.

## References and evidence

- [Specification](../specs/2026-10-11-codex-project-enablement-design.md): precise
  CLI, registration, hook, recovery and acceptance contracts; implementation
  owners; decision inventory and approval scope.
- [Compatibility research](../research/codex-worktree-hook-compatibility.md):
  installed Orca 1.4.223 traditional-hook trigger probe, Git 2.54 primary sources,
  installed Git 2.56.0 inventory and GitButler hook lifecycle inspection.
- [Local CLI policy](../guides/local-cli-reliability.md): trusted serial reliability
  and proportionate recovery; no adversarial filesystem protocol.

The prior Orca probe verified the trigger with setup skipped, not a native-hook
implementation. Native-hook coexistence, sparse/prepared paths and remote
hosts remain unverified. This design session inspected repository code and
sources and checked documentation consistency; it ran no product tests and
changed no live hooks or Git config. Installed `skillset` resolves to this
checkout's `bin/skillset`; runtime state belongs to `~/.agents`.

Refreshing Beads with `br list` automatically migrated the local database and
created recovery artifacts. No open workstream task was found. `br sync --status`
reported newer JSONL/import recommended; no explicit import, export, task
mutation or manual state-file cleanup was requested. Keep that unrelated tracker recovery
separate from the design.

## Continue in order

1. Review the specification, especially D3 ordinary-link removal, D5/D6 partial
   recovery and warning-only hook failures, and D7–D9 inspection/lifecycle/ignore
   trade-offs. Revise its canonical contracts and decision statuses as needed.
2. After specification approval, prepare an implementation plan in `docs/plans/`
   if requested, applying the complete specification and obtaining plan approval
   before implementation.
3. After plan approval, maintain this handoff and follow the repository's clean
   session boundary and execution-selection policy. Do not request a new
   implementation session while plan approval is pending.
4. Implement only with the required approvals, verify against the specification,
   and persist evidence in canonical owners. Preserve this handoff until the
   operator explicitly confirms the workstream is complete.
