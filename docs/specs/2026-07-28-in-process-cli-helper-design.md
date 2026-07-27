# In-Process CLI Test Helper

## Decision

`SkillsetTests.run_cli_in_process()` is an explicit test-only helper for
ordinary isolated command behavior. It invokes `skillset.cli.main()` with
temporary command state and restores process-global state in `finally`.
`run_cli()` remains the subprocess helper; it has no in-process mode.

## Selection rule

Use the in-process helper for deterministic output, normal return status,
ordinary temporary-home filesystem state, validation, and serial transitions.
Keep subprocess coverage whenever the assertion depends on executable launch,
fresh interpreter state, parent stdin, TTY, shell execution, delegation,
inherited streams or environment, signals, locks, fault injection,
interruption, or recovery.

## Completed scope

The completed delivery covered lifecycle commands, `doctor`, Codex, Claude,
Augment, nested `augment skills list`, and `skills`. Ordinary calls migrated
in three reviewed phases. `skills` retained subprocess coverage because its
contract delegates to an upstream child.

## Constraints

- Do not change production CLI behavior, runtime layout, dependencies, lock
  protocol, or test-runner configuration.
- Preserve an ordinary executable representative for each command area.
- Follow `docs/guides/local-cli-reliability.md` for filesystem-facing tests.
- Apply the operational rules in `docs/guides/in-process-cli-test-selection.md`
  to future tests.

## Durable outcome

The helper reduces avoidable Python child processes while retaining every
process-only contract. Current classification totals and exceptions are in the
companion audit.

## References

- `docs/guides/in-process-cli-test-selection.md`
- `docs/plans/2026-07-29-in-process-cli-helper-audit.md`
- `docs/guides/test-suite-performance.md`
