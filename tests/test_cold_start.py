#!/usr/bin/env python3
"""Deterministic cold-start and one-command installation tests."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = Path(
    os.environ.get(
        "ATLAS_WISPR_LAUNCHER_UNDER_TEST",
        str(ROOT / "bin/atlas-wispr-launch-flow"),
    )
)


def executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class ColdStartTests(unittest.TestCase):
    def test_existing_process_is_not_launched_twice(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / "proc/42").mkdir(parents=True)
            (tmp / "proc/42/cmdline").write_bytes(b"wine\0Wispr Flow.exe\0")
            log = tmp / "wine.log"
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            executable(fake_bin / "wine", f"#!/bin/sh\necho called >> '{log}'\n")
            env = dict(os.environ, HOME=str(tmp), ATLAS_WISPR_PROC_ROOT=str(tmp / "proc"))
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            result = subprocess.run([str(LAUNCHER), "--wait-seconds", "0"], env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("already running", result.stdout)
            self.assertFalse(log.exists())

    def test_cold_start_finds_exe_and_waits_for_process(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            proc = tmp / "proc"
            proc.mkdir()
            exe = tmp / ".wine-whisperflow/drive_c/users/test/AppData/Local/WisprFlow/Wispr Flow.exe"
            exe.parent.mkdir(parents=True)
            exe.touch()
            log = tmp / "wine.log"
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            executable(
                fake_bin / "wine",
                "#!/bin/sh\n"
                f"mkdir -p '{proc}/73'\n"
                f"printf 'wine\\0Wispr Flow.exe\\0' > '{proc}/73/cmdline'\n"
                f"printf '%s\\n' \"$WINEPREFIX|$1\" > '{log}'\n",
            )
            env = dict(os.environ, HOME=str(tmp), ATLAS_WISPR_PROC_ROOT=str(proc))
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            result = subprocess.run([str(LAUNCHER), "--wait-seconds", "2"], env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("started from", result.stdout)
            self.assertEqual(log.read_text().strip(), f"{tmp / '.wine-whisperflow'}|{exe}")

    def test_install_is_the_single_complete_entry_point(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            fake_bin = tmp / "fake-bin"
            fake_bin.mkdir()
            systemctl_log = tmp / "systemctl.log"
            executable(fake_bin / "systemctl", f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{systemctl_log}'\n")
            executable(fake_bin / "pgrep", "#!/bin/sh\nexit 0\n")
            env = dict(os.environ, HOME=str(tmp))
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            result = subprocess.run([str(ROOT / "install.sh")], env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue((tmp / ".local/bin/atlas-wispr-launch-flow").is_file())
            self.assertTrue((tmp / ".local/bin/wispr-focus-shim").is_file())
            self.assertTrue((tmp / ".local/bin/atlas-wispr-toggle").is_file())
            release = (tmp / ".local/share/atlas-wispr/release").read_text()
            self.assertIn("version=1.1.3", release)
            self.assertIn("revision=", release)
            self.assertIn("source_dirty=", release)
            unit = (tmp / ".config/systemd/user/wispr-focus-shim.service").read_text()
            self.assertIn("ExecStartPre=%h/.local/bin/atlas-wispr-launch-flow", unit)
            calls = systemctl_log.read_text()
            self.assertIn("--user daemon-reload", calls)
            self.assertIn("--user enable wispr-focus-shim.service", calls)
            self.assertIn("--user restart wispr-focus-shim.service", calls)
            self.assertTrue((tmp / ".config/autostart/atlas-wispr-tray.desktop").is_file())
            toggle = (tmp / ".local/share/applications/atlas-wispr-toggle.desktop").read_text()
            self.assertIn("X-KDE-Shortcuts=F16", toggle)


if __name__ == "__main__":
    unittest.main()
