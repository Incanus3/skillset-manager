# In-Process CLI Helper Implementation Record

## Completed changes

- Added the explicit `run_cli_in_process()` test helper with process-global
  state restoration.
- Migrated audited ordinary lifecycle, `doctor`, Codex, Claude, Augment, and
  nested discovery coverage without changing assertions or production code.
- Retained executable representatives and all prompt, TTY, shell, delegation,
  stream, exit, signal, lock, fault-injection, interruption, recovery, and
  fresh-interpreter tests as subprocess coverage.
- Classified every audited `skills` call as a subprocess boundary.

## Verification

The final selection audit accounts for 312 remaining-area tuples: 164 use the
in-process helper and 148 are retained representatives or boundaries. The
normal suite passed 234 tests. A completed traced suite recorded 497 direct
child-process creations; commands, host context, and measurement caveats are
in `docs/guides/test-suite-performance.md`.

## Maintenance rule

Classify each invocation by its asserted contract, not by command family or
runtime cost. Future conversions require an ordinary-behavior rationale and a
retained executable or process-boundary representative where applicable.

## References

- `docs/specs/2026-07-28-in-process-cli-helper-design.md`
- `docs/plans/2026-07-29-in-process-cli-helper-audit.md`
- `docs/guides/in-process-cli-test-selection.md`
