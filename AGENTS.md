# AI Agent Instructions for dotfiles

This repository contains dotfiles for macOS systems, using [Dotbot](https://github.com/anishathalye/dotbot) for automated installation and synchronization. Here's what you need to know to work effectively with this codebase:

## Architecture & Core Components

1. **Installation System (Dotbot)**
   - Configuration in `install.conf.yaml` defines symlinks and installation steps
   - Uses YAML for declarative configuration of dotfile management
   - Plugins extend functionality (e.g., `dotbot-brew` for Homebrew integration)

2. **Shell Environment (ZSH)**
   - Main config split between `zsh/zprofile` and `zsh/zshrc`
   - Uses [antidote](zsh/antidote/) for plugin management
   - Custom functions in `zsh/zfunc/` directory

3. **Package Management (Homebrew)**
   - Essential packages defined in `brew/Brewfile`
   - Manual installations preferred for certain apps (see `brew/README.md`)
   - Brewfile is intended for essential, cross-machine packages only

## Development Workflows

1. **Making Changes**
   ```yaml
   # To add a new dotfile:
   1. Create file in appropriate directory (e.g., zsh/, git/, etc.)
   2. Add symlink in install.conf.yaml:
      - link:
          ~/.new-config: category/new-config
   3. Run ./install to create symlinks
   ```

2. **Testing Changes**
   - Changes to existing files take effect immediately via symlinks
   - New files require running `./install` to create symlinks
   - Comment out `brewfile:` section in `install.conf.yaml` to skip package installation during testing

## Project Conventions

1. **Philosophy**
   - Balances simplicity with convenience
   - Prefers understanding over automation
   - Cross-developer relatability over exotic configurations

2. **File Organization**
   - Each category has its own directory (zsh/, git/, vim/, etc.)
   - Category-specific documentation in README.md files
   - Local machine overrides should be kept outside the repo

3. **Package Management**
   - Only essential, cross-machine packages in Brewfile
   - Direct downloads preferred for apps when available
   - Brew cask used only when recommended by creator

4. **Code conventions**
   - Custom functions in the `zsh/zfunc` directory should be written in idiomatic zsh syntax. It's
     not important to make many concessions for compatibility different shells (e.g. bash).
   - Across all directories, when writing a function in any language, comment the purpose of the
     function concisely and clearly. Describe the arguments that are expected, including any special
     cases that are handled by the function.

## Integration Points

1. **Machine Setup**
   - Requires Xcode command line tools and Python
   - `./install` is the main entry point
   - Follow post-install instructions in `brew/README.md` for certain packages

2. **External Dependencies**
   - Homebrew for package management
   - Git for version control
   - Python for running Dotbot
   - Various Homebrew packages defined in `brew/Brewfile`

When working with this codebase, prioritize reviewing the relevant README.md files in each directory for detailed context before making changes.
