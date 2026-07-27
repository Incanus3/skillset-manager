# Completion-Probe Batching

## Decision

Batch completion probes within one Fish or interactive Zsh process rather than
starting a fresh shell for every query. Preserve one real CLI-and-shell dynamic
name lookup for each shell.

## Design

The tests use a deterministic lookup stub for static completion cases and a
framed protocol that keeps individual assertions distinguishable. Zsh resets
its prompt state between probes; Fish consumes framed output from a shared
session.

## Constraints

- Preserve native-shell syntax and behavioral coverage.
- Preserve the real dynamic-name executable probe for Fish and Zsh.
- Do not treat local timing as an acceptance target.

## Durable outcome

The batching removes repetitive shell startup while retaining the boundaries
that only real shells can prove.

## References

- `docs/guides/test-suite-performance.md`
