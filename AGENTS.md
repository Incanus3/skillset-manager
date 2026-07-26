# Skillset implementation repository

## Scope and ownership

This repository owns the `skillset` implementation, its tests, executable entry
point, and project documentation. The live global skillset runtime is
`~/.agents`; it owns active-skillset state and must not be treated as a source
checkout.

Do not introduce a second managed runtime layout in this repository. In
particular, `skillsets/`, `active`, `skills`, `.skill-lock.json`, and
`.skillset.lock` are live runtime state when they exist under `~/.agents`.
Tests must construct isolated layouts under their temporary homes.

## Required context

Before designing, testing, or reviewing filesystem behavior in `skillset`, read
`docs/guides/local-cli-reliability.md`. `skillset` is a trusted local CLI, not a
security boundary: preserve serial functional reliability and proportionate
recovery from ordinary errors, do not add adversarial filesystem or TOCTOU
hardening, and treat concurrency as best effort only.

## Mirror upstream vocabulary in wrapper CLIs

When a CLI delegates to another CLI, reuse the upstream command verbs and option names wherever the semantics match.
Avoid unnecessary synonyms such as `delete` for an upstream `remove` command or `switch` for an upstream `use` command.
Matching vocabulary reduces translation overhead and makes upstream documentation easier to apply.
