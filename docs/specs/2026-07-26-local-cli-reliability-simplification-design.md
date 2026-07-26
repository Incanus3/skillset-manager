# Local CLI Reliability Simplification Design

**Date:** 2026-07-26
**Status:** Completed — implementation is published on PR #7; merge remains
separately authorized.

## Summary

Reorient `skillset` from adversarial filesystem hardening to functional
reliability for a small, local CLI used by trusted developers. Preserve correct
serial command behavior and practical recovery from ordinary filesystem errors
or Ctrl+C when needed to avoid loss or an unusable managed layout. Remove
disproportionate defenses against malicious or racing processes, and their
tests and documentation.

This is an iterative simplification program. Classify candidates before
changing them: remove clear adversarial hardening in coherent batches and
consider mixed behavior in small reviewable changes.

## Context and evidence

- The Linux-only, standard-library Python CLI manages named local agent-skill
  collections; it is neither a public service nor a security boundary.
- The Auggie review handoff records an unproductive cycle of same-UID hostile
  replacement, TOCTOU, descriptor identity, quarantine, FIFO-lock, and
  syscall-boundary fault-injection work.
- `docs/guides/transactional-cli-safety.md`, referenced by `AGENTS.md`, makes
  adversarial transaction testing appear mandatory for normal development.
- The checked-out `lib/skillset/augment.py` has no `ctypes`, `renameat2`, or
  `RENAME_NOREPLACE` reference. An intermediate review commit
  `9aba73b05a391d55e003eb2829d52de6126565a5` did add a `ctypes` Linux
  `renameat2` wrapper; the review handoff accurately describes that transient
  implementation. The program forbids reintroducing it.

## Goals

1. Establish a durable local-CLI threat model and review policy.
2. Preserve serial behavior, coherent managed state, ordinary I/O errors, and
   useful Ctrl+C recovery where it prevents loss or an unusable layout.
3. Document concurrency as best effort; retain only simple, proportionate
   safeguards.
4. Remove adversarial guidance, tests, and code while retaining intended normal
   user-facing functionality.
5. Keep Python-standard-library-only implementation; prohibit `ctypes`,
   platform-specific syscall bindings, and external native interfaces for
   filesystem hardening.
6. Delete the temporary Auggie review handoff only after durable information is
   harvested from it.

## Non-goals

- Security against a malicious local user or process.
- Guaranteed correctness for concurrently mutating commands.
- Exhaustive pre/post-syscall behavior testing.
- Platform-specific techniques to close theoretical race windows.
- Removing ordinary validation merely because it touches filesystem state.
- Changing public commands or normal workflows unless required to eliminate an
  adversarial protocol.

## Policy boundary

### Functional reliability to retain

- Normal semantics for initialization, creation, activation, rename, removal,
  delegation, inspection, and agent integrations.
- Coherent relationships among links, lock metadata, aliases, and registrations
  during serial operation.
- Clear errors for invalid input, ordinary I/O failure, and malformed local
  state.
- Simple recovery from Ctrl+C or operational failure when it materially avoids
  data loss or a plainly unusable layout.
- Preservation of unrelated data in normal, non-racing operation.

### Adversarial hardening to exclude

- Hostile same-UID actors and intentional filesystem replacement.
- TOCTOU resistance through identity comparison and repeated binding checks.
- Symlink/path-substitution protections whose rationale is malicious behavior.
- Quarantine protocols that exist to avoid deletion after a racing replacement.
- Fault injection around individual syscalls for attacker or arbitrary timing
  models.
- Fail-closed behavior justified only by a racing actor.
- `ctypes`, direct syscall bindings, or `renameat2` no-replace wrappers.

### Best-effort concurrency

Ordinary concurrent use is neither guaranteed nor treated as adversarial. A
small safeguard, including uncomplicated advisory locking, may remain only when
it is standard-library-based, easy to understand, and does not require a large
protocol or specialized test matrix. Documentation must say best effort rather
than promise race-free behavior.

## Classification framework

