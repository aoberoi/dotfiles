# Homebrew

Notes on the Homebrew package set and the manual follow-up some packages need. This was
`brew/README.md` before the chezmoi migration, which is why its scope is "everything Homebrew"
rather than one topic.

Set up essential packages from the Homebrew package manager.

## Initial setup

* The first time you git push a change that requires authentication, Git Credential Manager will
  ask for the system password. You should type it in and choose 'Always Allow' so it doesn't prompt
  every time. See [`git-notes.md`](git-notes.md) for how the helper is configured.

* Non-official taps must be trusted before Homebrew will load them or check whether they are
  outdated. Trust is per-machine (`~/.homebrew/trust.json`) and is deliberately not managed by this
  repo (D8), so each new Mac needs this run by hand:

  ```
  $ brew trust --formula eth-p/software/bat-extras-batman
  ```

  `alias man='batman'` in `dot_zshrc` depends on that formula, so an untrusted machine has a broken
  `man`.

* Rust needs two things after the formula is installed, and neither is what this file used to say.

  The formula **no longer ships `rustup-init`** — it states so in its own caveat. Instead, put
  `$(brew --prefix rustup)/bin` on `$PATH`; that directory holds the `cargo`, `rustc` and `rustfmt`
  shims, and without it none of them resolve even though rustup itself is installed. `dot_zprofile`
  now does this, spelled `$HOMEBREW_PREFIX/opt/rustup/bin` so no subshell is spawned on every login.

  Then install an actual toolchain — the formula does not bring one:

  ```
  $ rustup toolchain install stable
  ```

  `rustup default` may already report `stable-…` before you do this; that is only a recorded
  preference, not an installed toolchain. Check with `rustup toolchain list`.

  Completions need no maintenance. Homebrew installs `_rustup` into
  `$(brew --prefix)/share/zsh/site-functions`, which `dot_zshrc` already puts on `FPATH`, so it
  tracks `brew upgrade rustup` automatically. The copy that used to be checked in at
  `zsh/zfunc/_rustup` (now `exact_dot_zfunc/`) was deleted: because `~/.zfunc` is prepended to
  `fpath` *after* Homebrew's site-functions, that stale copy was actively shadowing the current one.
  Do not re-add it — `exact_dot_zfunc/` is `exact_`, so chezmoi owns that directory wholly.

  Cargo completions are a separate matter and are not set up — see R2 in
  [the migration runbook](chezmoi-migration-plan.md).

