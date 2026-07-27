# Lazy Command Imports Implementation Record

## Completed changes

- Deferred command-module imports until parser dispatch selects a command.
- Preserved parser, help, completion, lifecycle, and lock-routing behavior.
- Added regression coverage for the lazy import boundary.

## Verification

Fresh-process measurements recorded lower `skillset.cli` import and `list`
startup costs, with mixed help and completion results. The exact samples and
their caveats are retained in `docs/guides/test-suite-performance.md`; the
normal suite passed after the change.

## Maintenance rule

Keep command imports on their dispatch path unless parser construction or help
generation genuinely needs the implementation. Treat new eager imports as a
startup regression risk.
