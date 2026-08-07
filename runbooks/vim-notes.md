Why the vim configuration is as small as it is. This was `vim/README.md` before the chezmoi
migration; the config it describes is a single file, `dot_vim/vimrc` → `~/.vim/vimrc`.

## Philosophy

In the past, I've copied and pasted a ton of popular vim configurations from GitHub. While that
helped me get on with using vim, I likely used less than 10% of that configuration. The remaining
90% was likely duplicating (or worse, obscuring) vim's built-in behavior.

Taking a step back, the goal of this configuration isn't really to turn vim into a comprehensive
IDE with every capability under the sun. Realistically, I use and am happy with VS Code as my
primary code editor. I use vim in instances where I'm at the command line and want to do some light
editing. For example, I prefer using git at the command line, and `git commit` launches vim, where
I can craft a thoughtful commit message. Also when I ssh into a remote host (whether that be in the
cloud or on a Raspberry Pi at home), I prefer using vim to edit files. In this context, I might not
even have the opportunity to bring my own vim configuration over.

Therefore the philosophy of this configuration is to remain minimal. I don't want to drift too far
from what vim provides out of the box so that I'm not totally lost when I ssh into a machine with
a "stock" configuration. I want to fully understand the options I'm setting so that I know how to
get back what I need, and it's never more than a few commands away.

The following article is full of really helpful information for creating a vim configuration from
scratch, and is in philosophical agreement: https://github.com/romainl/idiomatic-vimrc

## Requirements

Vim 7.4+

macOS 14.7 (Sonoma) contained v9.0, which seemed fine for my purposes; macOS 26.6 ships v9.1. The
system configuration (`/usr/share/vim/vimrc`) sets `skip_defaults_vim=1`, disabling the "spartan"
`defaults.vim`, so I'm starting from a pretty blank canvas.

Note the config is installed as `~/.vim/vimrc`, not `~/.vimrc`. Vim reads it as the "2nd user vimrc
file" — see `vim --version`. `~/.vimrc` takes precedence if it exists, so don't create one.

## Side note

It seems like a lot of those popular vim configurations on GitHub have been migrated to NeoVIM in
the last few years. If I were to become interested in using a vim-like editor as a full blown code
editor for general use, I should probably look into using NeoVIM.
