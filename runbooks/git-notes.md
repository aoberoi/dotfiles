# git

Notes on the git configuration. This was `git/README.md` before the chezmoi migration, which is why
its scope is narrow — credentials were the one part that needed explaining.

The config lives at `dot_config/git/config.tmpl` → `~/.config/git/config` and
`dot_config/git/ignore` → `~/.config/git/ignore`. The `.tmpl` suffix is there because the commit
email is a per-machine value (D4) and the KDE credential block is role-guarded. Git reads
`~/.config/git/ignore` natively, so there is no `core.excludesfile` pointer.

## Credentials

[Git Credential Manager](https://github.com/git-ecosystem/git-credential-manager) is a cross-platform credential manager
which supports many popular git-based source code hosts (e.g. GitHub). It is installed by Homebrew —
`cask "git-credential-manager"` in the base Brewfile — and configured in `config.tmpl`.

The first time you push to a host like GitHub, you will be asked to log in.

Two things in the `[credential]` section that look wrong but are not:

* `helper =` (empty) comes first, deliberately. It resets the helper list, discarding `osxkeychain`
  inherited from the system config, so only GCM applies. Keep the two lines in that order.
* The helper path is `/usr/local/share/gcm-core/git-credential-manager`, not somewhere under
  `/opt/homebrew`. GCM's cask ships a `.pkg` that installs to `/usr/local` even on Apple Silicon.

GCM's
[`configure` command](https://github.com/git-ecosystem/git-credential-manager/blob/main/docs/faq.md#what-do-the-configure-and-unconfigure-commands-do)
always adds the `https://dev.azure.com` block with `useHttpPath = true`, even when the user does not
use Azure Repos. The setting is benign on such a machine: it is scoped to that host, contacts nothing
by itself, and only tells Git to pass the URL path to credential helpers for `dev.azure.com` so GCM
could
[distinguish organizations](https://github.com/git-ecosystem/git-credential-manager/blob/main/docs/configuration.md#credentialusehttppath).
The macOS installer runs `configure`, so keeping the block on every machine that uses GCM accepts the
tool's durable default instead of fighting it after installs or upgrades.

The `https://invent.kde.org` block (`provider = generic`) is different: it reflects an actual
personal account and therefore remains guarded by `role = personal`.

Verify what git actually resolved with:

```
$ git config --list --show-origin
```
