# Personal Mac chezmoi adoption plan

Status: **live cutover verified — pending real Terminal confirmation, push decision, and cooling-off**

Target machine: `iris.local` (`arm64`, user `ankur`)

Target identity:

| Setting | Planned value |
| --- | --- |
| `machine` | `iris` — confirm before Phase 2 |
| `role` | `personal` |
| `email` | `aoberoi@gmail.com` |
| chezmoi source | `~/.local/share/chezmoi` |

This is the execution plan for moving the personal Mac from the legacy dotbot checkout at
`~/Developer/dotfiles` to the chezmoi rewrite on `origin/main`. It derives from
`origin/main:runbooks/chezmoi-migration-plan.md`, but adapts that work-Mac cutover to the actual
state of this machine.

The plan is intentionally conservative. The old checkout remains the rollback source until the
new source, managed files, shell, Git configuration, package layers, and feature-branch work have all
been verified.

## 1. Current state and scope

Facts verified on 2026-08-07:

- Local `main` is clean and 20 commits behind `origin/main`.
- `origin/main` is at `48cc905`; `pre-chezmoi` marks the rewrite boundary.
- Homebrew 5.1.14 is installed at `/opt/homebrew/bin/brew`.
- `chezmoi` is not installed or initialized.
- The Mac is Apple Silicon and is a personal Mac.
- Git currently resolves `aoberoi@gmail.com`.
- No `~/.local/share/chezmoi` or `~/.config/chezmoi/chezmoi.toml` exists.
- The following live symlinks point into `~/Developer/dotfiles`:

  1. `~/.zprofile`
  2. `~/.zshrc`
  3. `~/.zfunc`
  4. `~/.vim/vimrc`
  5. `~/.gitconfig`
  6. `~/.config/ghostty/config`
  7. `~/.dotfiles`
  8. `~/.local/bin/git_blobless_clone`

Feature-branch state that must survive retirement of the old clone:

| Ref | Remote copy? | Material to preserve |
| --- | --- | --- |
| `in-progress-20260807` (`334e281`) | Yes, `origin/in-progress-20260807` | Experimental packages and LM Studio `PATH` |
| `sizeup` | Yes, `origin/sizeup` | Large zfunc evolution; forward-port separately |
| `window-management` | Yes, `origin/window-management` | macOS defaults and Notion helper work |

The local stash is not a migration dependency. Its Brewfile and LM Studio changes are identical to
`in-progress-20260807`, and its Apple Spaces change is identical to `window-management`. The three
remote branches above collectively preserve all of it.

This migration does **not** automatically merge the experimental branches. It verifies their remote
copies, then ports only the changes explicitly approved at the Phase 3 decision gate.

## 2. Non-negotiable safety rules

1. **Do not run `git pull`, `git switch origin/main`, or otherwise update the old checkout in
   place.** The rewrite deletes the legacy paths while `$HOME` still points into them, which would
   immediately leave the shell and Git configuration dangling.
2. **Do not run `chezmoi init --apply` while any of the eight legacy symlinks exists.** Chezmoi can
   follow a symlink and write into or delete from the old repository. The rewrite encountered this
   specifically with `~/.zfunc/_rustup`.
3. **Do not delete the old checkout during cutover.** Preserve it until every acceptance check and
   the Git-ref archival check passes.
4. **Do not run destructive cutover steps in parallel.** One coordinator owns Phase 6 from the
   first symlink move until `chezmoi verify` succeeds.
5. **Do not print secret values.** This machine is `role = personal`, so the work secrets template
   should render no file. Any secret investigation uses existence checks or hashes only.
6. **Do not mass-upgrade packages as part of adoption.** Every `brew bundle install` invocation
   uses `--no-upgrade`; package upgrades remain a separate task.
7. **Prefer recoverable moves over deletion.** The eight symlinks move to a timestamped backup.
8. **Stop at a failed gate.** Do not continue because a later phase might repair an earlier one.

