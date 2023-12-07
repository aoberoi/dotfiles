# Homebrew

Set up essential packages from the Homebrew package manager.

NOTE: The 1Password CLI installation requires inputting the admin password.

NOTE: Rust requires running `rustup-init` after the installation is complete.

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
