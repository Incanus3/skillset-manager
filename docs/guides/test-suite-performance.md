# Test Suite Performance Profile

## Scope and environment

This report profiles the `skillset` test suite as of 2026-07-27. It is a
durable baseline and prioritization aid, not an approved implementation plan.

The suite is one `unittest` module, `tests/test_skillset.py`. It creates an
isolated temporary home for each test and exercises the executable at
`bin/skillset` through subprocesses. The repository's test workflow runs:

```sh
python -m unittest discover -s tests
```

The measurements below were taken on a Linux host with 36 logical CPUs and
125.5 GiB of memory. They should be treated as relative evidence; repeat the
same measurements in CI before using a wall-clock target as an acceptance
criterion.

## Baseline and method

The full suite was run in five contiguous test partitions because the
interactive profiling environment has a 60-second command limit. Every
partition exited successfully.

| Measure | Result |
| --- | ---: |
| Test cases | 229 |
| Total elapsed time | 94.6 s |
| Direct child processes launched by tests | 1,018 |
| Cold `bin/skillset --help` mean | 86.0 ms |
| Cold `bin/skillset --help` median | 85.1 ms |
| `import skillset.cli` mean | 73.7 ms |
| In-process `completions bash` median after import | 3.75 ms |

The direct-child count records processes started by the Python test process.
It excludes grandchildren started by Bash, Fish, and Zsh completion probes, so
it is a conservative measure of process churn.

At the measured 86 ms cold-launch cost, the 1,018 direct launches account for
about 87.5 seconds, or 93% of the 94.6-second elapsed baseline. This is an
attribution estimate rather than additive CPU accounting, but it identifies
subprocess startup and import work as the dominant cost. Filesystem operations,
advisory locking, and individual implementation algorithms are not the primary
optimization target.

At the pre-lazy-import checkpoint, import-time tracing attributed 46.7 ms to
importing `skillset.cli` for `--help`. `skillset.augment` alone contributed
29.9 ms of cumulative import time. The CLI then imported command
implementations eagerly, including ones unrelated to the requested command.

## Largest measured tests

| Test | Time | Direct launches | Primary cause |
| --- | ---: | ---: | --- |
| `test_fish_completion_is_contextual_and_uses_managed_names` | 4.85 s | 51 | A fresh Fish process for each completion probe |
| `test_generated_zsh_completion_behavior` | 4.48 s | 19 | Repeated interactive Zsh sessions and completion lookups |
| `test_argparse_usage_errors_exit_two` | 4.45 s | 53 | One real CLI process for each invalid argument vector |
| `test_inspection_commands_reject_uninitialized_and_invalid_layouts_read_only` | 3.06 s | 36 | Cross-product of commands and invalid layouts |
| `test_invalid_names_are_operational_errors_and_cannot_escape_skillsets` | 2.29 s | 24 | Repeated name-validation entrypoint checks |
| `test_claude_first_enable_classifies_directory_creation_interrupts` | 1.60 s | 18 | Fault-injection variants |
| `test_augment_first_enable_classifies_directory_creation_interrupts` | 1.56 s | 18 | Fault-injection variants |
| `test_successful_inspection_commands_are_strictly_read_only` | 1.41 s | 16 | Repeated inspection-command checks |

The test helpers start subprocesses in `SkillsetTests.run_cli` and
`SkillsetTests.run_cli_tty`. Most tests intentionally use them, so the current
suite is predominantly an end-to-end suite rather than a unit-test suite.

## Optimization options

The table ranks actions by expected return on investment. Speedup estimates are
not additive: parallel execution multiplies the time remaining after other
changes, while the direct-test options overlap.

Ranking conventions:

- **Speed rank:** 1 is the largest expected reduction in suite wall time.
- **Complexity rank:** 1 is the smallest increase in code and maintenance
  complexity.
- **ROI rank:** 1 is the recommended first investment.

| ROI rank | Option | State | Approximate speedup | Speed rank | Complexity increase | Complexity rank |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 1 | Convert high-cardinality argument and validation matrices to direct parser/function tests, retaining representative executable checks | Done | 15–25% | 4 | Low–medium | 1 |
| 2 | Run isolated tests in parallel, initially with four workers | Postponed | 45–70% on a sufficiently provisioned local host; lower in CI with fewer CPUs | 2 | Medium | 2 |
| 3 | Batch shell-completion probes and stub dynamic name lookup except for one end-to-end check per shell | Done | 8–12% | 5 | Medium | 3 |
| 4 | Provide an in-process CLI test helper for ordinary behavior tests while retaining subprocess tests for process semantics | Done — pilot, lifecycle, and remaining areas complete | 55–75% | 1 | High | 5 |
| 5 | Lazy-load command modules after argument parsing | Done | 10–20% suite-wide; also improves user-visible startup | 3 | Medium–high | 4 |