## 3. Execution and subagent model

The primary agent is the migration coordinator. It owns the plan, user decisions, remote-ref
verification, source initialization, cutover, rollback, and final verification.

Subagents may be used only for bounded tasks with non-overlapping file ownership. All agents share
the same filesystem, so two agents must never edit the same file concurrently.

### Recommended wave structure

| Wave | Work | Parallel? | Ownership |
| --- | --- | --- | --- |
| A | Read-only inventory and remote-ref verification | Yes | Coordinator plus one audit agent |
| B | New source init and baseline verification | No | Coordinator |
| C | Approved forward ports | Yes, by file | Up to three implementation agents |
| D | Render, package, docs, and config audits | Yes, read-only | Up to three verification agents |
| E | Symlink cutover and first apply | **No** | Coordinator only |
| F | Smoke tests | Mostly yes after apply | Verification agents, then coordinator sign-off |
| G | Commit/push and old-clone retirement | No | Coordinator, with user approval where needed |

### Phase 3 file ownership if all three ports are approved

| Agent | Sole write ownership |
| --- | --- |
| Packages agent | `dot_config/homebrew/Brewfile.machine-iris` |
| Shell agent | `dot_zshrc` |
| Defaults agent | `.chezmoiscripts/run_onchange_after_30-macos-defaults.sh` |

The coordinator owns documentation files and integration. Agents must inspect the current file
before editing, use `apply_patch`, avoid unrelated formatting changes, and report the exact tests
they ran. The coordinator reviews the combined diff before any apply.

## 4. Phase 0 — human decisions

This phase is blocking.

### P0-1 Confirm the machine slug

Proposed value: `iris`, derived from `iris.local`.

Requirements:

- filename-safe;
- stable even if the macOS display name changes;
- suitable for `Brewfile.machine-iris`.

Acceptance: the user confirms `iris` or supplies a replacement. Substitute the final value for
`iris` everywhere below.

### P0-2 Classify local-only experiments

Decide whether each item should be ported now:

| Change | Recommended disposition | Reason |
| --- | --- | --- |
| `cmake` | `Brewfile.machine-iris` | Added experimentally for a local VoiceInk build |
| `wireshark-app` | `Brewfile.machine-iris` as a **cask** | Installed here; the old experimental commit used the wrong Brewfile kind |
| `mitmproxy` | `Brewfile.machine-iris`, only if still wanted | Recorded experimentally but not currently installed |
| LM Studio CLI path | `dot_zshrc`, using `$HOME` | Machine-local installed tool; remove hardcoded `/Users/ankur` |
| `AppleSpacesSwitchOnActivate=false` | macOS defaults script | Preserved on `origin/window-management`; intentional UI-automation behavior |
| `sizeup` branch | Defer to a separate forward-port | Large, independent zfunc change |
| `window-management` branch | Defer to a separate forward-port | Independent feature branch already present on origin |

Acceptance: every row is explicitly marked port/defer/drop in the execution notes.

## 5. Phase 1 — preserve and inventory the legacy source

Owner: coordinator. An audit subagent may independently verify the remote refs.

### P1-1 Reconfirm the old checkout is stable

From `~/Developer/dotfiles`:

```sh
git status --short --branch
git fetch --prune origin
git rev-parse main
git rev-parse origin/main
git for-each-ref --format='%(refname) %(objectname)' refs/heads refs/remotes/origin
```

Acceptance:

- working tree is clean;
- `main` remains at the legacy commit;
- `origin/main` remains the fetched chezmoi rewrite;
- the three feature branches and their origin counterparts are visible.

If the working tree is no longer clean, stop and inventory the new changes before continuing.

### P1-2 Verify feature branches on origin

Do not switch branches in the legacy checkout. Compare refs directly:

```sh
git rev-parse in-progress-20260807 origin/in-progress-20260807
git rev-parse window-management origin/window-management
git rev-parse sizeup origin/sizeup
git ls-remote --heads origin \
  in-progress-20260807 window-management sizeup
```

