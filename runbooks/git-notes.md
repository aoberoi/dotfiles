# git

Notes on the git configuration. This was `git/README.md` before the chezmoi migration, which is why
its scope is narrow — credentials were the one part that needed explaining.

The config lives at `dot_config/git/config.tmpl` → `~/.config/git/config` and
`dot_config/git/ignore` → `~/.config/git/ignore`. The `.tmpl` suffix is there because the commit
email is a per-machine value (D4) and two credential blocks are role-guarded. Git reads
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

Two host-specific blocks are guarded by role, so they only land where they apply:
`https://dev.azure.com` (`useHttpPath = true`, so GCM can tell org accounts apart) on work machines,
and `https://invent.kde.org` (`provider = generic`) on personal ones.

Verify what git actually resolved with:

```
$ git config --list --show-origin
```
