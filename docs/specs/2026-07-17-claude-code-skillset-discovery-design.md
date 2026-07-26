# Claude Code Skillset Discovery Design

**Date:** 2026-07-17
**Status:** Implemented 2026-07-18

## Summary

Extend `skillset` with a `claude` command group that makes named skillsets
available to Claude Code globally or beneath the current working directory:

```sh
skillset claude enable personal
skillset claude enable personal --local
skillset claude disable personal --local
skillset claude list
```

The command surface mirrors `skillset codex`, but the filesystem projection
cannot. Codex recursively discovers the contents of a collection link such as
`.codex/skills/personal -> ~/.agents/skillsets/personal/skills`. Claude Code
expects every direct `.claude/skills/<skill-name>` entry to contain
`SKILL.md`; it does not treat an extra grouping directory as a skill suite.
Claude support must therefore create one canonical link per direct skill
directory and separately record which skillset owns those links.

This design keeps unrelated Claude entries intact, supports multiple skillsets
when their direct skill-directory names do not collide, and makes a repeated
`enable` reconcile skills added to or removed from an already registered
skillset.

## Repository and environment state

- The implementation is a Linux-only, standard-library Python 3 CLI.
- The executable is `bin/skillset`; implementation modules live under
  `lib/skillset/`.
- `~/.agents/skillsets/<name>/skills` is the canonical skill content.
  Skillsets can be upstream-managed or manual, but both modes expose the same
  real `skills/` directory.
- `lib/skillset/codex.py` currently implements global and current-directory
  Codex discovery with one absolute collection link per skillset.
- `lib/skillset/cli.py` owns parsing, lock selection, and dispatch.
- `lib/skillset/completions.py` contains generated Bash, Zsh, and Fish scripts
  as source strings and must be updated in all three grammars.
- `lib/skillset/operations.py` prevents rename and removal while a canonical
  global Codex link exists. Local links are intentionally not tracked outside
  their project directories.
- `lib/skillset/metadata.py` already renders named and scoped set lists,
  including verbose inventories, manual markers, terminal-safe text, and TTY
  colors. Claude listing should reuse those renderers.
- `tests/test_skillset.py` is a black-box suite that invokes the real CLI under
  isolated temporary homes and working directories.
- The clean baseline on 2026-07-17 is 138 passing tests:

  ```text
  Ran 138 tests in 20.012s
  OK
  ```

- The installed local Claude Code version observed during design was
  `2.1.211`.

## External behavior researched

The current official Claude Code skills documentation states:

- Personal skills live at `~/.claude/skills/<skill-name>/SKILL.md`.
- Project skills live at `.claude/skills/<skill-name>/SKILL.md`.
- A direct `<skill-name>` entry may be a symlink to a skill directory
  elsewhere on disk.
- When a personal and project skill share a name, the personal skill takes
  precedence.
- Project skill directories are discovered from the starting directory and
  ancestors up to the repository root. Nested `.claude/skills` directories
  below the starting directory are discovered on demand as Claude works with
  files there.
- Creating a top-level skills directory after a Claude session starts may
  require restarting that session, while changes inside a directory already
  being watched are detected live.

Source, accessed 2026-07-17:
<https://code.claude.com/docs/en/skills>

Claude's "nested directories" feature means multiple `.claude/skills`
locations in a directory hierarchy. It does not mean arbitrary grouping
folders beneath one `skills/` directory. The open upstream request for
recursive discovery documents that only direct skill directories are
currently loaded and recommends top-level per-skill symlinks as the
workaround:
<https://github.com/anthropics/claude-code/issues/18192>

This is the reason a direct copy of `lib/skillset/codex.py` would produce a
layout that looks plausible but does not expose the contained Claude skills.

## Goals

- Add global and current-directory Claude Code discovery with the same CLI
  vocabulary and scope flags as the Codex integration.
- Preserve every unrelated entry already present under `.claude`.
- Project each direct real skill directory at the top level where Claude Code
  can discover it.
- Support more than one registered skillset across the effective global and
  exact-current-directory scopes when skill names do not collide.
- Keep enable idempotent and make it reconcile membership changes.
- Make partial multi-link operations explicit and recoverable by rerunning
  `enable` or `disable`.
- Reuse existing list formatting, manual markers, validation, locking, error
  handling, and shell-completion conventions.
