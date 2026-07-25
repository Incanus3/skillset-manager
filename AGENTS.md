# Global Agent Conventions

These rules capture general practices that should carry across projects and sessions.

## Use tool-neutral documentation paths

Store design artifacts in stable, purpose-based directories:

- Specifications: `docs/specs/`
- Implementation plans: `docs/plans/`
- Session handoffs: `docs/handoffs/`

Do not put workflow, skill collection, or tool names such as `superpowers` in documentation directory names unless the
documents are specifically about that tool. Tool-neutral paths remain accurate when workflows or agents change.

## Make specifications self-contained handoff artifacts

A fresh session should be able to plan and implement from a specification without relying on prior conversation history.
Include the context needed to resume safely:

- Relevant repository and environment state
- External research, observed behavior, and source links
- Requirements and explicit decisions
- Rejected alternatives and accepted trade-offs
- Exact command, API, and error semantics
- Expected file boundaries and responsibilities
- Testing and verification strategy
- Known caveats and a next-session checklist

Before finalizing a specification, remove placeholders and resolve contradictions or ambiguous requirements.

## Read design context before executing plans

Before implementing from a plan, read the complete design specification referenced by that plan. Use the design to
understand scope, safety constraints, and accepted decisions; do not rely on the plan alone when it summarizes them.

## Navigate project knowledge deliberately

Start with the project's navigation entry point, index, or equivalent repository map when one is available. Follow only
the references relevant to the task; do not load an entire knowledge base or documentation tree by default.

## Preserve durable knowledge and document authority

Capture meaningful findings, decisions, research progress, workflow changes, and verification evidence in their
canonical project artifacts rather than copying conversation transcripts. Prefer updating an existing source of truth
over creating a competing document.

When guidance is replaced, mark the older guidance as superseded and retain important rationale in the appropriate
decision record. When a repository maintains curated content indexes, update the relevant index when its contents or
children change.

## Curate durable knowledge rather than accumulate records

Persist conclusions, evidence, useful provenance, and actionable follow-up context. Do not preserve routine progress
narration, duplicated command output, ungrounded speculation, or complete conversation transcripts as durable project
knowledge.

When a detail does not affect future decisions, behavior, authority, verification, or resumption, omit it from
canonical documentation.

## Apply proportionate rigor and maintain human control

Treat work that creates or changes durable artifacts, decisions, task state, or multi-step work as **material**. Treat
work that can cause meaningful rework, external effects, security or data risk, or a change to canonical practice as
**consequential**. Apply documentation and verification rigor proportionately.

Keep the operator in control of priorities, scope expansion, irreversible or external actions, and the promotion of
experimental practice into canonical guidance. Escalate uncertainty that materially changes intent, risk, or blast
radius rather than silently choosing on the operator's behalf.

## Separate technical readiness from authorization

Completion, verification, committing, pushing, or other evidence of technical readiness does not authorize a
consequential action. Require explicit operator authorization before merging, deploying, publishing, altering shared or
external state, deleting material resources, or otherwise taking an irreversible action, unless an accepted project
policy explicitly grants that authority.

Before publishing or landing work, refresh the relevant target and remote state. Do not revive a stale branch, target,
review, or other shared reference merely because it remains locally visible.

## Match verification to the risk

Use self-checks for trivial, local, reversible edits; fresh-context review when author bias or discoverability matters;
independent specialist review for security, correctness, architecture, or domain risk; and human acceptance for intent,
priority, material risk, and external consequences.

Automated checks complement rather than replace judgment. A verifier should inspect the artifact directly, reproduce
checks where feasible, map evidence to acceptance criteria, and state material uncertainty.

When a task intentionally adds red tests, contract tests, fixtures, or scaffolding before later implementation, verify
the tests and helpers against that task's stated scope. Treat failures explained by deferred implementation as expected;
investigate only accidental regressions, broken scaffolding, or failures that contradict the scope. Do not broaden the
task into implementation or unrelated test cleanup without approval.

## Improve repeated failures with the smallest durable intervention

When a material failure or avoidable interruption recurs, identify its cause before changing the process. Prefer the
smallest durable intervention that addresses the demonstrated problem: a clear rule, checklist, example, test, or
template before a new tool or service.

Retain the intervention only when evidence shows a net improvement. Do not create lasting process or tooling for a
one-off problem without a clear reason to expect recurrence.

## Delegate with bounded ownership and evidence

Give delegated work a clear output, permitted actions, and acceptance criteria. Assign one owner to each writable
artifact, and isolate concurrent work when changes could collide.

For consequential work, separate implementation from verification and retain artifact-based evidence of the result.

## Delegate only work with a bounded, verifiable contract

Delegate when work is bounded, independently useful, explainable with compact context, and worth more than its
coordination cost. Keep small, serial, or tightly coupled work with the coordinating agent.

