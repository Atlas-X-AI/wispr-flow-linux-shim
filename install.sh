#!/usr/bin/env bash
# Install Atlas Wispr (tray + shim) into the current user's home.
set -euo pipefail

BIN="${HOME}/.local/bin"
UNITS="${HOME}/.config/systemd/user"
APPS="${HOME}/.local/share/applications"
AUTOSTART="${HOME}/.config/autostart"
ICONS="${HOME}/.local/share/icons/hicolor"
RELEASE_DIR="${HOME}/.local/share/atlas-wispr"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$BIN" "$UNITS" "$APPS" "$AUTOSTART" "$RELEASE_DIR" "${HOME}/.local/state"

install -m 755 "$here/bin/wispr-focus-shim"     "$BIN/wispr-focus-shim"
install -m 755 "$here/bin/atlas-wispr-launch-flow" "$BIN/atlas-wispr-launch-flow"
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
for c in wine ydotool wl-copy wl-paste kdotool notify-send; do
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
  echo "Arch:   sudo pacman -S wine ydotool wl-clipboard kdotool libnotify python-evdev libayatana-appindicator python-gobject"
  echo "Then run this installer again."
  exit 1
fi

version="$(tr -d '[:space:]' < "$here/VERSION")"
revision="$(git -C "$here" rev-parse HEAD 2>/dev/null || printf 'unknown')"
source_dirty=false
if git -C "$here" status --porcelain --untracked-files=normal 2>/dev/null | grep -q .; then
  source_dirty=true
fi
release_tmp="$(mktemp "$RELEASE_DIR/release.XXXXXX")"
printf 'version=%s\nrevision=%s\nsource_dirty=%s\n' \
  "$version" "$revision" "$source_dirty" > "$release_tmp"
chmod 644 "$release_tmp"
mv -f "$release_tmp" "$RELEASE_DIR/release"

# One install command must leave the complete cold-start path live. Restart is
# deliberate: on an upgrade, --now alone would leave the old unit definition
# and old executable running until the next login.
systemctl --user enable wispr-focus-shim.service
systemctl --user restart wispr-focus-shim.service

if ! pgrep -f '[a]tlas-wispr-tray' >/dev/null 2>&1; then
  nohup "$BIN/atlas-wispr-tray" \
    >"${HOME}/.local/state/atlas-wispr-tray.log" 2>&1 </dev/null &
fi

echo
echo "Installed and started. Atlas Wispr and Wispr Flow now start together."
echo "The tray and dictation service will both return automatically at login."
echo "If anything ever misbehaves, run:   atlas-wispr-doctor"