- Prevent globally registered Claude skillsets from being renamed or removed
  while their links would become stale.
- Preserve all existing Codex behavior and output.

## Non-goals

- Recursively projecting nested directories below a skillset's direct
  `skills/` children.
- Installing, updating, or validating Claude-specific skill frontmatter.
- Starting Claude Code or forcing a running session to reload skills.
- Searching every repository on disk for local registrations.
- Listing ancestor or descendant `.claude/skills` locations from one command.
  `--local` always addresses the exact current working directory.
- Automatically reconciling project projections after direct filesystem edits
  or an upstream command changes set membership. The user reruns `enable`.
- Managing Claude plugins, commands, agents, hooks, settings, or marketplaces.
- Extending `skillset doctor` to arbitrary external project directories.
- Replacing or migrating existing user-managed Claude entries.

## Command surface

Add `claude` as a top-level command beside `codex`:

```text
skillset claude enable NAME [-g|--global|-l|--local]
skillset claude disable NAME [-g|--global|-l|--local]
skillset claude list [-v|--verbose] [-g|--global|-l|--local]
```

The upstream executable and configuration directory are both named `claude`,
so `claude` is the durable wrapper verb. User-facing help and diagnostics call
the product "Claude Code".

`enable` and `disable` default to global scope, matching `skillset codex`.
`list` defaults to the combined global and exact-current-directory view.
`--global` and `--local` are mutually exclusive on all three subcommands.
Options may appear wherever `argparse` currently permits them.

Scope paths are:

| Scope | Claude root | Skill links | Registrations |
| --- | --- | --- | --- |
| Global | `~/.claude` | `~/.claude/skills` | `~/.claude/.skillsets` |
| Local | `$PWD/.claude` | `$PWD/.claude/skills` | `$PWD/.claude/.skillsets` |

The tool does not resolve a Git root or walk to a parent directory. Running
`--local` in a repository subdirectory intentionally registers the skillset
for that exact folder. Claude Code's own ancestor and nested-directory rules
then determine when it is discovered.

## Filesystem contract

Given a manual set containing two direct skills:

```text
~/.agents/skillsets/personal/
├── .skillset-manual
└── skills/
    ├── feature-status/
    │   └── SKILL.md
    └── handoff/
        └── SKILL.md
```

local enablement from `/work/example` creates:

```text
/work/example/.claude/
├── .skillsets/
│   └── personal -> /home/user/.agents/skillsets/personal/skills
└── skills/
    ├── feature-status -> /home/user/.agents/skillsets/personal/skills/feature-status
    └── handoff -> /home/user/.agents/skillsets/personal/skills/handoff
```

All managed links use absolute targets. The canonical target for a
registration is the absolute skillset `skills/` directory. The canonical
target for a projected skill is that directory's direct child with the same
basename as the link.

The registration lives outside `.claude/skills` so Claude Code never mistakes
it for a skill. It has two purposes:

1. Record that the scope intentionally projects a named skillset.
2. Leave recoverable intent in place if a multi-link enable, reconciliation,
   or disable operation is interrupted.

The registration target is sufficient to identify all owned links, including
dangling links for source children that were later removed. An entry named
`<skill-name>` is owned by a registration only when it is a symlink whose
canonical absolute target is exactly
`<registered-skills-directory>/<skill-name>`. Both the immediate-parent match
and the basename match are required. Prefix-only matches, aliases whose link
name differs from the target basename, relative targets, deeper descendants,
ordinary files, and directories are never treated as owned.

Canonical link comparison accepts one or more redundant trailing `/`
characters for compatibility with the existing documented Codex behavior, but
otherwise compares the absolute target text exactly. It does not collapse
interior `.`, `..`, duplicate-separator, or alternate-prefix spellings. Those
spellings can resolve differently when symlinked path components are involved
and are too broad for a destructive ownership decision.

This basename rule is a destructive-operation boundary, not merely a
synchronization check. For example, a user-created
`.claude/skills/review-alias -> <registered-skills-directory>/review` link is
not owned and must survive reconciliation and disable.

The implementation never removes the `.claude`, `.claude/skills`, or
`.claude/.skillsets` containers after creating them, even when they become
empty.