* The 1Password CLI installation requires inputting the admin password. After this completes, follow
  the [instructions to sign in](https://developer.1password.com/docs/cli/get-started#sign-in).

* MakeMKV (personal role only — `Brewfile.role-personal`) requires adding a license key after the
  installation is complete. The current beta key
  can be found in this [forum post](https://forum.makemkv.com/forum/viewtopic.php?t=1053). On macOS,
  you make need to right-click the app in /Applications and select "Open", then select "Open" in the
  warning since it is not signed by Apple.

## What is included?

The idea is to record the packages I believe any system I use should have on it, which I call essentials.

If a package is not an essential (or not yet), install it with `brew install <package>`. Later, if I decide the
package is essential, then I can add it to the appropriate Brewfile layer and install as described below.

### The three layers

There is no longer one Brewfile. Decision D3 in
[the migration runbook](chezmoi-migration-plan.md) defines three layers, applied in this order.
Later layers only add to earlier ones; they never remove.

| Layer | Source | Deployed to | Applies to |
| --- | --- | --- | --- |
| base | `dot_config/homebrew/Brewfile` | `~/.config/homebrew/Brewfile` | every machine |
| role | `dot_config/homebrew/Brewfile.role-<role>` | `~/.config/homebrew/Brewfile.role-<role>` | every machine of that role |
| machine | `dot_config/homebrew/Brewfile.machine-<machine>` | `~/.config/homebrew/Brewfile.machine-<machine>` | one specific machine |

`.chezmoiignore` filters the overlays so only the ones matching this machine's role and hostname are
ever written to `~/.config/homebrew/`. "Essential" in the sense above means the base layer;
role- and machine-specific packages are still recorded, just one layer down.

### What is not included?

I prefer getting apps or installers directly from the creator's own website. If its not available as
a direct download, then I'm fine with getting it from the Mac App Store. I don't use `brew cask` just because the app
is available that way (e.g. `brew cask install google-chrome`).

If the creator recommends using `brew` or `brew cask` on macOS, then I will include it here.

## Common tasks

#### Install from Brewfile

Normally you don't run this by hand. `chezmoi apply` runs
`.chezmoiscripts/run_onchange_after_20-install-packages.sh.tmpl`, which applies whichever of the
three layers exist on this machine, in order. It re-runs whenever any layer's contents change.

To apply a single layer by hand — idempotent, and can be run many times:

```
$ brew bundle install --no-upgrade --file ~/.config/homebrew/Brewfile
```

`--no-upgrade` matches what the script does. A bare `brew bundle install` upgrades every outdated
dependency as a side effect; upgrading is kept a separate deliberate act (see below).

#### Add a new package

Edit the Brewfile for the layer it belongs to — base if it belongs on every machine, otherwise the
role or machine overlay — then run `chezmoi apply`, or the install command above against that
layer's deployed file.

#### View outdated packages

```
$ brew outdated
```

Or view specifically just the outdated casks

```
$ brew outdated --cask
```

#### Upgrade packages

```
$ brew upgrade <package-name>
```

Upgrade all outdated packages:

```
$ brew upgrade
```

Upgrade all outdated casks (subset of packages):

```
$ brew upgrade $(brew outdated --cask --greedy --quiet)
```

To upgrade only what a Brewfile layer declares:

```
$ brew bundle upgrade --file ~/.config/homebrew/Brewfile
```

#### Remove packages that are not listed in the Brewfile

This should be done very rarely, because I will potentially lose any packages that are not essential. Think of it more
like a system reset.

**Now more dangerous than it used to be.** `brew bundle cleanup` takes a single `--file`, and the
package set is spread across three layers. Running it against the base Brewfile will uninstall
everything declared only in the role and machine overlays. If you really want this, concatenate the
layers first and clean up against that:

```
$ cat ~/.config/homebrew/Brewfile ~/.config/homebrew/Brewfile.role-* ~/.config/homebrew/Brewfile.machine-* > /tmp/Brewfile.all
$ brew bundle cleanup --file /tmp/Brewfile.all
```

Omitting `--force` prompts and lists what would be removed; add `--force` only after reading that
list.

#### Find dependents of a package

When reviewing outdated packages, I might find a bunch that I didn't directly install, but instead were installed as
dependencies of another package. I can use the following command to find all the other packages that might depend on
some `package_name`. I probably shouldn't worry about updating an outdated package if its a dependency (the dependant
should take care of updating it, when that is updated).

```
$ brew uses package_name --installed
```

I can also explicitly find all the packages that have no dependents using the following command

```
$ brew leaves
```

## Python

Homebrew separates 3.y (where `y` is considered major) releases from one another. Therefore, when you have multiple
major releases installed, there will be symlinks for each version (e.g. `python3.11`, `python3.12`, etc). There will
also be a symlink for `python3`, which will point to one of these versions. The best way to find out which version
that is, is to simply run `python3 --version` (or other binary name). **NOTE:** I'm not quite sure if and when the
`python3` symlink is updated. It may just remain pointing to the first version of Python 3.y that you installed on the
system, to avoid breakage.

<details>
    <summary>Unverified method to update <code>python3</code> symlink</summary>

```
# Unlink the older version
$ brew unlink python3
# Link the new version
$ brew link python@3.12
# Check your result
$ python3 --version
```

</details>


Learn more: https://docs.brew.sh/Homebrew-and-Python

### pip

In addition, several symlinks for pip will be available (e.g. `pip3.11`, `pip3.12`, etc). There will also be a `pip3`
symlink on the system. The best way to find out which python version a certain pip is using, is to run `pip3 --version`
(or other binary name) which has an output that ends in a specific python version (e.g. `(python 3.11)`). **NOTE:**
To avoid confusion and breakage, its important to maintain that the `python3` and `pip3` symlinks use the same version
of Python.

### virutalenv

It's important to limit the use of global binaries, given how managing the specific version of Python they are bound to
can get tricky (as is unavoidable for pip). In general, all Python packages should be installed in a virtualenv, and
that virtualenv should be activated before use (and deactivated after use).

Ironically, virtualenv itself is commonly used as a global binary. But that isn't necessary. Here are the commands I
use to use virtualenv without depending on the global binary:

#### Create a new virtualenv:

Use the specific python version you intend to "bind" the virtualenv onto.

```
$ python3.11 -m venv environment_name
```

#### Activate a virtualenv:

Now you don't have to remember which Python you were supposed to use for a specific project.

```
$ source environment_name/bin/activate
```

Once you're in the virtualenv, you should use `python` and `pip` (without any version numbers in the binary name) to use
the "bound" python.

#### Deactivate a virtualenv:

```
$ deactivate
```
