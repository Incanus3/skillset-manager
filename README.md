# Named Agent Skillsets

`skillset` manages multiple named global agent skill collections under
`~/.agents/skillsets` and activates one collection through stable relative
symlinks. Collections can be upstream-managed or explicitly hand-managed. The
Linux-only CLI provides lifecycle, inspection, and diagnostic commands plus
managed delegation to the upstream `skills` CLI.

<p align="center">
  <img src="agents.png" alt="Pixel-art agent in front of blue terminal code" width="320">
</p>

## Requirements and PATH

The CLI requires Linux and Python 3 and uses only the Python standard library.
Add its directory to your shell startup file using the syntax for your shell, then start a new shell:

```sh
# Bash and Zsh
export PATH="$HOME/.agents/bin:$PATH"
```

```fish
# Fish
fish_add_path "$HOME/.agents/bin"
```

## Use an alternate home directory

`skillset` stores its managed data under `$HOME/.agents`. To operate on a
different home directory for a single command, override `HOME` for that command:

```sh
HOME=/path/to/alternate-home skillset list
```

This reads the managed layout from `/path/to/alternate-home/.agents`. The
alternate home directory must already exist. The override also applies to any
upstream `skills` command delegated through `skillset skills`.

## Store skillsets in another directory

By default, named collections live in the real `~/.agents/skillsets`
directory. To keep them in a repository or another durable location, create
that directory first and add a real `~/.agents/config.json`:

```json
{
  "version": 1,
  "skillsets_directory": "/home/alice/Repos/dotfiles/skills"
}
```

The path must be absolute and normalized, outside the managed `~/.agents` root,
and it must name an existing real directory rather than a symlink. The
configured directory contains the named set directories (`default/`, `work/`,
and so on), not one flat collection of skills. Configuration does not permit
symlinked sets, `skills/` directories, or individual skill directories.
Use a dedicated directory inside the Git repository, not the repository root;
otherwise repository metadata such as `.git` is treated as a named skillset and
makes the configured layout invalid.

On a fresh installation, write the config before initialization:

```sh
mkdir -p /home/alice/Repos/dotfiles/skills
skillset init default
```

Initialization creates the exact absolute
`~/.agents/skillsets -> /home/alice/Repos/dotfiles/skills` link and creates the
initial named set in the configured directory. Other valid named sets may
already be present, but the initial name must be unused. Runtime aliases and
locks remain under `~/.agents`.

To migrate an initialized installation, stop concurrent `skillset` and
delegated upstream commands, move the real `~/.agents/skillsets` directory to
the desired destination, write `config.json`, and replace the old location with
the exact absolute link. Then run:

```sh
skillset doctor
skillset list
skillset current
```

One `~/.agents` installation should own a configured directory. Sharing the
same directory between installations with independent advisory locks is not
supported. An alternate `HOME` continues to select both its own
`.agents/config.json` and its own runtime state.

## Shell completions

Load completions for the current shell session:

```sh
# Bash
source <(skillset completions bash)

# Zsh
source <(skillset completions zsh)

# Fish
skillset completions fish | source
```

For persistent completion, redirect the generated script to a file in your shell's normal completion directory and
restart the shell. The destination depends on the shell and distribution. For Zsh, use an underscore-prefixed filename
such as `_skillset` in a directory on `fpath`; `compinit` will discover and autoload it.

Script generation does not require an initialized or healthy managed layout. Command and option completion is always
available after loading the script; existing skillset-name completion calls `skillset list` and therefore requires a
healthy managed layout at completion time. Arguments following `skillset skills` are left to the upstream CLI.

## Initialize the current installation

Choose a lowercase name for the current global collection:

```sh
skillset init default
```

This adopts existing real `~/.agents/skills` and
`~/.agents/.skill-lock.json` entries. Missing entries are created. Existing
symlinks or a partial managed layout are refused rather than guessed at.

## Create skillsets

Create an empty inactive set:

```sh
skillset create experiment
```

Create a hand-managed collection without upstream lock metadata:

```sh
skillset create --manual personal
```

Manual collections contain a real `skills/` directory and an empty
`.skillset-manual` marker, but never a local `.skill-lock.json`. Cloning a
collection preserves its mode. `--manual` and `--from` cannot be combined.

Or clone both the complete skills tree and lock metadata from another set:

```sh
skillset create experiment --from default
```

Create and activate an empty set in one command:

```sh
skillset create --use experiment
```

Clone and activate in one command:

```sh
skillset create --use --from default experiment
```

Options may appear before or after `NAME`. If creation succeeds but activation
fails before replacement, the new set remains and the previous set stays active;
inspect it and retry `skillset use NAME`.

