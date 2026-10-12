# Station Kiosk

Raspberry Pi OS Bookworm runs Wayfire (Wayland), so LXDE `autostart` entries
and `xset` have no effect there. `install.sh` sets up a user systemd service
that opens Chromium in kiosk mode on `http://127.0.0.1:3030`:

- Wayfire's `[autostart]` runs `ffa-kiosk-session`, which passes the display
  to systemd and starts `ffa-kiosk.service`.
- The service waits until ffa-app answers, then starts Chromium. If Chromium
  is closed (Alt+F4, Ctrl+W, crash) it is restarted after 2 s.
- Wayfire shortcuts that leave the kiosk are disabled: Super (menu),
  Ctrl+Alt+T/B/W/Space, Ctrl+Alt+Delete. Volume keys, screenshot and the
  physical power key still work. Esc, Tab, Ctrl, Shift and Caps Lock are
  HomeView shortcuts and are left alone.
- Screen blanking stays off (`[idle]` timeouts -1).

Run as the desktop user, from this folder:

```sh
./install.sh              # install and start now
./install.sh --uninstall  # remove and restore the original wayfire.ini
systemctl --user stop ffa-kiosk.service   # maintenance until next login
```

The first install keeps the original `~/.config/wayfire.ini` as
`wayfire.ini.before-ffa-kiosk`.
