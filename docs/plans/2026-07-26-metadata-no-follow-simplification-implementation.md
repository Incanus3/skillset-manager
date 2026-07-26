# Metadata No-Follow Simplification Implementation Plan

> **For agentic workers:** Use `subagent-driven-development` or
> `executing-plans` one task at a time. Steps use checkbox syntax for tracking.
> Stop after the task for independent review.

> **Status:** Completed — retained as a historical implementation plan. The
> durable policy and completion record are in
> `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md` and
> `docs/guides/local-cli-reliability.md`.

**Goal:** Remove the post-validation no-follow guards from skill metadata reads
while retaining normal serial rejection of malformed skill directories and
`SKILL.md` symlinks.

**Architecture:** `inspect_skill_entry()` continues to reject a direct
skill-directory symlink using `lstat()`, and `read_skill_text()` continues to
inspect `SKILL.md` without following it before opening it. Simplify only the
subsequent descriptor opens: replacement after those checks is outside the
best-effort concurrency contract, while static malformed-layout behavior and
ordinary I/O diagnostics remain unchanged.

**Tech Stack:** Python standard library, `unittest`, GitButler workspace.

## Global Constraints

- Read `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md`
  and `docs/guides/local-cli-reliability.md` in full before editing.
- Retain static `lstat()` checks, direct-symlink rejection, non-regular-file
  rejection, UTF-8 validation, ordinary-I/O results, and descriptor cleanup.
- Remove only the two `O_NOFOLLOW` values in `metadata.read_skill_text()`;
  retain `O_RDONLY` and `O_DIRECTORY` for the directory open.
- Do not add race, replacement, or syscall fault-injection tests.
- Do not modify `layout.py`, integration modules, staging, or rollback.
- Do not add dependencies, `ctypes`, direct syscall bindings, or `renameat*`.
- Do not commit, push, merge, publish, or delete handoffs without explicit
  operator authorization.

## File Map

- Modify: `lib/skillset/metadata.py` — simplify the two post-validation open
  flags in `read_skill_text(directory)`.
- Test: `tests/test_skillset.py` — retain the existing `doctor` and `show`
  direct-symlink contracts without adding a concurrent-replacement test.
- Reference: `docs/specs/2026-07-26-local-cli-reliability-simplification-design.md`
  and `docs/guides/local-cli-reliability.md` — durable policy and completion
  context; no active handoff remains.

---

### Task 1: Simplify metadata descriptor opens and verify retained behavior

**Files:**
- Modify: `lib/skillset/metadata.py:163-201`
- Test: `tests/test_skillset.py:1861-1902,3942-3972`
- Reference after verification: the durable design and reliability guide above;
  no active handoff remains.

**Interfaces:**
- Consumes: `inspect_skill_entry(candidate)`, which rejects a direct symlink
  before calling `read_skill_text(candidate)`.
- Produces: `read_skill_text(directory) -> tuple[str | None, str | None]` with
  unchanged serial results for missing, symlinked, non-regular, unreadable, and
  invalid-UTF-8 metadata.

- [x] **Step 1: Establish the retained static-symlink baseline**

Run:

````sh
python -m unittest -v \
  tests.test_skillset.SkillsetTests.test_doctor_ignores_regular_skill_entries_and_never_follows_skill_symlinks \
  tests.test_skillset.SkillsetTests.test_show_ignores_regular_files_and_never_follows_direct_skill_symlinks
````

Expected: both tests pass. They prove that static direct skill-directory and
`SKILL.md` symlinks remain uninspected and are reported as invalid.

- [x] **Step 2: Replace only the two post-validation flags**

In `read_skill_text()`, change the local flag assignments exactly to:

````python
directory_flags = os.O_RDONLY | os.O_DIRECTORY
file_flags = os.O_RDONLY
````

Keep the surrounding `os.stat(..., follow_symlinks=False)` check, both
`stat.S_ISLNK` and regular-file checks, every `OSError` return value, and both
`finally` descriptor-close blocks unchanged.

- [x] **Step 3: Re-run the retained focused contracts**

Run the Step 1 command again.

Expected: both tests pass unchanged. Do not add a test that replaces a path
after `lstat()`; that behavior is intentionally outside the supported
concurrency contract.

- [x] **Step 4: Verify the boundary and run regression checks**

Run:

````sh
if rg -n 'O_NOFOLLOW' lib/skillset/metadata.py; then exit 1; fi
rg -n -C 4 'candidate\.lstat|SKILL\.md.*follow_symlinks=False|S_ISLNK' lib/skillset/metadata.py
python -m compileall -q bin lib tests
python -m unittest discover -s tests
if rg -n 'ctypes|renameat|renameat2|RENAME_NOREPLACE' lib tests; then exit 1; fi
````

Expected: the first and final absence checks print nothing and exit `0`; the
middle inspection shows retained static validation; compilation and the full
suite pass. Classify any unexpected failure before changing other behavior.

- [x] **Step 5: Inspect scope, record evidence, and request review**

Run `but diff`.

Expected: apart from this plan, its approved specification update, and active
handoff tracking, source changes are limited to the two flag values in
`lib/skillset/metadata.py`. The completed branch is recorded in the durable
design; no active handoff remains.