| Classification | Definition | Change policy |
| --- | --- | --- |
| Functional reliability | Normal serial behavior, state coherence, ordinary errors, or proportionate recovery. | Retain; simplify without changing its contract. |
| Mixed | Functional behavior plus an adversarial protocol or disproportionate verification. | Change narrowly; preserve the functional subset. |
| High-confidence adversarial hardening | Primarily hostile replacement, TOCTOU, same-UID interference, or syscall timing. | Remove in batches with dedicated tests and helpers. |

High-confidence examples include tests that replace entries during `readlink`,
`rename`, `stat`, `open`, or `flock`; inode/descriptor identity assertions;
foreign quarantine-entry preservation; FIFO lock attacks; and manual-recovery
protocols needed only by these cases. Locks, staging markers, rollback, and
malformed-layout validation are initially mixed: state the serial functional
case before deciding each one.

## Initial candidate inventory

| Area | High-confidence adversarial candidates | Mixed candidates retained for later decision |
| --- | --- | --- |
| Tests | Auggie hostile-replacement/quarantine tests at `7494-8035`; Auggie replacement/lifecycle tests at `8610-9064`; advisory-lock replacement/FIFO tests at `4388` and `9933`. | Ctrl+C recovery, staging, ordinary lock waits, and ordinary malformed-layout cases. |
| `augment.py` | `directory_binding_problem`, `directory_at_binding_problem`, `ScopeState.verify_bindings`, source-child identity checks, and removal-quarantine helpers. | Normal link ownership, registration reconciliation, and simple interruption recovery. |
| `layout.py` | Descriptor-identity and no-follow behavior for inspection/discovery locks. | A small advisory lock, ordinary lock-file errors, and read-only discovery behavior. |
| Documentation | Transactional guide, attacker/race claims, quarantine recovery, and safe-lock detail. | Normal recovery and layout-repair instructions. |

Later plans must refresh this inventory against the live implementation and
remove only a candidate's adversarial portion when it also serves a serial
functional purpose.

## Documentation design

### Durable policy

Add a concise posture rule to `AGENTS.md`: this is a trusted local CLI, not a
security boundary; preserve functional reliability, use best-effort
concurrency, and do not add adversarial filesystem hardening. Direct agents to
a new authoritative `docs/guides/local-cli-reliability.md`.

The replacement guide defines this classification boundary, allowed reliability
practices, excluded hardening, and a short reviewer checklist. Delete
`docs/guides/transactional-cli-safety.md` rather than renaming it, then update
live specifications and plans that make it a binding constraint. Retain only
their still-applicable functional decisions.

### README audit

Audit `README.md` for security guarantees and discarded protocol detail. Initial
candidates include concurrent-command and lock promises; safe-lock/no-follow
language; full-lifetime delegated locks; quarantine-specific recovery; doctor
inspection security constraints; and atomicity/rollback language that exceeds
the retained contract. Remove or rewrite high-confidence material. Retain
concise instructions for normal recovery, layout repair, and supported
workflows. Any remaining lock language must state best effort.

### Review handoff retirement

The pre-simplification review's useful functional findings are captured in this
specification and the local reliability guide. Both review handoffs and their
index entries are removed at closure; the replacement policy and completion
evidence are the durable record.

## Expected file boundaries

| Area | Responsibility |
| --- | --- |
| `AGENTS.md` | Brief project posture and replacement-guide reference. |
| `docs/guides/local-cli-reliability.md` | Long-lived implementation and review guidance. |
| `docs/guides/transactional-cli-safety.md` | Delete after redirecting live references. |
| `README.md` | Supported behavior without obsolete security guarantees. |
| `docs/specs/`, `docs/plans/` | Remove or qualify transactional-safety references. |
| `tests/test_skillset.py` | Remove adversarial fault fixtures/cases; retain functional black-box coverage. |
| `lib/skillset/augment.py` | Simplify identity, quarantine, and hostile-replacement logic. |
| `lib/skillset/layout.py` | Simplify lock/descriptor hardening and decide any simple locking. |
| `claude.py`, `metadata.py`, `operations.py`, `delegate.py` | Review only classified hardening; retain normal workflows. |
| Handoff and index | Delete only at final closure after durable information is captured. |

