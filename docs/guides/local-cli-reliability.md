# Local CLI Reliability Guide

## Scope
`skillset` serves trusted developers on local machines and is not a security
boundary. Normal serial commands, ordinary I/O errors, and useful Ctrl+C
recovery are supported; hostile local actors are not.

## Functional reliability
- Correct links, lock metadata, aliases, and registrations in serial use.
- Clear errors and proportionate recovery that prevents loss or unusable state.
- Preserve unrelated local data in normal, non-racing operation.

## Exclude
- TOCTOU, hostile replacement, and same-UID attacker defenses.
- Syscall-boundary fault injection, descriptor identity protocols, and
  quarantine state created solely for racing replacements.
- `ctypes`, direct syscall bindings, and platform-specific filesystem APIs.

## Best-effort concurrency
Simple advisory locking may reduce accidental overlap when it remains
standard-library-based and easy to understand. It does not guarantee correct
behavior for concurrent mutations and must not grow a specialized test matrix.

## Classification
Classify every candidate before changing it:

| Classification | Meaning |
| --- | --- |
| Functional reliability | Normal serial behavior, ordinary errors, or proportionate recovery. Retain it. |
| Mixed | Functional behavior plus adversarial protocol. Preserve only the functional subset in a narrow change. |
| High-confidence adversarial hardening | Hostile replacement, TOCTOU, same-UID interference, or syscall timing. Remove it with its dedicated tests. |

## Review checklist
- Name the normal serial failure or user-visible behavior the change preserves.
- Reject a change whose only rationale is a hostile or racing process.
- Verify that a retained lock, staging marker, or rollback path remains the
  smallest understandable solution to its functional problem.