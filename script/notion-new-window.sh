#!/bin/bash

# Notion Desktop does not expose a decent automation interface - no AppleScript, App Intents, etc.
# The only remaining way to automate it is to use System Events, which uses the system's
# accessibility permissions. I'm choosing to package up an AppleScript, which invokes the System
# Events for automation, as an App bundle. This allows me to only grant those accessibility
# permissions to this specific App bundle, as opposed to granting that permission to or some other
# automation app that can invoke System Events. Earlier, I tried doing this using Shortcuts, but
# macOS would request the accessibility permission for whatever my foreground app was at the time -
# that was not reasonable.

# --- Configuration ---
APP_NAME="NotionNewWindow"
APP_DIR="$HOME/Applications"
APP_PATH="$APP_DIR/$APP_NAME.app"
BUNDLE_ID="me.aoberoi.custom.notion-opener"

# The AppleScript logic
NOTION_SCRIPT="tell application \"System Events\"
    if exists process \"Notion\" then
        tell process \"Notion\"
            set frontmost to true
            click menu item \"New Window\" of menu \"File\" of menu bar 1
        end tell
    else
        tell application \"Notion\" to launch
    end if
end tell"

# --- Idempotent Build Process ---

echo "🔍 Checking if $APP_NAME needs to be built..."

# Function to check if the app is already valid and correctly identified
should_build() {
    # If app doesn't exist, we must build
    if [ ! -d "$APP_PATH" ]; then return 0; fi

    # Check if Bundle ID matches
    CURRENT_ID=$(defaults read "$APP_PATH/Contents/Info.plist" CFBundleIdentifier 2>/dev/null)
    if [ "$CURRENT_ID" != "$BUNDLE_ID" ]; then return 0; fi

    # Check if signature is valid
    if ! codesign --verify "$APP_PATH" 2>/dev/null; then return 0; fi

    # If all tests pass, don't build
    return 1
}

if should_build; then
    echo "🔨 Building and signing $APP_NAME..."

    # 1. Compile the script into an .app bundle
    mkdir -p "$APP_DIR"
    osacompile -e "$NOTION_SCRIPT" -o "$APP_PATH"

    # 2. Inject stable Bundle Identifier
    defaults write "$APP_PATH/Contents/Info.plist" CFBundleIdentifier "$BUNDLE_ID"

    # 3. Force system to recognize the plist change
    touch "$APP_PATH"

    # 4. Sign with ad-hoc identity
    codesign --force --deep --sign - "$APP_PATH"

    echo "✅ Applet built and signed at: $APP_PATH"
    echo "⚠️  Reminder: You may need to toggle Accessibility permissions in System Settings if this is the first run."
else
    echo "✨ $APP_NAME is already present, signed, and correctly identified. Skipping build."
fi
