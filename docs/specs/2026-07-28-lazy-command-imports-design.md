# Lazy Command Imports

## Decision

Construct the command parser without eagerly importing every command module.
Import the implementation only after dispatch selects its command.

## Scope

The change improves import and ordinary command startup without changing the
CLI surface. Help, parser errors, and completion generation avoid unrelated
command imports; selected commands still load their required implementation.

## Constraints

- Preserve command names, options, output, exit status, and lock routing.
- Avoid new dependencies or import-cycle workarounds.
- Retain explicit regression coverage for command selection and import timing.

## Durable outcome

Lazy dispatch reduced import cost and improved selected command startup in
local measurements. Results are comparative host evidence, not a performance
target.

## References

- `docs/guides/test-suite-performance.md`