Local registrations and projected links contain machine-specific absolute
targets. They are runtime state, not portable project configuration, and may
become broken or expose a home-directory path if committed. The command does
not edit `.gitignore`; documentation must tell users to keep generated
registrations and links out of version control while preserving any
hand-authored project skills they do intend to commit.

## Source inventory

Projection uses direct children of the registered skillset's `skills/`
directory:

- A real directory becomes one projected skill link.
- A regular file or other non-directory entry is ignored, matching current
  inventory behavior for ordinary direct files.
- A direct symlink is refused before mutation. Managed skill inspection and
  diagnostics already reject skill-directory symlinks, and projecting one
  would add an unnecessary second link-following boundary.
- The directory basename, not the declared frontmatter `name`, is the
  destination link name. Claude Code uses the directory entry as its command
  identity and treats frontmatter `name` as optional display metadata.
- Invalid or missing `SKILL.md` metadata does not change projection ownership.
  Existing `list --verbose`, `show`, and `doctor` behavior remains responsible
  for surfacing malformed managed skill entries. Claude Code may ignore a
  projected invalid skill.

An empty skillset creates only its registration and is still considered
enabled.

## Enable semantics

`skillset claude enable NAME [scope]`:

1. Validate the complete managed `~/.agents` layout and selected skillset.
2. Inspect the selected set's direct source inventory without following
   symlinks.
3. Validate existing Claude containers. Every existing container must be a
   real directory. Missing containers are created only after all preflight
   checks that do not require them.
4. Validate the expected registration:
   - Missing is available for creation.
   - An exact canonical link means the set is already registered and should be
     reconciled.
   - Any other existing entry is refused without replacement.
5. Preflight every desired destination name in the selected scope. A missing
   path or exact canonical link is acceptable. Any file, directory, or
   different symlink is a collision, including a link owned by another
   registered set.
6. Preflight the other effective scope's `skills/` directory. A missing entry
   or exact canonical link to the same source skill is acceptable. The same
   basename with any different target or entry kind is a cross-scope
   collision.
7. Create the canonical registration before changing projected links. Once
   present, it is durable intent that either `enable` or `disable` can recover.
8. Create missing desired links.
9. Remove stale links that still satisfy the complete ownership predicate but
   whose basename is no longer a direct real source directory.
10. Verify the complete projection and other-scope preflight before reporting
    success.

Creating desired links before removing stale ones keeps existing skills
available for as long as possible. Collision preflight occurs before the
registration or any skill link is created, so expected conflicts are
all-or-nothing failures.

A local enable always checks the personal scope that can mask it. A global
enable checks the exact current directory's local scope. Local registrations
in other projects are intentionally not globally indexed, so they cannot all
be preflighted when a global registration is created; listing from an affected
project detects any resulting conflict.

A repeated enable is silent and successful when already synchronized. If set
membership changed, it adds and removes only canonical owned links. Content
changes within an existing skill directory require no reconciliation because
the link target remains live.

Accepting an exact canonical projected link when the registration is missing
is intentional adoption, matching the existing Codex idempotence policy.
Creating the registration makes that exact link managed, so a later Claude
disable may remove it. No noncanonical entry is ever adopted.

Preflight is repeated at each mutation boundary. Before creating a projected
link, re-inspect both the source child and destination without following
symlinks; the source must still be the same kind of real direct directory and
the destination must still be missing or canonical. Before removing a stale
or disabled link, re-read it and require the complete ownership predicate,
including matching basenames. A changed entry is reported and preserved.
Final verification repeats the complete source, registration, and projection
inventory.

Open the real source, registration, and projection directories with
`O_DIRECTORY | O_NOFOLLOW` and perform child inspection and mutation relative
to those held directory descriptors where the standard library supports it.
Compare opened identities with the entries accepted during preflight. This
prevents a concurrent replacement of a validated container from redirecting a
later child operation. Direct source edits can still race between observations;
such a race must converge to a verified complete state or an actionable
partial-state error, never broaden ownership.

If an unexpected filesystem error or interruption leaves a partial
projection, retain the canonical registration and report the registration,
source, and incomplete destination paths. Rerunning `enable` completes the
current source projection; running `disable` removes every owned projection.
Never guess at or replace a colliding unrelated entry.

## Disable semantics

`skillset claude disable NAME [scope]`:

