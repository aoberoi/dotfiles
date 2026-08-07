# Migration Plan: dotbot → chezmoi (macOS)

Status: **proposed** — agreed in principle, not yet executed.
Scope: this repo stays **macOS-only**. Linux lives in [`aoberoi/dotfiles-linux`](https://github.com/aoberoi/dotfiles-linux).

---

## 1. Why

| Driver | Assessment |
| --- | --- |
| dotbot unmaintained | **Partly true.** `anishathalye/dotbot` is healthy (last commit 2026-07-12, ~8k stars). `wren/dotbot-brew` is **dead**: last commit **2022-04-17**, 8 stars, and [PR #1](https://github.com/wren/dotbot-brew/pull/1) — the bug `install.conf.yaml` already works around — is still unmerged after four years. Homebrew is load-bearing here, so the abandoned piece is the piece that matters. |
| Per-machine config is hard | **True, and the stronger driver.** dotbot has no conditional/templating layer at all. Today the repo can only express "every machine gets exactly this." |

chezmoi is actively developed (v2.72.0, 2026-08-02, ~21k stars), is already the tool in the Linux repo, and solves both with first-class templates, `.chezmoidata`, init-time prompts, and script lifecycle management.

**Secondary wins available during this migration** (each is a real defect in the current setup, detailed in §4):
- A production API key sitting in the working copy.
- A hardcoded `/Users/ankur/...` path that is wrong on this machine.
- Three git submodules, two of which become unnecessary.
- A vendored `fzf.zsh` obsoleted by upstream `fzf --zsh`.
- A credential helper pointing at an Intel-only `/usr/local` path.

---

## 2. Agreed decisions

| # | Decision | Choice | Consequence |
| --- | --- | --- | --- |
| D1 | Edit model | **chezmoi default (copy)** | `~/.zshrc` becomes a real file. Editing it does *not* update the repo. Use `chezmoi edit --apply <target>`. Mitigated by setting `edit.apply = true`. |
| D2 | Repo layout | **Flat root** (no `.chezmoiroot`) | Matches `dotfiles-linux` exactly; patterns copy verbatim between repos. |
| D3 | Homebrew | **Three layers**, applied in order: base `Brewfile` → `Brewfile.role-<role>` → `Brewfile.machine-<machine>` | Native Brewfile syntax and comments preserved; each layer is a separate, readable file. Amended 2026-08-06 — see R3. The `role-` / `machine-` prefixes keep the two overlay kinds unambiguous in a flat directory. |
| D4 | Machine identity | **Prompt at `chezmoi init`, stored in config** | Explicit, survives renaming the Mac, and carries other per-machine values (git email, role). |
| D5 | Source directory | **chezmoi default `~/.local/share/chezmoi`** | No `sourceDir` override. The working copy leaves `~/Developer/dotfiles`; reach it with `chezmoi cd` / `chezmoi source-path`. Requires a one-time relocation at cutover — see §8 P8-4. |
| D6 | `KG_API_KEY` delivery | Stored in 1Password; rendered into a `0600` file at apply time. Never committed. | Recorded in §5. |
| D8 | Homebrew tap trust | **Per-formula, never per-tap. Not managed by this repo.** `~/.homebrew/trust.json` stays a manual, per-machine act; the README documents the commands. | Trust grants a third-party tap the ability to run arbitrary install code, so it stays a deliberate local decision rather than something a repo or bootstrap script confers. Cost: each new Mac needs the `brew trust` commands run by hand. |
| D7 | Where the secret lives, and who gets it | **Work account** `chanzuckerberg.1password.com`, vault **`Employee`**, item **`kg-api`**, field `credential`. Rendered **only on `role = work`** machines. | Two `op` accounts are configured on this machine, so `op read` is ambiguous without disambiguation — the account must be passed explicitly. See §5. |

All decisions are settled; there are no open questions blocking execution.

### Deferred decisions (non-blocking — revisit after cutover)

| # | Question | Current answer | Revisit when |
| --- | --- | --- | --- |
| R1 | What attributes belong on `~/.local/bin` and its children? | Ship as plain `dot_local/bin/executable_git_blobless_clone`. **Not** `exact_`. | `~/.local/bin` accumulates more than one or two repo-owned scripts, or a script is retired and its orphan needs cleaning up. Details in §3. |
| R2 | ~~Wanted: `cargo` shell completions.~~ | **RESOLVED 2026-08-07 — Option A.** `dot_zshrc` prepends `$(rustc --print sysroot)/share/zsh/site-functions` to `fpath`, guarded on `rustc` existing. Nothing generated, nothing checked in, follows the active toolchain. | Closed. |
| R3 | ~~D3 has no slot for "every personal machine."~~ | **RESOLVED 2026-08-06 — option 1 chosen.** D3 amended to three layers; personal-only packages go in `Brewfile.role-personal`. | Closed. |
| R4 | Is the `~/.cargo/env` block in `dot_zshrc` still needed? | Left in place, unchanged. It is guarded, so harmless. | It dates from a `rustup-init` install the formula no longer performs, and `~/.cargo/env` does not exist on this machine. Now that `$(brew --prefix rustup)/bin` is on `$PATH` (§4.4), that block is likely dead. Verify after a toolchain is installed, then probably delete. |

**R1 background.** The `exact_` asymmetry between `~/.zfunc` and `~/.local/bin` was inherited from dotbot's config (whole-directory symlink vs `glob: true`), and that original choice was not necessarily deliberate. On re-examination it happens to be correct, but for a reason dotbot never articulated: `exact_` buys **deletion propagation**, and its cost is that chezmoi deletes anything in the directory it doesn't manage.

- `~/.zfunc` has no runtime writer and stale entries are actively harmful (a shadowing completion — exactly the `_rustup` bug in §4.5). `exact_` earns its keep.
- `~/.local/bin` is shared: `zsh/zprofile` documents it as *"Used by uv"*, and uv installs tool shims there. `exact_` would delete them on every apply. Disqualifying.

Three options exist when this is revisited, in increasing order of disruption:

1. **Status quo.** No deletion propagation. Retiring a script leaves an orphan on every machine forever. Fine at one script.
2. **`remove_` entries.** A source entry named `remove_<name>` deletes that specific target. Gives surgical deletion propagation without claiming the directory. The recommended next step, and cheap.
3. **Dedicated directory.** Move repo-owned scripts to something chezmoi owns outright (e.g. `exact_dot_local/share/dotfiles/bin/`) and add it to `$PATH`. Full mirror semantics, at the cost of a new `$PATH` entry and moving files users may have muscle memory for.

Do **not** adopt option 3 as part of this migration — it is scope creep with no current payoff.

**R3 background — no role layer for packages.**

Surfaced 2026-08-06, immediately after the Phase 0.5 split was recorded: `exiftool`, the media tools (`ffmpeg`, `bento4`, `yt-dlp`, `makemkv`), and `deskflow` are wanted **only on the personal Mac** — a machine that does not exist yet and will be set up after this migration completes.

D3 defines exactly two layers: a base applied everywhere, and a `Brewfile.<machine>` overlay. There is no layer meaning "every personal machine," so these packages have nowhere correct to live. They are parked in a `PERSONAL (role = personal)` comment block in `brew/Brewfile`. They remain installed on this work Mac and nothing is uninstalled — `brew bundle install` never removes packages.

**Resolved: option 1, a role layer.** D3 now specifies three layers:

| Layer | Source path | Applied on |
| --- | --- | --- |
| base | `dot_config/homebrew/Brewfile` | every machine |
| role | `dot_config/homebrew/Brewfile.role-<role>` | every machine of that role |
| machine | `dot_config/homebrew/Brewfile.machine-<machine>` | one machine |

The `role-` and `machine-` prefixes matter: without them, `Brewfile.personal` and `Brewfile.czimacos6457` sit in one flat namespace with nothing marking which kind of overlay each is. The prefixes also keep the `.chezmoiignore` rules obvious — one exclude/negate pair per kind.

Cost is one extra `brew bundle` invocation and one extra pair of ignore rules. Option 2 (parking them in the future personal machine's overlay) was rejected because it conflates "personal" with "that one specific laptop," and a second personal machine would mean duplicating the list.

**`deskflow` — DECIDED 2026-08-06: personal role only.** It is a server/client application, so sharing input between two machines would require it on both ends; that is explicitly not wanted for now. It stays in `Brewfile.role-personal` and off every non-personal machine. Revisiting means moving two lines into the base Brewfile.

**R2 background — cargo completions.**

Verified state of this machine (2026-08-06):

| Check | Result |
| --- | --- |
| `command -v rustup` | `/opt/homebrew/bin/rustup` — installed |
| `command -v rustc` / `cargo` | **absent from `$PATH`** |
| `$(brew --prefix rustup)/bin` | contains `cargo`, `rustc`, `rustfmt`, `clippy`… but **is not on `$PATH`** |
| `rustup toolchain list` | **`no installed toolchains`** — `~/.rustup` holds only `settings.toml` |
| `_cargo` anywhere on disk | not found |
| `_cargo` in Homebrew's site-functions | not shipped (only `_rustup` is) |

So the Rust setup is incomplete in two ways, and both must be fixed before completions are even meaningful:

1. **`$(brew --prefix rustup)/bin` is missing from `$PATH`.** This is exactly what the formula caveat instructs, and `zsh/zprofile` never did it. It is why `cargo` and `rustc` don't resolve. Note this is the *current* replacement for the obsolete `rustup-init` guidance in `brew/README.md` (§4.4).
2. **No toolchain is installed.** `rustup default` reports `stable-aarch64-apple-darwin`, but that is only a recorded preference — nothing was ever downloaded. Needs `rustup toolchain install stable`.

Once those hold, the toolchain itself ships the completion at `<sysroot>/share/zsh/site-functions/_cargo` (this is how [rustup PR #1425](https://github.com/rust-lang/rustup/pull/1425) wired it up — the file is packaged with Rust releases, not generated by rustup). Three ways to reach it:

**Option A — dynamic `FPATH` from the active toolchain. Recommended.** Add to `dot_zshrc`, *before* `antidote load` (§4.6):

```zsh
if command -v rustc >/dev/null; then
  fpath=( "$(rustc --print sysroot)/share/zsh/site-functions" "${fpath[@]}" )
fi
```

Nothing is generated, nothing is checked in, nothing goes stale, and chezmoi is not involved at all. It resolves the *active* toolchain at shell startup, so it follows `rustup default` and per-directory overrides automatically. Cost: one `rustc` subprocess per interactive shell (~10–30 ms). This is the same shape as the `_rustup` answer in §4.5 — let the tool that owns the completion ship it, and just put its directory on `FPATH`.

**Option B — generate into the unmanaged site-functions directory.** The `run_onchange_` script sketched in §4.5, writing `~/.local/share/zsh/site-functions/_cargo`. Avoids the startup subprocess, but reintroduces a generated artifact that can drift from the active toolchain. Note that `rustup completions zsh cargo` reportedly emits a shim that *sources* the toolchain's `_cargo` rather than copying it — verify what it actually produces before relying on this.

**Option C — third-party antidote plugin. Rejected.** `ryutok/rust-zsh-completions` is the usual suggestion; it is **archived**, last pushed 2018-12-07, 6 stars. Do not add it.

Whichever is chosen, `_cargo` must **not** land in `exact_dot_zfunc/` (§4.5).

---

## 3. Target repository layout

```
.
├── .chezmoi.toml.tmpl                 # init prompts → ~/.config/chezmoi/chezmoi.toml
├── .chezmoidata.toml                  # static shared data (1Password item names)
├── .chezmoiignore                     # repo-only files + non-matching Brewfile overlays
├── .chezmoiscripts/
│   ├── run_once_before_10-install-homebrew.sh
│   ├── run_onchange_after_20-install-packages.sh.tmpl
│   ├── run_onchange_after_30-macos-defaults.sh
│   └── run_onchange_after_50-install-git-hooks.sh.tmpl
├── .gitignore
├── .githooks/pre-commit               # secret guard, wired via core.hooksPath
├── .gitleaks.toml                     # extends the default ruleset
├── .vscode/settings.json              # auto-ignored (leading dot)
├── AGENTS.md                          # rewritten; .chezmoiignore'd
├── CLAUDE.md                          # .chezmoiignore'd
├── README.md                          # rewritten; .chezmoiignore'd
├── runbooks/                          # .chezmoiignore'd
│   └── chezmoi-migration-plan.md      # this file
├── dot_config/
│   ├── ghostty/config
│   ├── git/
│   │   ├── config.tmpl                # templated: email, role-specific credential helpers
│   │   └── ignore                     # git reads ~/.config/git/ignore natively
│   ├── homebrew/                      # three layers, applied in order (D3)
│   │   ├── Brewfile                   # base — every machine
│   │   ├── Brewfile.role-personal     # every personal machine
│   │   ├── Brewfile.role-work         # every work machine
│   │   └── Brewfile.machine-<machine> # one specific machine
│   └── zsh/
│       ├── private_secrets.zsh.tmpl   # → ~/.config/zsh/secrets.zsh (0600), 1Password-backed
│       └── zsh_plugins.txt            # antidote plugin manifest
├── dot_local/bin/executable_git_blobless_clone
├── exact_dot_zfunc/                   # hand-written autoload functions ONLY —
│   ├── fnm_upgrade                    # never generated files (§4.5)
│   └── sizeup
├── dot_vim/vimrc
├── dot_zprofile                       # plain file — runtime guards, not templates
└── dot_zshrc                          # plain file initially
```

### Layout notes agents must respect

- **`exact_dot_zfunc/`** uses `exact_` deliberately: the directory is wholly owned by this repo, mirroring dotbot's whole-directory symlink. Unmanaged files there get removed.
- **`dot_local/bin/` must NOT be `exact_`.** `~/.local/bin` is shared with other tools (uv, the chezmoi bootstrap binary). This reproduces dotbot's `glob: true` "merge" semantics — chezmoi manages only the named file and leaves siblings alone. This is a **deliberately deferred decision — see R1 in §2** for the reasoning and the options when it is revisited.
- chezmoi **automatically ignores** source entries beginning with `.` (so `.git/`, `.vscode/`, `.gitignore` need no entry). `README.md`, `AGENTS.md`, `CLAUDE.md`, and `runbooks/` **do** need explicit `.chezmoiignore` entries.
- Nothing needs `.chezmoiexternal.toml`. Both remaining external dependencies resolve to Homebrew formulae (§4.3). Reach for externals only if a future dependency has no formula.

---

## 4. File-by-file mapping

### 4.1 Straight ports (no content change)

| Current | Target source path | Target |
| --- | --- | --- |
| `ghostty/config` | `dot_config/ghostty/config` | `~/.config/ghostty/config` |
| `vim/vimrc` | `dot_vim/vimrc` | `~/.vim/vimrc` |
| `zsh/zfunc/_rustup` | **deleted — not ported** | n/a — Homebrew ships it (§4.5) |
| `zsh/zfunc/fnm_upgrade` | `exact_dot_zfunc/fnm_upgrade` | `~/.zfunc/fnm_upgrade` |
| `zsh/zfunc/sizeup` | `exact_dot_zfunc/sizeup` | `~/.zfunc/sizeup` |
| `bin/git_blobless_clone` | `dot_local/bin/executable_git_blobless_clone` | `~/.local/bin/git_blobless_clone` |

Note: `zsh/zfunc/sizeup` is currently `+x` while `fnm_upgrade` is not. zsh `autoload` does not require the executable bit; normalise both to non-executable (i.e. no `executable_` prefix).

### 4.2 Path relocations

| Current | Target | Rationale |
| --- | --- | --- |
| `git/gitconfig` → `~/.gitconfig` | `dot_config/git/config.tmpl` → `~/.config/git/config` | Matches `dotfiles-linux`; XDG-native. |
| `git/gitignore_global` → referenced via `excludesfile` | `dot_config/git/ignore` → `~/.config/git/ignore` | git reads this path **natively**; the `excludesfile` line can be deleted entirely. |
| `brew/Brewfile` | `dot_config/homebrew/Brewfile` | Becomes a deployed artifact so `brew bundle` works standalone. |
| `zsh/zsh_plugins` | `dot_config/zsh/zsh_plugins.txt` | antidote's conventional name. |
| `script/macos.sh` | `.chezmoiscripts/run_onchange_after_30-macos-defaults.sh` | Lifecycle-managed. |

> **Cutover hazard:** `~/.gitconfig` takes precedence over `~/.config/git/config`. The old symlink **must be deleted** or the new config is silently inert. Tracked as task P6-2.

### 4.3 Eliminating the `~/.dotfiles` permalink

Copy mode means there is no repo path in `$HOME` to point at. All three consumers can be removed rather than rehomed:

| Reference | Resolution |
| --- | --- |
| `source ~/.dotfiles/zsh/fzf.zsh` | Delete the vendored file. Replace with `eval "$(fzf --zsh)"` (fzf ≥ 0.48 ships this; Homebrew's fzf is current). Removes a vendored, hand-modified upstream file. |
| `source ${HOME}/.dotfiles/zsh/antidote/antidote.zsh` | Add `brew "antidote"` to the Brewfile (formula exists, v2.2.2). Source from `$(brew --prefix)/opt/antidote/share/antidote/antidote.zsh` — **verify the exact path with `brew list antidote` at implementation time.** Deletes the `zsh/antidote` submodule. |
| `antidote load ${HOME}/.dotfiles/zsh/zsh_plugins` | `antidote load ~/.config/zsh/zsh_plugins.txt` |
| `git/gitconfig`: `excludesfile = ~/.dotfiles/git/gitignore_global` | Delete the line (see §4.2). |

Consequently the `~/.dotfiles` symlink itself is dropped.

> **antidote gotcha:** static loading writes a generated `zsh_plugins.zsh` next to the manifest. It is currently handled by `zsh/.gitignore`. After the move it lands at `~/.config/zsh/zsh_plugins.zsh` — add it to `.chezmoiignore` so chezmoi does not fight antidote over the file.

### 4.4 Defects to fix in-flight

| Defect | Location | Fix |
| --- | --- | --- |
| **Production API key in working copy** | `zsh/zshrc` last line: `export KG_API_KEY=sk_prod_…` | See §5. Highest priority. |
| **Hardcoded wrong username** | `zsh/zprofile`: `export PATH="/Users/ankur/.local/bin:$PATH"` — this machine's user is `aoberoi`, so the entry points at a nonexistent directory | Use `$HOME/.local/bin`. No template needed. |
| **Unguarded source** | `zsh/zprofile`: `source ~/.swiftly/env.sh` fails if swiftly isn't set up | Guard: `[ -f ~/.swiftly/env.sh ] && source ~/.swiftly/env.sh` |
| **Needless subprocess per login** | `zsh/zprofile`: `export PATH=$PATH:$(go env GOPATH)/bin` while `GOPATH` is set on the line above | `export PATH="$PATH:$GOPATH/bin"` |
| ~~**Intel-only path**~~ — **RETRACTED, verified 2026-08-06** | `git/gitconfig`: `helper = /usr/local/share/gcm-core/git-credential-manager` | **Not a defect.** The GCM cask ships a `.pkg` that installs to `/usr/local/share/gcm-core` on Apple Silicon too; `/opt/homebrew/share/gcm-core` does not exist. GCM 2.9.1 is installed and `git config --get-all credential.helper` resolves correctly (`osxkeychain` → empty reset → GCM). **Leave the gitconfig path alone.** |
| **Brewfile disagrees with reality on GCM** | `brew/Brewfile` comments out `cask "git-credential-manager"` with *"This installation is failing as of 4/13/2026"* — but the cask **is installed** (2.9.1) and working | Re-enable the entry and delete the stale comment. A fresh machine currently would not get GCM, silently breaking git auth. |
| **Role-specific credential config** | `git/gitconfig`: `[credential "https://dev.azure.com"]`, `[credential "https://invent.kde.org"]` | Move behind `{{ if eq .role "work" }}` / `"personal"` guards in `config.tmpl`. |
| **Wrong git email** | `git/gitconfig` hardcodes `aoberoi@gmail.com`; work machine needs `aoberoi@chanzuckerberg.com` | Template from the init prompt. This is the canonical demo of why D4 matters. |
| **Checked-in `_rustup` shadows a fresher copy** | `zsh/zfunc/_rustup` (27 KB, generated from an older rustup) | **Delete it.** See §4.5 — Homebrew already ships this file and it is already on `FPATH`. |
| **Obsolete `rustup-init` instruction** | `brew/README.md` says to run `rustup-init --no-modify-path` | The Homebrew formula (rustup 1.29.0) states: *"This formula no longer provides `rustup-init`."* Replace with the current caveat: put `$(brew --prefix rustup)/bin` on `$PATH`. |
| **Rust is installed but unusable** | `zsh/zprofile` never adds `$(brew --prefix rustup)/bin` to `$PATH`, so `cargo` and `rustc` do not resolve despite `rustup` being installed. Compounding it, no toolchain was ever downloaded (`rustup toolchain list` → `no installed toolchains`) | Add the `$PATH` entry per the formula caveat, guarded like the other zprofile entries. Installing a toolchain is a separate manual step. Background and verification in **R2, §2**. |

### 4.5 Shell completions: stop checking them in

`zsh/zfunc/_rustup` is checked in and documented in `brew/README.md` as needing manual regeneration when rustup's CLI changes. None of that is necessary.

**Homebrew's `rustup` formula already installs `_rustup`** to `$(brew --prefix)/share/zsh/site-functions/_rustup`, and `zsh/zshrc:86` already puts that directory on `FPATH`. The completion has been available automatically the whole time.

Worse, the checked-in copy **wins**. `zshrc:86` prepends brew's site-functions, then `zshrc:93` prepends `~/.zfunc` on top of it — so `~/.zfunc/_rustup` shadows the fresher Homebrew copy. The manual-maintenance burden described in `brew/README.md` is self-inflicted.

**Fix: delete `zsh/zfunc/_rustup` and add nothing.** It stays current via `brew upgrade rustup`. Drop the corresponding paragraph from `brew/README.md`.

**Generated completions must never live in an `exact_` directory.** `exact_dot_zfunc/` means chezmoi deletes anything there it doesn't manage, so a generated file would be removed on every apply. The rule for this repo:

| Kind of file | Home | Managed by |
| --- | --- | --- |
| Hand-written autoload functions (`fnm_upgrade`, `sizeup`) | `~/.zfunc` | chezmoi, `exact_` |
| Completions shipped by a package | `$(brew --prefix)/share/zsh/site-functions` | Homebrew |
| Completions that genuinely must be generated | `~/.local/share/zsh/site-functions` | a `run_onchange_` script; **not** chezmoi-managed |

The third row currently has no occupants, and may never need any — see **R2 in §2**, which captures the standing desire for `cargo` completions, the two prerequisites blocking it, and why the preferred answer (put the toolchain's own site-functions directory on `FPATH`) needs no generated file at all. The script below is the fallback, not the recommendation. The generation script should key its re-run on the tool version so it refreshes on upgrade, and must guard against the tool being absent:

```bash
{{ if lookPath "rustup" -}}
#!/usr/bin/env bash
set -euo pipefail
# rustup version: {{ output "rustup" "--version" }}
mkdir -p "${HOME}/.local/share/zsh/site-functions"
rustup completions zsh cargo > "${HOME}/.local/share/zsh/site-functions/_cargo"
{{ end -}}
```

That directory then needs adding to `FPATH` in `dot_zshrc`, before antidote's `compinit` runs (§4.6).

### 4.6 How antidote changes

Two independent things are being delivered today, and only one of them changes.

**Before:**
1. `zshrc:132` sources antidote itself from the **git submodule** at `zsh/antidote/`.
2. `zshrc:134` runs `antidote load ~/.dotfiles/zsh/zsh_plugins`, which reads the plugin manifest, clones any missing plugin repos into antidote's cache directory, generates a static `zsh_plugins.zsh` next to the manifest, and sources that.

The plugins themselves — `belak/zsh-utils` (history, completion, utility) and `sindresorhus/pure` — were **never** in this repo and still won't be. They live in antidote's cache. Only antidote's own delivery mechanism is changing.

**After:** antidote comes from Homebrew. Per the formula caveat, verbatim:

```sh
source $HOMEBREW_PREFIX/opt/antidote/share/antidote/antidote.zsh
antidote load ~/.config/zsh/zsh_plugins.txt
```

The `zsh/antidote` submodule is deleted; `brew "antidote"` (v2.2.2) replaces it.

**Ordering constraint that must survive the migration.** The `belak/zsh-utils path:completion` plugin is what calls `compinit`. Everything that adds to `FPATH` must run *before* `antidote load`, and every `compdef` must run *after*. The current `zshrc` respects this; any reshuffling during the port must preserve it:

```
FPATH += brew site-functions          (zshrc:86)
FPATH += ~/.zfunc                     (zshrc:93)
FPATH += ~/.local/share/zsh/site-functions   (only if §4.5 row 3 is ever used)
    ↓
antidote load …                       ← compinit happens in here
    ↓
compdef _op op / compdef _man batman  (zshrc:151,155)
```

**Generated artifact:** `antidote load` writes `zsh_plugins.zsh` beside the manifest. Today `zsh/.gitignore` handles it; after the move it lands at `~/.config/zsh/zsh_plugins.zsh` and needs the `.chezmoiignore` entry already listed in §6.

---

**Templating discipline:** only `dot_config/git/config`, `.chezmoiignore`, and the secrets file need to be templates. `dot_zprofile` and `dot_zshrc` stay **plain files** with runtime guards — simpler, and consistent with the repo's stated "less is better" philosophy. Convert them to `.tmpl` later only when something genuinely varies per machine.

---

## 5. Secret handling

Secrets never live in this repo. They live in 1Password and are pulled in at
`chezmoi apply` time by a template, so the source tree only ever contains an `op://`
reference. `.chezmoidata.toml` holds the coordinates; nothing sensitive is committed.

> **If you ever need to purge a value from git history, search for the VALUE, not the
> variable name.** `git log -S SOME_API_KEY --all` also matches any document that
> merely discusses the variable — including this runbook — so it can never come back
> clean and is useless as a purge criterion. Search for a distinctive substring of the
> secret itself. Beyond git, sweep shell history, editor undo/swap files, and Time
> Machine or Spotlight-indexed copies of the working tree before calling it done.
>
> Local session checkpoint refs are easy to miss: tooling can hold commits under refs
> like `refs/t3/checkpoints/…` that `git log --all` reaches but that no branch points
> at. Enumerate with `git for-each-ref`, delete with `git update-ref -d`, then
> `git reflog expire --expire=now --all && git gc --prune=now`.

### Setting up a secret

1. **Create the 1Password item**, then verify the round-trip by comparing hashes rather
   than printing the value:
   ```sh
   op item create --account=chanzuckerberg.1password.com --vault=Employee \
     --category='API Credential' --title=kg-api 'credential[password]=…'
   op read 'op://Employee/kg-api/credential' --account=chanzuckerberg.1password.com \
     | shasum -a 256
   ```
2. **Record the coordinates** in `.chezmoidata.toml` — account, vault and item name.
   Never the value.
3. 4. **Deliver it via a templated private file**, not via zshrc:

   `dot_config/zsh/private_secrets.zsh.tmpl` → `~/.config/zsh/secrets.zsh`
   ```
   {{- if and (eq .role "work") (lookPath "op") -}}
   export KG_API_KEY={{ onepasswordRead (printf "op://%s/%s/credential" .onepassword.vault .onepassword.kgApiItem) .onepassword.account | quote }}
   {{- end -}}
   ```

   **The account argument is mandatory here, not optional.** Two accounts are configured on this machine, and `op read` fails outright with `multiple accounts found` when it cannot disambiguate — verified:

   ```
   $ op read "op://Private/…/credential"
   [ERROR] … error initializing client: multiple accounts found.
           Use the --account flag or set the OP_ACCOUNT environment variable…
   ```

   There is **no `onepassword.account` config key** — `account` is the optional *second argument* to `onepasswordRead` (signature: `onepasswordRead` *url* \[*account*\]). It is supplied from `.chezmoidata.toml`.

   The `eq .role "work"` guard implements D7: on a personal machine the template renders empty, chezmoi writes no secrets file, and the work 1Password account never needs to be present.
   The `private_` prefix goes on the **file**, yielding `0600`. Do **not** write this as `private_dot_config/...`: the tree already contains `dot_config/`, and two source entries mapping to `~/.config` is a source-state conflict.

   **`lookPath` only tests whether the `op` binary exists — it says nothing about whether the vault is unlocked.** The three cases differ:

   | State of `op` | What happens at `chezmoi apply` |
   | --- | --- |
   | Not installed | Template renders empty → chezmoi **removes** `~/.config/zsh/secrets.zsh`. Clean no-op. |
   | Installed, unlocked | Secret is fetched and written at `0600`. |
   | Installed, **locked** | `onepasswordRead` triggers 1Password's interactive sign-in (chezmoi's `onepassword.prompt` defaults to true). At a TTY you unlock and continue. **Non-interactively it fails — and because a template error aborts target-state computation, the entire apply fails, not just this file.** |

   Set `onepassword.prompt = false` in the config so the locked-and-non-interactive case produces an immediate, legible error instead of a hang.

5. **Source it from `dot_zshrc`:**
   ```sh
   [ -f ~/.config/zsh/secrets.zsh ] && source ~/.config/zsh/secrets.zsh
   ```

**Tradeoffs to accept:**

- **The plaintext lives on disk** at `0600` between applies. The shell just sources an ordinary file — no 1Password involvement, no startup latency. The alternative (lazy `op read` inside `zshrc`) keeps it off disk but costs an unlock prompt and a subprocess on every new shell.
- **`chezmoi apply` becomes interactive-only** in practice, per the table above. Acceptable here because applies are always run by hand; it would need revisiting if apply were ever automated.
- **Value changes in 1Password do not propagate until the next `chezmoi apply`.** The on-disk file is a snapshot, not a live read.

6. **Add a guard — DONE 2026-08-06 (P5-3).** `.githooks/pre-commit`, wired up by `run_after_50-install-git-hooks.sh.tmpl` setting `core.hooksPath` (local to this repo only). Two layers: built-in high-signal patterns needing no dependencies, plus `gitleaks` when installed. Verified blocking Stripe-style keys, AWS key IDs, GitHub tokens and private-key headers via the built-ins, and a Google API key via gitleaks — with no false positive on this repo's own content, including the `sk_prod_<REDACTED>` string in this very file.

   **Prefix for the wiring script — it took three tries, and the reasoning is worth keeping:**

   | Prefix | Verdict |
   | --- | --- |
   | `run_once_` | Wrong. Recorded by content hash in state that outlives the source directory, so after the cutover move to `~/.local/share/chezmoi` (D5, P8-4) it is already marked done and the new clone silently has **no hook**. |
   | `run_` | Wrong. Runs every apply, so `chezmoi status` lists it as permanently pending and **`chezmoi verify` can never exit 0** — destroying its value as a drift detector and making P8-6's acceptance criterion unmeetable. Discovered the hard way during Phase 6. |
   | `run_onchange_` | **Right**, and only because the script body embeds `{{ .chezmoi.sourceDir }}`. Moving the source changes the rendered content, which re-fires the script — covering the cutover case without the `run_` tax. |

   **Baseline:** `gitleaks git .` over the full history reports *no leaks found*, so the guard starts from a clean repo.

   **`.gitleaks.toml` — why a custom rule was needed.** gitleaks' default ruleset catches a key of this shape, but only by luck of naming. Measured against a synthetic key of the same shape:

   | How it appears | Default ruleset |
   | --- | --- |
   | `export KG_API_KEY=sk_prod_<uuid>_<64 chars>` | caught (`generic-api-key`) |
   | `api_key = "sk_prod_<uuid>_<64 chars>"` | caught (`generic-api-key`) |
   | `FOO=sk_prod_<uuid>_<64 chars>` | **missed** |

   `generic-api-key` only runs its entropy check when a keyword like `api_key`, `token` or `secret` sits nearby. Rename the variable to something unrevealing and the identical secret passes. The `vendor-prefixed-secret-key` rule keys on the credential's own shape instead, so context does not matter. Verified: it fires on the previously-missed case, and two allowlists keep it off redacted placeholders (`sk_prod_<REDACTED>` in this very file) and short examples. Working tree and full history both scan clean with it active.

   **Use the current CLI spelling.** `gitleaks protect` / `gitleaks detect` still work in 8.30.1 but no longer appear in `gitleaks --help`; the supported surface is `git` / `dir` / `stdin`. The hook uses `gitleaks git --staged`. Had `protect` been removed, the hook would have kept running with layer 2 silently dead.

---

## 6. Key file contents

These are drafts. Agents should treat them as the intended shape, and verify flags/paths against the installed tool versions (see §9).

### `.chezmoi.toml.tmpl`

```toml
{{- $machine := promptStringOnce . "machine" "Machine short name (filename-safe, e.g. mbp-personal)" -}}
{{- $role    := promptChoiceOnce . "role" "Role for this machine" (list "personal" "work") -}}
{{- $email   := promptStringOnce . "email" "Git author email" -}}

[data]
    machine = {{ $machine | quote }}
    role    = {{ $role | quote }}
    email   = {{ $email | quote }}

# Copy mode (D1) means editing ~/.zshrc doesn't touch the repo.
# This makes `chezmoi edit <target>` apply on save, restoring most of the
# immediacy the dotbot symlink workflow had.
[edit]
    apply = true
```

Deliberately **not** defaulting `machine` from `scutil --get ComputerName`: that returns values like `Ankur's MacBook Pro`, which are unsafe as filename suffixes for the Brewfile overlay.

### `.chezmoidata.toml`

```toml
[onepassword]
# Two op accounts are configured locally, so `op read` cannot disambiguate on its
# own. This is passed as the second argument to onepasswordRead (§5) — there is no
# onepassword.account config key.
account    = "chanzuckerberg.1password.com"
vault      = "Employee"
kgApiItem  = "kg-api"
```

### `.chezmoiignore`

```
README.md
AGENTS.md
CLAUDE.md
runbooks/

# antidote generates this at runtime; chezmoi must not fight it
.config/zsh/zsh_plugins.zsh

# brew bundle may write a lockfile next to the Brewfile
.config/homebrew/Brewfile.lock.json

# Homebrew overlays belonging to other roles / other machines (D3).
# Exclude-then-negate: order matters, keep each negation directly after its exclude.
.config/homebrew/Brewfile.role-*
!.config/homebrew/Brewfile.role-{{ .role }}
.config/homebrew/Brewfile.machine-*
!.config/homebrew/Brewfile.machine-{{ .machine }}
```

The exclude-then-negate pattern is chezmoi-supported (`dir/f*` followed by `!dir/foo`). Ordering matters — keep the negation last.

### `.chezmoiscripts/run_onchange_after_20-install-packages.sh.tmpl`

```bash
#!/usr/bin/env bash
set -euo pipefail

{{- $roleFile    := printf "dot_config/homebrew/Brewfile.role-%s"    .role }}
{{- $machineFile := printf "dot_config/homebrew/Brewfile.machine-%s" .machine }}
# Embedding content hashes makes chezmoi re-run this script whenever any layer
# changes, even though the script body itself is unchanged.
# base hash: {{ include "dot_config/homebrew/Brewfile" | sha256sum }}
{{- if stat (joinPath .chezmoi.sourceDir $roleFile) }}
# role hash: {{ include $roleFile | sha256sum }}
{{- end }}
{{- if stat (joinPath .chezmoi.sourceDir $machineFile) }}
# machine hash: {{ include $machineFile | sha256sum }}
{{- end }}

eval "$(/opt/homebrew/bin/brew shellenv)"

echo "==> base"
brew bundle install --file="${HOME}/.config/homebrew/Brewfile"
{{ if stat (joinPath .chezmoi.sourceDir $roleFile) }}
echo "==> role: {{ .role }}"
brew bundle install --file="${HOME}/.config/homebrew/Brewfile.role-{{ .role }}"
{{- end }}
{{ if stat (joinPath .chezmoi.sourceDir $machineFile) }}
echo "==> machine: {{ .machine }}"
brew bundle install --file="${HOME}/.config/homebrew/Brewfile.machine-{{ .machine }}"
{{- end }}
```

Each layer is guarded by `stat`, so a role or machine with no overlay simply skips that step rather than failing. Note this script must **not** run `brew trust` (D8).

Verified: `include` resolves relative to the source directory; `sha256sum` comes from sprig, which chezmoi bundles wholesale.

### Script ordering

chezmoi runs scripts alphabetically within the `before` and `after` groups, hence the numeric prefixes:

| Script | Type | Purpose |
| --- | --- | --- |
| `run_once_before_10-install-homebrew.sh` | once, before | Replaces dotbot's `install-brew: true`. Idempotent; no-op if `/opt/homebrew/bin/brew` exists. |
| `run_onchange_after_20-install-packages.sh.tmpl` | onchange, after | Base + overlay `brew bundle`. |
| `run_onchange_after_30-macos-defaults.sh` | onchange, after | Port of `script/macos.sh`, unchanged. Keep its `uname` guard and the closing "log out" message. Runs only when the file changes, so `killall Dock` stays rare. |

> **Do not add `set -euo pipefail` to the macOS defaults script.** Two independent reasons, both found while porting it:
> 1. The guard `[ \`uname\` != Darwin ] && echo … && exit 0` returns non-zero *on macOS*, because the test fails there. Under `set -e` the script would abort immediately on precisely the platform it targets, taking the whole apply with it.
> 2. `killall Dock` exits non-zero when no Dock is running (SSH-only sessions). Harmless today only because there is no `set -e`.
>
> `script/macos.sh` also had **no shebang** — it worked under dotbot because dotbot invoked it via an explicit interpreter. chezmoi requires one, so the port adds `#!/usr/bin/env bash`. That is the only content change.
>
> **Behavioural difference from dotbot worth knowing:** `run_onchange_` keys on script content, so manually changing one of these settings in System Settings will *not* be re-asserted on the next apply. dotbot's `./install` re-ran the script unconditionally every time.

There is deliberately **no rustup script**. An earlier draft had `run_once_after_40-rustup-init.sh`; it was removed once the Homebrew formula turned out to no longer ship `rustup-init`, and completions to be shipped by the formula already (§4.4, §4.5). Do not reinstate it.

---

## 7. Bootstrap on a new machine

Replaces "clone the repo, run `./install`":

```sh
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply aoberoi
```

`aoberoi` is GitHub shorthand for `github.com/aoberoi/dotfiles`. Sequence:

1. curl installs a chezmoi binary (no Homebrew needed — resolves the chicken-and-egg problem dotbot had).
2. `.chezmoi.toml.tmpl` prompts for machine / role / email.
3. `run_once_before_10-install-homebrew.sh` installs Homebrew.
4. Files are written.
5. `run_onchange_after_20-install-packages.sh` runs `brew bundle`.
6. macOS defaults, then git-hooks wiring. (There is no rustup script — §4.4.)

Add `brew "chezmoi"` to the base Brewfile so chezmoi becomes brew-managed after bootstrap. **Task:** confirm the bootstrap binary's location and remove it if it shadows the brew-installed one on `$PATH`.

---

## 8. Workstreams

> ### ✅ HARD GATE LIFTED 2026-08-06 — Phase 6 executed, `chezmoi apply` is now safe
>
> All eight symlinks are torn down, the first real apply succeeded, and `chezmoi verify` passes. The block below is kept for the record, and because it explains an ordering constraint that matters if this is ever replayed on another machine.
>
> **Ordering constraint the phase list got wrong.** P6-2 (tear down symlinks) and P6-3 (delete the legacy tree) cannot be done in that order, and P6-3 cannot precede the first apply at all. Every symlink pointed *into* the legacy directories, so deleting `zsh/`, `git/`, `vim/`, `ghostty/`, `bin/` from the repo first would leave `~/.zshrc` and friends **dangling** — a broken shell with no config, before chezmoi had written anything to replace it. The working order is:
>
> 1. tear down the symlinks
> 2. `chezmoi apply` — real files replace them
> 3. *only then* delete the legacy tree from the repo
>
> ### ⛔ (historical) HARD GATE: do not run `chezmoi apply` before P6-2
>
> Verified 2026-08-06, not hypothetical. **All eight** dotbot targets are symlinks pointing *into this repo*:
>
> ```
> ~/.zprofile ~/.zshrc ~/.zfunc ~/.vim/vimrc
> ~/.gitconfig ~/.config/ghostty/config ~/.dotfiles ~/.local/bin/git_blobless_clone
> ```
>
> `~/.zfunc` is the dangerous one. It is a symlink to `zsh/zfunc/`, and because `exact_dot_zfunc/` deliberately does not contain `_rustup` (§4.5), `chezmoi status` currently reports:
>
> ```
> D .zfunc/_rustup
> ```
>
> Applying while that symlink stands means chezmoi resolves `~/.zfunc/_rustup` through it and **deletes `zsh/zfunc/_rustup` from the git working tree** — writing through a symlink into the source of truth. The same write-through risk applies to every other target in that list.
>
> Safe to run at any time: `chezmoi diff`, `chezmoi status`, `chezmoi managed`, `chezmoi ignored`, `chezmoi apply --dry-run`, and `chezmoi apply --destination=<scratch>`.
>
> Not safe until P6-2 has torn the symlinks down: a bare `chezmoi apply`.

Phases are ordered; tasks inside a phase marked ∥ are parallelisable.

### Phase 0 — Safety (blocking, do first)

| ID | Task | Acceptance |
| --- | --- | --- |
| P0-1 | Create the 1Password item holding the value and verify the round-trip before anything else depends on it | `op read` returns the expected value |
| P0-2 | Confirm no credential material is reachable from git history: `gitleaks git .` plus a search for any distinctive value substring | Both come back clean |
| P0-3 | Ensure no credential appears in the working tree | `gitleaks dir .` clean |
| P0-4 | `git tag pre-chezmoi && git push --tags`; branch `chezmoi-migration` | Tag on remote; rollback point exists |
| P0-5 | Commit or stash the three pending modifications (`brew/Brewfile`, `git/gitignore_global`, `zsh/zshrc`) | Clean tree before restructuring |

### Phase 0.5 — Brewfile audit (blocking, do on the *current* dotbot setup)

Deliberately sequenced **before** any chezmoi work. The audit is tool-independent, and doing it mid-migration conflates "is the new tooling broken?" with "is my package list wrong?" — every failure becomes ambiguous. Output is a corrected `brew/Brewfile` plus a decided base/overlay split, so Phase 3 is a pure file move with no judgment calls left in it.

| ID | Task | Acceptance |
| --- | --- | --- |
| P0.5-1 | Reconcile declared vs installed both directions: `brew bundle check --file=brew/Brewfile --verbose` (declared but missing), and `brew leaves` / `brew list --cask` against the Brewfile (installed but undeclared) | Both lists explained — every difference either added to the Brewfile or consciously left out |
| P0.5-2 | Resolve the dead entries: the commented-out `git-credential-manager` cask, and the `eth-p/software`, `deskflow/tap`, `1Password/tap`, `anomalyco/tap` taps | No commented-out or stale entries remain |
| P0.5-3 | Classify every entry as **base** (wanted on any Mac) or **overlay** (this machine only). Record as comment sections in the single Brewfile for now — do not split files yet | Every line carries a classification |
| P0.5-4 | Add `antidote` and `chezmoi` to the base set (§4.3, §7) | Both present |

#### P0.5-1 reconciliation results (run 2026-08-06)

**Installed but NOT declared** — every one of these is an overlay/base decision waiting to be made:

| Package | Kind | Note |
| --- | --- | --- |
| `chanzuckerberg/tap/argus` | formula | Work tool → strong **overlay** candidate |
| `chanzuckerberg/tap/aws-oidc` | formula | Work tool → strong **overlay** candidate |
| `awscli` | formula | Likely work → overlay |
| `kubernetes-cli` | formula | Likely work → overlay |
| `monitorcontrol` | cask | Machine-specific (external display) → likely overlay |
| `git-credential-manager` | cask | **Declared but commented out.** Installed and working — re-enable it (§4.4) |

These four work tools are exactly the case D3/D4 were designed for, and they make the base/overlay split concrete rather than hypothetical on a single machine.

**Declared but not satisfied:**

| Entry | Actual state |
| --- | --- |
| `makemkv` | Installed, but **outdated** — `brew bundle check` flags it as needing update |
| `eth-p/software/bat-extras-batman` | Installed and working (`/opt/homebrew/bin/batman` resolves), but **the tap is not trusted**, so Homebrew cannot check whether it is outdated |
| `deno` | Installed (2.9.4). Absent from `brew leaves` only because something depends on it — not a problem |

**Two environmental issues that will affect the Phase 4 script:**

1. **Untrusted tap — RESOLVED (D8).** Only one declared entry was untrusted: `eth-p/software/bat-extras-batman`. Trusted per-formula on 2026-08-06; `brew bundle check` now emits no trust warnings. Per D8 the install script must **not** trust taps automatically, and `~/.homebrew/trust.json` is **not** repo-managed — so a fresh Mac needs this run by hand. Currently trusted on this machine: `anomalyco/tap/opencode`, `chanzuckerberg/tap/argus`, `chanzuckerberg/tap/aws-oidc`, `eth-p/software/bat-extras-batman`. The `1password-cli` and `deskflow` casks required no trust.
2. **`libtiff` / `webp` circular dependency — RESOLVED 2026-08-06.** Worth recording the diagnosis, because the obvious fixes do not work and it can recur.

   Homebrew's message blames "stale dependency data in installed keg tabs," which is only half right. The declared graph is one-directional — `libtiff` depends on `webp`; `webp` declares only giflib, jpeg-turbo, libpng. But the **installed** keg tab for `webp` additionally recorded `libtiff`, closing the loop.

   The cause is that the `webp` bottle links `libtiff` whenever `libtiff` happens to be installed at the moment `webp` is poured. So:

   - `brew reinstall webp` **does not fix it** — verified. `libtiff` is still present, so the new tab records it again.
   - Homebrew's documented remedy works because removing both forces `webp` to be installed *first* (`libtiff` depends on it, so dependency resolution orders it that way), with no `libtiff` present to link against:
     ```sh
     brew uninstall --ignore-dependencies --force libtiff webp && brew install libtiff webp
     ```
   - Uninstalling unrelated packages does **not** help. `deno` is in the base set and depends on both, so they are never orphaned.

   **Will it recur on the personal Mac?** Not on first install — `libtiff` depends on `webp`, so `webp` is always poured first on a clean machine and its tab stays clean. It can reappear later, after a `webp` upgrade that happens while `libtiff` is installed. There is **no Brewfile-level decision that prevents this**; it is a Homebrew packaging quirk, the warning is cosmetic, and the remedy above is a one-liner to re-run if it shows up again.

3. **Broken `rustup-init` symlink.** `brew doctor` flagged `/opt/homebrew/bin/rustup-init` as dangling — independent corroboration of §4.4's finding that the formula no longer ships it. Cleared with `brew cleanup`.

> **Known limitation:** with only one Mac available, "base" is a judgment call — everything you'd want on a fresh machine. It can only be validated when a second machine is set up. Expect to move an entry or two afterward; that is normal and cheap.

### Phase 1 — Scaffold ∥

| ID | Task | Acceptance |
| --- | --- | --- |
| P1-1 | Do all migration work in the **existing** clone at `~/Developer/dotfiles` on branch `chezmoi-migration`, driving chezmoi with explicit `--source=~/Developer/dotfiles`. Per D5 there is no `sourceDir` config entry — the move to `~/.local/share/chezmoi` happens once at cutover (P8-4), not now | Every `chezmoi` invocation in Phases 1–7 passes `--source`; no `sourceDir` key appears in `.chezmoi.toml.tmpl` |
| P1-2 | Install chezmoi; `chezmoi doctor` | No errors |
| P1-3 | Create `.chezmoi.toml.tmpl`, `.chezmoidata.toml`, `.chezmoiignore` | `chezmoi execute-template --init` renders valid TOML |

### Phase 2 — Port configs ∥ (one agent per row)

| ID | Task | Acceptance |
| --- | --- | --- |
| P2-1 | zsh: `dot_zshrc`, `dot_zprofile` + §4.4 fixes + §4.3 rewrites | New shell starts clean; no `~/.dotfiles` refs remain |
| P2-2 | git: `dot_config/git/config.tmpl` + `dot_config/git/ignore`; drop `excludesfile`; role-guard credential blocks | `git config --list --show-origin` shows expected values |
| P2-3 | vim + ghostty straight ports | Files match byte-for-byte |
| P2-4 | `exact_dot_zfunc/` + `dot_local/bin/` (mind the `exact_` asymmetry) | `sizeup`, `fnm_upgrade` autoload; `git cl` works |

### Phase 3 — Homebrew

| ID | Task | Acceptance |
| --- | --- | --- |
Phase 0.5 already did the classification, so this is a mechanical split of `brew/Brewfile` at its section markers into three files. No judgment calls remain.

| ID | Task | Acceptance |
| --- | --- | --- |
| P3-1 | Move the BASE section to `dot_config/homebrew/Brewfile` | Contains `antidote` + `chezmoi`; no work- or hardware-specific entries |
| P3-2 | Move the `PERSONAL (role = personal)` block to `dot_config/homebrew/Brewfile.role-personal` — `exiftool`, `ffmpeg`, `bento4`, `yt-dlp`, `makemkv`, and `deskflow` **if** R3's deskflow question resolves as personal | File exists; entries removed from base |
| P3-3 | Move the `OVERLAY: czimacos6457` block to `dot_config/homebrew/Brewfile.machine-czimacos6457` — `argus`, `aws-oidc`, `awscli`, `kubernetes-cli`, `monitorcontrol` | File exists; entries removed from base |
| P3-4 | Create `dot_config/homebrew/Brewfile.role-work` holding `argus`, `aws-oidc`, `awscli`, `kubernetes-cli` | File exists and is satisfied on this machine |
| P3-5 | Verify the split is lossless: the union of the three files equals the pre-split `brew/Brewfile` | `git show pre-chezmoi:brew/Brewfile` diffed against the concatenation shows only section-marker differences |

### Phase 4 — Scripts ∥

| ID | Task | Acceptance |
| --- | --- | --- |
| P4-1 | `run_once_before_10-install-homebrew.sh` | No-op when brew present |
| P4-2 | `run_onchange_after_20-install-packages.sh.tmpl` | Hash comments change when a Brewfile changes; script re-runs |
| P4-3 | `run_onchange_after_30-macos-defaults.sh` | Behaviour identical to `script/macos.sh` |
| P4-4 | **No rustup script.** The formula no longer ships `rustup-init` (§4.4), and completions come from Homebrew (§4.5). Instead: delete `zsh/zfunc/_rustup`, and correct the stale rustup paragraph in `brew/README.md` | `rustup` completions still work in a fresh shell, sourced from `$(brew --prefix)/share/zsh/site-functions/_rustup`; no rustup script exists in `.chezmoiscripts/` |

### Phase 5 — Secrets

| ID | Task | Acceptance |
| --- | --- | --- |
| P5-1 | `dot_config/zsh/private_secrets.zsh.tmpl` (note: `private_` on the file, **not** on `dot_config` — see §5) | Renders with `op` unlocked; renders empty (file removed) without it; target is `0600` |
| P5-2 | Source it from `dot_zshrc` | `$KG_API_KEY` set in a new shell |
| P5-3 | Add secret-scanning guard | Planted test secret is rejected |

### Phase 6 — Decommission dotbot

| ID | Task | Acceptance |
| --- | --- | --- |
| P6-1 | Remove submodules properly — for each of `dotbot`, `dotbot-brew`, `zsh/antidote`: `git submodule deinit -f <p>` → `git rm -f <p>` → `rm -rf .git/modules/<p>` | `.gitmodules` deleted; `git submodule status` empty |
| P6-2 | **Delete stale dotbot symlinks before first apply**: `~/.zprofile`, `~/.zshrc`, `~/.zfunc`, `~/.vim/vimrc`, `~/.gitconfig`, `~/.config/ghostty/config`, `~/.dotfiles`, `~/.local/bin/git_blobless_clone` | `find ~ -maxdepth 2 -type l -lname '*dotfiles*'` empty. **`~/.gitconfig` especially** — see §4.2 hazard |
| P6-3 | Delete `install`, `install.conf.yaml`, `script/`, `brew/`, `zsh/` leftovers — **but preserve the four README files first**, see below | Only the §3 tree remains |
| P6-4 | Drop the transitional block from `.chezmoiignore` (§3) now that the legacy directories are gone | `chezmoi ignored` lists only repo docs and non-matching overlays |

> **Do not let P6-3 destroy documentation.** `brew/`, `zsh/`, `vim/` and `git/` each carried a README — about 380 lines in total, covering Homebrew common tasks and the Python/pip notes, zsh startup order, vim history, and git credentials. A literal reading of "delete `brew/`, `zsh/`" takes all of it. They were moved to `runbooks/homebrew.md`, `runbooks/zsh-notes.md`, `runbooks/vim-notes.md` and `runbooks/git-notes.md` instead. **Phase 7 should decide what to fold into the rewritten README and what stays as reference.**

### Phase 7 — Docs ∥

| ID | Task | Acceptance |
| --- | --- | --- |
| P7-1 | Rewrite `README.md`: bootstrap one-liner, edit workflow under copy mode, per-machine model, framework rationale | No dotbot references |
| P7-1a | **Required README section — "Reconciling drift".** Port §9a into `README.md` in full: why programs that edit their own config now get reverted, the `git config --global` example, `chezmoi status` as the pre-apply habit, and the `re-add` vs `merge` split including the fact that `re-add` will not touch templates. This is explicitly a user-facing reference, not planning material — it must survive into the permanent docs | `README.md` contains the detection commands and the reconciliation table; a reader who has forgotten the workflow can recover it from the README alone, without opening `runbooks/` |
| P7-1b | **Required README section — "Trusting taps" (D8).** New-machine setup must list the `brew trust --formula …` commands verbatim, because `~/.homebrew/trust.json` is deliberately not repo-managed and `brew bundle` misbehaves until they are run. Call out that `alias man='batman'` depends on `eth-p/software/bat-extras-batman`, so an untrusted machine has a broken `man` | README lists every currently-trusted formula; following the README alone on a fresh Mac produces a warning-free `brew bundle check` |
| P7-2 | Rewrite `AGENTS.md` for chezmoi conventions | Reflects §3 layout, the `exact_` asymmetry, and the §4.5 rule that generated files never go in `exact_` directories |
| P7-3 | Add `runbooks/adding-a-machine.md` | Covers init prompts + creating an overlay Brewfile |
| P7-4 | Correct `brew/README.md`: remove the obsolete `rustup-init` instruction and the "regenerate `_rustup` by hand" paragraph (§4.4, §4.5) | No stale rustup guidance remains |

### Phase 8 — Verify & cut over

Verification procedures are detailed in §9. Ordered tasks:

| ID | Task | Acceptance |
| --- | --- | --- |
| P8-1 | Run the full §9 dry-run and scratch-destination suite against `--source=~/Developer/dotfiles` | Scratch tree matches expectations; no diffs unaccounted for |
| P8-2 | Merge `chezmoi-migration` to `main` and push | `origin/main` holds the chezmoi tree |
| P8-3 | Execute P6-2 (delete stale dotbot symlinks), **especially `~/.gitconfig`** | `find ~ -maxdepth 2 -type l -lname '*dotfiles*'` empty |
| P8-4 | **Source-dir relocation (D5):** `chezmoi init --apply aoberoi`, which clones from `origin` into `~/.local/share/chezmoi` | `chezmoi source-path` reports `~/.local/share/chezmoi`; init prompts fire; apply succeeds |
| P8-5 | Confirm the new source dir is clean and current, then retire the old clone at `~/Developer/dotfiles` | No unpushed commits or untracked files remain in the old clone before it is removed |
| P8-6 | Post-cutover smoke tests (§9) | New shell, git config, `brew bundle check`, `chezmoi verify` all pass |

---

## 9. Verification

**Dry runs (safe, before touching `$HOME`):**
```sh
chezmoi doctor
chezmoi execute-template --init < .chezmoi.toml.tmpl
chezmoi execute-template < .chezmoiscripts/run_onchange_after_20-install-packages.sh.tmpl
chezmoi ignored                    # confirm overlay filtering + README exclusion
chezmoi diff
chezmoi apply --dry-run --verbose
```

**Scratch-destination test** — materialise the whole tree without touching the real home directory or running scripts:
```sh
chezmoi apply --destination=/tmp/chezmoi-test --exclude=scripts
find /tmp/chezmoi-test
```
Compare against the current `$HOME` to catch omissions.

**Per-machine matrix.** Re-run `chezmoi execute-template` with each `machine`/`role` combination and confirm the git email, credential blocks, and Brewfile overlay selection each change as intended. This is the feature being bought — test it explicitly.

**Post-cutover:** new login shell has correct `$PATH`, completions, prompt, and `$KG_API_KEY`; `git config` resolves correctly; `brew bundle check` passes; `chezmoi verify` is silent.

**Flags to confirm against installed versions** (do not assume — Homebrew has changed these):
- ~~Whether `brew bundle install` upgrades outdated formulae by default~~ — **CONFIRMED 2026-08-06, Homebrew 6.0.15.** It does. `brew bundle install --help` reads: *"Install and upgrade (by default) all dependencies from the Brewfile"*, and `--no-upgrade` is *"Do not run brew upgrade on outdated dependencies."* So the long-standing dotbot complaint that `./install` upgraded everything was accurate, not folklore. **Resolution:** `run_onchange_after_20-install-packages.sh.tmpl` passes `--no-upgrade` explicitly on every layer. Applying dotfiles converges the *declared set*; upgrading stays a deliberate separate act (`brew bundle upgrade --file=…` or plain `brew upgrade`). Passed explicitly rather than left to the default because `$HOMEBREW_BUNDLE_NO_UPGRADE` can flip it either way.

**Corrections to this document's own verification advice, learned during Phase 4:**
- `chezmoi managed` **does** list `.chezmoiscripts/*` entries on v2.72.0 — its default `--include` covers the `scripts` entry type. Asserting "managed must not list scripts" is unmeetable. Use `chezmoi managed --include=files,dirs,symlinks` to assert that scripts are never written into `$HOME`.
- `chezmoi source-path` does not resolve script targets (`not managed`). Expected, not a defect.
- `stat` returning falsy for a missing file is **confirmed** — a simulated personal machine with no `Brewfile.machine-mbp-personal` skipped both the hash line and the stanza rather than erroring.
- Whether `brew bundle` still emits `Brewfile.lock.json` (`.chezmoiignore` covers it either way).
- `stat` returning falsy for missing files.
- The antidote path under `$(brew --prefix)`.

---

## 9a. Living with copy mode: drift and reconciliation

Under dotbot, a program that rewrote `~/.gitconfig` wrote *into the repo file* — captured for free. Under copy mode that write lands on an independent copy, and the next `chezmoi apply` silently reverts it. This is the single biggest behavioural regression of D1 and needs a documented habit, not just awareness.

**Concrete instance in this setup:** `git config --global …` writes to `~/.config/git/config`, which will be a chezmoi-managed template. Those writes will be lost.

**Detection** — make this reflexive before every apply:
```sh
chezmoi status      # M = destination differs from source
chezmoi diff        # exactly what would change
chezmoi verify      # silent when everything matches
```

**Reconciliation:**

| Tool | Use | Limit |
| --- | --- | --- |
| `chezmoi re-add <target>` | Pull destination edits back into the source | **Will not overwrite templates.** Works for `dot_zshrc`; does **not** work for `dot_config/git/config.tmpl` |
| `chezmoi merge <target>` | Three-way merge of destination / source / target in a merge tool | The correct tool for templated files. Default is `vimdiff`; set `merge.command` to mirror the existing VS Code mergetool setup |
| `chezmoi merge-all` | Sweep every drifted target | — |

**Design-level options for files an application owns:**
- `create_` — chezmoi writes it only if absent, then never touches it again. Right for "seed once, app owns it thereafter."
- `modify_` — the source entry is a script that transforms the existing file, letting you enforce a few keys while leaving the rest alone.

**Recommendation for git specifically:** prefer editing the template over `git config --global`. Optionally add `[include] path = ~/.config/git/config.local` to the template and leave that file unmanaged as a home for machine-local overrides — noting that `--global` still targets the main file, so this is a convention you adopt, not a guardrail that enforces itself.

---

## 10. Risks

| Risk | Mitigation |
| --- | --- |
| **Copy mode breaks muscle memory** — editing `~/.zshrc` silently doesn't reach the repo | `edit.apply = true`; document `chezmoi edit --apply` prominently in README; `chezmoi verify` detects drift |
| **`~/.gitconfig` shadows `~/.config/git/config`** | P6-2, called out twice |
| **Stale symlinks collide with first apply** | P6-2 precedes any apply |
| **`chezmoi apply` needs 1Password unlocked** | Template guarded by `lookPath "op"`; degrades to no secrets file |
| **Losing the only copy of a secret while moving it** | Create and verify the 1Password item first; compare hashes rather than printing values |
| **Old clone at `~/Developer/dotfiles` drifts or holds unpushed work after cutover** | P8-5 gates removal on a clean, fully pushed state; `chezmoi source-path` confirms the new location first |
| **Losing file history** | Use `git mv` for every relocation so blame survives |
| **macOS defaults re-run disruptively** (`killall Dock`) | `run_onchange_`, not `run_` |
| **Big-bang cutover** | `pre-chezmoi` tag + feature branch; scratch-destination test first |
| **Divergence from the Linux repo** | Flat layout (D2) and shared `.chezmoidata`/1Password conventions chosen for this reason |

---

## 11. Explicitly out of scope

- Unifying with `dotfiles-linux` — agreed to keep separate.
- Any Linux/Windows support in this repo.
- Reworking the antidote plugin list, prompt, or completion styles. Port as-is; tune later.
- Migrating away from Homebrew (e.g. to Nix).
