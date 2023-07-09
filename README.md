
## Goals

* I'm using these dotfiles on macOS systems, running Ventura 13.4.1 or later. At this time, I'm not interested in
  putting in much effort to make sure this works as expected on other operating systems.
* These dotfiles reflect my choices and preferences in software. In some ways, it also documents those preferences, as
  they will likely change over time.
* I want to be able to install and sync these settings on multiple machines with as low an effort as possible.

## Requirements

* Xcode (installs command line tools like `git`)
* A working Python installation (macOS system Python is fine)

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

## Usage

#### Initial setup on a new machine

1. Verify requirements are met (git and python are available, etc).
2. Clone the repo. Any path you want will work.
3. Run `./install`.
   * There may be errors related to files already existing. If that's the case, you can rename those files to a temporary
     name, install, and then delete the temporary files once the install is successful. It's also a good idea to take
     a look at those temporary files to verify there isn't anything in there you want to keep and to sync them into the
     installed version.

#### Making local changes

Make changes inside the working copy of the repo.
  * In files that already exist, the changes will be reflected immediately, since the symlinks are already in place. You
may need to start a new shell or rerun the program that uses the changes.
  * For new files, you'll need to take a look at `install.conf.yaml` to make sure they get linked properly. Then you can
run the `./install` script to perform the link creation. Now you can start a new shell or rerun the program that uses
the changes.

Once the changes are working the way you intend, commit the changes and push to the remote repo.

NOTE: In general, use a package manager or submodules to fetch plugins or other projects with code we're trying to
import. Try to avoid copying files or parts of files directly, unless its something you plan to maintain.

#### Syncing submodules to the version stored (initialization)

```
$ git submodule update --init --recursive
```

NOTE: This command still needs to be run after this repo is initially cloned on a new machine. Conveniently, the
`install.conf.yaml` contains a shell step to do exactly that - so you shouldn't need to worry about it. Just clone and
install.

#### Updating submodules to the latest version (upgrading)

```
$ git submodule update --init --remote
```

#### Adding a submodule

```
$ git submodule add https://example.com/submodule-repo.git path
$ git commit -m "adding submodule"
```

## Framework

This repo uses the [dotbot](https://github.com/anishathalye/dotbot) project as a framework for managing dotfiles.

Before settling on dotbot, I considered and evaluated a few different options. The main alternatives was using
[stow](https://alexpearce.me/2016/02/managing-dotfiles-with-stow/) or using a [bare git
repo](https://www.atlassian.com/git/tutorials/dotfiles). This blog post contains [a decent
discussion](https://sgoel.dev/posts/replacing-gnu-stow-with-dotbot/) of the differences, and I mostly agree with these
points.

#### Advantages:
* dotbot's configuration is done with a pretty simple `.yaml` file, instead of in a raw shell scripting language.
* dotbot has a lot more functionality built-in than just putting the symlinks into place. It has workflows for
  installation on a new machine (from a repo), cleaning, updating, etc.

#### Disadvantages:
* dotbot depends on Python on the target machine. Python installations on macOS can be... tricky. There's a system
  Python that is usually woefully out of date (no `python`, but `python3`@`3.9.6`on macOS 13.4.1). But typically I use
  the Homebrew `python3.{y}` formula, [as discussed in the docs](https://docs.brew.sh/Homebrew-and-Python), which will
  mask the `python` and `python3` binaries in the system.
  * I think the risk from mixing/messing things up here is really low.

* dotbot has a strong opinion in favor of git submodules. I personally don't love submodules, mostly because they are
  very confusing and I prefer robust package managers for most use cases.
  * In this use case, there is no package manager. In this ecosystem, there are shell plugin managers that sort of take
    this role, but I'd like installation solution not to depend on a specific shell's plugin ecosystem.

## References

* [Dotbot tutorial by framework author](https://anishathalye.com/managing-your-dotfiles/)
* [Another dotbot tutorial](https://www.elliotdenolf.com/blog/bootstrap-your-dotfiles-with-dotbot)
* [](https://brandon.invergo.net/news/2012-05-26-using-gnu-stow-to-manage-your-dotfiles.html)
* [](https://www.youtube.com/watch?v=CxAT1u8G7is)
* [popular macos configs](https://github.com/mathiasbynens/dotfiles/blob/main/.macos)
  * [Strap project](https://github.com/MikeMcQuaid/strap)