Acceptance:

- each local/remote pair resolves to the same commit;
- GitHub reports all three branch heads;
- expected commits are `334e281` for `in-progress-20260807`, `e33fb4f` for
  `window-management`, and `79e0806` for `sizeup`;
- no checkout or stash operation was needed.

### P1-3 Capture the live symlink manifest

For each of the eight paths, record:

- that it is a symlink;
- its exact `readlink` target;
- whether the target exists;
- the target's checksum where it is a regular file.

Acceptance: every link resolves beneath `/Users/ankur/Developer/dotfiles`. Any link pointing
elsewhere stops the plan for investigation.

### Gate G1 — legacy source is recoverable

Proceed only when the three remote branches are verified and the symlink manifest is complete.

## 6. Phase 2 — create the new source without applying

Owner: coordinator. Serialized.

### P2-1 Bring Homebrew's command surface current

The installed Homebrew 5.1.14 does not provide `brew trust`; the latest origin documentation assumes
Homebrew 6.x.

`brew update` changes shared system tooling, so the coordinator must announce this checkpoint and
obtain the user's go-ahead immediately before running it. A subagent must not run it independently.

```sh
brew update
brew --version
brew help trust
```

Acceptance:

- Homebrew reports a version that provides `brew trust`;
- no formula or cask mass-upgrade was run;
- `brew doctor` findings are recorded, not blindly repaired.

Do not react to a sandbox-only “Cellar is not writable” diagnostic by changing ownership. Confirm
permissions from an ordinary terminal before considering any `chown` action.

### P2-2 Install migration control-plane tools

Install these before replacing shell files so the new zsh configuration can source antidote even
during a partially completed cutover:

```sh
brew install chezmoi antidote gitleaks
command -v chezmoi
command -v antidote
command -v gitleaks
```

Acceptance:

- `chezmoi` resolves to `/opt/homebrew/bin/chezmoi`;
- antidote's Homebrew source file exists under `$HOMEBREW_PREFIX/opt/antidote/`;
- gitleaks runs.

### P2-3 Initialize, but do not apply

```sh
chezmoi init aoberoi
```

Answers:

```text
Machine short name: iris
Role: personal
Git author email: aoberoi@gmail.com
```

Explicitly omit `--apply`.

Acceptance:

```sh
chezmoi source-path
git -C "$HOME/.local/share/chezmoi" status --short --branch
sed -n '/^\[data\]/,/^$/p' "$HOME/.config/chezmoi/chezmoi.toml"
```

Expected:

- source path is `~/.local/share/chezmoi`;
- source checkout is clean at current `origin/main`;
- data contains `machine = "iris"`, `role = "personal"`, and the personal email;
- none of the eight legacy symlinks changed.

### P2-4 Create an integration branch

If Phase 3 will port any changes or correct documentation, create
`codex/iris-chezmoi-adoption` in the new source checkout. Do not create the branch in the old clone.

### Gate G2 — two independent sources exist

Proceed only when the legacy checkout and the new clean chezmoi source both exist, and no apply has
occurred.

## 7. Phase 3 — forward-port approved local changes

Owner: implementation subagents by non-overlapping file, followed by coordinator review.

Skip any task the user did not approve in P0-2.

### P3-1 Personal machine package layer

Create `dot_config/homebrew/Brewfile.machine-iris` with the same explanatory header style as the
existing `Brewfile.machine-czimacos6457`.

Candidate entries:

```ruby
brew "cmake"           # Build VoiceInk locally
cask "wireshark-app"   # Inspect network traffic; installation may request sudo
brew "mitmproxy"       # Include only if explicitly approved
```

Acceptance:

- entries are absent from the base and role layers;
- Wireshark uses `cask`, not `brew`;
- `chezmoi ignored` selects the `iris` layer and hides `czimacos6457`;
- comments distinguish machine-specific experiments from role-wide personal tools.

