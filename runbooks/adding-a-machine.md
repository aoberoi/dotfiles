# Adding a machine

The step-by-step procedure for bringing a new Mac onto these dotfiles, and for deciding where its
packages belong afterwards.

[`README.md`](../README.md) has the short version of the bootstrap and the tap-trust commands. This
runbook is the long version: what each prompt is actually asking, what chezmoi does and deliberately
does not do, how to add a per-machine Homebrew layer, and how to tell when the machine is done.

The worked example throughout is the **personal** Mac `iris`, because `role = personal` exercises
every branch that the original work-Mac migration did not.

---

## 0. Before you start

| Prerequisite | Notes |
| --- | --- |
| Xcode command line tools | macOS offers them the first time `git` runs, and the Homebrew installer checks too. Nothing else is needed — chezmoi bootstraps itself and installs Homebrew. |
| Apple Silicon | `run_once_before_10-install-homebrew.sh` refuses to install on anything else, because the repo hard-codes the `/opt/homebrew` prefix. |
| A real terminal | The init prompts are read from `/dev/tty`. Running the bootstrap with no controlling terminal fails with `could not open a new TTY: open /dev/tty: device not configured`. Do not run it over a pipe or from a script. |
| Three answers ready | Machine slug, role, git email — see the next section. |

Decide the **machine slug** before you begin. It must be filename-safe, because it becomes the
suffix of `Brewfile.machine-<slug>`. The existing work Mac uses its hostname, `czimacos6457`; a
personal machine can use anything descriptive, e.g. `mbp-personal`. It is deliberately *not*
defaulted from `scutil --get ComputerName`, which returns things like `Ankur's MacBook Pro`.

---

## 1. Bootstrap

One command, from a terminal on the new machine:

```sh
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply aoberoi
```

`aoberoi` is GitHub shorthand for `github.com/aoberoi/dotfiles`. The repo is cloned into
`~/.local/share/chezmoi` — chezmoi's default source directory. There is no `sourceDir` override and
no `~/.dotfiles` symlink; `chezmoi cd` and `chezmoi source-path` are how you find the checkout later.

### The three prompts, verbatim

`chezmoi init` renders [`.chezmoi.toml.tmpl`](../.chezmoi.toml.tmpl), which asks:

```
Machine short name, filename-safe (e.g. czimacos6457)?
> string

Role for this machine?
> personal/work

Git author email?
> string
```

| Prompt | Stored as | What it drives |
| --- | --- | --- |
| Machine short name | `.machine` | Selects `Brewfile.machine-<machine>`. Filename-safe because it is literally part of a filename. |
| Role | `.role` | Selects `Brewfile.role-<role>`; gates the personal KDE credential block and the 1Password-backed secrets file. Free text validated against the two choices. |
| Git author email | `.email` | `user.email` in `~/.config/git/config`. |

For the personal Mac the answers are, for example, `mbp-personal` / `personal` /
`aoberoi@gmail.com`.

### Where the answers land

In `~/.config/chezmoi/chezmoi.toml`, which is **per-machine and not in this repo** — that is the
whole point of D4. The rendered file looks like:

```toml
[data]
    machine = "mbp-personal"
    role    = "personal"
    email   = "aoberoi@gmail.com"
```

plus `edit.apply = true` and `onepassword.prompt = false`, which come from the template unchanged.

The prompts use the `…Once` variants, so re-running `chezmoi init` later to pick up a *new* setting
will not re-ask anything already answered. To change an answer, edit
`~/.config/chezmoi/chezmoi.toml` directly (or delete the key and re-run `chezmoi init`).

---

## 2. What happens automatically

With `--apply`, the bootstrap continues straight into a full apply. In order:

1. **`run_once_before_10-install-homebrew.sh`** installs Homebrew. No-op if `/opt/homebrew/bin/brew`
   already exists; warns rather than installing a second copy if `brew` is found at another prefix;
   refuses outright on non-arm64. It installs no packages and trusts no taps. A human has to be at
   the keyboard — the Homebrew installer's `sudo` prompt reads from `/dev/tty`.
2. **Files are written** into `$HOME`: `.zshrc`, `.zprofile`, `.config/git/{config,ignore}`,
   `.config/ghostty/config`, `.config/zsh/zsh_plugins.txt`, `.vim/vimrc`, `.zfunc/*`,
   `.local/bin/git_blobless_clone`, and the Homebrew layers under `.config/homebrew/`. Real files,
   not symlinks — see "Reconciling drift" in the README before you edit any of them in place.
