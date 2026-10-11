# Codex project enablement

Status: active
Updated: 2026-10-11
Resume: `$resume codex-project-enablement`

## Objective and checkpoint

Implement automatic Codex skillset enablement across existing and future worktrees
of one clone, including Orca-created worktrees without an Orca setup-script
call. Independent clones remain independent.

The [specification](../specs/2026-10-11-codex-project-enablement-design.md)
is approved after decision review and naming/list-order revisions. The
[implementation plan](../plans/2026-10-11-codex-project-enablement-implementation.md)
is approved. The clean-session boundary was completed on 2026-10-11;
delegated implementation is executing the approved sequence. Task 1 is complete:
shared Git discovery and names-only registration,
checkpoint `04ba14c`, 14 focused tests, independent spec/quality review clean.
Task 2 is also complete: explicit-root Codex projection, checkpoint
`7d87576`, 6 projection and 12 Codex tests, independent review clean. Task 3 is complete: native hook and hidden dispatcher, checkpoint `bf35f40`,
22 hook and 53 focused tests, independent review clean. Actual Git 2.54
execution remains unverified; versioned primary sources support the floor.
Task 4 is complete: public enable/disable and retry recovery, checkpoint
`cd09144`, 23 operation/35 Codex/22 hook tests, independent review clean.
Task 5 is complete at `bdcf2da`: ordered listing, read-only health and
native Bash/Fish/Zsh completions. Independent review found relative-Git-cwd
and dropped-row errors; fix round 1 addressed both, scoped re-review clean.
Task 6 acceptance tests and README are checkpointed at `6d34372`; independent
verification remains. Nine new real-Git compatibility tests passed without
production changes. Focused project selection passed 96 tests, projection 6,
and Bash/Fish/Zsh completion checks 13, with no skips. The full suite passed
325 tests in 71.560s with no skips; the terminology search had no matches.
Canonical commands and evidence belong in the compatibility research.

Installed Orca 1.4.224 with setup skipped successfully triggered the native
hook and actual dispatcher using a disclosed temporary HOME/PATH adapter.
The unmodified service environment remains an unmet acceptance check: repo,
setup and create expose no environment override, and live `~/.agents` access
is excluded. Both probe worktrees and the registered setup were removed through
Orca, verified absent, then the disposable filesystem was removed. Sparse/prepared
Orca, SSH/WSL and actual Git 2.54 execution remain unverified.

The implementation and design remain independent GitButler stacks. The
coordinator directed acceptance tests/README to `codex-project-enablement`,
and research/handoff/index to `codex-project-enablement-design`, where their
files already belong. Do not stack or rewrite either branch to combine them.
Do not request another clean session solely to record these approvals.

D1–D9 are accepted. D4 uses harness-neutral `project-skillsets.json` with
version and one shared names list for all harnesses, inherited HOME and standard
PATH precedence. Only Codex project functionality is currently in scope; no
per-harness selections are stored. Shared hook keys are
`hook.skillset-project.command`/`.event`, invoking hidden top-level
`skillset _project-hook`; shared infrastructure belongs in `lib/skillset/project.py`
and Codex destinations/reconciliation in `codex.py`. D7 adds [p]
registration rows to unscoped list in global/project/local ([g]/[p]/[l]) order,
while --project remains
the full read-only health check. The specification owns all exact contracts.

## References and evidence

- [Specification](../specs/2026-10-11-codex-project-enablement-design.md): precise
  CLI, registration, hook, recovery and acceptance contracts; implementation
  owners; decision inventory and approval scope.
- [Implementation plan](../plans/2026-10-11-codex-project-enablement-implementation.md):
  six sequential tasks with shared interfaces, focused red/green checks and
  compatibility/Orca acceptance; approved, Tasks 1–5 complete and Task 6 under review. Planning self-review
  checked source coverage, interface consistency, Python snippet syntax and
  local artifact links. No product tests were run during planning.
- [Local HTML review companion](../specs/codex-project-enablement-review/index.html):
  ownership and disable-recovery diagrams, link-removal example and decision
  inventory. Its full HTML source snapshot and unchanged Markdown match the
  current canonical specification by SHA-256, based on commit `6eda5ed4399e`;
  refresh them when it changes.
  Desktop top, central and lower views were visually inspected; local links,
  source anchors, SVG structure and snapshot hash were checked. This is design
  presentation verification, not product acceptance evidence.
- [Compatibility research](../research/codex-worktree-hook-compatibility.md):
  exact verification commands, real Git compatibility and hook-coexistence
  acceptance, installed Orca 1.4.224 adapter command/results/cleanup and evidence
  boundary; retained prior trigger probe and versioned primary sources.
- [Local CLI policy](../guides/local-cli-reliability.md): trusted serial reliability
  and proportionate recovery; no adversarial filesystem protocol.

Native-hook coexistence now has real Git tests, including a disposable
reproduction of observed GitButler hook restoration/removal (without operating
GitButler itself). Product tests and probes changed no live hooks or Git config.
Installed `skillset` resolves to this checkout's `bin/skillset`; runtime state
belongs to `~/.agents` and must remain outside test fixtures.

Refreshing Beads with `br list` automatically migrated the local database and
created recovery artifacts. No open workstream task was found. `br sync --status`
reported newer JSONL/import recommended; no explicit import, export, task
mutation or manual state-file cleanup was requested. Keep that unrelated tracker recovery
separate from the design.

## Continue in order

1. Finish Task 6 from the plan's execution ledger at
   `.superpowers/sdd/2026-10-11-codex-project-enablement-implementation/progress.md`.
   Use subagent-driven-development with separate implementer
   and verifier agents under the delegation policy unless the operator chooses
   inline execution. Inspect current workspace state; preserve unrelated Beads
   recovery and reviewed documentation.
2. Obtain independent bounded Task 6 verification of implementation checkpoint
   `6d34372` and the separate design-branch documentation checkpoint. Update the
   plan/ledger after review; do not add
   other harnesses or re-review the pre-existing branch.
3. Report the exact remaining Orca service-environment acceptance gap for operator
   disposition. Further live-runtime testing, publication, merging and live hook
   installation need separate authorization. Preserve this handoff until the
   operator explicitly confirms the workstream is complete.
