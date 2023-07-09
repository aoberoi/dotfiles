# Homebrew

Set up essential packages from the Homebrew package manager.

## What is included?

The idea is to record the packages I believe any system I use should have on it, which I call essentials.

If a package is not an essential (or not yet), install it with `brew install <package>`. Later, if I decide the
package is essential, then I can add it to the `Brewfile` and install as described below.

### What is not included?

I prefer getting apps or installers directly from the creator's own website. If its not available as
a direct download, then I'm fine with getting it from the Mac App Store. I don't use `brew cask` just because the app
is available that way (e.g. `brew cask install google-chrome`).

If the creator recommends using `brew` or `brew cask` on macOS, then I will include it here.

## Common tasks

#### Install from Brewfile

This is mostly idempotent (aside from upgrading packages), and can be run many times.

```
$ brew bundle install --file ~/.dotfiles/brew/Brewfile
```

#### Add a new package

Edit the `Brewfile` to add the package, then run the install command above.

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

#### Remove packages that are not listed in the Brewfile

This should be done very rarely, because I will potentially lose any packages that are not essential. Think of it more
like a system reset.

```
$ brew bundle --force cleanup
```