### 1. Direct tests for high-cardinality matrices

`test_argparse_usage_errors_exit_two` is the clearest first target: it launches
53 processes solely to confirm parser error status. Test `parser()` and the
relevant validation functions directly, then retain a small executable-level
set that covers usage formatting and exit status.

The same pattern applies to name validation and command-by-layout matrices.

**Pros:** Small, focused change; clearer failures; retains subprocess coverage
where it supplies unique value.

**Cons:** Direct tests do not prove the executable wrapper, environment setup,
or exact process exit behavior. Keep representative end-to-end cases to cover
those boundaries.

### 2. Parallel execution

Each test creates a distinct temporary home, and no shared mutable test fixture
was found in the profile. This makes process-level test parallelism promising.
Start with four workers and run repeated local and CI trials before making it
the default. The current standard-library runner does not provide parallel
execution, so this requires a runner or a small sharding mechanism.

**Pros:** Large wall-time reduction without changing test assertions; combines
with later improvements.

**Cons:** Requires runner and CI configuration; lock, signal, and PTY tests
must be proven stable under concurrent workers. CI acceleration is constrained
by the actual CPU allocation rather than the profiling host's 36 CPUs.

### 3. Batch shell-completion probes

The Fish test launches 51 fresh shells, and the Zsh behavior test launches 19
interactive sessions. A single scripted shell session can evaluate multiple
command lines. For tests concerned with parser/completion behavior, a small
`skillset list` stub can provide deterministic set names; retain one real
CLI-and-shell integration check for each shell.

**Pros:** Directly addresses the two most expensive completion tests and makes
the test intent more explicit.

**Cons:** More complicated probe framing and output parsing; shared shell state
can mask reset-related defects unless the retained end-to-end checks cover it.

### 4. In-process CLI helper

An in-process `completions bash` call takes about 3.75 ms after import versus
about 86 ms for a cold executable invocation. A helper can temporarily set
`sys.argv`, environment, current directory, and captured streams before
calling `main()`.

Use it only for tests whose contract is command behavior, not operating-system
process behavior. Keep subprocesses for executable startup, TTY rendering,
signals, delegation, advisory-lock blocking, and interruption recovery.

**Pros:** The highest possible reduction while retaining the same Python command
dispatcher.

**Cons:** High harness complexity and potential state leakage. It requires
strict restoration of process-global state and a clear classification of tests
that must remain end-to-end.

### 5. Lazy command imports

At the pre-lazy-import checkpoint, `skillset.cli` imported every command
implementation before parsing. Move imports behind dispatch paths so `--help`,
parser errors, and completion generation do not load lifecycle, Auggie, Claude,
and Codex implementations.

**Pros:** Speeds both tests and real interactive CLI use; import tracing shows a
meaningful opportunity.

**Cons:** This is an application-architecture change rather than a test-only
improvement. It can introduce import cycles or defer failures, and commands
that need the lifecycle implementation will still pay much of the cost.

## Recommended sequence

1. Refactor the argument, name, and layout matrices into direct tests while
   retaining a narrow executable smoke set.
2. Trial four-worker parallel execution locally and in the actual CI runner;
   compare both median time and repeated-run stability.
3. Batch Fish and Zsh probes, preserving one real dynamic-name lookup check per
   shell.
4. Re-profile. Adopt the broader in-process helper only if the remaining suite
   time still justifies its additional harness boundary.
5. Consider lazy imports separately as a product startup improvement, with
   suite-time reduction as a secondary benefit.

## Verification and re-profiling checklist

Before accepting an optimization:

1. Run the full suite in its normal CI command on a clean checkout.
2. Run the changed tests repeatedly to detect parallel, lock, signal, or TTY
   flakiness.
3. Recount direct child processes and measure the complete suite wall time.
4. Confirm that retained subprocess tests cover executable launch, environment,
   exit status, TTY, signal, delegation, and advisory-lock semantics.
5. Record the new baseline and the CI hardware context in this document.

## Direct-test matrix results (2026-07-28)