1. Validate the managed layout and name.
2. Require the exact canonical registration when an entry is present. Treat an
   absent registration as a recoverable cleanup state so a repeated disable can
   verify and remove any remaining owned projection.
3. Inventory every canonical owned link in the scope's `.claude/skills`
   directory, including dangling targets for source children that no longer
   exist.
4. Remove owned links only.
5. Remove the registration last.
6. Verify that no owned links or registration remain.

A noncanonical registration is refused as "not Claude Code-enabled." An absent
registration is idempotent: disable still inventories and removes only links
whose exact canonical targets establish ownership, then verifies the completed
state. Unrelated skill entries are never removed, even if their names match
skills in the source set.

Keeping the registration until the final step makes interrupted disable
recoverable: rerun `disable` to continue removing owned links, or rerun
`enable` to restore a complete current projection. A post-unlink exception is
classified from the observed path state, following the repository's
transactional CLI safety guide.

Disable intentionally does not require the selected source set to remain
present in an otherwise valid managed layout. It validates the managed layout
and name, then derives the expected canonical target lexically so a
registration left behind after an out-of-band source removal can still clean
up its dangling owned links. If the source path still exists, normal complete
layout validation applies.

## Listing semantics

`skillset claude list` reuses the Codex scoped presentation:

```text
[g] always-on
[g] personal [m]
[l] obra
```

- `[g]` is cyan and `[l]` is green on an eligible TTY.
- Manual sets retain the yellow `[m]` suffix.
- Combined output contains one row per registration, so a set registered in
  both locations appears twice.
- Global-only or local-only output omits the redundant scope marker.
- `--verbose` uses the existing aligned source inventory table.
- There is no active `*` marker because Claude registrations are additive, not
  selected through one active set.
- If the global and local Claude roots are the same path, combined listing
  emits the registration only once, matching current Codex behavior.

A set is listable only when its registration is canonical, the source set is
valid, and the projection is synchronized. A validly named entry in
`.claude/.skillsets` that is noncanonical, has an invalid or missing source,
or has an incomplete or colliding projection is an operational error that
names the entry and scope and recommends the applicable `enable`, `disable`,
or manual-repair action; it must not disappear silently from output. Entries
whose names are not valid skillset names are outside this tool's namespace and
are ignored.

Listing also validates every registered source skill against the other
effective scope. An identical canonical target in both scopes is allowed. A
same-named entry with any different target or entry kind is an operational
error because Claude Code's personal-over-project precedence would mask the
local skill. This check applies to combined, global-only, and local-only
listing so no view presents a conflicting registration as effective.

Read-only listing never creates `.claude`, `skills`, or `.skillsets`.

Combined listing covers only global and exact-current-directory
registrations. It must not claim to enumerate every skill Claude can discover
from ancestor, descendant, enterprise, bundled, or plugin locations.
If a global registration was enabled outside a project containing a
same-named local skill, listing from that project reports the conflict and
requires one registration to be disabled.

## Rename and removal interaction

Rename and removal must refuse a set with either:

- a canonical global Codex link; or
- any entry at the expected global Claude registration path.

The Claude check treats a malformed entry as blocking because renaming or
removing the source could make recovery harder. The diagnostic identifies
whether Codex, Claude Code, or both block the operation and tells the user to
disable or repair those registrations first.

Absence is trusted only through missing or real global Claude containers. If
an existing `~/.claude` or `~/.claude/.skillsets` container is a symlink or
another non-directory entry, the lifecycle guard cannot safely prove that the
expected registration is absent and blocks rename or removal with the
container path.

As with current Codex behavior, local registrations outside the current
directory are not globally indexed. README documentation must tell users to
disable local Claude registrations before renaming or removing their source
set. Stale local registrations remain diagnosable from their own project
directory.

## Reliability and concurrency

Claude commands may use advisory locking to reduce accidental overlap. This is
best effort, not a guarantee against concurrent edits or direct upstream use.
Registration state lets `enable` reconcile normal partial projections and lets
`disable` remove its owned links before the registration. Ordinary operational
failures exit 1; Ctrl+C remains exit 130 when the CLI can provide useful normal
recovery information. The detailed local policy is
`docs/guides/local-cli-reliability.md`.

## Implementation boundaries

### `lib/skillset/claude.py`

