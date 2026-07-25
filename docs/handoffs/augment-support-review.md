# Augment Support Review Handoff

**Status:** four review findings open — implementation and re-review required before merge authorization
**Updated:** 2026-07-26
**Resume:** `$resume augment-support-review`

## Objective

Record the resolved safety, completion, documentation, and tracking findings
from the `augment-support` branch review and its verification evidence before
the Auggie feature is merged.

## Durable references

- Follow-up issue: `agents-lgj` — closed after all validated findings were
  resolved; the `.bv/` exception was accepted.
- Feature design: `docs/specs/2026-07-24-auggie-skillset-discovery-design.md`.
- Output designs:
  `docs/specs/2026-07-25-resolved-auggie-skill-paths-design.md`,
  `docs/specs/2026-07-25-auggie-skills-resolved-path-ordering-design.md`, and
  `docs/specs/2026-07-25-auggie-skills-table-output-design.md`.
- Filesystem-safety guidance: `docs/guides/transactional-cli-safety.md`.
- Review base: `main...augment-support`; `master` does not exist in this
  repository.
- Current review findings and verification are recorded in this handoff. Read
  the full feature design and transactional safety guide before editing.

## Completed checkpoint

- Read the Auggie design and implementation documents, then reviewed the full
  branch with four independent read-only review passes.
- Ran `python -m unittest discover -s tests`: 242 tests passed.
- Generated Bash, Zsh, and Fish completions passed syntax checks; `git diff
  --check main...augment-support` passed.
- **Issue 1 resolved:** managed link deletion uses a private, mode-700,
  UUID-named `.augment/.skillset-removal-*` quarantine. It atomically moves the
  candidate link, verifies the staged canonical link, then deletes it and
  removes only the identity-verified empty marker. A changed or interrupted
  staged entry remains in place for manual recovery; later managed and lifecycle
  commands refuse markers without mutation. The later P2 finding records the
  remaining recovery-message gaps. The suite now passes 250 tests.
- Quarantine creation records the `mkdir` identity and compares it with the
  opened descriptor. Cleanup revalidates the still-open descriptor against its
  parent name. Tests cover replacement during creation and cleanup, source-link
  replacement before staging, an interrupt after staging, and an open failure
  after creation (which removes only the verified empty quarantine).
- Final removal of a staged link and removal of an empty private quarantine
  necessarily retain a portable POSIX name-based interval: Python/POSIX provides
  neither remove-by-inode nor compare-and-remove. The mode-700 random quarantine
  isolates other users; exploitation requires a hostile same-UID actor able to
  alter the owner's `.augment` namespace. Closing that interval requires an
  expanded threat model and platform-specific primitives or a preserve-only
  deletion policy that leaves empty markers to block further mutation.
- **Issue 2 resolved:** lifecycle orphan detection now inspects `skills`
  relative to the accepted `.augment` descriptor, compares the inspected child
  and opened descriptor identities, and validates both public bindings before
  and after inventory. Missing-child handling rechecks the child and validates
  the parent again before allowing lifecycle mutation. Fault-injection tests
  cover public child replacement before open and during inventory, parent
  replacement at both relevant boundaries, and orphan creation after a missing
  lookup. The suite now passes 255 tests.
- **Issue 3 resolved:** the generated Zsh completion now offers `-h` and
  `--help` at both `augment` and `augment skills` group levels. The existing
  pseudo-terminal behavior test verifies `--h` completion at both levels; the
  generated Zsh script passes syntax validation.
- **Issue 4 resolved:** Bash, Fish, and pseudo-terminal Zsh tests now cover
  scoped Auggie enable/disable name completion plus `--verbose`, `--global`,
  and `--local` completion for the managed list. The Zsh fixture now creates
  managed names and exposes the repository `skillset` command on `PATH`.
  Coverage exposed that nested `_arguments` could not reliably complete both
  options and names. Auggie enable/disable/list now use explicit `_describe`
  candidate lists, suppress conflicting flags, honor `--`, and dynamically
  list skillsets before a name is supplied. Do not reintroduce nested
  `_arguments` there without behavior coverage for both scoped names and
  partial flags. Full suite: 255 passing tests; Bash/Zsh/Fish syntax checks
  and `git diff --check` pass.