For each delegated unit, state the desired output; acceptance criteria and evidence; relevant sources and constraints;
allowed and forbidden actions; writable artifact scope; whether isolation is required; stop, budget, and escalation
conditions; and who integrates and verifies the result. The coordinator remains responsible for synthesis unless that
ownership is explicitly transferred.

## Coordinate parallel work deliberately

Use parallel work only for separable tasks. Prefer read-only discovery fan-out before implementation fan-out, and keep
discovery separate from synthesis when multiple sources or perspectives are useful.

Reconcile conflicting findings explicitly rather than averaging them into false consensus. Stop adding workers when
coordination cost approaches the expected gain.

## Keep planning terminology out of product surfaces

Production code, test names, user-facing documentation, command output, and APIs must remain independent of internal
phases, beads, tickets, milestones, or implementation sequence. Describe behavior and capability instead.

Planning identifiers belong in trackers, implementation plans, and handoffs. Before completing work, search
implementation-facing files for leaked planning terminology and replace it with durable domain language.

## Mirror upstream vocabulary in wrapper CLIs

When a CLI delegates to another CLI, reuse the upstream command verbs and option names wherever the semantics match.
Avoid unnecessary synonyms such as `delete` for an upstream `remove` command or `switch` for an upstream `use` command.
Matching vocabulary reduces translation overhead and makes upstream documentation easier to apply.

## Inventory all persistent state before designing indirection

Before introducing profiles, switching, aliases, or symlink-based indirection, identify all state used by the underlying
tool. Inspect visible data directories as well as lockfiles, metadata, caches, links, and state-directory environment
variables.

Keep related data and metadata together. Switching visible files without their associated metadata can leave management
commands operating on a different logical state than the files currently in use.

## Keep handoffs as concise, short-lived resume state

Create or update a handoff at a clean, preferably verified checkpoint when work must pause or a context reset is
approaching. A handoff contains only the operational delta a fresh session needs to continue unfinished work; it is not
a durable source of truth or archive.

When context-window risk appears to be increasing, warn the requester at a clean checkpoint rather than during a small
edit or validation loop. State that the assessment is heuristic, recommend a handoff or fresh-session boundary, and
offer a compact resume prompt or summary when useful.

Before a reset, persist important learnings, decisions, caveats, and next actions in their canonical owners; create or
suggest a handoff when it would make continuation safer.

Include the objective; current status; current checkpoint and completed safety-relevant behavior; durable references
and relevant task identifiers; latest verification evidence; ordered next actions; blockers, decisions, constraints,
caveats, and temporary assumptions to re-check; and any failed attempt or environment caution needed to avoid
repetition.

When repository state materially affects continuation, record only the specific stable revision, bookmark, branch, or
caveat needed to resume safely. Do not include a list or inventory of currently dirty files.

Do not copy canonical documents, acceptance criteria, full logs, secrets, chat transcripts, or durable rationale and
evidence. Persist those in their canonical owners first, then link to them from the handoff.

When the workstream completes, capture any remaining durable information, update authoritative task state, and remove
or archive the handoff when it is no longer needed. When a project maintains handoff indexes or resume commands, update
the relevant index and return the project's copy-ready resume instruction.

## Close material work with durable state and evidence

Before declaring material work complete, persist meaningful findings, decisions, and evidence in their canonical
owners; update affected indexes or references; and record bounded follow-up work with enough context to resume.

Record the verification performed and unresolved uncertainty. Update or remove a handoff when work pauses or completes,
and summarize the outcome rather than the conversation.

## Load specialized guidance only when relevant

When work involves transactional filesystem operations, rollback, persistent staging markers, resource ownership, or
transparent CLI delegation, read `docs/guides/transactional-cli-safety.md` before designing or reviewing the change.
Keep specialized implementation guidance out of the baseline rules so unrelated sessions do not need to load it.

## Prefer repository-aware version-control tooling

Before the first version-control operation, run `but status --format json` when `but` is available. If `but` is
initialized in the workspace, use `but` for version-control operations; use raw Git only when `but` cannot perform the
required action. Never run `jj` in a `but` workspace.

If `but` is not initialized and the workspace contains `.jj/`, use Jujutsu for all version-control operations and do
not run raw Git. Otherwise, use raw Git as the fallback.

When a diff contains unexpected changes, do not revert them automatically. Treat them as potentially intentional; if
they should not be included in the current change, ask the requester before modifying or excluding them.

## Stop on stale Jujutsu working-copy state

If a Jujutsu command reports that the working copy is stale, stop immediately. Do not retry the command, refresh the
working copy, or attempt a workaround; report the condition to the requester and wait for them to resolve it.

## Treat rewriting pushed Jujutsu history as exceptional

Only bypass immutable-commit protection when the user explicitly requests rewriting pushed history. Do not weaken the
repository's immutable-head configuration for a one-off rewrite.

When a rewrite is authorized:

1. Use the command-scoped `--ignore-immutable` override.
2. Push through Jujutsu with the intended bookmark explicitly selected.
3. Verify that the local and remote commit IDs match after the push.