#!/usr/bin/env bash
# Install scroll-vol for the current user. Asks for sudo once, for the udev rule.
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f /etc/udev/rules.d/70-scroll-vol.rules ]] || ! cmp -s 70-scroll-vol.rules /etc/udev/rules.d/70-scroll-vol.rules; then
    echo "Installing udev rule (needs sudo)..."
    sudo install -m 644 70-scroll-vol.rules /etc/udev/rules.d/70-scroll-vol.rules
    sudo udevadm control --reload-rules
    sudo udevadm trigger --subsystem-match=input --action=change
fi

install -Dm755 scroll-vol-daemon.py ~/.local/bin/scroll-vol-daemon
install -Dm644 scroll-vol.service ~/.config/systemd/user/scroll-vol.service
systemctl --user daemon-reload
systemctl --user enable scroll-vol.service
systemctl --user restart scroll-vol.service

if kpackagetool6 --type=KWin/Script --show scrollvol >/dev/null 2>&1; then
    kpackagetool6 --type=KWin/Script --upgrade kwin-script >/dev/null
else
    kpackagetool6 --type=KWin/Script --install kwin-script >/dev/null
fi
kwriteconfig6 --file kwinrc --group Plugins --key scrollvolEnabled true
# Unload first so an upgraded script is actually reloaded.
qdbus6 org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript scrollvol >/dev/null || true
qdbus6 org.kde.KWin /KWin reconfigure

echo "scroll-vol installed."
