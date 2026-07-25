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

## Create explicit handoffs before context resets

At a clean checkpoint near a context-window boundary, create a concise document under `docs/handoffs/`. Include:

- Committed and uncommitted repository state
- Latest verification evidence
- Completed behavior and important safety invariants
- Remaining tracker issue and exact scope
- Known caveats and unresolved decisions
- A copy-ready resume prompt with workflow and verification instructions

Prefer a handoff after a verified checkpoint rather than in the middle of an edit or debugging loop. Keep the document
self-contained enough for a fresh session, and remove or archive it when it is no longer useful.

## Load specialized guidance only when relevant

When work involves transactional filesystem operations, rollback, persistent staging markers, resource ownership, or
transparent CLI delegation, read `docs/guides/transactional-cli-safety.md` before designing or reviewing the change.
Keep specialized implementation guidance out of the baseline rules so unrelated sessions do not need to load it.

## Treat rewriting pushed Jujutsu history as exceptional

Only bypass immutable-commit protection when the user explicitly requests rewriting pushed history. Do not weaken the
repository's immutable-head configuration for a one-off rewrite.

When a rewrite is authorized:

1. Use the command-scoped `--ignore-immutable` override.
2. Push through Jujutsu with the intended bookmark explicitly selected.
3. Verify that the local and remote commit IDs match after the push.