# Local CLI Reliability Policy Implementation Plan

> **For agentic workers:** Use `subagent-driven-development` or
> `executing-plans` to implement one task at a time. Steps use checkbox syntax
> for tracking. Stop after each task for operator approval.

> **Status:** Completed — implementation was verified and independently
> reviewed. The durable policy and completion record are in
> `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md` and
> `docs/guides/local-cli-reliability.md`.

**Goal:** Establish the approved trusted-local-CLI policy, replace conflicting
transactional-safety guidance, document best-effort concurrency, and record an
initial classified inventory before application simplification begins.

**Architecture:** This plan intentionally delivers only the documentation and
classification foundation (Pass 1 of the approved specification). It creates a
new authoritative local-reliability guide, redirects live guidance to it,
removes unsupported security claims from user documentation, and records the
initial high-confidence candidates. Later plans will remove tests and code only
after using this inventory to define narrow, independently reviewable batches.

**Tech Stack:** Markdown documentation, Python standard-library CLI,
`unittest`, GitButler workspace.

## Global Constraints

- Read `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md`
  in full before modifying any file in this plan.
- This is a trusted local CLI, not a security boundary. Preserve serial
  functional reliability, ordinary I/O errors, and useful Ctrl+C recovery.
- Concurrency is best effort; do not promise race-free behavior or introduce
  adversarial TOCTOU hardening.
- Do not add dependencies, `ctypes`, platform-specific syscall bindings, or
  `renameat2` wrappers.
- Keep `docs/handoffs/augment-support-review.md` and its index entry for now;
  the approved specification requires their removal only at final closure.
- Do not commit, push, merge, or delete the handoff without explicit operator
  authorization.

## File map

- Create: `docs/guides/local-cli-reliability.md` — authoritative scope,
  classification, and reviewer guidance.
- Modify: `AGENTS.md` — concise posture and guide reference.
- Delete: `docs/guides/transactional-cli-safety.md` — superseded guidance.
- Modify: `README.md` — best-effort lock and recovery descriptions without
  hostile-process guarantees.
- Modify: `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md`
  — add the initial classified inventory used by later plans.
- Modify: `docs/specs/2026-07-10-skillset-module-extraction-design.md` and
  `docs/specs/2026-07-17-claude-code-skillset-discovery-design.md` — mark old
  adversarial constraints as superseded while retaining historical context.
- Modify: `docs/plans/2026-07-10-skillset-module-extraction.md` — replace the
  deleted-guide prerequisite in the completed historical plan.

---

### Task 1: Establish the authoritative local reliability policy

**Files:**
- Create: `docs/guides/local-cli-reliability.md`
- Modify: `AGENTS.md:188-192`

**Interfaces:**
- Consumes: the approved design's policy boundary and classification framework.
- Produces: the sole policy source future implementation and review work reads
  for local filesystem behavior.

- [x] **Step 1: Replace the transactional-guide loading rule in `AGENTS.md`**

Replace the current “Load specialized guidance only when relevant” paragraph
with this concise rule:

````markdown
## Local CLI reliability policy

`skillset` is a trusted local CLI, not a security boundary. Preserve serial
functional reliability and proportionate recovery from ordinary errors, but do
not add adversarial filesystem or TOCTOU hardening. Treat concurrency as best
effort only. Before designing, testing, or reviewing filesystem behavior, read
`docs/guides/local-cli-reliability.md`.
````

- [x] **Step 2: Create `docs/guides/local-cli-reliability.md`**

Write this complete guide:

````markdown
# Local CLI Reliability Guide

## Scope
`skillset` serves trusted developers on local machines and is not a security
boundary. Normal serial commands, ordinary I/O errors, and useful Ctrl+C
recovery are supported; hostile local actors are not.

## Functional reliability
- Correct links, lock metadata, aliases, and registrations in serial use.
- Clear errors and proportionate recovery that prevents loss or unusable state.
- Preserve unrelated local data in normal, non-racing operation.

## Exclude
- TOCTOU, hostile replacement, and same-UID attacker defenses.
- Syscall-boundary fault injection, descriptor identity protocols, and
  quarantine state created solely for racing replacements.
- `ctypes`, direct syscall bindings, and platform-specific filesystem APIs.

## Best-effort concurrency
Simple advisory locking may reduce accidental overlap when it remains
standard-library-based and easy to understand. It does not guarantee correct
behavior for concurrent mutations and must not grow a specialized test matrix.

## Classification
Classify every candidate before changing it:

| Classification | Meaning |
| --- | --- |
| Functional reliability | Normal serial behavior, ordinary errors, or proportionate recovery. Retain it. |
| Mixed | Functional behavior plus adversarial protocol. Preserve only the functional subset in a narrow change. |
| High-confidence adversarial hardening | Hostile replacement, TOCTOU, same-UID interference, or syscall timing. Remove it with its dedicated tests. |

## Review checklist
- Name the normal serial failure or user-visible behavior the change preserves.
- Reject a change whose only rationale is a hostile or racing process.
- Verify that a retained lock, staging marker, or rollback path remains the
  smallest understandable solution to its functional problem.
