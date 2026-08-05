#!/usr/bin/env bash
# Install wispr-flow-linux-shim into ~/.local/bin and ~/.config/systemd/user.
set -euo pipefail

BIN="${HOME}/.local/bin"
UNITS="${HOME}/.config/systemd/user"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$BIN" "$UNITS" "${HOME}/.local/state"
install -m 755 "$here/bin/wispr-focus-shim"     "$BIN/wispr-focus-shim"
install -m 755 "$here/bin/wispr-hub-visibility" "$BIN/wispr-hub-visibility"
install -m 644 "$here/systemd/wispr-focus-shim.service" "$UNITS/wispr-focus-shim.service"
systemctl --user daemon-reload

missing=()
for c in ydotool wl-copy wl-paste kdotool notify-send; do
  command -v "$c" >/dev/null 2>&1 || missing+=("$c")
done
python3 -c "import evdev" 2>/dev/null || missing+=("python-evdev")
pgrep -x ydotoold >/dev/null 2>&1 || echo "WARNING: ydotoold is not running; key injection will fail."
id -nG | tr ' ' '\n' | grep -qx input || echo "WARNING: your user is not in the 'input' group; the shim cannot read /dev/input."

if [ ${#missing[@]} -gt 0 ]; then
  echo "MISSING dependencies: ${missing[*]}"
  echo "Install them, then: systemctl --user enable --now wispr-focus-shim"
  exit 1
fi

echo "Installed. Start it with:  systemctl --user enable --now wispr-focus-shim"