Add a Claude-specific module rather than parameterizing `codex.py`. The two
integrations share CLI vocabulary and rendering, but their filesystem
transactions are different:

- Resolve global and exact-current-directory Claude containers.
- Inventory real direct source skill directories.
- Validate registrations and projected links without following them.
- Implement enable, reconciliation, disable, and synchronized-name discovery.
- Reuse `layout` validation and `metadata` scoped rendering.
- Format product-specific paths and operational errors.

Keep `lib/skillset/codex.py` behavior unchanged. A future refactor may extract
small path or parser helpers after both integrations have stable tests, but
must not obscure Claude's multi-link ownership model.

### `lib/skillset/cli.py`

- Add the `claude` parser, nested commands, scope options, and dispatch.
- Extract a small parser helper shared by Codex and Claude only if it preserves
  current help and usage behavior.
- Treat `claude list` as read-only inspection for lock creation.
- Keep usage errors at exit 2 and operational errors at exit 1.
- Preserve exit 130 plus actionable recovery text for a classified Claude
  interruption.

### `lib/skillset/errors.py`

- Add a narrowly scoped carrying exception only if needed to distinguish a
  classified interruption from an ordinary operational failure.
- Do not change existing error formatting or statuses for Codex and other
  commands.

### `lib/skillset/operations.py`

- Extend global discovery guards for rename and removal.
- Report all blocking integrations deterministically.
- Do not scan for local project registrations.

### `lib/skillset/completions.py`

- Add `claude` to top-level Bash, Zsh, and Fish completions.
- Complete `enable`, `disable`, `list`, managed set names, scope flags, and
  verbose listing exactly as for `codex`.
- Update completion contract tests, including positional counting around
  options and `--`.

### `lib/skillset/metadata.py`

No new rendering model is required. Reuse `list_named_sets` and
`list_scoped_sets`. Change this module only if a narrowly reusable input shape
is needed; preserve all existing output bytes.

### `README.md`

Add a "Use skillsets in Claude Code" section covering:

- flattened per-skill links and the hidden registration;
- global and exact-current-directory examples;
- scope and listing output;
- name collision behavior;
- cross-scope collision refusal and the identical-target exception;
- rerunning enable after source membership changes;
- partial-operation recovery;
- Claude session restart caveat when a top-level skills directory is newly
  created;
- the machine-specific absolute links created by `--local` and the need to
  exclude generated Claude state from commits without ignoring hand-authored
  project skills;
- Claude Code's personal-over-project precedence as the reason different-target
  global/local name collisions are refused;
- disabling global and known local registrations before rename/removal.

### `tests/test_skillset.py`

Continue using black-box isolated-home tests. Do not invoke Claude Code or use
network access in the automated suite.

## Required test coverage

### Command grammar and completion

- Top-level help includes exactly the new `claude` command.
- Claude nested help, missing subcommands, mutually exclusive scopes, unknown
  options, and usage exit statuses.
- Bash, Zsh, and Fish complete Claude commands, names, scopes, and verbose
  flags without changing Codex completion.

### Projection and ownership

- Global enable creates one flat absolute link per real direct source skill
  and one registration; it never creates a collection link under `skills`.
- Local enable uses the exact subprocess working directory and leaves global
  state unchanged.
- Managed, manual, and empty skillsets.
- Repeated enable is byte-for-byte and inode-stable where no reconciliation is
  needed.
- Enable adds newly introduced source skills and removes dangling stale owned
  links after source removals.
- Direct source skill symlinks are refused before mutation.
- Existing unrelated files, directories, relative links, and absolute links
  with different targets cause collision refusal without replacement.
- A same-parent alias whose link name differs from its target basename is
  never owned and survives reconciliation and disable.
- A pre-existing exact canonical link is explicitly adopted when enable
  creates the missing registration.
- Multiple skillsets coexist when names are disjoint and collide
  deterministically when names overlap.
- Trailing slashes in otherwise canonical absolute targets are accepted, but
  targets containing interior `.`, `..`, or alternate absolute spellings are
  noncanonical and are never adopted or removed.

### Disable and recovery

- Disable removes all owned links and its registration but preserves every
  unrelated `.claude` entry and all containers.
- Missing registrations are accepted as an idempotent recovery state: any
  remaining canonical projection is cleaned and the result is verified.
  Noncanonical registrations are refused.
