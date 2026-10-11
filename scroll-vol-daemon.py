#!/usr/bin/env python3
"""Change the volume with the mouse wheel while the pointer is over a Plasma panel.

The companion KWin script ("scrollvol") calls SetOverPanel(bool) on this
daemon whenever the pointer enters or leaves a panel. This daemon passively
reads wheel events from every mouse in /dev/input (it does not grab them) and,
while the pointer is over a panel, triggers Plasma's own volume shortcuts so
the normal OSD and step size are used.
"""

import argparse
import errno
import os
import struct
import subprocess
import sys

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

BUS_NAME = "local.ScrollVol"
OBJECT_PATH = "/local/ScrollVol"
IFACE = "local.ScrollVol"

# struct input_event { struct timeval time; __u16 type; __u16 code; __s32 value; }
EVENT_FORMAT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)
EV_REL = 0x02
REL_WHEEL = 0x08

RESCAN_SECONDS = 3


def log(*args):
    print(*args, file=sys.stderr, flush=True)


def wheel_devices():
    """Return /dev/input/eventN paths for devices that report REL_WHEEL."""
    paths = []
    for name in os.listdir("/sys/class/input"):
        if not name.startswith("event"):
            continue
        try:
            with open(f"/sys/class/input/{name}/device/capabilities/rel") as f:
                # Space-separated hex words, most significant first.
                rel = int(f.read().split()[-1], 16)
        except (OSError, ValueError, IndexError):
            continue
        if rel & (1 << REL_WHEEL):
            paths.append(f"/dev/input/{name}")
    return paths


class Volume:
    def __init__(self, bus, fine):
        self.bus = bus
        self.up = "increase_volume_small" if fine else "increase_volume"
        self.down = "decrease_volume_small" if fine else "decrease_volume"
        self.wpctl_step = "1%" if fine else "5%"

    def step(self, direction):
        name = self.up if direction > 0 else self.down
        try:
            kmix = self.bus.get_object("org.kde.kglobalaccel", "/component/kmix")
            kmix.invokeShortcut(name, dbus_interface="org.kde.kglobalaccel.Component")
        except dbus.DBusException as e:
            log(f"kglobalaccel failed ({e.get_dbus_name()}), falling back to wpctl")
            sign = "+" if direction > 0 else "-"
            subprocess.run(["wpctl", "set-volume", "-l", "1.0",
                            "@DEFAULT_AUDIO_SINK@", self.wpctl_step + sign])


class ScrollVol(dbus.service.Object):
    def __init__(self, bus, volume):
        super().__init__(bus, OBJECT_PATH)
        self.volume = volume
        self.over_panel = False
        self.devices = {}  # path -> (fd, watch id)
        self.denied = set()
        self.rescan()
        GLib.timeout_add_seconds(RESCAN_SECONDS, self.rescan)

    @dbus.service.method(IFACE, in_signature="b", out_signature="")
    def SetOverPanel(self, over):
        self.over_panel = bool(over)

    @dbus.service.method(IFACE, in_signature="", out_signature="b")
    def OverPanel(self):
        return self.over_panel

    def rescan(self):
        for path in wheel_devices():
            if path in self.devices:
                continue
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
            except PermissionError:
                if path not in self.denied:
                    self.denied.add(path)
                    log(f"permission denied: {path} (is the udev rule installed?)")
                continue
            except OSError:
                continue
            self.denied.discard(path)
            watch = GLib.io_add_watch(fd, GLib.PRIORITY_DEFAULT,
                                      GLib.IO_IN | GLib.IO_ERR | GLib.IO_HUP,
                                      self.on_input, path)
            self.devices[path] = (fd, watch)
            log(f"listening on {path}")
        return True

    def drop(self, path):
        fd, _ = self.devices.pop(path)
        os.close(fd)
        log(f"device gone: {path}")

    def on_input(self, fd, condition, path):
        if condition & (GLib.IO_ERR | GLib.IO_HUP):
            self.drop(path)
            return False
        try:
            data = os.read(fd, EVENT_SIZE * 64)
        except OSError as e:
            if e.errno == errno.EAGAIN:
                return True
            self.drop(path)
            return False
        if not self.over_panel:
            return True
        for i in range(0, len(data) - EVENT_SIZE + 1, EVENT_SIZE):
            _, _, etype, code, value = struct.unpack_from(EVENT_FORMAT, data, i)
            if etype == EV_REL and code == REL_WHEEL and value:
                for _ in range(abs(value)):
                    self.volume.step(value)
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fine", action="store_true",
                        help="use Plasma's small volume step instead of the normal one")
    args = parser.parse_args()

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    name = dbus.service.BusName(BUS_NAME, bus, do_not_queue=True)  # noqa: F841 (keeps name owned)
    ScrollVol(bus, Volume(bus, args.fine))
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
