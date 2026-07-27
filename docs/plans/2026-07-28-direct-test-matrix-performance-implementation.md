# Direct-Test Matrix Optimization Implementation Record

## Completed changes

- Replaced exhaustive subprocess parser-error checks with direct parser
  coverage while retaining executable usage and exit representatives.
- Replaced exhaustive invalid-name subprocess checks with direct
  `validate_name()` coverage while retaining command-routing representatives.
- Replaced exhaustive unhealthy-layout subprocess checks with direct
  `validate_layout()` coverage while retaining inspection-command refusal and
  read-only representatives.

## Verification

The focused three-method benchmark passed all runs with a median reduction of
76.50 percent. The normal suite also passed; completed timing and host context
are recorded in `docs/guides/test-suite-performance.md`.

## Maintenance rule

Keep direct tests for pure parser or validator contracts. Keep a subprocess
test when the assertion observes executable launch, process streams or exits,
environment, TTY, shell, delegation, locks, interruption, or recovery.
