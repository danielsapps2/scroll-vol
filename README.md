# scroll-vol

Scroll the mouse wheel anywhere over a KDE Plasma panel (Wayland) to change the volume.

## How it works

Wayland doesn't let regular programs see where the pointer is or receive input meant for other windows, so this has three parts:

- **`kwin-script/`**: a KWin script that runs inside the compositor. It watches the pointer and calls `SetOverPanel(true/false)` on the daemon over D-Bus whenever the pointer enters or leaves a panel (any `dock` window).
- **`scroll-vol-daemon.py`**: a user systemd service that reads wheel events from your mice in `/dev/input`. It only listens and never grabs the device. While the pointer is over a panel, each wheel notch triggers Plasma's own *Increase/Decrease Volume* shortcut, so you get the normal OSD, step size and volume limit.
- **`70-scroll-vol.rules`**: a udev rule that gives the logged-in user read access to mouse devices only (not keyboards). This avoids adding yourself to the `input` group.

## Requirements

- KDE Plasma 6 on Wayland, with systemd user sessions (the default)
- Python 3 with `dbus-python` and PyGObject (Debian/Ubuntu: `sudo apt install python3-dbus python3-gi`; Fedora: `python3-dbus python3-gobject`; Arch: `python-dbus python-gobject`)
- `kpackagetool6`, `kwriteconfig6` and `qdbus6` (part of a normal Plasma install)

## Install / uninstall

```sh
git clone https://github.com/danielsapps2/scroll-vol.git
cd scroll-vol
./install.sh     # asks for sudo once, for the udev rule
./uninstall.sh
```

Use Plasma's small (1%) step instead of the normal one by adding `--fine` to `ExecStart` in `~/.config/systemd/user/scroll-vol.service`.

## Notes

- Panel widgets still receive the wheel as well. If the Task Manager or Pager also reacts (cycling windows, switching desktops), turn that off in the widget's settings.
- Logs: `journalctl --user -u scroll-vol`
