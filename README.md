# dotfiles

My personal configuration for macOS, managed with [chezmoi](https://www.chezmoi.io/).

## Goals

* I'm using these dotfiles on macOS systems, on Apple Silicon. At this time, I'm not interested in putting in much
  effort to make sure this works as expected on other operating systems. Linux lives separately, in
  [`aoberoi/dotfiles-linux`](https://github.com/aoberoi/dotfiles-linux).
* These dotfiles reflect my choices and preferences in software. In some ways, it also documents those preferences, as
  they will likely change over time.
* I want to be able to install and sync these settings on multiple machines with as low an effort as possible — and to
  let those machines differ from each other where they genuinely need to, without forking anything.

## Philosophy

Balancing convenience with simplicity. It's tricky because often times these things are at odds with one another.
* Simplicity - I want to understand everything in my configuration, at a medium-high level. Less is better.
* Convenience - I want to adopt solutions that make my life easier, and do less manually. More is better.

A concrete example

* I don't want to set up the most fancy `$PROMPT` which depends on custom icon fonts and runs many scripts that poll
  several kinds of state to produce a beautiful prompt. It would not only slow me down, but it would be harder to
  relate to other developers. I do intend to make content so I don't want my setup to be too exotic. But displaying
  the name of your git branch and a symbol for whether or not it has uncommitted changes has become common. This seems
  reasonable.

The same rule applies to the tooling here. Files are plain files unless something about them actually varies per
machine; only `dot_config/git/config.tmpl`, `dot_config/zsh/private_secrets.zsh.tmpl`, `.chezmoiignore` and two of the
scripts are templates. Everything else is ordinary content with runtime guards.

## Requirements

* Xcode command line tools (for `git`). macOS will offer to install them the first time `git` is invoked, and the
  Homebrew installer checks for them too.
* Nothing else. chezmoi bootstraps itself, and it installs Homebrew before it needs it.

## Setup on a new machine

One command:

```sh
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply aoberoi
```

`aoberoi` is GitHub shorthand for `github.com/aoberoi/dotfiles`. The repo is cloned into `~/.local/share/chezmoi`,
chezmoi's default source directory — there is no `sourceDir` override and no `~/.dotfiles` symlink to point at a
checkout elsewhere. `chezmoi cd` and `chezmoi source-path` are how you find it.

`chezmoi init` renders [`.chezmoi.toml.tmpl`](.chezmoi.toml.tmpl), which prompts for three things:

| Prompt | Example | Used for |
| --- | --- | --- |
| Machine short name (filename-safe) | `czimacos6457` | Selects `Brewfile.machine-<machine>` |
| Role (`personal` / `work`) | `work` | Selects `Brewfile.role-<role>`, gates the personal KDE credential block and the secrets file |
| Git author email | `me@example.com` | `user.email` in `~/.config/git/config` |

The answers land in `~/.config/chezmoi/chezmoi.toml`, which is per-machine and deliberately not in this repo.

Then, in order:

1. `run_once_before_10-install-homebrew.sh` installs Homebrew. It is a no-op if Homebrew is already there, and it
   refuses to install anywhere other than macOS on arm64, because the rest of the repo hard-codes the `/opt/homebrew`
   prefix.
2. chezmoi writes every managed file into `$HOME`.
3. `run_onchange_after_20-install-packages.sh.tmpl` runs `brew bundle install --no-upgrade` over the three Brewfile
   layers: base, then the role overlay, then the machine overlay.
4. `run_onchange_after_30-macos-defaults.sh` sets macOS defaults. It ends by asking you to log out and back in.
5. `run_onchange_after_50-install-git-hooks.sh.tmpl` points this repo's `core.hooksPath` at the tracked `.githooks/`
   directory, so the secret-scanning pre-commit hook is live in the fresh clone.

Two things to do afterwards:

* **Trust the taps.** See the next section — this is not optional, and it is not automated.
* **On a `work` machine, apply a second time.** `~/.config/zsh/secrets.zsh` is only rendered when the `op` binary is
  present, and `op` arrives in step 3 — after the file-writing phase of the same run. A plain `chezmoi apply` once
  1Password CLI is installed and unlocked fills it in.

Some Homebrew packages have caveats and follow-up work of their own; see [`runbooks/homebrew.md`](runbooks/homebrew.md).

## Trusting taps

Homebrew will not load anything from a non-official tap until it has been trusted, and it cannot check whether such an
entry is outdated. Trust is recorded in `~/.homebrew/trust.json`, which is **deliberately not managed by this repo**:
trusting a tap authorises it to run arbitrary code at install time, so it stays a conscious, per-machine act rather
than something a dotfiles clone hands out on your behalf. The install script never calls `brew trust` (D8).

**Casks need trusting too, and they need a different flag.** `brew trust` takes `--formula`, `--cask`, `--command`, or
a bare tap name for whole-tap trust; `--formula` does *not* cover a cask from the same tap. This is easy to miss,
because a cask that is already installed keeps working perfectly while untrusted — its binaries are on disk and run
fine. What you silently lose is upgrade visibility (`brew outdated` skips it) and installability on a fresh Mac.

The cost is that every new Mac needs these run by hand:

```sh
# base layer — every machine
brew trust --formula eth-p/software/bat-extras-batman
brew trust --formula anomalyco/tap/opencode
brew trust --cask    1password/tap/1password-cli

# role = work
brew trust --formula chanzuckerberg/tap/argus
brew trust --formula chanzuckerberg/tap/aws-oidc

# role = personal
brew trust --cask    deskflow/tap/deskflow
```

Casks from official taps (`ghostty`, `git-credential-manager`, the fonts, `kap`, `claude-code`, `monitorcontrol`) need
nothing.

Check the result:

```sh
brew trust --json v1                                     # what is currently trusted
brew doctor                                              # warns per-TAP, see below
brew bundle check --file="$HOME/.config/homebrew/Brewfile"
```

`brew doctor` warns at **tap** granularity, not per entry — a tap disappears from the warning as soon as *one* of its
entries is trusted:

```
Warning: The following taps are not trusted:
  1password/tap
```

So a green-ish `brew doctor` does not mean every entry in the Brewfiles is trusted. `brew trust --json v1` is the
authoritative view; check it against the command list above.

Until the commands above are run, `brew bundle check` prints one warning per untrusted entry, and reports it as
unsatisfied if it is not already installed:

```
Warning: Cannot check whether eth-p/software/bat-extras-batman is outdated because its tap is not trusted.
         Run `brew trust --formula eth-p/software/bat-extras-batman` to trust it.
```

`brew doctor` says it is *"ignoring formulae, casks and commands from these taps"*, which sounds absolute but is not.
Per [the Tap Trust docs](https://docs.brew.sh/Tap-Trust), *"an untrusted tap is not loaded … unless you explicitly
install a fully qualified formula or cask from that tap."* What an untrusted tap loses is **name resolution**, so a
fully-qualified entry (`brew "eth-p/software/bat-extras-batman"`) still installs untrusted, and only its outdatedness
check is skipped. Every tapped entry in the Brewfiles is written fully qualified for exactly this reason — don't
shorten one to its bare token.

**Two things break in ways you will not blame on Homebrew:**

* **`man`.** `dot_zshrc` sets `alias man='batman'`, and `batman` comes from `eth-p/software/bat-extras-batman`. On a
  machine where that formula has not been trusted, `man` is broken.
* **The whole `chezmoi apply`.** `private_secrets.zsh.tmpl` calls `onepasswordRead`, so a work machine without a
  working `op` fails the apply outright — and `op` is `1password-cli`, the cask above.

### Leftover taps

Uninstalling a package does not untap its tap, and neither does `brew bundle install` — it only ever adds. So removing
the last package from a tap leaves the tap behind, where it is inert but shows up in `brew tap` and trips the
`brew doctor` warning above. Clean up by hand:

```sh
brew untap <user>/<tap>
```

If a new tapped formula or cask is ever added to a Brewfile, add its `brew trust --formula` / `--cask` line to the list
above at the same time.

## Daily use

```sh
chezmoi edit --apply ~/.zshrc   # edit the source, write the result out on save
chezmoi diff                    # what an apply would change
chezmoi status                  # short form of the same question
chezmoi verify                  # exit 0 when $HOME matches the source; silent
chezmoi apply                   # write it all out
chezmoi cd                      # shell in the source directory
chezmoi update                  # git pull in the source, then apply
```

`edit.apply = true` is set in the config, so a bare `chezmoi edit <target>` applies on save too; the explicit
`--apply` above is just habit-forming.

**Source changes are still ordinary git commits.** `chezmoi edit` and `chezmoi apply` move content between the source
directory and `$HOME`; neither one touches git. Once a change works:

```sh
chezmoi cd
git add -p && git commit && git push
exit
```

`chezmoi git -- <args>` does the same thing without the subshell.

## Reconciling drift

**Read this before you go looking for a bug.** This repo uses chezmoi's default *copy* mode: `~/.zshrc` and friends
are real files, not symlinks into the repo. That is a deliberate choice, but it has one sharp edge, and it is the
single biggest behavioral difference from the old symlink-based setup.

**A program that rewrites its own config writes to the copy, and the next `chezmoi apply` silently reverts it.**

The concrete case in this setup is git:

```sh
git config --global user.name "Some Name"
```

`~/.gitconfig` does not exist here, so that writes to `~/.config/git/config` — which is chezmoi-managed, and generated
from a template. The edit is real, it works, and it disappears at the next apply with no warning.

### Detection

Make this reflexive *before* every apply:

```sh
chezmoi status      # two columns: last-written vs actual, then actual vs target
chezmoi diff        # exactly what an apply would change
chezmoi verify      # silent and exit 0 when everything matches
```

In `chezmoi status`, `M` in the second column means "apply will modify this" — i.e. the file in `$HOME` no longer
matches what the source would produce. That is the signal that something drifted and needs reconciling rather than
overwriting.

### Reconciliation

| Tool | Use | Limit |
| --- | --- | --- |
| `chezmoi re-add <target>` | Pull edits made in `$HOME` back into the source | **Will not overwrite templates.** Works for `~/.zshrc`; does nothing useful for `~/.config/git/config`, which comes from `config.tmpl` |
| `chezmoi merge <target>` | Three-way merge of destination / source / target in a merge tool | The right answer for templated files. Defaults to `vimdiff`; set `merge.command` if you want something else |
| `chezmoi merge-all` | Sweep every drifted target in one pass | — |

With no arguments, `chezmoi re-add` re-adds every modified file, so prefer naming the target you mean.

Why `re-add` refuses templates: it would have to un-render the file to know which parts came from `{{ .email }}` and
which are literal, and it can't. `merge` is the escape hatch — it puts the destination, the source and the rendered
target in front of you and lets you decide.

### Design-level options

If a file is genuinely owned by an application rather than by this repo, the fix is structural rather than a habit:

* **`create_` prefix** — chezmoi writes the file only if it is absent, then never touches it again. Right for "seed it
  once, the app owns it thereafter."
* **`modify_` prefix** — the source entry is a script that transforms the existing file. Lets you enforce a few keys
  while leaving everything else the app wrote alone.

Neither is in use today. **For git specifically, prefer editing the template over `git config --global`.** If that
proves too strict, the option not yet taken is to add an `[include] path = ~/.config/git/config.local` line to the
template and leave that file unmanaged as a home for machine-local overrides — but note that `--global` would still
target the main file, so it is a convention to adopt, not a guardrail that enforces itself.

## Per-machine model

Two answers from `chezmoi init` — `machine` and `role` — drive everything that differs between machines.

### Homebrew, in three layers

Applied in order; later layers add to earlier ones and never remove:

| Layer | Source path | Applied on |
| --- | --- | --- |
| base | `dot_config/homebrew/Brewfile` | every machine |
| role | `dot_config/homebrew/Brewfile.role-<role>` | every machine with that role |
| machine | `dot_config/homebrew/Brewfile.machine-<machine>` | one specific machine |

Each layer is a real Brewfile with native syntax and comments, and each is deployed to `~/.config/homebrew/` so
`brew bundle` can be run against any of them by hand. Both overlays are optional: the install script `stat`s the
source path first, so a role or machine with no overlay simply skips that step.

The `role-` / `machine-` prefixes are load-bearing. Without them a flat directory of `Brewfile.personal` and
`Brewfile.czimacos6457` gives no clue which kind of overlay each one is.

`.chezmoiignore` is itself a template, and that is what keeps other machines' overlays out of `$HOME`:

```
.config/homebrew/Brewfile.role-*
!.config/homebrew/Brewfile.role-{{ .role }}
.config/homebrew/Brewfile.machine-*
!.config/homebrew/Brewfile.machine-{{ .machine }}
```

Exclude-then-negate, and the ordering matters — keep each negation directly beneath the exclude it refines. Check the
result with `chezmoi ignored`.

`brew bundle install` is run with `--no-upgrade`. Applying dotfiles converges the *declared set*; upgrading is a
separate deliberate act (`brew upgrade`, or `brew bundle upgrade --file=…`).

### Other per-machine differences

* `dot_config/git/config.tmpl` templates `user.email` from the init prompt and guards the KDE credential block
  behind `role = personal`. GCM's benign `dev.azure.com` `useHttpPath` default is present on every machine that
  uses GCM; it does not imply that the machine uses Azure Repos.
* `dot_config/zsh/private_secrets.zsh.tmpl` renders `~/.config/zsh/secrets.zsh` only on `role = work`.

### Machine-local config is not in this repo

`~/.config/chezmoi/chezmoi.toml` holds the per-machine answers and is not version controlled. `.chezmoidata.toml`
holds the opposite — static values shared by every machine, committed here. Re-running `chezmoi init` will not re-ask
questions already answered; the prompts use the `…Once` variants.

## Secrets

Secrets never live in this repo. They live in 1Password, and a template pulls them in at `chezmoi apply` time, so the
source tree only ever contains an `op://` reference. [`.chezmoidata.toml`](.chezmoidata.toml) records the coordinates
— account, vault, item name — and nothing else.

The mechanics:

* `dot_config/zsh/private_secrets.zsh.tmpl` renders to `~/.config/zsh/secrets.zsh`. The `private_` prefix on the
  *filename* is what makes the result `0600`.
* It is gated on `role = work` and on the `op` binary being present. On a personal machine the template renders empty,
  and chezmoi removes the target rather than leaving a stale file behind.
* `dot_zshrc` sources it behind an existence guard, so its absence is harmless.
* The account is passed explicitly, because more than one `op` account is configured and `op read` otherwise fails
  with `multiple accounts found`.

Tradeoffs worth knowing: the plaintext sits on disk at `0600` between applies (the shell pays no 1Password cost at
startup); a value rotated in 1Password does not propagate until the next `chezmoi apply`; and if the vault is locked,
`onepasswordRead` fails, which aborts the *entire* apply rather than just that file. `onepassword.prompt = false` is
set so that failure is a legible error instead of a hang — though not always a fast one. Signed out, `op` errors in
about a second; if an unlock prompt is raised and left unanswered it waits out its authorization timeout first, so
`chezmoi` can sit silent for ~90s before reporting. `op` also re-locks on its own after a while, so a long session can
start erroring mid-way through — unlock and re-run.

**If a chezmoi command hangs instead of erroring, it is not chezmoi.** In a session driven by a remote client, macOS
app-data consent makes `open()` on 1Password's group container block forever waiting for a dialog on the physical
console, and `op` — and therefore every chezmoi command — blocks with it. `onepassword.prompt` cannot help; the block
is below `op`. Confirm with `ls ~/Library/Group\ Containers/2BUA8C4S2C.com.1password`, which hangs the same way. Work
around it by path-scoping (`chezmoi status ~/.config/homebrew`); fix it by granting the consent at the console or
giving the client app Full Disk Access. Full detail in [AGENTS.md](AGENTS.md).

A pre-commit hook in `.githooks/` scans staged content for credential-shaped strings — built-in patterns first, then
`gitleaks` when it is installed, configured by [`.gitleaks.toml`](.gitleaks.toml). It is wired up by
`run_onchange_after_50-install-git-hooks.sh.tmpl` setting `core.hooksPath`, local to this repo only.

## Framework

This repo uses [chezmoi](https://www.chezmoi.io/). It previously used
[dotbot](https://github.com/anishathalye/dotbot), and the reasons for switching are worth recording accurately,
because one of them is not the reason people usually assume.

**dotbot itself is fine.** It is actively maintained and I have no complaint about the project. What was abandoned was
[`dotbot-brew`](https://github.com/wren/dotbot-brew), the plugin this repo depended on for Homebrew integration: last
commit 2022-04-17, and the very bug my `install.conf.yaml` was working around had an open, unmerged pull request four
years later. Homebrew is load-bearing here, so the dead piece was the piece that mattered.

**The stronger driver was templating.** dotbot has no conditional or templating layer at all. Its config can only
express "every machine gets exactly this." Once I had a work Mac and a personal Mac wanting different git emails,
different credential helpers and different package sets, that stopped being expressible. chezmoi has first-class
templates, init-time prompts, per-machine data and script lifecycle management, which is the whole of the
"Per-machine model" section above.

Two smaller wins came along with it: chezmoi bootstraps itself with a single `curl`, so there is no chicken-and-egg
problem with Python or Homebrew on a fresh machine; and it is already the tool in
[`dotfiles-linux`](https://github.com/aoberoi/dotfiles-linux), so patterns move between the two repos verbatim.

**What was given up.** dotbot's symlinks meant editing `~/.zshrc` edited the repo. chezmoi's default copy mode does
not, which is exactly the hazard the "Reconciling drift" section exists to manage. `edit.apply = true` and
`chezmoi edit --apply` recover most of the immediacy; the rest is habit.

## Reference

Deeper notes live in [`runbooks/`](runbooks/) and are not deployed anywhere:

* [`runbooks/chezmoi-migration-plan.md`](runbooks/chezmoi-migration-plan.md) — the full design record: every decision,
  why it was made, what was rejected, and what is deliberately deferred.
* [`runbooks/adding-a-machine.md`](runbooks/adding-a-machine.md) — step-by-step procedure for onboarding a new Mac,
  including the manual steps chezmoi deliberately does not automate.
* [`runbooks/homebrew.md`](runbooks/homebrew.md) — Homebrew common tasks, first-run caveats, and the Python notes.
* [`runbooks/zsh-notes.md`](runbooks/zsh-notes.md) — zsh startup file order and what belongs in which file.
* [`runbooks/git-notes.md`](runbooks/git-notes.md) — git credential setup.
* [`runbooks/vim-notes.md`](runbooks/vim-notes.md) — why the vim config is as small as it is.

Conventions for editing this repo — the source-path naming rules, the `exact_` asymmetry, where generated files may
and may not live — are in [`AGENTS.md`](AGENTS.md).
