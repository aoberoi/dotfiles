#
# macOS Settings
#
# This file does not contain every setting in macOS that I prefer set. Instead, it's focussed on the settings which are
# difficult or impossible to set in the UI.


# Guard from accidentally running on a non-macOS system
[ `uname` != Darwin ] && echo "Skipping macOS setup." && exit 0

# Disable press-and-hold for keys in favor of key repeat
# The press-and-hold accents menu interferes with I often hold down keys to repeat in vim mode
defaults write -g ApplePressAndHoldEnabled -bool false

# Keyboard repeat rate
# https://mac-os-key-repeat.vercel.app/
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write NSGlobalDomain InitialKeyRepeat -int 12

# Disable automatic period substitution as it’s annoying when typing code
defaults write NSGlobalDomain NSAutomaticPeriodSubstitutionEnabled -bool false

# Increase sound quality for Bluetooth headphones/headsets
# defaults write com.apple.BluetoothAudioAgent "Apple Bitpool Min (editable)" -int 40

# Expand save panel by default
defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode -bool true
defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode2 -bool true

echo "Log out and log back in for macOS settings to take effect."