3. **`run_onchange_after_20-install-packages.sh.tmpl`** runs `brew bundle install --no-upgrade` over
   the three layers in order: base → `Brewfile.role-<role>` → `Brewfile.machine-<machine>`. Each
   overlay is `stat`-guarded on its source path, so a machine with no overlay skips that step
   instead of failing. `--no-upgrade` is explicit: applying dotfiles converges the *declared set*,
   it does not mass-upgrade installed packages.
4. **`run_onchange_after_30-macos-defaults.sh`** writes the macOS defaults and ends with
   `killall Dock` and a "log out and log back in" message.
5. **`run_onchange_after_50-install-git-hooks.sh.tmpl`** points the fresh clone's
   `core.hooksPath` at the tracked `.githooks/` directory, so the pre-commit scanner is live. This
   is local to that repo and never leaks into others.

`brew "chezmoi"` is in the base Brewfile, so after step 3 chezmoi is Homebrew-managed. Check that
the bootstrap binary is not shadowing it:

```sh
command -v chezmoi        # want /opt/homebrew/bin/chezmoi
```

If the one-liner left a binary in `~/.local/bin` (it is on `$PATH` ahead of Homebrew), remove it.

---

## 3. Manual steps chezmoi deliberately does not do

Each of these is left out on purpose, and the reason matters as much as the command.

### 3.1 Trust the taps

**Why it is not automated (D8).** Trusting a tap authorises it to run arbitrary third-party code at
install time. That is a decision to make consciously, per machine, not something a dotfiles clone
confers on your behalf. Trust is recorded in `~/.homebrew/trust.json`, which this repo does not
manage, and the install script never calls `brew trust`.

Trust is per entry and per kind: a formula trust does not cover a cask from the same tap. The
commands needed across the current machine roles are:

```sh
# base layer — every machine, regardless of role
brew trust --formula eth-p/software/bat-extras-batman
brew trust --formula anomalyco/tap/opencode
brew trust --cask 1password/tap/1password-cli

# role = work only
brew trust --formula chanzuckerberg/tap/argus
brew trust --formula chanzuckerberg/tap/aws-oidc

# role = personal only
brew trust --cask deskflow/tap/deskflow
```

On a `role = personal` machine, run the three base-layer commands and the Deskflow command.
`makemkv` is an official cask and needs no trust entry.

**`man` depends on this.** `dot_zshrc` sets `alias man='batman'`, and `batman` comes from
`eth-p/software/bat-extras-batman`. On an untrusted machine Homebrew will not load the formula, so
`man` is broken — and Homebrew is the last thing you will think to blame. Until the commands are
run, `brew bundle check` also reports the formula as unsatisfied with:

```
Warning: Cannot check whether eth-p/software/bat-extras-batman is outdated because its tap is not trusted.
```

If a new tapped formula or cask is ever added to a Brewfile, add its matching `brew trust
--formula` or `brew trust --cask` line to the README's "Trusting taps" section at the same time.

### 3.2 Sign in to the 1Password CLI

**Why it is not automated.** chezmoi can read from 1Password, but it cannot authenticate on your
behalf, and `onepassword.prompt = false` is set so that a locked vault fails fast with a legible
error instead of hanging.

