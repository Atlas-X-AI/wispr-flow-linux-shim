# How it works, and what we found on the way

Every fix here came from a diagnosed cause, not a guess. The findings are worth
reading even if you never run this code, because each one makes dictation under
Wine look broken in a different way.

## 1. The silent-microphone trap

**Symptom:** you press the hotkey, the app shows it is recording, and nothing
ever appears. No error.

**Cause:** the application had selected a *monitor* device - the loopback of a
headphone output - rather than the headset's microphone. A monitor device on an
idle output produces pure silence, so there is genuinely nothing to transcribe.

**Fix:** set the microphone by device NAME, not by ID. Wispr Flow stores
`overrideAudioDeviceId` and `rankedAudioDevices` in its `config.json`, and the
device IDs are hashes that change between launches - pin the ID and the fix
silently evaporates on the next start. Rank the device you want by name at
position 0. Confirm from `logs/main.log`, which prints
`Acquired media stream { audioDeviceName: ... }` on every recording.

## 2. The hotkey only works when the window is focused

**Cause:** the Wine application is an X11 client under XWayland. Wayland does
not deliver global shortcuts to unfocused X11 clients unless the compositor is
told to eavesdrop.

**Fix (KDE):** `XwaylandEavesdrops=Combinations` in the `[Wayland]` group of
`kwinrc`, then `qdbus6 org.kde.KWin /KWin reconfigure`.

**Why the shim still exists:** eavesdropping alone did not deliver a
modifier-only chord (Ctrl+Meta) reliably. The shim guarantees delivery by
briefly focusing the Wispr window, injecting the chord, then restoring focus.

## 3. Physical keyboards are already grabbed

**Symptom:** an evdev listener sees no key events at all, even as root.

**Cause:** a remapper (keyd, input-remapper) holds an `EVIOCGRAB` exclusive
grab on the hardware nodes. Real keystrokes only ever appear on the remapper's
own virtual node - and naive listeners filter that node out, because it lives
under `/devices/virtual/input/` and looks synthetic.

**Fix:** watch the virtual node deliberately. This is `WISPR_SHIM_DEVICES`.

## 4. Injected keys come back to you

**Symptom:** the first working version spammed the window open and closed about
once a second until it was killed.

**Cause:** keys injected with ydotool are re-emitted through the same remapper
node the shim watches, so the shim heard its own injection and fired again.

**Fix:** a deaf window (2.5s) opened at the start of every injection, before any
event can return. Debouncing alone is not enough; the echo arrives late.

## 5. The clipboard was never the app's job

**Symptom:** transcripts reach the clipboard on some attempts and not others.

**Cause:** the only thing delivering them was Wine's X11 clipboard sync, which
is focus-gated. Whether a dictation "worked" depended on where focus happened to
be when it finished.

**Fix:** the shim polls the application's own `flow.sqlite` history table, and
`wl-copy`s each new formatted transcript itself, verifying by read-back before
claiming success.

## 6. The Wine app cannot paste into Wayland

`logs/main.log` reports `pasteSuccess: false, couldNotGetTextBoxInfo: true` on
every attempt into a native window. The application genuinely cannot see those
text fields. Auto-paste therefore has to be driven from the Linux side, which is
what the one-button flow does with `ydotool`.

## 7. Never count presses for a toggle

The first one-button implementation counted presses to decide start versus stop.
It desynchronised the moment recording was stopped by any other route (a
different key, the application's own UI), after which every press did the
opposite of what was expected.

**Fix:** ask the application. A recording in flight leaves the newest row of the
history table with an empty status. State that can be read is always better than
state that must be tracked.

## 8. F13 is not a free key

Binding the one-button flow to F13 opened System Settings on every press. F13 is
`XF86Tools`, and KDE ships `X-KDE-Shortcuts=Tools,Meta+I` in
`systemsettings.desktop`, so the desktop launches Settings from it by default -
a binding that appears in no user shortcut file and is easy to blame on your own
code. F16 is unbound on a stock system.

## Not yet solved

**Verified paste with retry.** There is a real signal for "someone read the
clipboard" (`wl-copy --paste-once --foreground` exits when a client takes the
selection), but a clipboard manager such as Klipper reads every new selection
immediately, so the signal fires whether or not a human pasted. A genuine
paste-confirmation needs the shim to own the clipboard at the protocol level.
Until then, a failed paste leaves the text on the clipboard - paste it yourself.
