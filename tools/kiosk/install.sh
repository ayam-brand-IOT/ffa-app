#!/bin/sh
# FFA kiosk for Raspberry Pi OS Bookworm with Wayfire (Wayland).
#   ./install.sh              install and start the kiosk
#   ./install.sh --uninstall  stop it and restore the original wayfire.ini
# Run as the desktop user (not root), from this folder.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
INI="$HOME/.config/wayfire.ini"
BACKUP="$INI.before-ffa-kiosk"

# Earlier versions ran Chromium from a systemd user service.
remove_legacy_service() {
    systemctl --user stop ffa-kiosk.service 2>/dev/null || true
    rm -f "$HOME/.config/systemd/user/ffa-kiosk.service" "$HOME/.local/bin/ffa-kiosk-wait"
    systemctl --user daemon-reload 2>/dev/null || true
}

if [ "$1" = "--uninstall" ]; then
    "$HERE/ffa-kiosk-stop"
    remove_legacy_service
    rm -f "$HOME/.local/bin/ffa-kiosk-session" "$HOME/.local/bin/ffa-kiosk-stop"
    if [ -f "$BACKUP" ]; then mv "$BACKUP" "$INI"; fi
    echo "Kiosk removed; wayfire.ini restored."
    exit 0
fi

remove_legacy_service
mkdir -p "$HOME/.local/bin"
install -m 755 "$HERE/ffa-kiosk-session" "$HERE/ffa-kiosk-stop" "$HOME/.local/bin/"

# Keep the very first original: re-running the installer must not overwrite it.
[ -f "$BACKUP" ] || cp "$INI" "$BACKUP"
python3 - "$INI" <<'PY'
import configparser, sys
path = sys.argv[1]
ini = configparser.RawConfigParser(strict=False)
ini.optionxform = str
ini.read(path)
def put(section, key, value):
    if not ini.has_section(section):
        ini.add_section(section)
    ini.set(section, key, value)
put("autostart", "ffa_kiosk", "~/.local/bin/ffa-kiosk-session")
# Wayfire defaults already never blank; keep it explicit.
put("idle", "screensaver_timeout", "-1")
put("idle", "dpms_timeout", "-1")
# Shortcuts that leave the kiosk: menu, terminal, panels, shutdown dialog.
# Volume, screenshot and the physical power key stay. Esc, Tab, Ctrl, Shift
# and Caps Lock are HomeView defect shortcuts and are never bound here.
for name in ("menu", "terminal", "bluetooth", "netman", "orca", "quit"):
    put("command", "binding_" + name, "none")
with open(path, "w") as f:
    ini.write(f)
PY

# Start now when a desktop session is running, with that session's display.
"$HOME/.local/bin/ffa-kiosk-stop"
if pgrep -u "$(id -u)" -x wayfire >/dev/null; then
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    WAYLAND_DISPLAY=$(ls "$XDG_RUNTIME_DIR" | grep -E '^wayland-[0-9]+$' | head -1)
    export WAYLAND_DISPLAY
    setsid "$HOME/.local/bin/ffa-kiosk-session" >/dev/null 2>&1 < /dev/null &
fi
echo "Kiosk installed. Exit for maintenance over SSH:"
echo "  ~/.local/bin/ffa-kiosk-stop     (until next login)"
echo "  $HERE/install.sh --uninstall    (permanently)"
