# Choosing In-Process and Subprocess CLI Tests

## Rule of thumb

Use `run_cli_in_process()` when a test proves isolated command behavior.
Use `run_cli()` when the assertion depends on a real executable process.
If one behavior needs both, write focused tests for both boundaries rather
than weakening either assertion.

## What the in-process helper guarantees

`run_cli_in_process()` is an explicit test-only helper. It invokes
`skillset.cli.main()` directly and restores the complete environment, current
directory, `sys.argv`, `sys.stdin`, `sys.stdout`, and `sys.stderr` in
`finally`. It is not a replacement mode for `run_cli()` and does not emulate
a fresh interpreter or a child process.

## Choose in-process coverage for

- deterministic command output and ordinary return codes;
- normal isolated filesystem state changes;
- ordinary serial lifecycle transitions;
- non-interactive validation and refusal paths; and
- command behavior whose existing assertions do not depend on executable
  launch or inherited process state.

## Keep subprocess coverage for

- executable launch, real exit propagation, or wrapper environment behavior;
- parser/usage executable smoke coverage;
- inherited environment, file descriptors, or parent-process stdin;
- TTY rendering, interactive prompts, and native-shell probes;
- signals, keyboard interrupts, interruption recovery, and fresh-child
  fault injection;
- delegated child lifetime and advisory-lock blocking; and
- fresh-interpreter import behavior.

## Combining both forms safely

Keep an ordinary executable smoke for each command area and retain every
special-boundary test. When a test combines ordinary behavior with a process
contract, split it into focused tests before converting the ordinary portion;
do not convert the process assertion or turn it into an implementation detail.

## Before committing a new CLI test

1. Name the behavior being proved.
2. Decide whether that behavior needs a real process using the list above.
3. Keep or add a subprocess representative when it is the only executable or
   process-boundary proof for that behavior.
4. Use the explicit helper name in every in-process test.
5. Run the focused test and the retained representative affected by the
   change.

## Further reading

- [In-process helper design](../specs/2026-07-28-in-process-cli-helper-design.md)
- [Completed helper-selection audit](../plans/2026-07-29-in-process-cli-helper-audit.md)

This guide is the operational decision rule; the linked designs provide
rationale and measurement context.