The first direct-test matrix delivery measured the three methods below locally
in the Orca interactive workspace. Python was `3.14.6` on Linux
`7.1.4-arch1-1 x86_64`, with 36 logical CPUs visible to the runner. This host
does not provide GNU `time` at `/usr/bin/time`; Bash's `time` keyword with
`TIMEFORMAT=%R` recorded elapsed wall-clock seconds instead.

| Run | Baseline (s) | Direct-test result (s) |
| ---: | ---: | ---: |
| 1 | 10.028 | 2.364 |
| 2 | 9.934 | 2.109 |
| 3 | 9.510 | 2.335 |
| 4 | 9.507 | 2.163 |
| 5 | 9.351 | 2.235 |
| Median | 9.510 | 2.235 |

The median reduction is 76.50%. All five direct-test runs were faster than the
baseline median, so the focused gate passes: every run passed, the median
improved by more than 5%, and at least four post-change runs beat the baseline
median.

The measured focused set is:

```sh
python -m unittest \
  tests.test_skillset.SkillsetTests.test_argparse_usage_errors_exit_two \
  tests.test_skillset.SkillsetTests.test_invalid_names_are_operational_errors_and_cannot_escape_skillsets \
  tests.test_skillset.SkillsetTests.test_inspection_commands_reject_uninitialized_and_invalid_layouts_read_only
```

Coverage split:

```text
Direct: all 53 parser vectors; all seven invalid names; one uninitialized and
five structural invalid layouts.
Subprocess: four parser usage/exit cases; five command-to-name-validator cases;
six inspection commands against both uninitialized and active-target layouts.
```

The temporary raw timing files are intentionally not repository artifacts;
their values are reproduced in the table above. The full-suite result remains
contextual evidence. The required post-change command,
`python -m unittest discover -s tests`, passed all 229 tests in 82.271 seconds
on the same local host.

## Completion-probe batching baseline (2026-07-28)

The next focused optimization batches the Fish and Zsh completion probes while
retaining one real CLI-and-shell dynamic-name lookup for each shell. Its
pre-change baseline was measured in the same Orca interactive workspace on
Python `3.14.6`, Linux `7.1.4-arch1-1 x86_64`, with 36 logical CPUs visible.
The command was:

```sh
python -m unittest \
  tests.test_skillset.SkillsetTests.test_fish_completion_is_contextual_and_uses_managed_names \
  tests.test_skillset.SkillsetTests.test_generated_zsh_completion_behavior
```

| Run | Baseline (s) | Batched result (s) |
| ---: | ---: | ---: |
| 1 | 9.087 | 1.834 |
| 2 | 8.512 | 1.735 |
| 3 | 8.682 | 1.997 |
| 4 | 8.655 | 2.086 |
| 5 | 9.190 | 1.859 |
| Median | 8.682 | 1.859 |

The focused gate requires all five post-change runs to pass, a median
improvement of at least 5%, and at least four post-change runs faster than the
8.682-second baseline median. Full-suite timing remains contextual evidence.

The optimized focused command was measured five times on the same Orca
interactive workspace. The five runs all reported `OK` for the two tests.

Sorted, the values are 1.735, 1.834, 1.859, 1.997, and 2.086 seconds. All
five values are strictly below the 8.682-second baseline. The median reduction
is `(8.682 - 1.859) / 8.682 * 100 = 78.59%`, so the focused gate passes:
five of five runs passed, the median reduction exceeds 5%, and five of five
runs beat the baseline median.

The focused command ran two tests on Python `3.14.6`, Linux
`7.1.4-arch1-1 x86_64 GNU/Linux`, on an Intel(R) Core(TM) i9-10980XE CPU @
3.00GHz with 36 logical CPUs visible. A `strace -ff -e trace=process` capture
of that focused run reported 8 direct `clone`, `clone3`, `fork`, or `vfork`
calls from the Python runner trace (the trace whose first `execve` is Python).

The retained Fish and Zsh dynamic-name probes still execute
`bin/skillset` from an initialized temporary managed layout; their static
completion cases use the deterministic `skillset list` stub. The focused
tests therefore reduce setup processes without replacing the two executable
and native-shell probes. The full suite command
`python -m unittest discover -s tests` passed all 229 tests in 76.377 seconds
on this host. That elapsed time is contextual evidence only, not a full-suite
wall-clock target.

The [direct-test implementation record](../plans/2026-07-28-direct-test-matrix-performance-implementation.md)
summarizes the retained executable boundaries for future direct-test work.

## Lazy command imports (2026-07-28)