Names use lowercase letters, digits, underscores, and hyphens, and must start
with a letter or digit.

## Activate a skillset

```sh
skillset use experiment
```

Activation atomically retargets `~/.agents/active`. Managed collections keep
the root lock alias pointed at `active/.skill-lock.json`; a manual collection
instead uses the read-only shared empty-lock sentinel
`~/.skillset-manual-empty-lock.json`. Keeping this runtime-owned file outside
the skillset repository prevents version-control tools from trying to rewrite
it during commits. `skillset use` recreates it when needed; `skillset doctor
--fix` can also restore a missing sentinel after confirmation. An interrupted activation leaves
a verified intent record in place and is completed only after confirmation via
`skillset doctor --fix`.

## Install and maintain skills

After activating the intended set, run upstream commands through the wrapper:

```sh
skillset skills add SOURCE
skillset skills list
skillset skills remove SKILL
skillset skills update
```

While a manual collection is active, lock-aware upstream commands (`add`,
`list`, `remove`, and `update`, including their aliases) are refused before
`npx` starts. Maintain those skills by editing their files directly. Scope-free
upstream commands such as `find` and `use` remain available.

For `add`, `list`/`ls`, `remove`/`rm`, and `update`, the wrapper injects
`--global` unless exact `-g` or `--global` is already present before an option
terminator. It inserts the flag before `--`, or appends it when no terminator is
present. Exact `-p` and `--project` options are rejected for those commands
because managed skillsets contain global state; tokens after `--` remain
literals. Scope-free `find`, `use`, and upstream `init` commands, as well as an
invocation with no upstream arguments, pass through unchanged:

```sh
skillset skills find formatter
skillset skills use SKILL
```

Unknown upstream commands also pass through unchanged, but the wrapper warns
on stderr that global scope was not injected. It does not reinterpret other
upstream arguments or output. The delegated process inherits terminal streams,
signals, and exit status; only its copied environment has `XDG_STATE_HOME`
removed so lock metadata resolves through the active managed alias.

All `skillset` management, inspection, diagnostic, and delegated operations first
take a stable, non-creating advisory lock on the existing HOME directory. Routine
operations then take `~/.agents/.skillset.lock`, always in that order, and retain
its existing on-disk compatibility. Routine managed inspection validates the
complete managed layout and remains read-only. `skillset augment skills list` is
a separate read-only discovery view: it neither requires nor validates the
managed layout and uses its managed lock only when an existing candidate is a
safe regular file. `doctor` aggregates invalid and partial state and acquires the
managed lock only when it is a safe regular file.
Delegation preserves both locks for the complete `npx skills` process lifetime,
so wrapper operations safely wait for one another. After initialization, always
prefer `skillset skills ...` for global installation and maintenance. Direct
`npx skills` commands cannot honor these locks and must not run concurrently with
any `skillset` operation.

## Inspect skillsets

List sets in sorted order. The active set is the only one prefixed with `* `:

```text
$ skillset list
* default
experiment
```

Hand-managed sets are annotated with `[m]` (yellow on a color-enabled TTY):

```text
$ skillset list
* default
personal [m]
```

Verbose output with either `-v` or `--verbose` uses an aligned inventory table.
Valid entries use declared skill names; malformed entries use their directory name
followed by `[invalid: REASON]`. A set with no inspectable entries shows `(no skills)`:

```text
$ skillset list --verbose
  SKILLSET   | SKILLS
  -----------|---------------------------------------------
* default    | alpha, broken [invalid: missing description]
  experiment | (no skills)
```

Print only the active name and its terminating newline for use in scripts:

```text
$ skillset current
default
```

Show the active set's direct skill directories, sorted by the displayed name:

```text
$ skillset show
SKILL            | DESCRIPTION
-----------------|-------------------------------
alpha            | First skill
broken-directory | [invalid: missing description]
```

`NAME` is optional for `skillset show [NAME]`: omitting it inspects the active
skillset, while an explicit name inspects that set whether it is active or
inactive. Non-empty sets use the headered, aligned `SKILL | DESCRIPTION` table
shown above. An empty set prints `No skills installed.` without table headers.
Manual sets first print `Manual skillset [m]: no upstream lock metadata.`.

When stdout is a TTY, `NO_COLOR` is absent, and `TERM` is not `dumb`, verbose
`list` and `show` make both header cells bold and valid skill names cyan. They
color `[invalid: missing description]` annotations yellow and every other invalid
annotation red, and dim every row's `|` delimiter and the complete separator.
Verbose `list` also makes the active marker and skillset name bold cyan and dims
`(no skills)`; `show` dims its empty-set message. All non-TTY output, including
pipes and redirects, is plain text; `NO_COLOR` and `TERM=dumb` also suppress ANSI
styling.

