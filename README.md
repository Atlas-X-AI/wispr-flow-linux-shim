# Atlas Wispr

Make [Wispr Flow](https://wisprflow.ai) genuinely usable on Linux - with a
system tray you can actually configure, not a config file you have to guess at.

Wispr Flow ships no Linux build. The Windows app runs under Wine, but three
things break badly enough that most people give up:

| Symptom | Cause |
| --- | --- |
| Hotkey does nothing unless the Wispr window is focused | XWayland does not forward global chords to unfocused X11 clients |
| Dictation "works sometimes" - text reaches the clipboard on some attempts and not others | Wine's X11 clipboard sync is itself focus-gated |
| Text never lands in the app you were typing in | The Wine app cannot see native Wayland text fields (`couldNotGetTextBoxInfo`) |

This shim fixes all three from the Linux side. It changes nothing inside the
Wine prefix and does not patch the application.

## What you get

- **A system tray app.** Set your dictation key by pressing it, choose your
  keyboard, toggle auto-paste and notifications, hide or show the Wispr window,
  start and stop dictation. A first-run wizard checks your dependencies and
  walks you through setup.

- **Dictation from any window.** Press your chord anywhere. The shim remembers
  the focused window, activates Wispr, re-injects the chord, restores your
  focus and minimises Wispr again.
- **Reliable clipboard.** Every finished transcript is copied to the Wayland
  clipboard by the shim itself and verified by read-back, with a desktop
  notification preview.
- **Optional one-button flow.** Bind a spare key (or a mouse side button):
  first press starts recording, second press stops it and auto-pastes the
  transcript plus Enter. Start and stop are read from the application's own
  history database, so the state cannot drift out of sync.
- **Paste deny-list.** Windows where a stray Enter would be destructive (system
  settings pages, Wispr itself) are never auto-pasted into.

## Requirements

- Wayland compositor. Window control uses `kdotool`, so KDE Plasma / KWin is
  the tested target.
- `python-evdev`, `ydotool` + a running `ydotoold`, `wl-clipboard`, `kdotool`,
  `libnotify`.
- Your user in the `input` group (read access to `/dev/input`).

## Install

```sh
git clone https://github.com/Atlas-X-AI/wispr-flow-linux-shim
cd wispr-flow-linux-shim
./install.sh
atlas-wispr-tray &
```

The installer checks every dependency and tells you exactly what to install if
something is missing. The tray then opens a setup wizard on first run: pick your
keyboard, press the key you want for dictation, done. It starts automatically at
login from then on.

Then, once, allow XWayland to receive global chords so the Wine app can hear
its own hotkey (KDE Plasma):

```sh
kwriteconfig6 --file kwinrc --group Wayland --key XwaylandEavesdrops Combinations
qdbus6 org.kde.KWin /KWin reconfigure
```

## Configuration

Use the tray. Everything below is for automation and troubleshooting.

Settings live in `~/.config/wispr-shim/config.json`, written by the tray.
Environment variables override the file, so a running setup can always be
debugged without editing anything:

| Variable | Default | Purpose |
| --- | --- | --- |
| `WISPR_FLOW_DB` | auto-discovered | Path to `flow.sqlite` in the Wine prefix |
| `WINEPREFIX` | `~/.wine*` | Searched when auto-discovering the database |
| `WISPR_SHIM_DEVICES` | `keyd virtual keyboard,input-remapper keyboard` | Input nodes to watch |
| `WISPR_ONE_BUTTON_CODES` | `183,186` (F13, F16) | Keys driving the one-button flow |
| `WISPR_PASTE_DENY` | `systemsettings` | Window classes never auto-pasted into |
| `WISPR_WINDOW_CLASS` | `wispr flow.exe` | Wine window class to control |
| `YDOTOOL_SOCKET` | `/run/user/$UID/.ydotool_socket` | ydotoold socket |

**Which input device do I watch?** If a remapper (keyd, input-remapper) is
running, it holds an exclusive grab on your physical keyboards and its virtual
node is the only one carrying real keystrokes. `sudo evtest` lists your nodes;
watch the virtual one, not the hardware one.

**Choosing a one-button key:** avoid F13. It is `XF86Tools` on most desktops,
and KDE launches System Settings from it by default - every press opens a
window. F16 is unbound on a stock system.

## Extras

- `bin/wispr-hub-visibility show|hide` - the same window transparency toggle the
  tray offers, exposed for scripts.
- `contrib/naga-bind` - bind Razer Naga side buttons through input-remapper
  presets from the command line, with macro validation and automatic backups.

## How it works

See [docs/how-it-works.md](docs/how-it-works.md) for the mechanism and for the
diagnostic findings behind each fix - including the silent-microphone trap that
makes dictation look broken when the application is actually recording from a
monitor (loopback) device.

## Status

Built and used daily on Arch Linux with KDE Plasma 6 (Wayland), Wispr Flow
1.6.x under Wine. Reports from other distributions and compositors are welcome.

## Licence and affiliation

MIT - see [LICENSE](LICENSE). Built and maintained by
[Atlas AI](https://atlas-ai.au) (Atlas X AI Pty Ltd).

This is an unofficial community tool. It is not affiliated with, endorsed by,
or supported by Wispr AI. "Wispr Flow" is used descriptively to name the
application this tool works alongside.