## Iterative delivery

### Pass 1: policy and documentation

1. Add the posture and reliability guide.
2. Delete the transactional-safety guide and update live references.
3. Rewrite high-confidence security-oriented README statements.
4. Keep the review handoff unchanged for now.
5. Verify links and terminology.

### Pass 2: high-confidence adversarial tests

1. Inventory tests, fault patches, assertions, and helpers.
2. Batch-remove hostile replacement, descriptor identity, quarantine attack,
   FIFO attack, and syscall-timing cases with no functional purpose.
3. Retain normal results, ordinary invalid inputs, and I/O/Ctrl+C recovery that
   avoids loss or unusable layout.
4. Run focused groups, then the full suite; classify any failure before code
   changes.

### Pass 3: corresponding code

1. Remove code made unnecessary by the approved test removals.
2. Prefer straightforward `pathlib`, `os`, and `shutil` operations with
   ordinary errors and bounded recovery.
3. Remove specialized errors/diagnostics that exist only for adversarial state.
4. Confirm no FFI, syscall binding, or non-standard dependency is introduced.
5. Run focused tests, full suite, and syntax checks.

### Later passes: mixed cases

For each remaining lock, staging, rollback, or validation mechanism: state its
serial failure case, identify its adversarial rationale, retain the smallest
functional behavior, remove adversarial assertions, update documentation, and
verify narrowly and globally. Stop every approved item at a review checkpoint;
do not broaden a mixed-case change into general refactoring without approval.

#### Approved initialization-recovery classification

The next narrow batch covers initialization rollback with a configured external
skillsets directory. It retains `lib/skillset/operations.py` unchanged:
ordinary `OSError` and Ctrl+C failures must roll back managed aliases, restore
the original skills and lock content where possible, and report exact paths
when recovery is incomplete. Stale staging paths and malformed configured
layouts remain normal serial diagnostics and must not be overwritten.

Remove only the dedicated concurrent-mutation test contracts in
`tests/test_skillset.py`:

- `test_configured_init_preserves_a_set_created_after_preflight`
- `test_configured_init_preserves_a_link_and_set_created_after_preflight`
- `test_configured_init_rollback_never_traverses_a_replaced_link`
- `test_configured_init_refuses_a_link_replaced_after_creation`
- `test_configured_init_refuses_a_link_replaced_during_alias_creation`

They inject a second actor that creates a target or replaces the configured
`skillsets` link between operations. That behavior is outside the best-effort
concurrency contract. Retain tests for ordinary configured initialization,
pre-existing collisions, ordinary rollback, Ctrl+C recovery, incomplete
rollback diagnostics, stale staging, and malformed configured layouts.

#### Approved activation and active-rename recovery classification

Activation and active-rename recovery remain functional reliability; this
classification makes no code or test changes. For activation, the
`.skillset-use.staging` JSON record is written before aliases change, so
`doctor --fix` can complete an interrupted activation. Retain structural
validation of that activation record, stale-record refusal, alias target
checks, and clear recovery diagnostics: together they prevent an ordinary
failure or Ctrl+C from silently leaving an unusable managed layout.

For an active rename, the same pathname is instead a transient symlink made
after the set directory moves and atomically replaced into `active`; inline
`recover_active_rename()` recovery, not `doctor --fix`, handles errors in that
flow. Retain stale-staging refusal, rollback, committed-layout detection,
cleanup, and incomplete-recovery diagnostics. They preserve the renamed set or
restore the original layout after an ordinary `OSError` or Ctrl+C; when rollback
cannot complete, they identify the remaining set paths rather than risking data
loss. The corresponding tests exercise these ordinary failure and interruption
contracts, not a second actor replacing paths during the operation.