`show` reads UTF-8 `SKILL.md` files whose first line is exactly `---` and that
have a later exact `---` closing line. Before that close, top-level `name` and
`description` must each appear exactly once and be nonempty. The focused,
dependency-free reader supports plain scalars, YAML-style single quotes with
doubled apostrophes, JSON-compatible double-quoted escapes, and `|` or `>`
block markers with optional `+` or `-` chomping indicators (such as `>-`),
followed by indented block content. Plain and quoted values may
continue on indented physical lines, and trailing comments are ignored outside
quotes. It ignores extra keys and the body, and collapses whitespace in both
displayed values.

Malformed, non-UTF-8, or invalid decoded-Unicode candidates remain visible in
the `show` table as `<directory> | [invalid: <reason>]` and in verbose `list` as
`<directory> [invalid: <reason>]` inventory entries. Verbose `list` uses
`(no skills)` only when inspection finds no valid or invalid skill-directory
entries; ignored direct regular files do not prevent this state. Direct
skill-directory symlinks and `SKILL.md` symlinks are never followed. Declared
names and descriptions preserve ordinary printable Unicode, while terminal
controls, invisible format controls, and line/paragraph separators are rendered
as deterministic `\xNN`, `\uNNNN`, or `\UNNNNNNNN` escapes. Wrapper-created
table delimiters and line endings remain unchanged.

## Rename skillsets

Rename an inactive set without changing the active aliases:

```sh
skillset rename experiment trial
```

The active set can be renamed with the same command:

```sh
skillset rename default baseline
```

An active rename moves the complete set first and then atomically retargets
`~/.agents/active`; the stable root aliases remain unchanged. Rename refuses
any existing destination, including files and symlinks, without overwriting it.
If active retargeting fails before it commits, the directory rename is rolled
back. If rollback cannot restore a valid layout, the error names the old, new,
and active paths and identifies the remaining data location. Preserve that copy
and inspect the reported state before either moving the set back or retargeting
`active`; then run `skillset doctor`.

## Remove skillsets

Remove an inactive set with an interactive confirmation:

```text
$ skillset remove trial
Remove skillset 'trial'? [y/N] yes
```

Only `y` or `yes`, ignoring case and surrounding whitespace, confirms removal.
Use `--yes` for noninteractive operation:

```sh
skillset remove trial --yes
```

The active set is always refused, even with `--yes`. Activate another set with
`skillset use` before removing it.

## Use skillsets in Codex

Codex recursively discovers skills below `~/.codex/skills` and a project's
`.codex/skills` directory. Each enabled entry is an absolute link to a managed
skillset's `skills/` directory. The commands below never replace unrelated
Codex entries.

### Enable

Enable a skillset globally:

```sh
skillset codex enable personal
```

This creates `~/.codex/skills/personal` pointing to
`~/.agents/skillsets/personal/skills`. `enable` is idempotent for that exact
link and refuses to replace any other entry. It creates only missing real
`.codex` and `skills` directories.

Use `-l` or `--local` to manage a `.codex/skills` directory beneath the current
working directory instead. The target remains an absolute path derived from the
current user's home directory:

```sh
skillset codex enable personal --local
```

`-g`/`--global` explicitly selects `~/.codex` and is the default for `enable`
and `disable`. The scope flags are mutually exclusive and are available on
`enable`, `disable`, and `list`.

### Disable

Disable a canonical global link:

```sh
skillset codex disable personal
```

Use `--local` to disable the corresponding link in the current project instead.
`disable` removes only the expected absolute target; it refuses a missing or
unrelated entry.

### List

List every skillset Codex can discover from the global and current-project
locations:

```text
$ skillset codex list
[g] always-on
[g] personal [m]
[l] obra
```

`[g]` identifies a global link and `[l]` a local link. They are cyan and green,
respectively, on a color-enabled terminal. A skillset enabled in both locations
appears twice. There is no `*` marker: all listed skillsets are available to
Codex.

Use `-g`/`--global` or `-l`/`--local` to inspect one location only; the scope
marker is then omitted because it would be redundant:

```sh
skillset codex list --global
skillset codex list --local
```

Add `-v` or `--verbose` to either the combined or filtered listing to show the
same skill inventory table used by `skillset list`:

```sh
skillset codex list --verbose
skillset codex list --local --verbose
```

Rename and removal refuse a globally Codex-enabled skillset; disable it first
so the link cannot become stale. Local links are intentionally not tracked
outside their project directory, so disable them before renaming or removing
their referenced skillset.

