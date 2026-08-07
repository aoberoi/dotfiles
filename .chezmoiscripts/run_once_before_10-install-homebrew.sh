#!/usr/bin/env bash
#
# Install Homebrew
#
# Replaces dotbot's `install-brew: true` step.
#
# Why `before_`: everything downstream leans on Homebrew. The package install script
# (`run_onchange_after_20-install-packages.sh`) obviously does, but so does the shell
# config itself — `dot_zprofile` opens with `eval "$(/opt/homebrew/bin/brew shellenv)"`
# and derives `$HOMEBREW_PREFIX` paths from it. Running before chezmoi writes any files
# keeps the ordering honest: by the time a `.zprofile` lands in $HOME, the thing it
# references exists.
#
# Why `run_once_`: chezmoi hashes this file's *contents* and records the hash in its
# state database (`chezmoi state dump`). It re-runs only if that hash changes, so the
# no-op path below is really only exercised on the first apply after an edit to this
# file. The early exit is still worth having — see below.
#
# This script deliberately installs *no packages* and trusts *no taps*. Packages are
# P4-2's job. Tap trust (`~/.homebrew/trust.json`) is a deliberate manual per-machine
# act (decision D8): trusting a tap authorises arbitrary third-party install code, and
# that is not a thing a dotfiles repo should hand out on your behalf.

set -euo pipefail

# Fast path: already installed, nothing to do.
#
# Belt and braces on purpose. The absolute path is the authoritative check — this repo
# hard-codes /opt/homebrew in dot_zprofile and in the package script, so a Homebrew that
# isn't there isn't the Homebrew this repo means. But `command -v` is checked too, so
# that a machine with an unusual prefix gets a warning instead of a second, conflicting
# installation. We can't rely on $PATH alone: during bootstrap this runs from a chezmoi
# process whose environment predates any Homebrew at all.
if [ -x /opt/homebrew/bin/brew ]; then
  echo "==> Homebrew already installed at /opt/homebrew; skipping."
  exit 0
fi

if command -v brew >/dev/null 2>&1; then
  echo "==> Found brew at $(command -v brew), but not at /opt/homebrew." >&2
  echo "    This repo assumes the Apple Silicon prefix. Not installing a second copy;" >&2
  echo "    reconcile by hand before relying on dot_zprofile." >&2
  exit 0
fi

# Apple Silicon only, stated rather than assumed.
#
# Homebrew's prefix is /opt/homebrew on arm64 and /usr/local on Intel. Supporting both
# would mean templating the prefix through dot_zprofile, the Brewfile scripts, and every
# $HOMEBREW_PREFIX reference — real work for a case that doesn't exist here. So: fail
# loudly rather than install into a prefix the rest of the repo will not look in.
if [ "$(uname -s)" != Darwin ] || [ "$(uname -m)" != arm64 ]; then
  echo "==> This repo targets macOS on Apple Silicon (arm64); found $(uname -s)/$(uname -m)." >&2
  echo "    Install Homebrew manually and audit the hard-coded /opt/homebrew paths." >&2
  exit 1
fi

echo "==> Installing Homebrew..."

# The official installer from https://brew.sh. It is fetched fresh rather than vendored
# so we get upstream's current bootstrap logic (Xcode CLT check, sudo handling, prefix
# selection) instead of a snapshot that rots.
#
# NONINTERACTIVE is set explicitly rather than left to chance. Piping into bash means the
# installer's stdin is the pipe, not a terminal, so it would infer non-interactive mode
# anyway and print a warning about it; saying so up front makes the behaviour deterministic
# regardless of how chezmoi wires up the script's stdin. Note this does *not* silence the
# sudo password prompt — sudo reads from /dev/tty — so a human still has to be at the
# keyboard for a fresh install.
#
# `set -o pipefail` above matters here: without it a failed curl would silently feed an
# empty script to bash and we would "succeed" having installed nothing.
curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh \
  | NONINTERACTIVE=1 /bin/bash

# Put brew on $PATH for the remainder of *this script*.
#
# Scope note, twice over. It does not persist into the user's shell — `dot_zprofile` is what
# does that permanently, and chezmoi writes it a moment after this script returns. It also
# does not reach the later scripts in this same apply: chezmoi runs each script as its own
# process, so nothing exported here survives into `run_onchange_after_20-install-packages.sh`.
# That script opens with its own `brew shellenv` for exactly this reason. The eval here is
# purely so the verification line below can say `brew` rather than the absolute path.
eval "$(/opt/homebrew/bin/brew shellenv)"

echo "==> Homebrew installed: $(brew --version | head -1)"
