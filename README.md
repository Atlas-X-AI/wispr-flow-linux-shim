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
- **One cold-start path.** Starting Atlas Wispr also starts Wispr Flow under
  Wine when it is not already running. The app, listener and tray return at
  login without a separate launch step.

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

## Supported target

- Arch Linux, x86-64, KDE Plasma 6, Wayland or X11.
- A working microphone and an internet connection.

That is the target covered by the automated installer and fresh-prefix proof.
Other distributions and compositors are **UNKNOWN**, not silently treated as
supported.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/Atlas-X-AI/wispr-flow-linux-shim/v1.1.3/bootstrap.sh | bash
```

The release is pinned, its archive checksum is verified before anything runs,
and the installer provisions the complete supported stack: Arch packages,
an isolated checksum-pinned Wine build, `ydotool`, Wayland and X11
clipboard/window tools, a checksum-pinned `kdotool`, the official Wispr Flow Windows
installer, Atlas Wispr, its tray, and its enabled user services. `sudo` may ask
The installer does **not** run `pacman` or upgrade the host. It retains an
existing Wine runtime or installs a pinned portable Wine build under
`~/.local/opt/atlas-wispr`. A Linux base missing the remaining Hermes desktop
tools fails loudly without changing packages; that blank-Arch path remains
**UNKNOWN**, not advertised as working.

The proprietary Wispr Flow installer comes directly from Wispr's official
download host; it is not redistributed by Atlas AI. Its version and SHA-256 are
pinned in the release.

After the command finishes:

1. Sign into Wispr Flow in the window it opens.
2. Bind your desired hardware button to **F16**. Atlas Wispr registers F16 as
   the KDE shortcut for **Atlas Wispr Toggle**.

That is the whole user setup. One press records. The next press stops,
auto-pastes the transcript, and presses Enter. Both Wispr Flow and Atlas Wispr
return automatically at login.

The F16 command path does not require input-group membership or XWayland global
key eavesdropping. Those are retained only for existing advanced configurations
that choose to let the shim watch raw evdev devices directly.

## Configuration

Use the tray. Everything below is for automation and troubleshooting.

Settings live in `~/.config/wispr-shim/config.json`, written by the tray.
Environment variables override the file, so a running setup can always be
debugged without editing anything:

| Variable | Default | Purpose |
| --- | --- | --- |
| `WISPR_FLOW_DB` | auto-discovered | Path to `flow.sqlite` in the Wine prefix |
| `WISPR_FLOW_EXE` | auto-discovered | Path to `Wispr Flow.exe` when the Wine prefix is unusual |
| `WINEPREFIX` | `~/.wine*` | Searched when auto-discovering the database |
| `WISPR_SHIM_DEVICES` | `keyd virtual keyboard,input-remapper keyboard` | Input nodes to watch |
| `WISPR_ONE_BUTTON_CODES` | `186` (F16) | Keys driving the one-button flow |
| `WISPR_PASTE_DENY` | `systemsettings` | Window classes never auto-pasted into |
| `WISPR_WINDOW_CLASS` | `wispr flow.exe` | Wine window class to control |
| `YDOTOOL_SOCKET` | `/run/user/$UID/.ydotool_socket` | ydotoold socket |
| `ATLAS_WISPR_CLIPBOARD` | auto-detected | Force `wayland` or `x11` for diagnostics |
| `ATLAS_WISPR_WINDOW_TOOL` | auto-detected | Force `kdotool` or `xdotool` for diagnostics |

**Which input device do I watch?** If a remapper (keyd, input-remapper) is
running, it holds an exclusive grab on your physical keyboards and its virtual
node is the only one carrying real keystrokes. `sudo evtest` lists your nodes;
watch the virtual one, not the hardware one.

**Choosing a one-button key:** avoid F13. It is `XF86Tools` on most desktops,
and KDE launches System Settings from it by default - every press opens a
window. F16 is unbound on a stock system.

## When something is wrong

```sh
atlas-wispr-doctor            # what is wrong?
atlas-wispr-doctor --restart  # stop every copy, start exactly one, re-check
atlas-wispr-doctor --version  # installed version, source commit, dirty state
```

Checks the things that actually break dictation - duplicate or missing
processes, dependencies, input-group access, your chosen keyboard and key, the
Wine database, a real clipboard round-trip, and whether your panel was given the
tray icon. Every check reports PASS, FAIL or UNKNOWN, and a check that could not
run says UNKNOWN rather than quietly passing.

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

Built and used on Arch Linux with KDE Plasma 6 (Wayland and X11), Wispr Flow
1.6.x under Wine. Reports from other distributions and compositors are welcome.

## Licence and affiliation

MIT - see [LICENSE](LICENSE). Built and maintained by
[Atlas AI](https://atlas-ai.au) (Atlas X AI Pty Ltd).

This is an unofficial community tool. It is not affiliated with, endorsed by,
or supported by Wispr AI. "Wispr Flow" is used descriptively to name the
application this tool works alongside.