## Use skillsets in Claude Code

Claude Code discovers direct skill directories rather than collection
directories. `skillset claude` therefore creates one flat link per direct
skill and records the owning collection separately:

```text
~/.claude/
├── .skillsets/
│   └── personal -> ~/.agents/skillsets/personal/skills
└── skills/
    ├── feature-status -> ~/.agents/skillsets/personal/skills/feature-status
    └── handoff -> ~/.agents/skillsets/personal/skills/handoff
```

The actual targets are absolute paths. Existing unrelated entries beneath
`.claude` are preserved.

Enable a collection globally, or beneath the exact current working directory:

```sh
skillset claude enable personal
skillset claude enable personal --local
```

Global scope is the default for `enable` and `disable`; an unscoped `list`
combines global and exact-current-directory registrations. `-g`/`--global` and
`-l`/`--local` are mutually exclusive and work with all three commands. More
than one collection can be enabled when their direct skill-directory names do
not overlap. Enable also checks the effective global and
exact-current-directory scopes against each other. A different-target name
collision is refused before registration or projected links are changed; an
identical canonical target in both scopes is allowed.

Rerun `enable` after adding or removing direct source skills. It adds missing
links, removes only stale links owned by that registration, and leaves
unrelated files, directories, and links intact. A partial operation retains
its registration as recovery intent: rerun the same `enable` to complete the
current projection, or run `disable` to remove its owned links.

Disable a global or exact-current-directory registration:

```sh
skillset claude disable personal
skillset claude disable personal --local
```

The registration is removed last. The `.claude`, `.claude/skills`, and
`.claude/.skillsets` containers remain even when empty.

List global and exact-current-directory registrations:

```text
$ skillset claude list
[g] always-on
[g] personal [m]
[l] obra
```

Use `--global` or `--local` to omit the redundant scope label, and
`--verbose` to include the normal skill inventory. This reports synchronized
registrations, not every skill Claude Code can discover from ancestor,
descendant, plugin, bundled, or enterprise locations. Claude Code gives a
personal skill precedence over a project skill with the same name, so listing
refuses different-target collisions across the effective global and local
scopes instead of presenting the masked local registration as available.

Global enable can preflight only the exact current project; local
registrations in other projects are not globally indexed. If a global skill
is later enabled from elsewhere, running `claude list` or `claude enable`
inside an affected project reports the collision. Disable one of the
conflicting registrations before using that local projection.

Local registrations and links contain machine-specific home paths. Keep this
generated state out of version control without ignoring any hand-authored
`.claude/skills` content that the project intentionally commits. The command
does not edit `.gitignore`.

Claude Code may need a session restart when a top-level skills directory is
created after the session starts. Changes inside an already watched skill
directory are normally visible through the live link.

Rename and removal operations refuse globally registered Claude Code
skillsets, including malformed registration state that cannot safely be
classified. Local
registrations are not indexed globally, so disable every known local
registration before renaming or removing its source set.

## Use skillsets in Auggie

Auggie, like Claude Code, discovers direct skill directories. `skillset
augment` therefore projects a managed collection as flat, absolute links and
keeps its registration outside the public skills directory:

```text
~/.augment/
├── .skillsets/
│   └── personal -> ~/.agents/skillsets/personal/skills
└── skills/
    ├── feature-status -> ~/.agents/skillsets/personal/skills/feature-status
    └── handoff -> ~/.agents/skillsets/personal/skills/handoff
```

Enable or disable a managed collection globally, or in the exact current
directory with `--local`:

```sh
skillset augment enable personal
skillset augment enable personal --local
skillset augment disable personal
skillset augment disable personal --local
```

Global scope is the default for `enable` and `disable`; an unscoped
`skillset augment list` combines global and exact-current-directory managed
registrations. `-g`/`--global` and `-l`/`--local` are mutually exclusive for
all three commands. `--verbose` adds the usual managed-skill inventory.

`enable` never replaces unrelated entries. It rejects different-target direct
skill-name collisions between the effective global and local `.augment`
projections, while allowing the identical canonical target in both scopes.
Rerun `enable` after changing direct source skills to reconcile missing and
stale links; `disable` removes owned projected links before its registration.
An interrupted or partial operation normally retains its registration as
recovery intent, so rerun the same `enable` or use `disable` to recover. If an
operation instead reports a preserved removal quarantine, inspect and recover
that exact path manually before running another Auggie command. Empty
containers remain in place.

Global Auggie registrations, including malformed registration state, block
rename and removal of their source skillset. Local registrations are not
globally indexed, so disable every known local registration before renaming or
removing its source set. Local `.augment` links and registrations contain
machine-specific absolute paths: do **not** commit this generated state. The
command does not edit `.gitignore` or unrelated entries.