The `1password-cli` cask asks for the admin password during installation, then follow the
[sign-in instructions](https://developer.1password.com/docs/cli/get-started#sign-in).

**Ordering trap on a `role = work` machine.** The secrets template is gated on the `op` binary being
present, and `op` only arrives in step 3 of the apply — *after* the file-writing phase of the same
run. So the very first apply never renders `~/.config/zsh/secrets.zsh`. Once `op` is installed and
unlocked, run a plain `chezmoi apply` again and it fills in. On a `role = personal` machine this
does not arise at all (§5).

### 3.3 Install a Rust toolchain

**Why it is not automated.** The Homebrew `rustup` formula ships the `rustup` shims but no
toolchain, and there is deliberately no rustup script in `.chezmoiscripts/`.

```sh
rustup toolchain install stable
```

`rustup default` may report `stable-aarch64-apple-darwin` before you do this. That is only a
*recorded preference*, not an installed toolchain. The authoritative check is:

```sh
rustup toolchain list
# before: no installed toolchains
# after:  stable-aarch64-apple-darwin (active, default)
```

`dot_zprofile` already puts `$HOMEBREW_PREFIX/opt/rustup/bin` on `$PATH`, so `command -v cargo`
resolves even with no toolchain installed — it is a shim. Note that *invoking* it (`cargo --version`)
makes rustup download the default toolchain on the spot, which is a ~1.4 GB surprise if you were not
expecting it. Do it deliberately with the command above.

Side benefit worth knowing: the toolchain ships `_cargo` at
`$(rustc --print sysroot)/share/zsh/site-functions/_cargo`. Nothing puts that directory on `FPATH`
yet — that is R2 in the migration plan, still open.

### 3.4 Carried over from `runbooks/homebrew.md`

Still applicable on a new machine:

* **First authenticated `git push`.** The credential helper asks for the system password. Choose
  *Always Allow* so it stops asking. Git Credential Manager comes from the base Brewfile; see
  [`git-notes.md`](git-notes.md) for why its helper path is under `/usr/local` even on Apple Silicon.
* **MakeMKV needs a license key** — `role = personal` only, since `makemkv` lives in that layer. The
  current beta key is in [this forum post](https://forum.makemkv.com/forum/viewtopic.php?t=1053). The
  app is unsigned, so the first launch may need right-click → Open → Open.
* **Log out and back in** after the macOS defaults script, as it tells you to.

Not onboarding steps, but in the same file if you need them: the Homebrew common-tasks reference and
the Python/pip/virtualenv notes.

---

## 4. Creating a new machine layer

### Which layer does a package belong in?

| Layer | Source path | Put something here when… |
| --- | --- | --- |
| base | `dot_config/homebrew/Brewfile` | you would want it on *any* Mac you use. |
| role | `dot_config/homebrew/Brewfile.role-<role>` | it follows the *role*, not the hardware — employer tooling, or a hobby toolchain you would want on any personal machine. |
| machine | `dot_config/homebrew/Brewfile.machine-<slug>` | it is genuinely tied to *this one physical machine*. |

**Rule of thumb: prefer the role layer.** A second machine of the same role then inherits it for
free. The machine layer is for things a sibling machine would not want — the current example is
`monitorcontrol` on `Brewfile.machine-czimacos6457`, a brightness/volume utility for one specific
external display. The CZI and cloud CLIs originally sat in that machine layer only because the role
layer did not exist yet; they were moved to `Brewfile.role-work` precisely so the next work Mac gets
them without a copy-paste.

Layers only ever add. `brew bundle install` never removes packages, so moving an entry between
layers does not uninstall anything on machines that stop matching.

### Creating the file

```sh
chezmoi cd
$EDITOR dot_config/homebrew/Brewfile.machine-<slug>      # or Brewfile.role-<role>
exit
chezmoi apply
```

Start the file with a comment block saying which layer it is and what belongs in it — every existing
layer does, and it is the only thing stopping the distinction from eroding.

### A new machine slug needs no `.chezmoiignore` edit — verified

This is the non-obvious part, so it is worth stating plainly.
[`.chezmoiignore`](../.chezmoiignore) is itself a template, and it filters by **glob**, not by an
enumerated list of machines:

```
.config/homebrew/Brewfile.role-*
!.config/homebrew/Brewfile.role-{{ .role }}
.config/homebrew/Brewfile.machine-*
!.config/homebrew/Brewfile.machine-{{ .machine }}
```

The exclude hides *every* overlay of that kind; the negation immediately below re-admits only the
one matching this machine's answers. No slug is hard-coded anywhere, so adding
`Brewfile.machine-<new-slug>` is a one-file change — create it, commit it, done.

Confirmed against a simulated `machine = mbp-personal` / `role = personal` config with a freshly
created `Brewfile.machine-mbp-personal`, with `.chezmoiignore` untouched:

```
$ chezmoi ignored
.config/homebrew/Brewfile.machine-czimacos6457     <- other machine, hidden
.config/homebrew/Brewfile.role-work                <- other role, hidden
AGENTS.md
CLAUDE.md
README.md
runbooks

$ chezmoi managed --include=files | grep homebrew
.config/homebrew/Brewfile
.config/homebrew/Brewfile.machine-mbp-personal     <- new slug, picked up automatically
.config/homebrew/Brewfile.role-personal
```

A scratch apply (`chezmoi apply --destination=/tmp/scratch --exclude=scripts`) wrote exactly those
three Brewfiles and neither of the two hidden ones.

The one thing to keep in mind: **ordering matters.** Each negation must stay directly beneath the
exclude it refines. If you ever add a fourth kind of overlay, add the exclude/negate pair together.

### Sanity-check the split

After adding or moving entries:

```sh
chezmoi ignored                 # the other machines'/roles' overlays, and nothing you wanted
chezmoi managed --include=files # the layers this machine should get
chezmoi diff                    # what an apply would actually change
```

---

## 5. What a `role = personal` machine gets that the work Mac does not

| Difference | Personal | Work (`czimacos6457`) |
| --- | --- | --- |
| Homebrew role layer | `Brewfile.role-personal` — `exiftool`, `ffmpeg`, `bento4`, `yt-dlp`, `makemkv` (cask), `deskflow` (tap + cask) | `Brewfile.role-work` — `chanzuckerberg/tap/{argus,aws-oidc}`, `awscli`, `kubernetes-cli` |
| `~/.config/zsh/secrets.zsh` | **not written at all** | rendered `0600` from 1Password |
| shared GCM default | `https://dev.azure.com` → `useHttpPath = true` | `https://dev.azure.com` → `useHttpPath = true` |
| role-specific git credential block | `https://invent.kde.org` → `provider = generic` | none |
| git `user.email` | whatever you answered at init | ditto — this is the canonical demo of why the prompt exists |
| Entries to trust | two base formulae + base 1Password cask + personal Deskflow cask | two base formulae + base 1Password cask + two CZI formulae |

**Why there is no secrets file, mechanically.** `dot_config/zsh/private_secrets.zsh.tmpl` is wrapped
in `{{- if and (eq .role "work") (lookPath "op") -}}`. On a personal machine the condition is false,
the template renders to nothing, and **chezmoi removes the target for an empty render** rather than
writing an empty file — so there is nothing to go stale, and the work 1Password account never needs
to exist on that machine. `dot_zshrc` sources the file behind `[ -f … ]`, so its absence is silent.

One quirk that looks alarming and is not: `chezmoi managed` still lists `.config/zsh/secrets.zsh` on
a personal machine, because *managed* means "there is a source entry for it," not "a file will
exist." The scratch apply above confirms nothing is written.

Note also that `Brewfile.role-personal`'s packages are not installed on the work Mac — they were
removed from it during the migration. Adopting `iris` is the first real-hardware exercise of that
layer, so validate every entry rather than assuming the simulated matrix covered Homebrew behavior.

---

## 6. Verification checklist

Run these on the new machine once §3 is done. Every command below was checked against the work Mac,
and the "want" column is its actual output.

### chezmoi

```sh
chezmoi doctor          # want: no `error` rows. `info` rows for absent password managers are fine.
chezmoi source-path     # want: ~/.local/share/chezmoi
chezmoi verify          # want: silent, exit 0
chezmoi status          # want: empty
```

`chezmoi verify` exiting 0 is the real signal: it means `$HOME` matches the source, including the
`run_onchange_` scripts having already fired.

### Homebrew

```sh
brew trust --json v1                                                     # the entries from §3.1
brew bundle check --file="$HOME/.config/homebrew/Brewfile"
brew bundle check --file="$HOME/.config/homebrew/Brewfile.role-<role>"
brew bundle check --file="$HOME/.config/homebrew/Brewfile.machine-<slug>"   # if the layer exists
```

Each should print `The Brewfile's dependencies are satisfied.` with **no trust warnings**. A trust
warning here means §3.1 was skipped for that formula.

### Login shell smoke test

Open a fresh terminal window — a real login shell, not `zsh -c` — and check:

| Check | Want |
| --- | --- |
| Prompt renders | the `pure` prompt, not a bare `%`. Confirms antidote loaded from Homebrew. |
| `alias man` | `man=batman`, and `batman ls` renders a colourised page. Doubles as the tap-trust check. |
| Tab completion | `git che<TAB>` completes. Confirms `compinit` ran after everything added to `FPATH`. |
| `sizeup` / `fnm_upgrade` | both autoload from `~/.zfunc`. |
| `git cl` | resolves to `~/.local/bin/git_blobless_clone`. |
| <kbd>Ctrl</kbd>+<kbd>R</kbd> | `bindkey "^R"` reports `fzf-history-widget`. Confirms `eval "$(fzf --zsh)"`. |
| `command -v cargo` | `/opt/homebrew/opt/rustup/bin/cargo`; then `cargo --version` prints a version *without* downloading anything (proves §3.3 was done). |
| `git config --list --show-origin` | the right email; the Azure `useHttpPath` GCM default on every machine; and the KDE provider only on personal machines. |
| `role = work` only: `echo ${KG_API_KEY:+set}` | `set`. On personal, expect empty and no `~/.config/zsh/secrets.zsh`. |

### Then commit anything you added

If the machine needed a new overlay layer:

```sh
chezmoi cd
git status                        # the new Brewfile.machine-<slug>
git add -p && git commit && git push
exit
```

The pre-commit hook in `.githooks/` is already wired up by the apply, so it will scan the change.