### P3-2 LM Studio shell path

Port the old branch's LM Studio block into `dot_zshrc`, replacing the absolute username with:

```zsh
export PATH="$PATH:$HOME/.lmstudio/bin"
```

Prefer an existence guard if the directory may not always be installed.

Acceptance: `zsh -n dot_zshrc` succeeds and no `/Users/ankur` literal is introduced.

### P3-3 Apple Spaces default

Port the `AppleSpacesSwitchOnActivate` setting from `origin/window-management` into
`.chezmoiscripts/run_onchange_after_30-macos-defaults.sh`.

Preserve the script's intentional behavior:

- it has a bash shebang;
- it does **not** gain `set -euo pipefail`;
- the setting is placed before the final settings activation and Dock reload;
- comments explain the UI-scripting motivation without retaining dead commented commands.

Acceptance: `bash -n` succeeds and the diff is limited to the approved setting.

### P3-4 Correct stale onboarding documentation

The latest `README.md` correctly requires explicit cask trust, but
`runbooks/adding-a-machine.md` still says the personal casks do not require trust. Update the latter
to match the latest README:

```sh
brew trust --formula eth-p/software/bat-extras-batman
brew trust --formula anomalyco/tap/opencode
brew trust --cask 1password/tap/1password-cli
brew trust --cask deskflow/tap/deskflow
```

Also update comments that claim the personal Mac does not yet exist.

Acceptance: the README, adding-machine runbook, and Brewfile comments tell the same story.

### P3-5 Coordinator integration review

The coordinator reviews:

```sh
git status --short
git diff --check
git diff
rg '/Users/ankur|deskflow/homebrew-tap|brew "wireshark-app"' .
```

Do not commit yet unless retaining the exact pre-cutover state in Git is useful. If committed, keep
the commit local until the full migration passes.

### Gate G3 — source changes are intentional

Proceed only when every changed line maps to a P0-2 decision or the documentation correction.

## 8. Phase 4 — read-only and scratch validation

This phase may use parallel read-only subagents after the source stops changing.

### P4-1 Chezmoi rendering audit

```sh
chezmoi doctor
chezmoi ignored
chezmoi managed --include=files,dirs,symlinks
chezmoi status
chezmoi diff
chezmoi apply --dry-run --verbose
```

Expected personal-machine behavior:

- base, `role-personal`, and `machine-iris` are selected;
- `role-work` and `machine-czimacos6457` are ignored;
- the shared Azure `useHttpPath` GCM default is rendered even though this machine does not use Azure Repos;
- the KDE credential block is rendered;
- `~/.config/zsh/secrets.zsh` is not written;
- repo documentation is ignored as a target.

### P4-2 Scratch-destination audit

Use a new `mktemp -d` destination and exclude scripts:

```sh
chezmoi apply --destination=/explicit/scratch/path --exclude=scripts --verbose
find /explicit/scratch/path -print
```

Inspect the rendered Git config, Brewfile layers, zsh files, modes, and `~/.zfunc` contents. Never
print a secret file even though none should exist for this role.

Acceptance:

- rendered tree contains exactly the expected personal files;
- `.zfunc` contains only the managed hand-written functions;
- `git_blobless_clone` is executable;
- no source-only docs are materialized;
- no work secret file exists.

### P4-3 Template matrix regression

An audit subagent should render at least these conceptual identities without applying to `$HOME`:

| Machine | Role | Expected layers |
| --- | --- | --- |
| `iris` | personal | base + role-personal + machine-iris |
| `czimacos6457` | work | base + role-work + machine-czimacos6457 |
| arbitrary second work slug | work | base + role-work only |

Acceptance: adding `machine-iris` does not alter the two work cases.

### Gate G4 — apply is predictable

The coordinator signs off on the actual dry-run diff and scratch tree. No unexplained path may be
created, modified, or deleted.

## 9. Phase 5 — pre-converge packages and trust