- A canonical registration with a partial projection can be completed by
  enable or cleaned by disable.
- Dangling owned links for removed source children are cleaned by disable.
- Fault injection covers failures before and after registration creation,
  per-skill symlink creation, stale-link unlink, projected-link unlink, and
  registration unlink.
- Interrupted pre- and post-syscall cases retain exit 130 and include
  actionable observed-state recovery text.
- Every injected partial state has an asserted recovery command and final
  filesystem state.

### Listing and lifecycle

- Combined, global-only, and local-only plain output.
- Verbose alignment, TTY scope colors, manual `[m]`, `NO_COLOR`, and
  `TERM=dumb`.
- Global/local path deduplication when the working directory is HOME.
- Global/local different-target skill-name collisions are refused before
  enable mutation in either order; identical canonical targets are allowed.
- Listing reports a cross-scope collision created by enabling a global skill
  outside an already registered local project's directory.
- Read-only list does not create missing Claude paths.
- Incomplete recognized registrations fail with actionable recovery text.
- Validly named noncanonical registration entries fail visibly rather than
  disappearing from list output; invalidly named entries remain ignored.
- Global Claude registration blocks rename and removal, including a malformed
  expected registration entry.
- Malformed global Claude containers conservatively block rename and removal
  because registration absence cannot be proven without following them.
- Local registrations retain the documented untracked caveat.
- Existing Codex guard text and behavior remain covered.

### Full verification

Run:

```sh
python3 -m unittest discover -s tests
python3 -m compileall -q bin lib tests
git diff --check
```

Then search implementation-facing files for leaked planning terminology and
review every changed path against the ownership rules:

```sh
rg -n "phase|milestone|ticket|bead" bin lib tests README.md
```

## Rejected alternatives

### Link the complete set below `.claude/skills`

```text
.claude/skills/personal -> ~/.agents/skillsets/personal/skills
```

Rejected because Claude Code expects `personal/SKILL.md`; it does not discover
the child skill directories through this grouping level.

### Replace `.claude/skills` with a link to one set

This would make membership changes automatic and switching atomic, but it
would replace the user's project skill container, prevent unrelated local
skills, and allow only one selected set. It conflicts with the existing Codex
integration's non-destructive, additive behavior.

### Store an absolute JSON manifest in the project

A manifest can list every projected link, but introduces non-portable
machine-specific content that may be accidentally committed. A canonical
registration symlink plus lexical ownership of immediate child targets
contains enough information to reconcile and disable safely.

### Infer enablement from flat skill links alone

Rejected because an empty set cannot be represented, independently created
canonical links cannot be distinguished from a complete registered
projection, and interrupted operations lack durable recovery intent.

### List masked cross-scope registrations as synchronized

Rejected because Claude Code resolves a personal skill before a same-named
project skill. Presenting both registrations through the existing list
renderer would imply that the local skill is effective. The stricter invariant
rejects different-target collisions and treats externally created conflicts
as operational errors; exact links to the same source remain harmless.

### Convert each skillset into a Claude plugin

Plugins support suites but add manifests, marketplace and settings state,
namespace commands as `plugin:skill`, and extend beyond the requested skill
discovery feature.

### Generalize Codex and Claude into one integration engine immediately

The shared surface is small, while the mutation and ownership models differ.
Premature generalization would either encode Claude-specific transaction state
as conditionals or weaken Codex's simple single-link safety boundary.

## Implementation checklist

1. Add black-box command and projection tests that fail against the current
   code.
2. Implement the Claude registration and projection module with focused
   preflight helpers.
3. Add CLI parsing, dispatch, and inspection lock classification.
4. Extend rename/removal integration guards.
5. Add Bash, Zsh, and Fish completions plus their contract tests.
6. Add fault-injection tests for every multi-link state boundary and verify
   recovery convergence.
7. Document the feature and current-directory semantics in README.
8. Run full verification and review existing Codex output for byte-level
   regressions.

## Implementation result

The implementation lives in `lib/skillset/claude.py`, with CLI, lifecycle,
completion, documentation, and black-box test integration in the boundaries
described above. The verified projection creates no collection-level link
under `.claude/skills`, preserves Codex behavior, and retains a canonical
registration as recovery intent across partial multi-link operations.
