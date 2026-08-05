#!/usr/bin/env python3
"""Fresh-machine contract tests for the public GitHub installer."""

from __future__ import annotations

import hashlib
import io
import os
import runpy
import shutil
import signal
import sqlite3
import stat
import subprocess
import tarfile
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class BootstrapTests(unittest.TestCase):
    def make_release(self, root: Path, install_body: str) -> Path:
        version = (ROOT / "VERSION").read_text().strip()
        release = root / f"atlas-wispr-{version}"
        release.mkdir()
        executable(release / "install.sh", install_body)
        (release / "REVISION").write_text("known-release-revision\n")
        archive = root / f"atlas-wispr-{version}.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(release, arcname=release.name)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        (root / f"{archive.name}.sha256").write_text(f"{digest}  {archive.name}\n")
        return archive

    def test_bootstrap_verifies_release_and_runs_one_provisioning_installer(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            log = tmp / "install.log"
            self.make_release(
                tmp,
                "#!/bin/sh\nprintf '%s|%s\\n' \"$*\" \"$ATLAS_WISPR_RELEASE_REVISION\" > \"$BOOTSTRAP_TEST_LOG\"\n",
            )
            env = dict(
                os.environ,
                ATLAS_WISPR_RELEASE_BASE=f"file://{tmp}",
                BOOTSTRAP_TEST_LOG=str(log),
            )
            result = subprocess.run(
                [str(ROOT / "bootstrap.sh")], env=env, capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(log.read_text().strip(), "--provision|known-release-revision")
            self.assertIn("PASS: release checksum verified", result.stdout)

    def test_bootstrap_rejects_a_bad_checksum_before_installing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            marker = tmp / "should-not-run"
            archive = self.make_release(
                tmp, f"#!/bin/sh\ntouch '{marker}'\n"
            )
            archive.write_bytes(archive.read_bytes() + b"tampered")
            env = dict(os.environ, ATLAS_WISPR_RELEASE_BASE=f"file://{tmp}")
            result = subprocess.run(
                [str(ROOT / "bootstrap.sh")], env=env, capture_output=True, text=True
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            self.assertIn("checksum", (result.stderr + result.stdout).lower())


class ProvisioningTests(unittest.TestCase):
    def test_arch_provisioner_installs_portable_wine_verified_kdotool_and_ydotool_service(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            home = tmp / "home"
            fake_bin = tmp / "bin"
            log = tmp / "calls.log"
            home.mkdir()
            fake_bin.mkdir()
            (tmp / "os-release").write_text("ID=arch\n")

            executable(fake_bin / "sudo", f"#!/bin/sh\nprintf 'sudo:%s\\n' \"$*\" >> '{log}'\n")
            executable(fake_bin / "pacman", f"#!/bin/sh\nprintf 'pacman:%s\\n' \"$*\" >> '{log}'\n")
            executable(fake_bin / "systemctl", f"#!/bin/sh\nprintf 'systemctl:%s\\n' \"$*\" >> '{log}'\n")
            executable(fake_bin / "kdotool", "#!/bin/sh\nexit 1\n")

            payload = tmp / "kdotool"
            executable(payload, "#!/bin/sh\nexit 0\n")
            archive = tmp / "kdotool.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                bundle.add(payload, arcname="kdotool")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()

            wine_root = tmp / "wine-11.14-amd64-wow64"
            for command in ("wine", "wineboot", "wineserver"):
                executable(wine_root / "bin" / command, "#!/bin/sh\nexit 0\n")
            wine_archive = tmp / "wine.tar.xz"
            with tarfile.open(wine_archive, "w:xz") as bundle:
                bundle.add(wine_root, arcname=wine_root.name)
            wine_digest = hashlib.sha256(wine_archive.read_bytes()).hexdigest()

            env = dict(
                os.environ,
                HOME=str(home),
                PATH=f"{fake_bin}:/usr/bin",
                ATLAS_WISPR_OS_RELEASE=str(tmp / "os-release"),
                ATLAS_WISPR_KDOTOOL_URL=f"file://{archive}",
                ATLAS_WISPR_KDOTOOL_SHA256=digest,
                ATLAS_WISPR_FORCE_KDOTOOL_INSTALL="1",
                ATLAS_WISPR_WINE_URL=f"file://{wine_archive}",
                ATLAS_WISPR_WINE_SHA256=wine_digest,
                ATLAS_WISPR_FORCE_WINE_INSTALL="1",
            )
            result = subprocess.run(
                [str(ROOT / "scripts/provision-system")],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            calls = log.read_text()
            self.assertNotIn("pacman", calls)
            self.assertIn("systemctl:--user enable --now ydotool.service", calls)
            self.assertTrue((home / ".local/bin/kdotool").is_file())
            self.assertTrue((home / ".local/bin/wine").exists())
            self.assertIn("PASS: portable Wine installed", result.stdout)
            self.assertIn("PASS: Atlas Wispr runtime provisioned", result.stdout)

    def test_provisioner_fails_loudly_on_an_unsupported_distribution(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / "os-release").write_text("ID=ubuntu\n")
            env = dict(os.environ, ATLAS_WISPR_OS_RELEASE=str(tmp / "os-release"))
            result = subprocess.run(
                [str(ROOT / "scripts/provision-system")],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("supports Arch Linux", result.stderr + result.stdout)


class WisprInstallerTests(unittest.TestCase):
    def test_official_installer_is_verified_and_installed_into_a_fresh_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            home = tmp / "home"
            fake_bin = tmp / "bin"
            log = tmp / "wine.log"
            home.mkdir()
            fake_bin.mkdir()
            installer = tmp / "Wispr Flow Setup.exe"
            installer.write_bytes(b"known vendor installer")
            digest = hashlib.sha256(installer.read_bytes()).hexdigest()
            executable(
                fake_bin / "wine",
                "#!/bin/sh\n"
                f"printf '%s|%s\\n' \"$WINEPREFIX\" \"$*\" > '{log}'\n"
                "dest=\"$WINEPREFIX/drive_c/users/test/AppData/Local/WisprFlow\"\n"
                "mkdir -p \"$dest\"\n"
                "touch \"$dest/Wispr Flow.exe\"\n",
            )
            env = dict(
                os.environ,
                HOME=str(home),
                PATH=f"{fake_bin}:/usr/bin",
                ATLAS_WISPR_INSTALLER_URL=installer.as_uri(),
                ATLAS_WISPR_INSTALLER_SHA256=digest,
            )
            result = subprocess.run(
                [str(ROOT / "scripts/install-wispr-flow")],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            call = log.read_text()
            self.assertIn(str(home / ".wine-whisperflow"), call)
            self.assertIn("--silent", call)
            self.assertIn("PASS: Wispr Flow installed", result.stdout)


class ToggleCommandTests(unittest.TestCase):
    def test_toggle_command_starts_service_then_signals_its_main_process(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            fake_bin = tmp / "bin"
            log = tmp / "systemctl.log"
            fake_bin.mkdir()
            executable(
                fake_bin / "systemctl",
                "#!/bin/sh\n"
                f"printf '%s\\n' \"$*\" >> '{log}'\n"
                "[ \"$2\" = is-active ] && exit 1\n"
                "exit 0\n",
            )
            env = dict(os.environ, PATH=f"{fake_bin}:/usr/bin")
            result = subprocess.run(
                [str(ROOT / "bin/atlas-wispr-toggle")],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            calls = log.read_text()
            self.assertIn("--user start wispr-focus-shim.service", calls)
            self.assertIn(
                "--user kill --signal=USR1 --kill-whom=main wispr-focus-shim.service",
                calls,
            )

    def test_service_waits_for_first_login_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            home = tmp / "home"
            home.mkdir()
            config = tmp / "config.json"
            config.write_text('{"devices": []}\n')
            env = dict(
                os.environ,
                HOME=str(home),
                WINEPREFIX=str(tmp / "empty-prefix"),
                WISPR_SHIM_CONFIG=str(config),
                WISPR_SHIM_LOG=str(tmp / "shim.log"),
            )
            process = subprocess.Popen(
                [str(ROOT / "bin/wispr-focus-shim")],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                log_path = tmp / "shim.log"
                for _ in range(30):
                    if log_path.exists() and "first login" in log_path.read_text():
                        break
                    time.sleep(0.1)
                self.assertIsNone(process.poll(), "service exited before Wispr login")
            finally:
                process.terminate()
                output, _ = process.communicate(timeout=5)
            evidence = output + (log_path.read_text() if log_path.exists() else "")
            self.assertIn("waiting for Wispr Flow first login", evidence)
            self.assertIn("ready for the atlas-wispr-toggle command", evidence)


class ClipboardBackendTests(unittest.TestCase):
    def test_x11_clipboard_round_trip_uses_xclip(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            clipboard = tmp / "clipboard"
            executable(
                fake_bin / "xclip",
                "#!/bin/sh\n"
                f"case \"$*\" in *-o*) cat '{clipboard}' 2>/dev/null;; *) cat > '{clipboard}';; esac\n",
            )
            executable(fake_bin / "xdotool", "#!/bin/sh\nprintf '42\\n'\n")
            env = dict(
                os.environ,
                HOME=str(tmp),
                PATH=f"{fake_bin}:/usr/bin",
                ATLAS_WISPR_CLIPBOARD="x11",
            )
            with mock.patch.dict(os.environ, env, clear=True):
                shim = runpy.run_path(str(ROOT / "bin/wispr-focus-shim"))
                shim["clipboard_write"]("SheaHermes X11")
                self.assertEqual(shim["clipboard_text"](), "SheaHermes X11")
                self.assertEqual(shim["clipboard_backend"](), "x11")
                os.environ["XDG_SESSION_TYPE"] = "x11"
                self.assertEqual(shim["kdotool"]("getactivewindow"), "42")


if __name__ == "__main__":
    unittest.main()