This phase changes Homebrew state but does not touch the legacy dotfile symlinks.

Before changing Homebrew state, capture these read-only baselines in the execution log or an
adjacent artifact:

```sh
brew leaves
brew list --formula --versions
brew list --cask --versions
brew tap
brew trust --json v1
defaults read -g AppleSpacesSwitchOnActivate
```

The last command may report that the key does not exist; record that result. Homebrew installs,
trust decisions, and macOS defaults are not transactional. Restoring the legacy symlinks does not
undo them, so any compensation must be decided from this baseline rather than improvised.

### P5-1 Trust the exact personal-machine entries

Run manually and deliberately:

```sh
brew trust --formula eth-p/software/bat-extras-batman
brew trust --formula anomalyco/tap/opencode
brew trust --cask 1password/tap/1password-cli
brew trust --cask deskflow/tap/deskflow
brew trust --json v1
```

Acceptance: the JSON output contains all four entries with the correct formula/cask kind.

### P5-2 Pre-converge the selected Brewfiles

Using the files in the new source checkout:

```sh
brew bundle install --no-upgrade --file="$HOME/.local/share/chezmoi/dot_config/homebrew/Brewfile"
brew bundle install --no-upgrade --file="$HOME/.local/share/chezmoi/dot_config/homebrew/Brewfile.role-personal"
brew bundle install --no-upgrade --file="$HOME/.local/share/chezmoi/dot_config/homebrew/Brewfile.machine-iris"
```

Skip the third command if no machine layer was approved.

Acceptance:

- no mass-upgrade occurs;
- each selected layer's `brew bundle install --no-upgrade` exits zero without trust warnings;
- a later `brew bundle check` may still report already-installed but outdated entries as needing an
  update; record those separately rather than upgrading them during adoption;
- antidote, chezmoi, gitleaks, fzf, and other shell dependencies are present before cutover;
- unrelated installed packages are not removed (Brew bundle is additive).

### Gate G5 — the new files will not reference missing tools

Proceed only when the selected Brewfiles are satisfied.

## 10. Phase 6 — serialized cutover

Owner: coordinator only. No subagents edit files or run chezmoi during this phase.

Keep the current terminal open until the full phase succeeds.

### P6-1 Create the rollback directory

Create a timestamped directory outside both Git checkouts, for example under
`~/.local/state/dotfiles-migration/`. Record its absolute path in the execution notes.

### P6-2 Revalidate and move only the eight symlinks

Immediately before moving anything, re-run the symlink manifest checks. Each path must still be a
symlink into the old checkout.

Move the symlink objects—not their targets—into the rollback directory, preserving enough path
structure to restore them unambiguously. Do not use recursive deletion.

After the move:

```sh
find "$HOME" -maxdepth 4 -type l -lname '/Users/ankur/Developer/dotfiles/*' -print
```

Acceptance:

- all eight symlinks exist in the rollback directory;
- none remains active under `$HOME`;
- files in the old Git checkout are still present and unchanged.

### P6-3 Apply files only

```sh
chezmoi apply --exclude=scripts --verbose
```

This deliberately separates the critical symlink-to-file replacement from package/defaults/hooks
scripts.

Acceptance:

- `~/.zprofile`, `~/.zshrc`, `~/.zfunc`, `~/.vim/vimrc`, and Ghostty config are real files or real
  directories, not symlinks;
- `~/.gitconfig` is absent;
- `~/.config/git/config` exists and identifies the personal email;
- `~/.dotfiles` is absent;
- `~/.local/bin/git_blobless_clone` is a real executable file;
- the old checkout remains clean.

If this step fails before usable shell and Git files exist, stop and execute the rollback procedure
in Section 13.

### P6-4 Run the full apply

```sh
chezmoi apply --verbose
```

Because packages were pre-converged, the package script should be a fast, non-upgrading check. The
macOS defaults script may reload the Dock. The git-hooks script should point the new source clone at
`.githooks`.

Acceptance:

