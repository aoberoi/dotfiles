## zsh configuration

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


### Resources

Reference for zsh configuration files and macOS defaults:

* [macos - ZSH: .zprofile, .zshrc, .zlogin - What goes where? - Ask Different](https://apple.stackexchange.com/questions/388622/zsh-zprofile-zshrc-zlogin-what-goes-where)
* [zsh - What should/shouldn't go in .zshenv, .zshrc, .zlogin, .zprofile, .zlogout? - Unix & Linux Stack Exchange](https://unix.stackexchange.com/questions/71253/what-should-shouldnt-go-in-zshenv-zshrc-zlogin-zprofile-zlogout)
* [Properly setting $PATH for zsh on macOS (fighting with path_helper) · GitHub](https://gist.github.com/Linerre/f11ad4a6a934dcf01ee8415c9457e7b2#zsh-initializations)
* [zsh: 5 Files](https://zsh.sourceforge.io/Doc/Release/Files.html#Files)

Reference for some zsh configuration options and settings:

* [zshbuiltins(1): zsh built-in commands - Linux man page](https://linux.die.net/man/1/zshbuiltins)
* [zshoptions(1): zsh options - Linux man page](https://linux.die.net/man/1/zshoptions)

