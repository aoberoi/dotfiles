# AI Agent Instructions

This repository is a [chezmoi](https://www.chezmoi.io) **source tree** for macOS on Apple
Silicon. There is no `install` script and no dotbot; chezmoi renders this tree into `$HOME`.

Read this file before editing anything. Most of it is not chezmoi documentation — it is the
set of decisions in this repo that look like inconsistencies and are not. Several of them
will break the machine if "tidied up."

Background and rationale for every decision cited below (D-numbers, R-numbers, section
numbers) live in `runbooks/chezmoi-migration-plan.md`. That document is a *plan*: where it
disagrees with the tree, the tree wins.

---

## Orientation: the repo vs. the source directory

chezmoi reads from **one** source directory, and by default that is
`~/.local/share/chezmoi` (D5 — there is no `sourceDir` override in the config).

Before running any chezmoi command, check where that points:

```sh
chezmoi source-path          # chezmoi's source directory
pwd                          # the checkout you are editing
```

If they differ, **every** chezmoi command in this file needs `--source="$PWD"` (or
`--source=/path/to/checkout`). Without it the commands silently operate on a different tree —
`chezmoi managed` will print nothing and `chezmoi diff` will show no changes, which looks like
success and is not.

Per-machine state lives outside the repo and is not version controlled:

| Path | Contents |
| --- | --- |
| `~/.config/chezmoi/chezmoi.toml` | answers to the `chezmoi init` prompts: `.machine`, `.role`, `.email`, plus `edit.apply` and `onepassword.prompt`. Generated from `.chezmoi.toml.tmpl`. |
| `~/.config/chezmoi/chezmoistate.boltdb` | the state database: `run_once_` script hashes, entry states. **Lives with the config, not with the source** — see the `run_once_` trap below. |

Edits are in **copy mode** (D1), not symlinks: `~/.zshrc` is a real file, and editing it does
*not* reach this repo. Use `chezmoi edit <target>` (`edit.apply = true` is set, so saving
applies) or edit the source file here and `chezmoi apply`.

---

## Layout

```
.
├── .chezmoi.toml.tmpl                     init prompts → ~/.config/chezmoi/chezmoi.toml
├── .chezmoidata.toml                      static shared data (1Password coordinates)
├── .chezmoiignore                         itself a template; repo-only files + overlay filtering
├── .chezmoiscripts/
│   ├── run_once_before_10-install-homebrew.sh
│   ├── run_onchange_after_20-install-packages.sh.tmpl
│   ├── run_onchange_after_30-macos-defaults.sh
│   └── run_onchange_after_50-install-git-hooks.sh.tmpl
├── .githooks/pre-commit                   secret guard; wired via core.hooksPath
├── .gitleaks.toml                         gitleaks ruleset used by that hook
├── .gitignore
├── .vscode/settings.json
├── AGENTS.md                              this file (ignored by chezmoi)
├── CLAUDE.md                              contains only `@AGENTS.md` (ignored by chezmoi)
├── README.md                              human-facing docs (ignored by chezmoi)
├── runbooks/                              design notes and tool cheatsheets (ignored)
├── dot_config/
│   ├── ghostty/config
│   ├── git/
│   │   ├── config.tmpl                    templated: email, personal KDE block, shared GCM defaults
│   │   └── ignore                         git reads ~/.config/git/ignore natively
│   ├── homebrew/                          three layers, applied in order (D3)
│   │   ├── Brewfile                       base — every machine
│   │   ├── Brewfile.role-personal
│   │   ├── Brewfile.role-work
│   │   └── Brewfile.machine-czimacos6457
│   └── zsh/
│       ├── private_secrets.zsh.tmpl       → ~/.config/zsh/secrets.zsh, 0600, 1Password-backed
│       └── zsh_plugins.txt                antidote plugin manifest
├── dot_local/bin/executable_git_blobless_clone
├── dot_vim/vimrc
├── dot_zprofile                           plain file — runtime guards, not templates
├── dot_zshrc                              plain file
└── exact_dot_zfunc/                       hand-written autoload functions ONLY
    ├── fnm_upgrade
    └── sizeup
```

Layout is **flat** — no `.chezmoiroot` (D2), deliberately, so patterns copy verbatim to and
from the sibling `dotfiles-linux` repo.

### Source name → target mapping

chezmoi derives the target path and its attributes from the source filename prefixes. Adding
a file means naming it correctly; there is no manifest to update.

| Prefix / suffix | Effect on the target |
| --- | --- |
| `dot_` | leading `.` — `dot_zshrc` → `~/.zshrc`, `dot_config/git/ignore` → `~/.config/git/ignore` |
| `private_` | mode `0600` |
| `executable_` | mode `+x` (`0755`) |
| `exact_` (directories) | chezmoi **deletes** anything in the target directory it does not manage |
| `.tmpl` | rendered as a Go text/template; the suffix is stripped from the target name |
| `run_` | script; runs on **every** apply |
| `run_once_` | script; runs once per distinct rendered content, ever |
| `run_onchange_` | script; runs whenever its rendered content differs from last time |
| `before_` / `after_` | on scripts: run before / after the file-writing phase |
| `create_` | write only if the target is absent, then never touch it again |
| `modify_` | the source entry is a script that transforms the existing target |
| `remove_` | delete that specific target |

Prefixes compose in a fixed order, e.g. `exact_dot_zfunc`, `private_secrets.zsh.tmpl`,
`run_onchange_after_20-install-packages.sh.tmpl`.

Entries whose names start with `.` are ignored by chezmoi automatically (`.git/`, `.githooks/`,
`.vscode/`, `.gitignore`, `.gitleaks.toml`) — they need no `.chezmoiignore` rule. `README.md`,
`AGENTS.md`, `CLAUDE.md` and `runbooks` **do**, and have them.

---

## The `exact_` asymmetry is deliberate — do not "fix" it

`exact_dot_zfunc/` uses `exact_`. `dot_local/bin/` does not. This is not an oversight, and
making them consistent breaks the machine.

- **`~/.zfunc` is wholly repo-owned.** Nothing else writes there. A stale entry is actively
  harmful, because `~/.zfunc` is prepended to `FPATH` *after* Homebrew's site-functions, so a
  leftover completion there shadows the fresher packaged one. `exact_` buys deletion
  propagation and the cost is zero.
- **`~/.local/bin` is shared.** `dot_zprofile` puts it on `$PATH` and annotates it *"Used by
  uv"*; uv installs tool shims there. Adding `exact_` would make chezmoi delete every one of
  those shims on **every apply**. Disqualifying.

This is a deferred decision, not an accident: **see R1 in §2 of the runbook**, which records
the reasoning and the three options for revisiting it. If deletion propagation is ever wanted
in `~/.local/bin`, the answer is a `remove_<name>` entry (surgical, cheap), not `exact_`.

### Generated files never go in an `exact_` directory

`exact_` deletes what chezmoi does not manage, so a file written by some other tool into
`exact_dot_zfunc/`'s target is removed on the next apply. §4.5 fixes where each kind of
completion belongs:

| Kind of file | Home | Managed by |
| --- | --- | --- |
| Hand-written autoload functions (`fnm_upgrade`, `sizeup`) | `~/.zfunc` | chezmoi, `exact_` |
| Completions shipped by a package | `$(brew --prefix)/share/zsh/site-functions` | Homebrew |
| Completions that genuinely must be generated | `~/.local/share/zsh/site-functions` | a `run_onchange_` script — **not** chezmoi-managed |

Row 3 currently has no occupants. Prefer row 2 whenever the tool ships its own completion:
put its directory on `FPATH` rather than checking a copy in. (`_rustup` was checked in for
years, shadowed the newer Homebrew copy, and was deleted for exactly this reason.)

**`FPATH` ordering constraint in `dot_zshrc`:** the `belak/zsh-utils path:completion` plugin
calls `compinit`. Everything that adds to `FPATH` must run **before** `antidote load`, and
every `compdef` must run **after** it. Preserve that ordering across any edit.

---

## Homebrew: three layers (D3)

Applied in order; later layers only add.

| Layer | Source | Applied on |
| --- | --- | --- |
| base | `dot_config/homebrew/Brewfile` | every machine |
| role | `dot_config/homebrew/Brewfile.role-<role>` | every machine with that role (`personal` \| `work`) |
| machine | `dot_config/homebrew/Brewfile.machine-<machine>` | one specific machine |

The `role-` / `machine-` prefixes are load-bearing: they keep the two overlay kinds
unambiguous in one flat directory, and they let `.chezmoiignore` filter with one
exclude-then-negate pair per kind:

```
.config/homebrew/Brewfile.role-*
!.config/homebrew/Brewfile.role-{{ .role }}
```

Order matters — keep each negation directly beneath the exclude it refines. Only the matching
overlays are ever written to `$HOME`; confirm with `chezmoi ignored`.

**Placement rule.** Employer tooling that any work Mac would want goes in `Brewfile.role-work`,
not in a machine overlay. A machine overlay is for things tied to that physical machine (e.g.
a display utility for one desk setup).

---

## Scripts, and the traps found the hard way

Scripts live in `.chezmoiscripts/` (never written to `$HOME`) and run alphabetically within
the `before_` and `after_` groups, hence the numeric prefixes.

| Script | When | Purpose |
| --- | --- | --- |
| `run_once_before_10-install-homebrew.sh` | once, before | Install Homebrew. Apple-Silicon-only; installs no packages and trusts no taps. |
| `run_onchange_after_20-install-packages.sh.tmpl` | onchange, after | `brew bundle install --no-upgrade` over the three layers. `after_` because the Brewfiles must be written first. |
| `run_onchange_after_30-macos-defaults.sh` | onchange, after | `defaults write` settings that are hard to set in the UI. |
| `run_onchange_after_50-install-git-hooks.sh.tmpl` | onchange, after | Points this repo's `core.hooksPath` at `.githooks`. |

### `run_once_` state outlives the source directory

`run_once_` is recorded in `~/.config/chezmoi/chezmoistate.boltdb` under `scriptState`, keyed
by the **sha256 of the rendered script content**. That database sits with the *config*, not
with the source tree. So a `run_once_` script whose job depends on *where the source lives*
will not re-run after the source moves — it is already marked done, silently.

This is exactly why `50-install-git-hooks` is `run_onchange_` and embeds
`repo={{ .chezmoi.sourceDir | quote }}`: moving the source changes the rendered content, which
re-fires the script. Do not "simplify" it to `run_once_`.

Inspect the state with `chezmoi state dump`.

### `run_` makes `chezmoi verify` useless

A bare `run_` script is *permanently pending*: `chezmoi status` always shows it as ` R`, and
`chezmoi verify` therefore exits non-zero **forever**, destroying its value as a drift
detector. (Measured: `run_` → `verify` exit 1; `run_once_` after one apply → exit 0.) Do not
introduce `run_` scripts in this repo.

### Do NOT add `set -euo pipefail` to `run_onchange_after_30-macos-defaults.sh`

Two independent reasons, both real:

1. Its platform guard, `` [ `uname` != Darwin ] && echo "Skipping macOS setup." && exit 0 ``,
   evaluates to non-zero **on macOS** — the test fails there. Under `set -e` the script would
   abort on precisely the platform it targets, taking the whole apply with it.
2. `killall Dock` exits non-zero when no Dock is running (SSH-only sessions).

Both are harmless only because there is no `set -e`. The other three scripts *do* set it, and
should keep it — the exception is specific to this one file. It is `run_onchange_` rather than
`run_` on purpose: `killall Dock` is disruptive and should stay rare. The consequence is that
changing one of these settings by hand in System Settings is **not** re-asserted on the next
apply.

### The install-packages script must never run `brew trust` (D8)

Trusting a third-party tap authorises it to run arbitrary install code. That stays a
deliberate, manual, per-machine act; `~/.homebrew/trust.json` is not repo-managed. The README
lists the `brew trust` commands to run by hand.

**Untrusted still installs — but only for fully-qualified names.** This is the load-bearing
detail, and `brew doctor`'s wording obscures it. Doctor says *"Homebrew is currently ignoring
formulae, casks and commands from these taps"*, which sounds absolute. It is not: what an
untrusted tap loses is **name resolution**, not installability.
[docs.brew.sh/Tap-Trust](https://docs.brew.sh/Tap-Trust) is explicit —

> An untrusted tap is not loaded when tap trust is required unless you explicitly install a
> fully qualified formula or cask from that tap.

Homebrew's own source agrees: `Library/Homebrew/bundle/brew.rb` comments that *"fully
qualified tap formulae can be checked by their Cellar rack name without loading the formula
from an untrusted tap,"* and its untrusted branch emits `opoo "Cannot check whether … is
outdated"` then returns early — warn, skip the outdatedness check, proceed.

So in a Brewfile, **always write tapped entries fully qualified**:

```
brew "eth-p/software/bat-extras-batman"     # resolves untrusted
cask "1password/tap/1password-cli"          # resolves untrusted
cask "1password-cli"                        # NEEDS the tap loaded — fails untrusted
```

An unqualified token cannot even be trusted in advance: both `bundle/brew.rb` and
`bundle/cask.rb` guard their trust calls with `if … Utils.full_name?(…)`, commented *"only
fully-qualified names map to a tap, so unqualified tokens cannot be meaningfully trusted."*
Every tapped entry in this repo is fully qualified; keep it that way.

**Trust is per-kind.** `brew trust` takes `--formula`, `--cask`, `--command`, or a bare tap
name. `--formula` does not cover a cask from the same tap. An already-installed but untrusted
cask keeps working — its binaries are on disk — so the only symptom is that `brew outdated`
silently skips it. That is how `1password-cli` sat untrusted here unnoticed.

**Do not use the Brewfile `trusted:` option.** `tap`, `brew` and `cask` entries accept
`trusted: true`, which writes the trust entry before installing. It would make the warning go
away in one line, and adopting it would invert D8 — the point is that a dotfiles clone must
not hand out trust on your behalf. `brew bundle dump` emits it for already-trusted entries;
strip it if you ever re-dump.

`--no-upgrade` is also passed explicitly on every layer, deliberately: a bare `brew bundle
install` upgrades everything outdated. Applying dotfiles should converge the *declared set*;
upgrading is a separate act.

---

## Templates

Only three things are templates by design: `dot_config/git/config.tmpl`,
`dot_config/zsh/private_secrets.zsh.tmpl`, and `.chezmoiignore` itself. `dot_zprofile` and
`dot_zshrc` are **plain files with runtime guards** — keep them that way unless something
genuinely varies per machine.

Available data: `.machine`, `.role`, `.email` (from the per-machine config),
`.onepassword.*` (from `.chezmoidata.toml`), and chezmoi's own `.chezmoi.*` namespace.

**Traps:**

- **chezmoi evaluates template actions everywhere, including inside `#` comments.** A TOML or
  shell comment containing an example like `{{ .Destination }}` fails to render the whole
  file. Use a `{{/* … */}}` template comment instead — that is why the header comments in
  `.chezmoi.toml.tmpl`, `.chezmoiignore` and `private_secrets.zsh.tmpl` are written that way.
- **`include` resolves relative to the source directory**, so
  `include "dot_config/homebrew/Brewfile"` works from `.chezmoiscripts/`. `sha256sum` comes
  from sprig, which chezmoi bundles.
- **`stat` returns falsy for a missing file**, which is how the optional Brewfile layers are
  guarded — a role or machine with no overlay skips its stanza instead of failing to render.
  `stat` takes a *source* path, so build it with `joinPath .chezmoi.sourceDir …`.
- **A template that renders empty causes chezmoi to REMOVE the target.** This is load-bearing,
  not a bug: `private_secrets.zsh.tmpl` is gated on `role == "work"`, so on a personal machine
  it renders empty and `~/.config/zsh/secrets.zsh` is removed rather than left stale.
- A template error aborts computation of the **whole** target state, not just that one file.
  One bad template fails the entire apply.

### Secrets mechanism

Secrets are never committed. `private_secrets.zsh.tmpl` calls `onepasswordRead` at apply time
and writes `~/.config/zsh/secrets.zsh` at mode `0600`; `dot_zshrc` sources it behind an
existence guard. The coordinates (account, vault, item) are non-sensitive and live in
`.chezmoidata.toml`.

Two details that are easy to get wrong:

- The 1Password **account is the optional second argument to `onepasswordRead`**. There is no
  `onepassword.account` config key. With two accounts configured, omitting it makes `op read`
  fail with "multiple accounts found."
- `lookPath "op"` proves only that the binary exists, not that the vault is unlocked. If op is
  locked, the read fails and the whole apply fails. `onepassword.prompt = false` in the
  per-machine config makes that a legible error rather than a hang. Two shapes of that error,
  both measured on czimacos6457 2026-08-07:

  | State | Result | Latency |
  | --- | --- | --- |
  | signed out | `[ERROR] … account is not signed in`, exit 1 | ~1s |
  | unlock prompt dismissed or failed | `[ERROR] … response: promptError`, exit 1 | ~1s |
  | unlock prompt raised, unanswered | `[ERROR] … authorization timeout`, exit 1 | ~90s |

  So "legible rather than a hang" is right, but **not necessarily prompt** — op waits out its
  own authorization timeout before giving up, and chezmoi sits there the whole time. Do not
  conclude a command is wedged until you have given it two minutes. Note also that op
  re-locks on its own, so a long working session can start erroring part-way through; unlock
  and re-run. **This guarantee covers a locked vault only** — see the next section for a
  failure mode it cannot save you from.

`private_` must stay on the **filename**. Do not hoist it to a `private_dot_config/`
directory — two source entries mapping to `~/.config` is a source-state conflict.

### When `chezmoi status` hangs, suspect macOS, not chezmoi

Diagnosed on czimacos6457 2026-08-07. In a session driven by a **remote client**, bare
`chezmoi status`, `diff` and `apply` can hang forever, printing nothing.

The cause is macOS's app-data consent gate — the *"«App» wants to access data from other
apps"* dialog. `open()` on a third-party group container under `~/Library/Group Containers/`
does not fail when consent is missing; it **blocks indefinitely** waiting for a dialog that
renders on the physical console. `stat` still succeeds, so the directory looks fine.

The chain: `op` reaches 1Password's desktop CLI integration through a socket under
`2BUA8C4S2C.com.1password/` → blocks in `open()` → `onepasswordRead` never returns → and
because chezmoi computes target state for the **whole tree** before printing anything, one
wedged template stalls every command.

`onepassword.prompt = false` cannot help here. It governs only whether chezmoi shells out to
`op signin`; this block is in the kernel, one layer below `op`.

**Diagnose in one command** — this hangs too, which proves it is not chezmoi:

```sh
ls ~/Library/Group\ Containers/2BUA8C4S2C.com.1password
```

Not 1Password-specific: every un-consented third-party team-ID container behaves this way
(Todoist and WS1 Hub were also confirmed). Apple's `group.com.apple.*` containers do not.

**Work around it** by path-scoping away from the secrets template, which skips the `op` call:

```sh
chezmoi status ~/.config/homebrew
chezmoi diff ~/.zshrc
```

**Fix it** by granting the consent once at the console, or by giving the client app Full Disk
Access (System Settings → Privacy & Security), which supersedes app-data gating for every
container. A full `apply` is not available remotely until one of those is done.

Beware when timing this out: macOS ships no `timeout(1)`. For C programs — including the `ls`
probe above — `perl -e 'alarm 10; exec @ARGV' <cmd>` works, and exit 142 means it hung. It
does **not** work on `chezmoi` or `op`: both are Go, and the Go runtime handles `SIGALRM`
itself rather than dying on it, so the alarm is swallowed and you wait the full time anyway.
For those, background the command and `kill -9` it, then read its output file.

To see what a blocked process is actually waiting on, sample it — this is what identified the
gate as an `open()` block rather than anything in chezmoi or op:

```sh
<cmd> & pid=$!; sample $pid 2 -file /tmp/s.txt; kill -9 $pid; grep -E '^ +[0-9]+ ' /tmp/s.txt
```

---

## Verifying a change safely

Nothing below writes to `$HOME`, except the last section's `apply`.

```sh
# Render one template and read the result.
chezmoi execute-template < dot_config/git/config.tmpl
chezmoi execute-template < .chezmoiscripts/run_onchange_after_20-install-packages.sh.tmpl
chezmoi execute-template --init < .chezmoi.toml.tmpl

# What would change in $HOME, and what is currently drifted.
chezmoi diff
chezmoi status                 # M = destination differs from source; R = script pending
chezmoi verify                 # silent + exit 0 when everything matches

# What is managed. Note: bare `chezmoi managed` DOES list .chezmoiscripts/* entries —
# its default --include covers the `scripts` type. Do not assert that it must not.
chezmoi managed --include=files,dirs,symlinks

# Which source entries .chezmoiignore is filtering out (overlays, docs).
chezmoi ignored

# Full dry materialisation into a scratch tree — the strongest check.
# The destination directory must already exist.
mkdir -p /tmp/chezmoi-test
chezmoi apply --destination=/tmp/chezmoi-test --exclude=scripts
find /tmp/chezmoi-test        # compare against the real $HOME; check modes too

chezmoi doctor
```

Add `--source="$PWD"` to all of the above if `chezmoi source-path` is not this checkout.

**Test the per-machine matrix when you touch anything role- or machine-gated.** Varying
`.role` and `.machine` is the feature being bought; exercise both values and confirm the git
email, the personal-only KDE credential block, the shared Azure GCM default, the secrets file
and the Brewfile overlay selection each behave as intended.

**Copy-mode drift.** Because targets are copies, anything that rewrites a managed file in
`$HOME` (e.g. `git config --global …` writing `~/.config/git/config`) is silently reverted by
the next apply. Run `chezmoi status` before applying. To reconcile: `chezmoi re-add <target>`
pulls destination edits back into the source but **refuses templated files**; use
`chezmoi merge <target>` for those.

---

## Committing

A pre-commit hook refuses commits that look like they contain a credential. It is tracked at
`.githooks/pre-commit` and wired up by `core.hooksPath` (set per-repository, locally, by
`run_onchange_after_50-install-git-hooks.sh.tmpl`). Verify with:

```sh
git config --local --get core.hooksPath     # expect: .githooks
```

Two layers, so there is always some check:

1. A small built-in set of high-signal regexes (vendor-prefixed secret keys, AWS access key
   IDs, GitHub and Slack tokens, PEM private-key headers), matched only against **added**
   lines in the staged diff.
2. `gitleaks git --staged`, if gitleaks is installed. It reads `.gitleaks.toml` from the repo
   root, which extends the default ruleset with a shape-based rule that does not depend on the
   surrounding variable name. gitleaks is in the base Brewfile; its absence is a soft miss,
   not an error.

Both layers are tuned for very few false positives — a hook that cries wolf gets bypassed
reflexively. If you hit a genuine false positive, `git commit --no-verify` bypasses it. Do not
reach for that reflexively, and never to get a real value past the hook.

Do not commit or push unless you were asked to.

---

## Conventions

- **Less is better.** Prefer the configuration you can explain over the clever one. Prefer no
  file over a generated file, and a runtime guard in a plain shell file over a template.
- **Comment the non-obvious decision, in the file it affects.** The scripts and templates here
  carry long header comments explaining *why* a prefix or a flag was chosen. That is the house
  style; preserve it, and add to it when you make a similar call. Deeper rationale belongs in
  `runbooks/`.
- **Cross-machine, essential packages only** in the base Brewfile. Direct downloads are
  preferred over casks for apps that offer them; casks are used when the creator recommends it.
- **Local machine overrides stay outside the repo** — in `~/.config/chezmoi/chezmoi.toml`, or
  in an unmanaged file the managed one includes.
- Use `git mv` when relocating files so blame survives.
- `runbooks/` holds design history and per-tool notes (`homebrew.md`, `git-notes.md`,
  `zsh-notes.md`, `vim-notes.md`). Check the relevant one before changing a subsystem.