The post-change measurements below used 11 fresh subprocess samples per
operation with `PYTHONPATH=lib` and `PYTHONDONTWRITEBYTECODE=1`. They compare
this run with the 2026-07-28 design checkpoint.

| Operation | Checkpoint median | Current median | Median reduction | Checkpoint mean | Current mean | Mean reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `import skillset.cli` | 75.1 ms | 51.0 ms | 32.09% | 75.1 ms | 49.1 ms | 34.62% |
| `bin/skillset --help` | 72.4 ms | 88.5 ms | -22.24% | 74.5 ms | 84.6 ms | -13.56% |
| `bin/skillset completions bash` | 78.8 ms | 73.4 ms | 6.85% | 88.5 ms | 78.0 ms | 11.86% |
| `bin/skillset list` | 92.9 ms | 72.0 ms | 22.50% | 93.2 ms | 77.4 ms | 16.95% |

The import and `list` measurements were lower in this run; `--help` was
higher, while completion generation was lower. These are comparative,
host-dependent observations, not fixed wall-clock acceptance targets, and no
complete-suite runtime was measured here.

## In-process CLI helper pilot (2026-07-28)

The approved delivery migrated exactly four existing ordinary command-behavior
tests to the in-process helper. The parser-exit cleanup regression test is the
fifth pilot test, but it is intentionally excluded from this before/after
speed comparison. Measurements were actually captured on 2026-07-29 in
`/home/jakub/orca/projects/agents`, with Python `3.14.6` at `/usr/bin/python`
on `Linux 7.1.4-arch1-1 x86_64 GNU/Linux` (36 logical CPUs visible).

The focused command was:

```sh
TIMEFORMAT='elapsed=%3R seconds'
time python -m unittest \
  tests.test_skillset.SkillsetTests.test_completions_emit_deterministic_scripts_without_managed_state \
  tests.test_skillset.SkillsetTests.test_scoped_command_help_describes_each_default \
  tests.test_skillset.SkillsetTests.test_current_prints_exact_active_name_before_and_after_use \
  tests.test_skillset.SkillsetTests.test_create_empty_set_without_changing_active_set
```

All five post-change invocations passed with `Ran 4 tests` and `OK`.

| Run | Task 1 baseline (s) | Post-change (s) |
| ---: | ---: | ---: |
| 1 | 1.810 | 0.252 |
| 2 | 1.716 | 0.235 |
| 3 | 1.596 | 0.199 |
| 4 | 1.644 | 0.169 |
| 5 | 1.618 | 0.169 |
| Median | 1.644 | 0.199 |

The baseline values sorted to 1.596, 1.618, 1.644, 1.716, and 1.810 seconds;
the post-change values sorted to 0.169, 0.169, 0.199, 0.235, and 0.252
seconds. The median reduction is `(1.644 - 0.199) / 1.644 * 100 = 87.90%`.
These wall-clock measurements are host/load-sensitive comparative evidence,
not a fixed target.

A completed fresh focused capture used `strace -ff -e trace=process` with the
same four-test command. It exited 0 with `Ran 4 tests in 0.520s` and `OK`.
As in Task 1, counting only `clone`, `clone3`, `fork`, and `vfork` in the
Python test-runner trace (the trace whose first `execve` starts
`/usr/bin/python`) gives 21 completed direct-child calls before migration and
0 after migration. No whole-suite process-count claim is made.

Subprocess tests remain required for executable launch, environment boundaries,
TTY rendering, signals, delegation, advisory-lock blocking, interruption
recovery, inherited file descriptors, parent-process stdin, native-shell
completion probes, and fresh-interpreter import probes.

The normal suite command, `python -m unittest discover -s tests`, passed all
234 tests in 72.389 seconds on the same host. This delivery is a five-test
pilot; any further migration needs a new classification and approved plan.

Future test authors should use the [in-process and subprocess selection guide](in-process-cli-test-selection.md) to classify new coverage. It preserves executable and process-boundary tests while making ordinary command behavior eligible for the explicit in-process helper.

## Lifecycle helper expansion (2026-07-29)

This completed local verification follows the [in-process helper selection audit](../plans/2026-07-29-in-process-cli-helper-audit.md).
The audit selects one in-process row for each of `init`, `create`, `use`,
`current`, `list`, `show`, `rename`, and `remove`. Three command areas share
`test_invalid_names_are_operational_errors_and_cannot_escape_skillsets`, so
the exact focused command contains these six methods:

