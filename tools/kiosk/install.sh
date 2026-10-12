#!/bin/sh
# FFA kiosk for Raspberry Pi OS Bookworm with Wayfire (Wayland).
#   ./install.sh              install and start the kiosk
#   ./install.sh --uninstall  stop it and restore the original wayfire.ini
# Run as the desktop user (not root), from this folder.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
INI="$HOME/.config/wayfire.ini"
BACKUP="$INI.before-ffa-kiosk"

if [ "$1" = "--uninstall" ]; then
    systemctl --user stop ffa-kiosk.service 2>/dev/null || true
    rm -f "$HOME/.config/systemd/user/ffa-kiosk.service" \
          "$HOME/.local/bin/ffa-kiosk-wait" "$HOME/.local/bin/ffa-kiosk-session"
    systemctl --user daemon-reload
    if [ -f "$BACKUP" ]; then mv "$BACKUP" "$INI"; fi
    echo "Kiosk removed; wayfire.ini restored."
    exit 0
fi

mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user"
install -m 755 "$HERE/ffa-kiosk-wait" "$HERE/ffa-kiosk-session" "$HOME/.local/bin/"
install -m 644 "$HERE/ffa-kiosk.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload

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

# Start now when run inside a desktop session (Wayfire reloads its ini live).
if pgrep -u "$(id -u)" -x wayfire >/dev/null; then
    WF_PID=$(pgrep -u "$(id -u)" -x wayfire | head -1)
    for var in WAYLAND_DISPLAY DISPLAY XAUTHORITY; do
        value=$(tr '\0' '\n' < "/proc/$WF_PID/environ" | sed -n "s/^$var=//p")
        [ -n "$value" ] && systemctl --user set-environment "$var=$value"
    done
    systemctl --user restart ffa-kiosk.service
fi
echo "Kiosk installed. Exit for maintenance over SSH:"
echo "  systemctl --user stop ffa-kiosk.service   (until next login)"
echo "  $HERE/install.sh --uninstall              (permanently)"
