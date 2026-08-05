#!/usr/bin/env bash
# Install Atlas Wispr (tray + shim) into the current user's home.
set -euo pipefail

BIN="${HOME}/.local/bin"
UNITS="${HOME}/.config/systemd/user"
APPS="${HOME}/.local/share/applications"
AUTOSTART="${HOME}/.config/autostart"
ICONS="${HOME}/.local/share/icons/hicolor"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$BIN" "$UNITS" "$APPS" "$AUTOSTART" "${HOME}/.local/state"

install -m 755 "$here/bin/wispr-focus-shim"     "$BIN/wispr-focus-shim"
install -m 755 "$here/bin/wispr-hub-visibility" "$BIN/wispr-hub-visibility"
install -m 755 "$here/bin/atlas-wispr-tray"     "$BIN/atlas-wispr-tray"
install -m 755 "$here/bin/atlas-wispr-doctor"   "$BIN/atlas-wispr-doctor"
install -m 644 "$here/systemd/wispr-focus-shim.service" "$UNITS/wispr-focus-shim.service"
install -m 644 "$here/desktop/atlas-wispr-tray.desktop" "$APPS/atlas-wispr-tray.desktop"
install -m 644 "$here/desktop/atlas-wispr-tray.desktop" "$AUTOSTART/atlas-wispr-tray.desktop"

for size in 16 22 24 32 48 64 128 256; do
  mkdir -p "$ICONS/${size}x${size}/apps"
  for state in idle recording off; do
    if command -v magick >/dev/null 2>&1; then
      magick "$here/icons/atlas-wispr-$state.png" -resize "${size}x${size}" \
        "$ICONS/${size}x${size}/apps/atlas-wispr-$state.png"
    else
      install -m 644 "$here/icons/atlas-wispr-$state.png" \
        "$ICONS/${size}x${size}/apps/atlas-wispr-$state.png"
    fi
  done
done
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t "$ICONS" 2>/dev/null || true
systemctl --user daemon-reload

missing=()
for c in ydotool wl-copy wl-paste kdotool notify-send; do
  command -v "$c" >/dev/null 2>&1 || missing+=("$c")
done
python3 -c "import evdev" 2>/dev/null || missing+=("python-evdev")
python3 -c "import gi; gi.require_version('AyatanaAppIndicator3','0.1')" 2>/dev/null \
  || missing+=("libayatana-appindicator (python bindings)")
pgrep -x ydotoold >/dev/null 2>&1 || echo "NOTE: ydotoold is not running - key injection will fail until it is."
id -nG | tr ' ' '\n' | grep -qx input || echo "NOTE: you are not in the 'input' group - run: sudo usermod -aG input \$USER, then log out and back in."

if [ ${#missing[@]} -gt 0 ]; then
  echo
  echo "Missing dependencies: ${missing[*]}"
  echo "Arch:   sudo pacman -S ydotool wl-clipboard kdotool libnotify python-evdev libayatana-appindicator python-gobject"
  echo "Then run this installer again."
  exit 1
fi

echo
echo "Installed. Start the tray now with:   atlas-wispr-tray &"
echo "It will walk you through setup, and start automatically at login from here on."
echo "If anything ever misbehaves, run:   atlas-wispr-doctor"