- **Important review recovery resolved:** `create_removal_quarantine()` now
  checks whether its generated marker exists after a `mkdir` interrupt or
  `OSError`. An ambiguous marker is never removed; interruption and recovery
  output name its exact path. Fault-injection coverage distinguishes both
  boundaries: it calls real `mkdir` then raises `KeyboardInterrupt` or `OSError`
  to assert preserved-marker recovery, and raises before `mkdir` to assert no
  marker, an unchanged projection target, and an unblocked later operation.
  Focused quarantine regressions pass;
  full suite: 257 passing tests; all shell syntax checks and `git diff --check`
  pass.
- **Earlier final independent review:** the pre-`mkdir` target-identity review
  found no remaining findings within that narrow assertion. Its conclusion is
  superseded by the later whole-branch review below, which found additional
  interruption and advisory-lock edge cases.
- **Latest whole-branch review (2026-07-26):** read all current Auggie design,
  plan, and handoff documents, then used four independent read-only passes for
  transaction safety, discovery, CLI/completions, and test/scope coverage.
  `python -m unittest discover -s tests` passed 257 tests. Generated Bash and
  Zsh completion scripts and Fish syntax validation passed. No `TODO`, `FIXME`,
  `XXX`, or `HACK` marker was found in changed implementation or test files.
  The review found the unresolved items listed below; existing tests do not
  cover their edge cases.
- **Preserved-quarantine recovery repair (2026-07-26):** introduced a typed
  `ManualRecoveryError` for non-interrupt failures and a dedicated interrupted
  diagnostic for exit-130 paths. Every known preserved removal quarantine now
  names its exact path and says manual recovery is required; generic rerun
  guidance remains limited to states with no preserved marker. The README now
  distinguishes the two recovery modes. New fault-injection coverage exercises
  interrupts from the first post-`mkdir` `stat` and `open`, and strengthens the
  post-move interruption assertion. Eight focused quarantine tests and the full
  suite pass; latest full result: 258 tests. A separate read-only review of this
  repair found no findings.
- **FIFO advisory-lock repair (2026-07-26):** discovery now opens the optional
  `.skillset.lock` candidate with `O_NONBLOCK` as well as `O_NOFOLLOW`, then
  retains the existing descriptor-relative regular-file validation before
  `flock`. A FIFO therefore falls back safely rather than hanging, while valid
  regular lock behavior remains unchanged. The new black-box test creates a
  real FIFO and fails on timeout before the implementation change. Its focused
  lock tests pass, the full suite now passes 259 tests, and focused read-only
  review found no substantiated finding.
- **Zsh option-terminator completion repair (2026-07-26):** the generated
  enable/disable completer now suppresses option candidates only after `--` and
  continues to its existing positional skillset-name completion. PTY cases cover
  both enable and disable after the terminator, require the managed name, and
  reject help/global/local option candidates. The focused Zsh test and the full
  suite pass; latest full result remains 259 tests. Focused review initially
  identified the missing option-suppression assertions; those assertions were
  added and verified.
- **Discovery scope-completion coverage (2026-07-26):** added Bash and Zsh
  behavior coverage for partial `--global` and `--local` completion under
  `augment skills list`. The Zsh PTY test also proves that a selected global
  scope suppresses a local candidate. The focused completion tests and full
  suite pass; latest full result remains 259 tests. Focused review found no
  finding and confirmed the assertions do not confuse echoed partial input with
  a completed option.
- **Discovery lock documentation repair (2026-07-26):** the README now scopes
  complete-layout validation to managed inspection and identifies `augment
  skills list` as a distinct read-only view that neither requires nor validates
  the managed layout. It documents opportunistic use of a safe existing managed
  lock, matching the design and implementation. No runtime behavior changed.
