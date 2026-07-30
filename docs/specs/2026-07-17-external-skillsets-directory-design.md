# External Skillsets Directory Design

**Date:** 2026-07-17
**Status:** Approved for implementation

## Summary

Allow a `skillset` installation to keep named skillsets in a real directory
outside `~/.agents`. An optional real `~/.agents/config.json` authorizes one
absolute `skillsets_directory`. When configured, `~/.agents/skillsets` is a
canonical symlink to that directory. Runtime aliases, advisory locks, and
activation state remain under `~/.agents`.

This supports repository-backed skill collections without permitting arbitrary
symlinks inside a skillset. Named skillset directories and their `skills/`
directories remain real entries.

## Goals and non-goals

Goals:

- Keep authored skillsets in a separate version-controlled directory.
- Preserve all existing behavior when `config.json` is absent.
- Allow only the single top-level symlink explicitly authorized by config.
- Make initialization create and roll back the configured link safely.
- Keep diagnostics read-only and refuse unconfigured or mismatched symlinks
  before inspecting their descendants.
- Preserve alternate-`HOME` behavior.

Non-goals:

- Support multiple external roots in one installation.
- Allow symlinked named skillsets, `skills/` directories, or individual skills.
- Move an existing initialized installation automatically.
- Expand environment variables, `~`, or relative paths in config.
- Manage Git state in the external directory.

## Configuration contract

The optional file is `~/.agents/config.json`:

```json
{
  "version": 1,
  "skillsets_directory": "/absolute/path/to/skillsets"
}
```

The file must:

- be a real regular UTF-8 file, never a symlink;
- contain one JSON object with exactly `version` and `skillsets_directory`;
- use integer version `1`;
- provide a nonempty absolute path without NUL characters;
- point outside the managed `~/.agents` root;
- point to an existing real directory, never a symlink.

The configured path is normalized without substituting a resolved path into
the configuration or managed link. The serialized path and the
`~/.agents/skillsets` link target must both equal that normalized absolute
path. Resolution is additionally used as a containment check: the source's
resolved location must remain outside the resolved managed root.

Unknown keys, relative paths, malformed JSON, unsupported versions, missing
targets, and symlink targets are errors.

## Filesystem contract

Without config, the existing layout is unchanged:

```text
~/.agents/
├── skillsets/                  # real directory
├── active -> skillsets/NAME
├── skills -> active/skills
└── .skill-lock.json -> ...
```

With config:

```text
~/.agents/
├── config.json                 # real file
├── skillsets -> /absolute/configured/path
├── active -> skillsets/NAME
├── skills -> active/skills
└── .skill-lock.json -> ...

/absolute/configured/path/
└── NAME/
    ├── skills/                 # real directory
    └── .skill-lock.json        # or .skillset-manual
```

The configured source is the only permitted symlinked skillsets container.
Every descendant retains the existing real-entry rules.

## Initialization

`skillset init NAME` reads and validates config before changing state.

Without config, it creates the real `~/.agents/skillsets` directory as before.
With config, the external directory must already exist. Initialization creates
the canonical `~/.agents/skillsets` symlink, creates the initial named set
through that link, and then creates the existing root aliases.

The configured external directory may contain other valid named sets, but the
requested initial name must not already exist.

If initialization fails:

1. Remove only aliases whose targets exactly match those created by this run.
2. Restore adopted root `skills` and lock contents from the initial set.
3. Remove the newly created initial set only when it is empty after restoration.
4. Remove the configured `skillsets` link only when it is still canonical.
5. Never remove or rename the configured external directory or its unrelated
   contents.

Incomplete rollback reports the concrete root, target-set, and configured-source
paths.

## Normal operations

Layout validation reads config first. A valid configured installation accepts
the exact canonical top-level link and then uses the existing lifecycle,
activation, delegation, and Codex-link behavior unchanged.

The root advisory lock remains `~/.agents/.skillset.lock`. One `~/.agents`
installation owns a configured external directory; sharing the same external
directory between independently locked installations is unsupported.

## Diagnostics and repair

`skillset doctor`:

- reports config errors before skillset descendant findings;
- never follows a configured-source link until config, link target, and source
  directory all validate;
- preserves the existing error for a skillsets symlink when config is absent;
- accepts the exact configured link and then diagnoses named sets normally;
- never creates or rewrites `config.json` or the configured source.

`doctor --fix` does not create or rewrite the configured source. It can restore
a missing configured link from the exact configured path. When runtime aliases
are also missing, it asks the user to choose a valid named skillset before
recreating the canonical aliases; it never guesses the active set.

## Migration

Migration of an already initialized installation is explicit:

1. Stop concurrent `skillset` and delegated upstream commands.
2. Move the real `~/.agents/skillsets` directory to the desired external path.
3. Write canonical `~/.agents/config.json`.
4. Create `~/.agents/skillsets` pointing to the configured absolute path.
5. Run `skillset doctor`, `skillset list`, `skillset current`, and
   `skillset show`.

Initialization into a fresh root instead writes config first, then runs
`skillset init NAME`.

## Implementation boundaries

- `lib/skillset/layout.py`: parse config and validate the skillsets container.
- `lib/skillset/operations.py`: create and roll back the configured link during
  initialization.
- `lib/skillset/doctor.py`: diagnose config and the authorized link without
  following untrusted descendants.
- `README.md`: document configuration, initialization, and migration.
- `tests/test_skillset.py`: cover config parsing, initialization, rollback,
  normal operations, diagnostics, and unchanged default behavior.

## Verification

Run:

```sh
python3 -m unittest discover -s tests -v
```

The suite must include:

- fresh configured initialization and normal lifecycle operations;
- alternate-`HOME` operation;
- malformed, symlinked, relative, missing, and mismatched configuration;
- refusal to follow an unauthorized skillsets symlink;
- configured initialization failure and interrupt rollback;
- preservation of unrelated external source contents;
- read-only doctor behavior;
- unchanged unconfigured layout and diagnostics.

## Rejected alternatives

- **Allow any skillsets symlink:** weakens the containment boundary globally.
- **Allow symlinked individual skills:** reintroduces the per-skill indirection
  this feature is intended to replace.
- **Use per-set external-source configuration:** splits every set's metadata
  from its skills and complicates clone, rename, and removal semantics.
- **Use alternate `HOME` permanently:** relocates all home-relative behavior,
  including delegated upstream state, rather than only the skillsets source.
- **Use YAML:** adds a runtime dependency or requires an unsafe partial parser.
- **Create the external source automatically:** risks claiming or mutating an
  unintended path; the user must create it explicitly.
