## zsh configuration

Reference notes on how zsh startup works on macOS, and on this repo's plugin and completion setup.
This was `zsh/README.md` before the chezmoi migration, which is why it mixes general zsh reference
material with repo-specific detail.

The files themselves now live at `dot_zprofile` → `~/.zprofile`, `dot_zshrc` → `~/.zshrc`,
`exact_dot_zfunc/` → `~/.zfunc`, and `dot_config/zsh/zsh_plugins.txt` → `~/.config/zsh/zsh_plugins.txt`.

### Order, conditions, and defaults

When a shell is opened:

1. `/etc/zshenv` - Does not exist on macOS systems.
2. `~/.zshenv` - Does not exist in default user home.
3. `/etc/zprofile` - **Login shells only** Calls `path_helper` to populate and reorder `$PATH`.
4. `~/.zprofile` - **Login shells only** Does not exist in default user home. Homebrew inserts startup script here by
  default, prepending the `$PATH` with its prefix.
5. `/etc/zshrc` - **Interactive shells only** macOS default settings for command history, keyboard bindings, prompt,
  Terminal.app integration
6. `~/.zshrc` - **Interactive shells only** Does not exist in default user home.
7. `/etc/zlogin` - **Login shells only** Does not exist on macOS systems.
8. `~/.zlogin` - **Login shells only** Does not exist in default user home.

When a shell is closed:

1. `~/.zlogout` - **Login shells only** Does not exist in default user home.
2. `/etc/zlogout` - **Login shells only** Does not exist on macOS systems.

A practical consequence of step 4 being login-only: `~/.zprofile` is where `brew shellenv` runs, so
`$HOMEBREW_PREFIX` is not set in a non-login interactive shell that did not inherit it. `~/.zshrc`
therefore defaults it (`: ${HOMEBREW_PREFIX:=/opt/homebrew}`) before using it to locate antidote.

### Interactive and login shells

A **login shell** is simply a shell, whether local or remote, that allows a user to authenticate to the system. These
shells are typically interactive shells.

An **interactive shell**, can accept input typed from the keyboard. Non-interactive shells are typically scripts,
including those that are called by `launchd`.

Terminal initially opens a both **login and interactive shell** (despite not putting in a username and password). But if
you run `zsh` inside an existing shell, that is **not a login shell** but it is an interactive shell.

SSH sessions are both **login and interactive shells**.

### Guidelines for each file

* `~/.zshenv` - Set environment for scripts. This should be used sparingly.
* `~/.zprofile` - Set environment for login shells. Good place to set `$PATH` and other things that don't assume
  interactivity.
* `~/.zshrc` - Set environment for interactive shells. Good place to set `$PROMPT`, aliases, completions, colors, and
  other things that are based on interactivity. `setopt` and `unsetopt` are typically in this file.
