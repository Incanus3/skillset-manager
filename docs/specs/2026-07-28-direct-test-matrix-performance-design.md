# Direct-Test Matrix Optimization

## Decision

Use direct Python tests for high-cardinality parser and validation matrices
when the contract does not require the executable process. Keep a small
subprocess set for parser usage and exit formatting, command routing, and
read-only command boundaries.

## Scope

The completed delivery covers malformed parser arguments, invalid skillset
names, and inspection of uninitialized or structurally invalid layouts. Direct
tests exercise `parser()`, `validate_name()`, and `validate_layout()`;
subprocess tests retain the corresponding wrapper contracts.

## Constraints

- Do not change CLI behavior or filesystem semantics for a test-only speedup.
- Preserve subprocess coverage for executable startup, streams and exits, TTY,
  signals, delegation, locks, interruption, and recovery.
- Follow `docs/guides/local-cli-reliability.md` for filesystem-facing tests.
- Treat timing as local comparative evidence, never as an acceptance target.

## Durable outcome

The direct matrices preserve their complete input sets while representative
subprocess checks prove the user-facing executable boundaries. Future direct
conversions require the same contract-based classification; they must not be
chosen solely because a test is slow.

## References

- `docs/guides/test-suite-performance.md`
- `docs/guides/local-cli-reliability.md`