- **Final tracking closure (2026-07-26):** `agents-lgj` now records the accepted
  `.bv/` exception, links this handoff as evidence, and is closed with the same
  rationale. No unresolved review finding remains. The latest full suite result
  is 259 passing tests; no merge, push, or external review state changed.
- **Latest independent whole-branch review (2026-07-26; supersedes the prior
  readiness conclusion):** reviewed all Auggie designs, implementation plans,
  this handoff, and `docs/guides/transactional-cli-safety.md`; then performed
  independent transaction-safety, discovery, CLI/completions, and test/scope
  passes. Five new substantiated findings remain open, listed below. The full
  suite still passes 259 tests; Bash, Zsh, and Fish generated-completion syntax
  checks and `git diff --check main...augment-support` pass. These results prove
  no existing regression but do not cover the newly identified fault boundaries.
- The review range is `main...augment-support`; `master` does not exist. The
  separate `update-global-rules` stack and the accepted `.bv/` ignore exception
  are not Auggie findings. No `TODO`, `FIXME`, `XXX`, or `HACK` marker was found
  in changed Auggie implementation or test files.
- **P1 staging repair (2026-07-26):** `unlink_link()` now moves a managed link
  through a small `ctypes` binding to Linux `renameat2` with
  `RENAME_NOREPLACE`, rather than replacement-capable `os.rename()`. An occupied
  quarantine `entry` leaves the public link and foreign entry intact; the
  existing error path preserves the quarantine and reports its exact path for
  manual recovery. Focused regression coverage creates both foreign regular
  files and symlinks immediately after quarantine creation. Existing
  replacement/interruption tests now hook the no-replace wrapper or the correct
  quarantine-creation boundary, retaining their prior safety assertions. The
  focused four-test transaction group and full suite pass (260 tests);
  `py_compile` and `git diff --check` pass. Finding 15 is resolved; findings
  16–19 remain open.

## Validated findings and current open items

1. **P1 — resolved — destructive link deletion race.**
   `lib/skillset/augment.py:83-106` verifies a link, while `unlink_link()` at
   `474-491` later deletes it. The stale-reconciliation and disable callers at
   `704-715` and `801-825` can unlink an unrelated replacement made after the
   check. The quarantine transaction now makes public-link replacement atomic
   and preserves any noncanonical staged entry for manual recovery. It also
   validates quarantine creation and cleanup identities; see the POSIX caveat
   above for the remaining same-UID final-unlink limitation.
2. **P2 — resolved — orphaned-projection lifecycle race.**
   `orphaned_projection_blocker()` at `976-996` inventories an opened skills
   directory without validating its binding before an unblocked result. The
   callers at `1038-1041`, `1050-1053`, and `1067-1068` can miss a replacement
   directory and allow rename/remove to leave stale links. The blocker now uses
   descriptor-relative inspection and fails closed on changed parent or child
   bindings, including child creation after an initial negative lookup.
3. **P2 — resolved — Zsh completion misses group-level help.**
   `lib/skillset/completions.py:266-272` and `287-290` offer only subcommands.
   Real pseudo-terminal reproduction showed `skillset augment --h` has no
   `--help` candidate. Both groups now offer standard help aliases with
   pseudo-terminal coverage for `--h` completion.
4. **P3 — resolved — completion coverage is incomplete.**
   Behavioral coverage now exercises Auggie enable/disable names after scope,
   partial scope flags, and all managed-list flags across Bash, Fish, and Zsh.
   The Zsh implementation now uses an explicit completer for managed commands
   because nested `_arguments` parsing could not reliably handle both cases.
5. **P3 — resolved — README terminology conflicts.**
   The discovery precedence table now calls `User/...` and `Workspace/...`
   values “Precedence root” and their filesystem entries “Skill root”, avoiding
   conflict with the concise labels rendered in the `SOURCE` column.
6. **P3 — accepted scope exception — `.bv/` ignore rule.**
   `.gitignore:21-22` is unrelated to Auggie and has no repository usage, but
   the operator explicitly chose to retain the Beads Viewer local-config and
   cache ignore rule rather than remove or split it. Do not treat it as an
   Auggie behavior change.