The simple canonical-alias checks in these flows also observe current link
state, but no separate attacker-timing protocol or dedicated concurrent-
mutation test remains in these areas. Their bounded serial state-validation
role is retained. Do not remove or expand these mechanisms without a future
candidate inventory that identifies a separable adversarial-only portion.

#### Approved Claude descriptor-binding simplification

Remove Claude Code's descriptor/public-path identity protocol and its dedicated
replacement-race tests. This includes `directory_binding_problem()`,
`ScopeState.verify_bindings()`, repeated `fstat()` inode comparisons after
opening scope containers, the source `lstat()`/`fstat()` identity comparison,
and per-source-child inode revalidation. These checks detect a directory or
source child replaced between operations, which is outside the best-effort
concurrency contract.

Delete only the corresponding tests:
`test_claude_enable_revalidates_public_directory_bindings`,
`test_claude_disable_revalidates_public_directory_bindings`, and
`test_claude_disable_detects_initially_absent_containers_appearing`. They
inject a second actor that moves and recreates scope directories or creates an
initially absent container during final verification.

Retain normal preflight container and collision validation, fd-relative link
operations, source inventory and ordinary I/O errors, idempotent enable and
disable, and Ctrl+C recovery. Keep `_identity()` solely for `same_directory()`,
which compares configured global and local scope roots in normal serial setup.
This batch does not change Claude's `O_NOFOLLOW` flags or broader symlink
validation; their retained serial contract is classified below.

#### Approved Claude collision and symlink-validation classification

Claude's normal serial enable behavior retains its pre-mutation global/local
scope collision check. Remove the later post-synchronization collision recheck
and `test_claude_enable_rechecks_opposite_scope_created_during_sync`: both
exist only to detect a second actor creating a conflicting entry after
preflight, which is outside the best-effort concurrency contract. Retain the
preflight collision test and the existing recovery diagnostic for an ordinary
operation failure after the command has begun.

Keep `DIRECTORY_FLAGS`, including `O_DIRECTORY | O_NOFOLLOW`, along with
non-following metadata inspection, real-container validation, source-symlink
refusal, and exact canonical-link validation. In normal serial use these
checks reject malformed Claude containers, avoid projecting an indirect source
entry, and preserve ownership/collision decisions before mutation. They do not
promise to detect a path replacement after validation or establish a hostile
process security boundary. No code or test change is approved for these
retained safeguards in this classification.

#### Approved skill-metadata no-follow simplification

Keep the static `lstat()` validation that rejects direct skill-directory
symlinks, `SKILL.md` symlinks, and non-regular `SKILL.md` entries. It preserves
the documented serial malformed-layout behavior used by `show`, verbose list
output, and `doctor`. In `metadata.read_skill_text()`, remove `O_NOFOLLOW`
from the subsequent directory and `SKILL.md` opens: each only prevents a
replacement after the retained validation, which is outside the best-effort
concurrency contract. Retain the existing ordinary-I/O diagnostics, UTF-8
handling, descriptor cleanup, and static-symlink tests. Do not add race or
syscall fault-injection coverage for the removed behavior.

#### Approved configured-remove confirmation simplification

`remove()` validates the managed layout and selected set before asking for
confirmation. Remove its later `validate_skillsets_directory()` call after an
affirmative response, along with
`test_configured_remove_refuses_a_replaced_managed_link_after_confirmation`.
That call and test require refusal when another actor replaces the configured
`skillsets` link while standard input waits for confirmation, which is outside
the best-effort concurrency contract.

Retain all pre-prompt name, layout, target-set, active-set, and enabled-lifecycle
validation; the advisory lock held across confirmation; and direct deletion
error reporting. Keep ordinary declined-confirmation, invalid-target, and
normal external-link-preservation coverage. Do not add another post-prompt
replacement or timing protocol.

#### Approved manual-sentinel permission simplification