- apply exits zero;
- no work-secret prompt appears;
- no `~/.config/zsh/secrets.zsh` exists;
- `git -C ~/.local/share/chezmoi config --local --get core.hooksPath` returns `.githooks`.

### Gate G6 — cutover complete

Do not retire the old checkout yet. First complete all Phase 7 checks.

## 11. Phase 7 — verification wave

After the apply finishes, read-only verification can be divided among subagents. The coordinator
collects all results and reruns any failed check directly.

### P7-1 Chezmoi verification

```sh
chezmoi source-path
chezmoi doctor
chezmoi status
chezmoi verify
```

Expected: default source path, no errors, empty status, silent successful verify.

### P7-2 Git verification

```sh
git config --list --show-origin
git config --global --get user.email
git config --get credential.https://invent.kde.org.provider
git config --get credential.https://dev.azure.com.useHttpPath
```

Expected:

- personal email;
- KDE provider `generic`;
- Azure `useHttpPath` is `true`, as GCM configures on every machine;
- configuration originates from `~/.config/git/config`, not `~/.gitconfig`;
- `git cl` resolves through `~/.local/bin/git_blobless_clone`.

### P7-3 Homebrew verification

Run `brew bundle check` for base, personal role, and the optional `iris` layer. Confirm there are no
trust warnings and no unexpected unsatisfied entries.

### P7-4 Fresh login-shell smoke test

Open a genuinely new terminal window and verify:

| Check | Expected |
| --- | --- |
| Prompt | Pure prompt renders |
| `alias man` | `man=batman`; `batman ls` works |
| Git completion | `git che<TAB>` completes |
| Functions | `sizeup` and `fnm_upgrade` autoload |
| FZF | `bindkey "^R"` reports `fzf-history-widget` |
| Rust | `cargo --version`; no surprise toolchain download |
| LM Studio, if ported | `lms` resolves from `$HOME/.lmstudio/bin` |
| Personal role | no `secrets.zsh`; no `KG_API_KEY` |

### P7-5 Hook verification

Verify the tracked pre-commit hook is executable and configured. Test it with a synthetic disposable
file containing a non-secret string, then use the hook's documented safe test mechanism for a
credential-shaped placeholder. Do not introduce a real credential.

### P7-6 Legacy isolation check

```sh
find "$HOME" -maxdepth 4 -type l -lname '/Users/ankur/Developer/dotfiles/*' -print
git -C /Users/ankur/Developer/dotfiles status --short --branch
```

Expected: no active links and the old checkout still clean.

### Gate G7 — migration accepted

All P7 checks pass, and a fresh interactive login shell is usable.

## 12. Phase 8 — retain changes and retire the legacy checkout

Owner: coordinator.

### P8-1 Review and commit source changes

In `~/.local/share/chezmoi`:

```sh
git status --short
git diff --check
git diff
```

Commit only the approved `iris` layer, shell/default changes, and documentation corrections. Push or
open a PR only with the user's approval.

### P8-2 Re-verify remote preservation

Before retiring anything, fetch origin and repeat P1-2. Confirm that all desired feature work is
either:

- forward-ported and committed in the new source; or
- still present on its verified origin branch.

### P8-3 Cooling-off period

Prefer renaming or moving the old checkout to an archival location for several days rather than
deleting it immediately. Since no `$HOME` symlink points into it anymore, its location no longer
affects the live configuration.

After the cooling-off period, deletion is a separate explicitly approved action. Report what is
removed and confirm that the three feature branches remain available on origin.

## 13. Rollback procedure

Rollback is owned by the coordinator and is only needed if the file-only apply leaves the shell or
Git configuration unusable.

1. Stay in the already-open terminal.
2. Record the apply error and `chezmoi status`; do not run repeated applies blindly.
3. Move any newly created versions of the eight legacy target paths into a separate failed-apply
   directory. Do not overwrite them or mix them with the saved symlinks.