7. **Important review item — accepted residual cleanup interval.**
   Empty-quarantine `rmdir` has the same descriptor-check to name-removal
   interval as the staged-link `unlink`. The operator accepted the documented
   mode-700, hostile-same-UID residual threat model rather than a preserve-only
   design that would leave empty markers blocking all later managed operations.
8. **Important review item — resolved — ambiguous post-`mkdir` marker.**
   An interrupt or `OSError` raised after `mkdir` created a private removal
   quarantine left the marker blocking future mutation without reporting its
   path. Creation now preserves and reports an existing generated marker, while
   a pre-creation-failure regression proves definite failures leave no marker
   and retain the original projection target plus unblocked behavior.
9. **P2 — resolved — preserved quarantine gives usable recovery advice.**
   `unlink_link()` at `lib/skillset/augment.py:665-679` preserves a moved link
   in `<quarantine>/entry` after an interrupt, but `_interrupted()` routes it to
   `_recovery_message()` at `485-499`, which tells the operator to rerun the
   same command. A later command refuses the preserved quarantine at `139-150`,
   so rerunning cannot recover it. `ManualRecoveryError` now bypasses generic
   rerun wrapping for preserved markers, while a dedicated `ClaudeInterrupted`
   message retains exit 130 for interrupts. `create_removal_quarantine()` now
   handles post-`mkdir` `stat`, `open`, and descriptor-verification interruptions
   as preserved markers. The focused tests assert the exact path, manual-recovery
   wording, absence of rerun advice, later no-mutation blocking, and exit 130.
10. **P2 — resolved — FIFO advisory lock no longer hangs read-only discovery.**
    `discovery_operation_lock()` opens `.skillset.lock` with `O_RDONLY |
    O_NOFOLLOW` at `lib/skillset/layout.py:351-353` before its regular-file
    check at `359`. A FIFO at that path blocks the open until a writer connects,
    so `skillset augment skills list` never reaches its malformed-lock fallback.
    The open now includes `O_NONBLOCK`, then uses the existing `fstat` check to
    reject the FIFO before attempting `flock`. The new timeout-based black-box
    test confirms successful output, unchanged filesystem state, and preservation
    of the FIFO lock path.
11. **P3 — resolved — Zsh completes names after an option terminator.**
    The parser accepts `skillset augment enable -- NAME` and `disable -- NAME`,
    but `lib/skillset/completions.py:276-298` immediately returns when `--` is
    present. The generator now avoids option construction after the terminator
    but still offers the first required skillset name. Pseudo-terminal coverage
    tests both commands and confirms options are absent.
12. **P3 — resolved — discovery scope flags have Bash/Zsh behavior coverage.**
    Bash and Zsh now test partial `--global` and `--local` completion for
    `augment skills list`; the Zsh PTY test additionally rejects `--local`
    after `--global`.
13. **P3 — resolved documentation inconsistency.** `README.md:221-226`
    says routine inspection validates the complete managed layout. The new
    `augment skills list` deliberately works without one and only
    opportunistically uses a safe existing lock. The README now limits the
    general claim to managed inspection and explicitly documents this exception.
14. **P3 — resolved tracking inconsistency.** `agents-lgj` now states that all
    validated findings are resolved, retains `.bv/` by accepted scope decision,
    and is closed with that rationale.
15. **P1 — resolved — quarantine staging could overwrite unrelated data.**
    `unlink_link()` moves an owned link to the fixed `entry` name with
    `os.rename()` (`lib/skillset/augment.py:695-711` before repair), which could
    replace a foreign file or symlink created by a hostile same-UID actor after
    private quarantine creation. Staging now uses `renameat2` with
    `RENAME_NOREPLACE`; an occupied `entry` is preserved, the public managed
    link remains untouched, and the command gives path-specific manual-recovery
    guidance. `test_augment_preserves_foreign_quarantine_entries_during_staging`
    covers both file and symlink destinations.
