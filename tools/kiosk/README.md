# Station Kiosk

Raspberry Pi OS Bookworm runs Wayfire (Wayland), so LXDE `autostart` entries
and `xset` have no effect there. `install.sh` makes Wayfire open Chromium in
kiosk mode on `http://127.0.0.1:3030`:

- Wayfire's `[autostart]` runs `ffa-kiosk-session`, which waits until ffa-app
  answers, then starts Chromium. If Chromium is closed (Alt+F4, Ctrl+W, crash)
  it is restarted after 2 s.
- Chromium must be a child of the Wayfire session. The first version launched
  it from a systemd user service; on Chromium 125 / Wayfire 0.7.5 it then often
  ignored `--kiosk` and showed up as a normal window behind the desktop.
  Wayfire 0.7.5 window rules cannot force full screen (maximize only).
- Chromium runs on X11 through Xwayland. With the native Wayland backend,
  `--kiosk` and `--start-fullscreen` opened a ~500x1 px window at the top-left
  (screen showed only the desktop); verified with screenshots on 2026-10-14.
- Wayfire shortcuts that leave the kiosk are disabled: Super (menu),
  Ctrl+Alt+T/B/W/Space, Ctrl+Alt+Delete. Volume keys, screenshot and the
  physical power key still work. Esc, Tab, Ctrl, Shift and Caps Lock are
  HomeView shortcuts and are left alone.
- Screen blanking stays off (`[idle]` timeouts -1).

Run as the desktop user, from this folder:

```sh
./install.sh                 # install (or update) and start now
./install.sh --uninstall     # remove and restore the original wayfire.ini
~/.local/bin/ffa-kiosk-stop  # maintenance: close it until next login
```

The first install keeps the original `~/.config/wayfire.ini` as
`wayfire.ini.before-ffa-kiosk`.
