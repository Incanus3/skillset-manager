# Completion-Probe Batching Implementation Record

## Completed changes

- Added framed Fish batch execution for static completion probes.
- Added prompt-reset Zsh batch execution for interactive probes.
- Retained executable and dynamic-name shell probes for both shells.

## Verification

Five focused post-change runs passed. Their median elapsed time fell from
8.682 seconds to 1.859 seconds; the complete-suite result and direct-child
trace are recorded in `docs/guides/test-suite-performance.md`.

## Maintenance rule

Keep shell-specific assertions in native-shell tests. Batch only probes whose
independence is preserved by the framing and reset protocol.
