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
defaults write NSGlobalDomain KeyRepeat -int 3
defaults write NSGlobalDomain InitialKeyRepeat -int 16

# Disable automatic period substitution as it’s annoying when typing code
defaults write NSGlobalDomain NSAutomaticPeriodSubstitutionEnabled -bool false

# Increase sound quality for Bluetooth headphones/headsets
# defaults write com.apple.BluetoothAudioAgent "Apple Bitpool Min (editable)" -int 40

# Expand save panel by default
defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode -bool true
defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode2 -bool true

# Show App Switcher (Cmd+Tab) on all displays. The default only shows the it on the display with the Dock, but when I
# use an external display I often leave the Dock on the laptop display.
defaults write com.apple.dock appswitcher-all-displays -bool true

# Disable the "Switch to Space with open windows" setting
# In order to script Electron apps that don't respond to JXA (no direct object creation), we
# control them using UI Scripting (simulating menu clicking). This requires activating the app
# before sending the key presses, which can jump to a different Space, unless this setting is disabled.
#defaults write com.apple.applespaces AppleSpacesSwitchOnActivate -bool false
defaults write -g AppleSpacesSwitchOnActivate -bool false

# Reload Settings that were applied programatically
/System/Library/PrivateFrameworks/SystemAdministration.framework/Resources/activateSettings -u

# Restart the Dock (which manages Spaces) to apply changes
killall Dock


echo "Log out and log back in for macOS settings to take effect."