```sh
TIMEFORMAT='elapsed=%3R seconds'
time python -m unittest \
  tests.test_skillset.SkillsetTests.test_invalid_names_are_operational_errors_and_cannot_escape_skillsets \
  tests.test_skillset.SkillsetTests.test_show_defaults_to_active_set_and_explicit_name_overrides_it \
  tests.test_skillset.SkillsetTests.test_current_escapes_unsafe_operational_errors_at_the_final_boundary \
  tests.test_skillset.SkillsetTests.test_list_sorts_set_names_and_marks_only_the_active_set \
  tests.test_skillset.SkillsetTests.test_show_empty_set_prints_explanatory_message \
  tests.test_skillset.SkillsetTests.test_remove_yes_skips_prompt
```

All five runs passed (`Ran 6 tests`, `OK`). The audit baseline values below
are normalized from its locale-formatted elapsed output; the post-change
values are from this completed verification.

| Run | Audit baseline (s) | Post-change (s) |
| ---: | ---: | ---: |
| 1 | 1.660 | 0.888 |
| 2 | 1.711 | 0.826 |
| 3 | 1.689 | 0.694 |
| 4 | 1.679 | 0.689 |
| 5 | 1.738 | 0.655 |
| Median | 1.689 | 0.694 |

The sorted baseline values are 1.660, 1.679, 1.689, 1.711, and 1.738
seconds; post-change values are 0.655, 0.689, 0.694, 0.826, and 0.888
seconds. The median reduction is `(1.689 - 0.694) / 1.689 * 100 = 58.91%`.
These are host- and load-sensitive comparative measurements, not a fixed
wall-clock target.

The measurements used Python `3.14.6` on `Linux 7.1.4-arch1-1 x86_64
GNU/Linux`, with 36 logical CPUs visible on an Intel(R) Core(TM) i9-10980XE
CPU @ 3.00GHz. A completed `strace -ff -e trace=process` capture of the same
focused command exited 0 with `Ran 6 tests in 1.497s` and `OK`. Counting only
`clone`, `clone3`, `fork`, and `vfork` in the Python test-runner trace (whose
first `execve` starts `/usr/bin/python`) recorded 7 direct-child calls, all
`vfork`. No whole-suite process-count claim is made.

The audit/helper mapping was independently rechecked: all 134 `in-process`
audit rows map to `run_cli_in_process`, while all 9 subprocess-representative
and 45 subprocess-boundary rows retain `run_cli`, `run_cli_tty`, or
`popen_cli`. The retained executable workflow and the helper's parser-exit
cleanup regression both passed. Subprocess coverage remains for ordinary
executable smoke, executable/exit and wrapper-environment behavior,
parser/usage smoke, inherited environment/file-descriptor/parent-stdin
boundaries, TTY and interactive behavior, signals and interruption recovery,
fresh-child fault injection, delegation and advisory-lock blocking,
native-shell probes, and fresh-interpreter imports.

The normal suite command, `python -m unittest discover -s tests`, passed all
234 tests on this host. The unittest runner reported 59.419 seconds; Bash
wall-clock output was 59.528 seconds. These complete-suite durations are
contextual evidence only, not a target. Further command areas require a new
classification and approved plan.

## Remaining CLI helper areas: final verification (2026-07-29)

Final verification for the [in-process helper selection audit](../plans/2026-07-29-in-process-cli-helper-audit.md)
completed on this Orca workspace with Python `3.14.6`, Linux
`7.1.5-arch1-2 x86_64 GNU/Linux`, 36 logical CPUs, and an Intel(R) Core(TM)
i9-10980XE CPU @ 3.00GHz. The normal complete-suite command was:

```sh
python -m unittest discover -s tests
```

It exited `0` with `Ran 234 tests in 44.372s` and `OK`. This is completed
verification evidence; its duration is local, host- and load-sensitive
comparison context, not an acceptance target.

The complete suite was captured for a direct-child measurement:

```sh
strace -ff -e trace=process -o /tmp/skillset-remaining-areas-trace.iwlQih/trace \
  python -m unittest tests.test_skillset.SkillsetTests
```

The extended 180-second capture completed with exit `0`: `Ran 234 tests in
99.159s` and `OK`. Counting only `clone`, `clone3`, `fork`, and `vfork` calls
in the Python test-runner trace (the trace whose first `execve` starts
`/usr/bin/python`) recorded **497 direct child-process creations**. This
excludes grandchildren created by those child processes. The traced duration
is instrumentation-affected and is local comparative evidence, not a timing
target.
