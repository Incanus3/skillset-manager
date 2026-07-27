# In-Process CLI Helper Selection Audit

## Purpose

This completed audit records the durable boundary decisions for the explicit
in-process CLI test helper. The selection guide, not this historical record,
governs future tests.

## Lifecycle coverage

Ordinary serial coverage for `init`, `create`, `use`, `current`, `list`,
`show`, `rename`, and `remove` uses the in-process helper where its assertions
do not require a real executable. Executable smoke, prompts, TTY, injected
faults, locks, interruption, recovery, shell behavior, and delegation remain
subprocess tests.

## Remaining-area coverage

The final remaining-area inventory contains 312 reachable tuples:

| Area | In-process | Executable representative | Subprocess boundary |
| --- | ---: | ---: | ---: |
| `doctor` | 13 | 1 | 17 |
| Codex | 23 | 1 | 0 |
| Claude | 48 | 1 | 36 |
| Augment and discovery | 80 | 2 | 51 |
| `skills` | 0 | 0 | 39 |

`skills` remains entirely subprocess-based because its tests prove upstream
delegation, argument boundaries, child environment and streams, exit status,
signals, child lifetime, lock lifetime, or refusal before a child launches.

## Key exceptions

- A test name containing “recover” does not by itself require a subprocess.
  The dangling-link cleanup test is in-process because it proves ordinary
  serial filesystem cleanup and no child-process contract.
- A test with an injected environment fault, interruption, lock wait, TTY,
  prompt, shell, signal, delegated child, or inherited stream remains a
  subprocess test even when adjacent ordinary calls are eligible.
- Lifecycle and completion behavior were not silently reclassified by the
  remaining-area delivery.

## Verification

The final inventory reconciled 221 scoped static sites, 34 dynamic sites, and
312 tuples. The full suite passed 234 tests. The completed direct-child trace
is recorded in `docs/guides/test-suite-performance.md`.