16. **P2 — open — a changed quarantine binding is reported as rerunnable.**
    If `directory_at_binding_problem()` detects that the quarantine changed
    after its creation, `lib/skillset/augment.py:701-705` raises a normal
    `OperationalError`. The changed path remains a marker that blocks every
    later Auggie operation, while the outer `enable`/`disable` error wrappers
    (`1039-1053`, `1129-1132`) advise rerunning. Raise `ManualRecoveryError`
    containing the exact quarantine path instead, and add a replacement-before-
    binding test requiring manual-recovery—not rerun—guidance.
17. **P2 — open — post-unlink and cleanup interruptions can strand unreported
    markers.** `os.unlink(REMOVAL_ENTRY)` may complete then raise; the absent-
    entry `OSError` path at `lib/skillset/augment.py:757-770` leaves an empty
    quarantine and returns generic rerun advice. The cleanup helpers at
    `641-674` also do not distinguish `KeyboardInterrupt` before versus after
    `rmdir`, so an existing marker can reach the generic unnamed interruption
    handler. Recheck and safely remove an empty quarantine after a committed
    unlink, or preserve it with its exact path and manual-recovery guidance.
    Add pre- and post-syscall fault injection for both unlink and rmdir.
18. **P2 — open — global lifecycle blocking has an initial `.augment` identity
    gap.** `global_registration_blocker()` validates the global `.augment`
    directory and later opens it without retaining the first identity
    (`lib/skillset/augment.py:1349-1359`). Replacing the directory in that gap
    with an empty real directory can let rename/remove bypass an existing
    registration in the detached original. Bind the validated identity to the
    opened descriptor, or make inspection descriptor-relative from an accepted
    parent binding; fail closed on mismatch. Add fault-injected rename and
    remove tests for replacement immediately before the open.
19. **P2 — open — discovery does not fall back when advisory-lock acquisition
    fails.** `discovery_operation_lock()` catches missing, malformed, open, and
    fstat failures, but an `OSError` from `fcntl.flock()` at
    `lib/skillset/layout.py:367-374` escapes. On a filesystem that does not
    support advisory locking, read-only discovery fails instead of scanning
    without the optional lock. Catch that acquisition error, yield no lock, and
    preserve descriptor cleanup. Add fault injection that raises from flock and
    proves successful, non-mutating discovery.

## Ordered next actions

1. Before editing, read the full Auggie design, this handoff, and
   `docs/guides/transactional-cli-safety.md`. Preserve the `.augment`-only
   mutation boundary and the accepted final-unlink/rmdir residual threat model.
2. Resolve findings 16 and 17 together as recovery-state work. Cover changed
   quarantine bindings plus pre/post unlink and rmdir failures or interruptions;
   every preserved marker must be named and require manual recovery, while a
   successfully removed marker must not leave blocking state.
3. Resolve finding 18 with descriptor/identity binding and fault-injection
   lifecycle tests for both rename and remove.
4. Resolve finding 19 with an advisory-lock acquisition fallback test and
   minimal implementation change.
5. Run focused new tests, the complete `python -m unittest discover -s tests`
   suite, generated Bash/Zsh/Fish completion syntax checks, and
   `git diff --check main...augment-support`. Request an independent re-review
   of the transaction and lifecycle changes before any merge authorization.
6. Do not merge, push, publish, or otherwise change shared state without
   explicit operator authorization.

## Constraints and environment cautions

- Managed commands may mutate only `.augment`; compatible `.claude/skills` and
  `.agents/skills` roots remain read-only external inputs.
- Preserve the existing no-dependency, standard-library Python implementation
  and the flat, direct-child projection model.
- This is a GitButler workspace: use `but` for version-control actions. The
  requested `jj diff -f master` could not run because `master` is absent; use
  the documented `main...augment-support` review base instead. Do not use
  Jujutsu unless the operator explicitly directs it.
- `update-global-rules` is a separate stacked branch. Do not attribute its
  general `AGENTS.md` changes to Auggie behavior during the next review pass.