### Inspect effective Auggie discovery

`skillset augment skills list` is separate from `skillset augment list`: it is
a read-only view of effective individual skills, not the managed registration
ledger. It scans all six documented discovery roots in this precedence order and prints each
winning skill in a `SKILL | SOURCE | DIRECTORY` table. `SOURCE` uses concise,
unbracketed labels: user roots are `~/.augment`, `~/.claude`, or `~/.agents`;
workspace roots are `./.augment`, `./.claude`, or `./.agents`. `DIRECTORY` is
the resolved skill-directory path. Paths under the configured home directory
use `~`; paths outside it remain absolute:

| Order | Precedence root | Skill root |
| --- | --- | --- |
| 1 | `User/.augment` | `~/.augment/skills` |
| 2 | `Workspace/.augment` | `$PWD/.augment/skills` |
| 3 | `User/.claude` | `~/.claude/skills` |
| 4 | `Workspace/.claude` | `$PWD/.claude/skills` |
| 5 | `User/.agents` | `~/.agents/skills` |
| 6 | `Workspace/.agents` | `$PWD/.agents/skills` |

Only direct child directories containing `SKILL.md` are candidates. The first
candidate for a skill-directory name wins; lower-precedence duplicates are
omitted. Effective winners print first in lexicographic concise source-label
order, then in canonical resolved skill-directory order. On eligible TTY output, headers are bold, dividers are
dim, skill names and `~/...` sources are cyan, and `./...` sources are green.
Captured output and TTY output with `NO_COLOR` set or `TERM=dumb` remain plain.
`--verbose` instead retains its non-tabular diagnostic blocks: its first line
uses bracketed concise source labels, followed by unchanged resolved-directory
and `SKILL.md` detail lines. The command resolves all six roots before
`--global` or `--local` filters the winners, so a lower-precedence local skill
shadowed by a global one is not reported as effective.

The `.claude/skills` and `.agents/skills` roots are compatible, read-only
external inputs to this view. Auggie management never creates, validates,
modifies, registers, or removes entries there; a same-name compatible skill
does not block a managed `.augment` projection because documented precedence
selects the effective skill.

## Diagnose the managed layout

Run the read-only diagnostic command after initialization, when another command
reports an invalid layout, or before attempting manual recovery:

```sh
skillset doctor
```

`doctor` first takes the stable advisory lock on the existing HOME directory. It
then inspects `.skillset.lock` without following it and, when it is a real regular
file, holds that lock for the full inspection. A missing `.agents` root or a
missing, symlinked, or nonregular managed lock is reported alongside missing
aliases, `active`, and `skillsets`; read-only `doctor` creates neither path.
It does not stop at the first invalid component. It checks all three canonical aliases, the active target
grammar and existence, direct skillset directory names and shapes, stale
use/create staging markers, readable version-3 lockfiles, and each direct skill
directory's `SKILL.md` metadata. Set directories, skill directories, and
`SKILL.md` files must be real entries; diagnostic inspection never follows their
symlinks.

Every finding is written to stderr on one line. Structural, alias, lockfile,
metadata, symlink, and staging problems are `skillset: error:` findings. A lock
entry without a corresponding real direct skill directory, or an installed
directory absent from the lockfile, is a `skillset: warning:` finding. Direct
regular files under `skills` are not installed skill directories and are
otherwise ignored. Finding text uses the same visible escaping for controls and
line separators, so each finding remains one physical line. Errors are printed
before warnings. Any error produces exit status 1; warnings alone and a healthy
layout produce status 0. A healthy run may print nothing.

## Recovery

Operations refuse invalid layouts and stale staging paths without deleting
them. When an error names recovery paths:

1. Preserve the only remaining copy of every skill directory and lockfile.
2. Run `skillset doctor` and review every error and warning before changing
   anything.
3. Inspect the concrete original, staged, old, new, and active paths named by
   the failed operation.
4. Restore a missing original only from its staged counterpart, or move a set
   back/retarget `active` only after confirming which path contains the data.
5. Run `skillset doctor` again after manual recovery.

`doctor --fix` can repair a deliberately small set of lossless omissions after
an interactive `y` or `yes` confirmation. It may create a missing advisory lock
and a missing version-3 empty lockfile only when that skillset's real `skills`
directory is empty. It never overwrites a file, follows a symlink, invents lock
metadata for installed skills, deletes stale markers, rewrites lock metadata,
changes aliases, or chooses between competing copies. Each created file is
reported as `skillset: repaired:`. Resolve every other finding manually only
after preserving the data it identifies.