````

- [x] **Step 3: Verify the policy source is reachable and complete**

Run:

````sh
test -f docs/guides/local-cli-reliability.md
grep -n 'local-cli-reliability.md' AGENTS.md
grep -nE '^## (Scope|Functional reliability|Exclude|Best-effort concurrency|Classification|Review checklist)' docs/guides/local-cli-reliability.md
````

Expected: all commands exit `0`; the guide has all six headings and `AGENTS.md`
contains exactly the replacement policy reference.

### Task 2: Replace live historical references and record the initial inventory

**Files:**
- Modify: `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md`
- Modify: `docs/specs/2026-07-10-skillset-module-extraction-design.md:15-18`
- Modify: `docs/specs/2026-07-17-claude-code-skillset-discovery-design.md:429-464`
- Modify: `docs/plans/2026-07-10-skillset-module-extraction.md:19-31`
- Delete: `docs/guides/transactional-cli-safety.md`

**Interfaces:**
- Consumes: the new guide from Task 1 and the discovery evidence in the
  approved design.
- Produces: no live reference to the deleted guide and a durable candidate
  inventory for later implementation plans.

- [x] **Step 1: Add an “Initial candidate inventory” section to the approved design**

Insert the section immediately after **Classification framework**. Include this
table; its classifications are initial decisions, not authorization to remove
mixed candidates:

````markdown
| Area | High-confidence adversarial candidates | Mixed candidates retained for later decision |
| --- | --- | --- |
| Tests | Auggie hostile-replacement/quarantine tests at `7494-8035`; Auggie replacement/lifecycle tests at `8610-9064`; advisory-lock replacement/FIFO tests at `4388` and `9933`. | Ctrl+C recovery, staging, ordinary lock waits, and ordinary malformed-layout cases. |
| `augment.py` | `directory_binding_problem`, `directory_at_binding_problem`, `ScopeState.verify_bindings`, source-child identity checks, and removal-quarantine helpers. | Normal link ownership, registration reconciliation, and simple interruption recovery. |
| `layout.py` | Descriptor-identity and no-follow behavior for inspection/discovery locks. | A small advisory lock, ordinary lock-file errors, and read-only discovery behavior. |
| Documentation | Transactional guide, attacker/race claims, quarantine recovery, and safe-lock detail. | Normal recovery and layout-repair instructions. |
````

Add a paragraph after the table: later plans must refresh this inventory against
the live implementation and remove only a candidate's adversarial portion when
it also serves a serial functional purpose.

- [x] **Step 2: Redirect the module-extraction design context**

Replace its two transactional-guide lines with one factual historical statement:

````markdown
- Historical designs included transactional filesystem hardening. The current
  local-CLI policy is `docs/guides/local-cli-reliability.md`; it supersedes that
  adversarial guidance while retaining ordinary functional recovery.
````

- [x] **Step 3: Replace the Claude design's obsolete safety protocol**

Replace the entire **Locking and safety** section through the paragraph ending
before **Implementation boundaries** with this content:

````markdown
## Reliability and concurrency

Claude commands may use advisory locking to reduce accidental overlap. This is
best effort, not a guarantee against concurrent edits or direct upstream use.
Registration state lets `enable` reconcile normal partial projections and lets
`disable` remove its owned links before the registration. Ordinary operational
failures exit 1; Ctrl+C remains exit 130 when the CLI can provide useful normal
recovery information. The detailed local policy is
`docs/guides/local-cli-reliability.md`.
````

- [x] **Step 4: Correct the completed module-extraction plan's prerequisites**

Replace its requirement to read the deleted guide with:

````markdown
- This completed extraction plan predates the current local-CLI policy. For
  later maintenance, read `docs/guides/local-cli-reliability.md` rather than
  restoring its former transactional-hardening constraints.
````

- [x] **Step 5: Delete the superseded guide only after references are redirected**

Delete `docs/guides/transactional-cli-safety.md`. Retain the Auggie review
handoff as historical evidence until final closure.

- [x] **Step 6: Verify references and inventory**

Run:

````sh
test ! -e docs/guides/transactional-cli-safety.md
grep -RIn 'transactional-cli-safety\.md' AGENTS.md README.md docs | sort
````

Expected: the guide is absent. The search reports only this implementation
plan, the approved design, and the still-retained Auggie review handoff; it
must not report `AGENTS.md`, the module-extraction plan, or either updated
historical design.

### Task 3: Rewrite README guarantees as functional reliability

**Files:**
- Modify: `README.md:76-90, 176-184, 221-234, 562-571, 627-637, 651-670`

**Interfaces:**
- Consumes: the authoritative guide and existing user-facing command behavior.
- Produces: accurate documentation that preserves normal workflows but makes no
  adversarial or race-free claim.

- [x] **Step 1: Rewrite configured-directory migration guidance**

Keep the migration commands. Replace the instruction to “stop concurrent”
commands and the independent-lock explanation with:

````markdown
Before migration, close any `skillset` or delegated upstream command that is
currently using the installation. One `~/.agents` installation should own a
configured directory; sharing it between installations is unsupported.
````

- [x] **Step 2: Retain activation recovery while removing verification protocol detail**

Replace `README.md:176-184` with:

````markdown
Activation retargets `~/.agents/active`. Managed collections keep the root lock
alias pointed at `active/.skill-lock.json`; a manual collection instead uses the
read-only shared empty-lock sentinel `~/.skillset-manual-empty-lock.json`.
Keeping this runtime-owned file outside the skillset repository prevents
version-control tools from trying to rewrite it during commits. `skillset use`
recreates it when needed; `skillset doctor --fix` can also restore a missing
sentinel after confirmation. An interrupted activation may leave a recovery
record for `skillset doctor --fix`.
````

- [x] **Step 3: Replace the global lock protocol paragraph**

Replace `README.md:221-234` with:

````markdown
`skillset` uses advisory locks to reduce accidental overlap between its own
operations. This is best effort: do not run conflicting `skillset` or direct
upstream mutations at the same time. Managed inspection remains read-only, and
`skillset augment skills list` can inspect discovery roots without requiring a
managed layout. After initialization, prefer `skillset skills ...` for global
installation and maintenance.
````

- [x] **Step 4: Remove Auggie quarantine-specific recovery text**

Keep the documented enable/disable reconciliation. Replace the two sentences
beginning “An interrupted or partial operation” with: “If a normal operation is
interrupted, rerun `enable` to reconcile the projection or use `disable` to
remove its owned links.” Keep “Empty containers remain in place.”

- [x] **Step 5: Simplify doctor and recovery wording**

Replace `README.md:627-637` with:

````markdown
`doctor` inspects the managed layout without creating it and reports all
discovered layout problems. A missing `.agents` root or managed lock is reported
alongside missing aliases, `active`, and `skillsets`. It checks all three
canonical aliases, the active target grammar and existence, direct skillset
directory names and shapes, stale use/create staging markers, readable
version-3 lockfiles, and each direct skill directory's `SKILL.md` metadata.
````

Keep the five recovery steps at `README.md:651-661`. Replace the final
`doctor --fix` paragraph with:

````markdown
`doctor --fix` can repair a deliberately small set of lossless omissions after
an interactive `y` or `yes` confirmation. It may create a missing advisory lock
and a missing version-3 empty lockfile only when that skillset's `skills`
directory is empty. It does not overwrite existing files. Each created file is
reported as `skillset: repaired:`. Resolve every other finding manually after
preserving the data it identifies.
````

- [x] **Step 6: Validate user documentation claims**

Run:

````sh
grep -nEi 'quarantine|same-UID|TOCTOU|race-free|without following|safe regular file' README.md || true
grep -n 'best effort' README.md
````

Expected: the first command prints no removed adversarial phrases. The second
prints the advisory-lock paragraph. Review every remaining use of “atomic” or
“safe” manually; retain it only when it describes serial functional behavior.

### Task 4: Documentation-only regression review

**Files:**
- Modify: all files changed by Tasks 1-3 only

**Interfaces:**
- Consumes: the policy, redirected references, inventory, and README edits.
- Produces: a verified documentation checkpoint before test or code work.

- [x] **Step 1: Check formatting and reference integrity**

Run:

````sh
git diff --check
grep -RIn 'local-cli-reliability\.md' AGENTS.md docs | sort
grep -RIn 'transactional-cli-safety\.md' AGENTS.md README.md docs | sort
````

Expected: no whitespace errors; the new guide is referenced by `AGENTS.md` and
the redirected historical documents; old-guide occurrences are only the plan,
approved design, user prompt, and retained historical handoff identified in
Task 2.

- [x] **Step 2: Confirm no application or test behavior changed**

Run:

````sh
git diff --name-only
python -m unittest discover -s tests
````

Expected: changed paths are documentation only. The full black-box suite exits
`0`; this checkpoint establishes that policy documentation did not alter CLI
behavior.

- [x] **Step 3: Request review and stop**

Report the modified and deleted documents, the exact old-guide references
intentionally retained for historical evidence, and the test result. Do not
begin the test-removal or code-simplification work until the operator approves
the documentation checkpoint.

## Later-plan boundaries

After Task 4 approval, write separate plans for these ordered work items:

1. High-confidence Auggie quarantine, hostile-replacement, and identity test
   removal, followed by the matching `augment.py` simplification.
2. Advisory-lock, descriptor/no-follow, and discovery hardening classification
   and simplification across `layout.py`, `metadata.py`, `claude.py`, and tests.
3. Remaining mixed staging, rollback, and Ctrl+C cases, one functional contract
   at a time.
4. Final README/reference refresh, durable-information harvest, and deletion of
   `docs/handoffs/augment-support-review.md` plus its index entry.

Each later plan must start by refreshing the candidate inventory and identifying
the serial functional behavior preserved by its change.