The shared manual empty-lock sentinel remains a real regular file containing
the canonical empty-lock JSON and must remain non-writable. Continue creating
or repairing a missing sentinel with mode `0444`, but do not require every
existing valid sentinel to have that exact mode. `validate_manual_sentinel()`
must instead reject only modes containing owner, group, or other write bits.
This preserves the documented read-only serial invariant while accepting
ordinary non-writable local permission variations such as `0400` or `0440`.

Retain the active manual-mode lock alias, activation and doctor recovery,
canonical-content validation, real-file validation, and ordinary I/O errors.
Do not remove permission validation entirely, relax a writable sentinel, or
add a concurrency/replacement protocol. Focused coverage must show that a
canonical non-writable sentinel remains usable, a writable one is refused, and
newly created or repaired sentinels still use `0444`.

#### Final residual inventory classification

The final live inventory found no further adversarial-only mechanism suitable
for removal. Retain static symlink and canonical-link validation, advisory
locks, and the `O_NOFOLLOW` directory/lock opens: in normal serial use they
reject malformed managed layouts, keep operations scoped to the configured
containers, and provide simple best-effort coordination. `_identity()` remains
only for normal global/local scope-root comparison.

Retain the interrupted scope-directory diagnostic in Auggie and Claude Code.
After `mkdir()` is interrupted, it identifies whether the directory exists so
the command can name recovery paths and a later enable can safely recover. It
does not revalidate a path after a successful operation or promise detection
of a concurrent replacement. The apparent duplicate `operation_lock()` kind
check is also retained: when creating a lock it produces a clear ordinary
malformed-layout error rather than silently opening an unsuitable entry.

## Error and recovery semantics

Continue to report invalid input and ordinary I/O errors without silently
overwriting unrelated data in normal serial use. Keep a simple staging,
rollback, or diagnostic mechanism only when it materially improves ordinary
recovery. A concurrently replaced path need not be detected or recovered: the
CLI may report the direct operational error and leave the resulting filesystem
state visible. It must not create permanent quarantine state solely for that
race.

## Verification

For each implementation batch:

1. Run focused black-box tests for the changed command or recovery path.
2. Run `python -m unittest discover -s tests`.
3. Run `python -m compileall -q bin lib tests` after Python changes.
4. Check completion syntax if completion generation changes.
5. Inspect the diff and search changed implementation/tests for `ctypes`,
   `renameat`, `renameat2`, and `RENAME_NOREPLACE`; expect no references.
6. Independently review mixed cases against this policy, not generic security
   hardening.

For documentation-only work, verify internal links and ensure the README makes
no unsupported concurrency or threat-model promise.

## Rejected alternatives

- **Only `AGENTS.md`:** too brief to reliably distinguish ordinary reliability
  from adversarial hardening.
- **Rewrite and retain transactional safety:** its framing caused the unwanted
  review behavior and would preserve ambiguous legacy guidance.
- **Remove all recovery, staging, and locks:** rejected because serial
  functional consistency and ordinary recovery remain requirements.
- **Retain the Auggie handoff indefinitely:** rejected because it is temporary
  workstream state and an obsolete review posture source.

## Completion criteria

- `AGENTS.md` and the replacement guide express the agreed local posture.
- Transactional-security guidance and live references are removed.
- README language reflects functional reliability and best-effort concurrency.
- High-confidence adversarial tests and supporting code are gone.
- Mixed cases have explicit, reviewed functional justifications.
- No `ctypes`, `renameat2`, or similar platform-specific filesystem binding is
  in the implementation.
- Normal serial behavior and proportionate recovery remain covered and pass.
- The Auggie review handoff and index entry are removed after durable knowledge
  is harvested, with no live references remaining.

## Closure record

- The final fresh inventory classified all remaining examined filesystem
  mechanisms as functional reliability or proportionate best-effort
  coordination; no additional removal plan is warranted.
- The latest published batch passed its focused tests, compilation, forbidden
  binding search, full test suite (227 tests), and task/final reviews.
- The short-lived reliability and historical-review handoffs, together with
  their index entries, are removed at this checkpoint. The source prompt is
  also removed after its durable requirements were captured here.