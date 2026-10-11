#!/usr/bin/env bash
set -uo pipefail

systemctl --user disable --now scroll-vol.service
rm -f ~/.config/systemd/user/scroll-vol.service ~/.local/bin/scroll-vol-daemon
systemctl --user daemon-reload

kwriteconfig6 --file kwinrc --group Plugins --key scrollvolEnabled --delete
qdbus6 org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript scrollvol >/dev/null
kpackagetool6 --type=KWin/Script --remove scrollvol >/dev/null
qdbus6 org.kde.KWin /KWin reconfigure

if [[ -f /etc/udev/rules.d/70-scroll-vol.rules ]]; then
    echo "Removing udev rule (needs sudo)..."
    sudo rm /etc/udev/rules.d/70-scroll-vol.rules
    sudo udevadm control --reload-rules
    sudo udevadm trigger --subsystem-match=input --action=change
fi

echo "scroll-vol removed."