4. Restore the eight symlink objects from the rollback directory to their original paths.
5. Confirm each `readlink` target exists in the old checkout.
6. Start a new login shell and run `git config --list --show-origin`.
7. Leave the new chezmoi source and config in place for diagnosis; neither controls `$HOME` after the
   symlinks are restored.

Restoring symlinks rolls back dotfile delivery only. It does not uninstall packages, revoke tap
trust, or restore macOS defaults. Compare those systems with the Phase 5 baseline and propose any
compensating commands for explicit approval; do not run package removals or defaults rewrites as an
automatic rollback.

Rollback acceptance:

- all eight legacy symlinks are restored;
- the old shell and Git configuration work;
- the old checkout remains unchanged;
- the failed new files and logs remain available for diagnosis.

## 14. Completion definition

The migration is complete only when all of the following are true:

- `chezmoi source-path` reports `~/.local/share/chezmoi`;
- `chezmoi doctor`, `status`, and `verify` are clean;
- no symlink in `$HOME` points into the legacy checkout;
- personal Git identity and credentials render correctly;
- no work secret file or work-only package layer is present;
- base, personal-role, and optional `iris` Brewfiles are satisfied without trust warnings;
- a fresh login shell passes the smoke tests;
- the new source's pre-commit hook is active;
- feature-branch material is preserved on origin or forward-ported;
- the old checkout has not been deleted before the cooling-off decision;
- any new source changes have been reviewed and intentionally committed.

## 15. Execution log template

Fill this in during execution so another agent can resume safely.

```text
Machine slug confirmed: iris
P0-2 decisions:
  port now = cmake, wireshark-app, mitmproxy
  drop = LM Studio PATH, AppleSpacesSwitchOnActivate
  defer = sizeup branch, remaining window-management branch
Remote feature refs verified at: 2026-08-07
  origin/in-progress-20260807 = 334e281
  origin/window-management    = e33fb4f
  origin/sizeup               = 79e0806
Legacy checkout state:
  current branch = window-management
  tracked changes = none
  intentional untracked file = runbooks/personal-mac-chezmoi-adoption.md
Symlink manifest: complete; all eight expected links resolve into the legacy checkout; no extras
Rollback directory: /Users/ankur/.local/state/dotfiles-migration/20260807T1420-iris
New source commit before local changes: 48cc905
Integration branch: codex/iris-chezmoi-adoption
Source changes made: Brewfile.machine-iris (cmake, mitmproxy, wireshark-app); personal-role comments; cask-trust onboarding corrections
Local checkpoint commit: 796ab02 Add iris personal Mac adoption
Dry-run reviewer: three-agent audit passed; no unexplained changes
Scratch destination: /private/tmp/chezmoi-iris-render.VHuW5K
Package/trust reviewer: four exact personal trust entries present; all three layers converge with --no-upgrade; check reports outdated entries only
Cutover start time: 2026-08-07 14:20 America/Los_Angeles
File-only apply result: exit 0; managed targets are real files/directories; legacy-only links absent
Full apply result: exit 0; base/personal/iris layers complete; macOS defaults ran; hook wired
Verification agents and findings:
  chezmoi = source/branch correct; status and verify empty; doctor exit 0 with sandbox-only network/hardlink limitations
  git/paths = personal identity and KDE block correct; shared Azure GCM default present; secrets/legacy links absent; modes correct
  homebrew = exact four trust entries; all layers pass --no-upgrade; mitmproxy cask 12.2.3
  shell/hooks = pseudo-TTY scratch smoke test and hook pass; authoritative real Terminal launch pending
  incidental Homebrew behavior = first control-plane install auto-cleaned ripgrep, shfmt, libiconv, icu4c@77; ripgrep was restored and declared directly after trust-aware dependency audit
Final source commits: recorded on the local integration branch; use `git log -2 --oneline`
Push/PR status: integration branch remains local; user approval pending
Old checkout archival path:
Cooling-off deletion decision:
```