* `~/.zlogin` - Don't need this. Just use `~/.zprofile`.
* `~/.zlogout` - Release any resources obtained in `~/.zprofile`. Could be used to reset a terminal window title.
* `~/.zfunc` - Shell functions, used for extending the completion system and adding arbitrary helpers. [Helpful StackOverflow explanation](https://unix.stackexchange.com/a/33898)

### Plugin management

This repo uses [antidote](https://getantidote.github.io/) to manage zsh plugins. It's quite an active and helpful
project, and doesn't cost too much on performance.

Antidote is installed by Homebrew (`brew "antidote"` in `dot_config/homebrew/Brewfile`), not vendored
here — it used to be a git submodule at `zsh/antidote/`. `~/.zshrc` sources it from the path in the
formula's caveat and then statically loads the manifest:

```
source $HOMEBREW_PREFIX/opt/antidote/share/antidote/antidote.zsh
antidote load ~/.config/zsh/zsh_plugins.txt
```

The plugins listed in the manifest (`dot_config/zsh/zsh_plugins.txt`) are not in this repo; antidote
clones them into its own cache. Static loading also generates `~/.config/zsh/zsh_plugins.zsh` next to
the manifest, which `.chezmoiignore` excludes so chezmoi doesn't fight antidote over it.

**Ordering constraint:** the `belak/zsh-utils path:completion` plugin is what calls `compinit`.
Everything that adds to `FPATH` must run *before* `antidote load`, and every `compdef` must run
*after* it. `~/.zshrc` is arranged that way deliberately; preserve it when editing.

### Quick look at antidote performance

I ran [zsh-bench](https://github.com/romkatv/zsh-bench#usage) on two barebones configurations, accomplishing the same
thing. Both configurations use one plugin (the pure prompt) The first does not have antidote and the second does have
antidote. This helps me judge how much time it costs to use antidote. Bottom line: its not perceptible.

<table>
<tr>
  <td>no antidote</td>
  <td>antidote</td>
  <td>change</td>
</tr>
<tr>
  <td>

```
creates_tty=0
has_compsys=1
has_syntax_highlighting=0
has_autosuggestions=0
has_git_prompt=0
first_prompt_lag_ms=75.472
first_command_lag_ms=75.902
command_lag_ms=1.193
input_lag_ms=1.593
exit_time_ms=78.113
```

  </td>
  <td>

```
creates_tty=0
has_compsys=1
has_syntax_highlighting=0
has_autosuggestions=0
has_git_prompt=0
first_prompt_lag_ms=77.781
first_command_lag_ms=78.152
command_lag_ms=1.201
input_lag_ms=1.696
exit_time_ms=80.483
```

  </td>
  <td>

<p>First prompt lag: +2.309ms / +3.06% </p>
<p>First command lag: +2.25ms / +2.96%% </p>
<p>Command lag: +0.008ms / +0.67%% </p>
<p>Input lag: +0.103ms / +6.47%% </p>
<p>Exit time: +2.37ms / +3.03%% </p>

  </td>
</tr>
</table>

### Completion system

When new completion functions are added, its often necessary to clear the cache before those completions will work:

```
$ rm ~/.cache/zsh/compdump
```

In addition, `~/.zfunc` is prepended to the zsh fpath. chezmoi writes it from `exact_dot_zfunc/` in
this repo. It holds hand-written autoload functions (`fnm_upgrade`, `sizeup`) and could hold custom
completion functions (named with an underscore and then the command name).

Two caveats that come with `exact_`:

* chezmoi owns the directory wholly — anything in `~/.zfunc` that isn't in `exact_dot_zfunc/` gets
  deleted on apply. Never put a *generated* completion file there.
* `~/.zfunc` is prepended *after* Homebrew's site-functions, so anything here shadows Homebrew's
  copy of the same name. That is why `_rustup` is not checked in; Homebrew ships a fresher one.

### Resources

Reference for zsh configuration files and macOS defaults:

* [macos - ZSH: .zprofile, .zshrc, .zlogin - What goes where? - Ask Different](https://apple.stackexchange.com/questions/388622/zsh-zprofile-zshrc-zlogin-what-goes-where)
* [zsh - What should/shouldn't go in .zshenv, .zshrc, .zlogin, .zprofile, .zlogout? - Unix & Linux Stack Exchange](https://unix.stackexchange.com/questions/71253/what-should-shouldnt-go-in-zshenv-zshrc-zlogin-zprofile-zlogout)
* [Some inspiration](https://stuvel.eu/post/2020-08-05-zsh-config/)
* [Properly setting $PATH for zsh on macOS (fighting with path_helper) · GitHub](https://gist.github.com/Linerre/f11ad4a6a934dcf01ee8415c9457e7b2#zsh-initializations)
* `/usr/share/zsh/5.9/functions` - location of most functions on macOS (completions, builtins, etc).
* [zsh: 5 Files](https://zsh.sourceforge.io/Doc/Release/Files.html#Files)
* [ZSH - LOVERS](https://grml.org/zsh/zsh-lovers.html)
* [Quick zsh reference](https://github.com/mattmc3/zdotdir/tree/main/.docs)
* [Zephyr - a framework with some lightweight plugins](https://github.com/mattmc3/zephyr)
* zsh completion system
  * [A Guide to the Zsh Completion with Examples](https://thevaluable.dev/zsh-completion-guide-examples/)
  * [HOWTO guide](https://github.com/zsh-users/zsh-completions/blob/master/zsh-completions-howto.org#)
  * [Docs](https://zsh.sourceforge.io/Doc/Release/Completion-System.html#Completion-System)
* [zsh fpath autoload](https://unix.stackexchange.com/a/33898)
* [fzf intro](https://www.youtube.com/watch?v=tB-AgxzBmH8)


Reference for some zsh configuration options and settings:

* [zshbuiltins(1): zsh built-in commands - Linux man page](https://linux.die.net/man/1/zshbuiltins)
* [zshoptions(1): zsh options - Linux man page](https://linux.die.net/man/1/zshoptions)

