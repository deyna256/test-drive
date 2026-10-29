import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class BrowserSelectionTests(unittest.TestCase):
    def test_browser_selection_rejects_old_version_and_honors_explicit_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binaries = root / "bin"
            binaries.mkdir()
            suffix = ".cmd" if os.name == "nt" else ""
            old = binaries / f"agent-browser{suffix}"
            configured = root / f"custom browser{suffix}"

            def write_browser(path, version):
                script = (
                    f"@echo off\r\necho agent-browser {version}\r\n"
                    if os.name == "nt"
                    else f"#!/bin/sh\nprintf '%s\\n' 'agent-browser {version}'\n"
                )
                path.write_text(script, encoding="utf-8")
                path.chmod(0o755)

            for path, version in ((old, "0.34.0"), (configured, "0.40.0")):
                write_browser(path, version)

            env = os.environ.copy()
            env.pop("TEST_DRIVE_AGENT_BROWSER", None)
            env["PATH"] = str(binaries)
            env["TEST_DRIVE_RUNTIME_DIR"] = str(root / "missing-runtime")
            command = [sys.executable, "-m", "test_drive", "agent-browser-path"]
            rejected = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("0.34.0", rejected.stderr)
            self.assertEqual(rejected.stdout, "")

            env["TEST_DRIVE_AGENT_BROWSER"] = str(configured)
            for version in ("0.40.0", "0.40.1", "0.100.0", "1.0.0", "0.40.0+build.1"):
                with self.subTest(version=version):
                    write_browser(configured, version)
                    accepted = subprocess.run(
                        command, env=env, capture_output=True, text=True, check=False
                    )
                    self.assertEqual(accepted.returncode, 0, accepted.stderr)
                    self.assertEqual(accepted.stdout.strip(), str(configured.resolve()))

            write_browser(configured, "0.41.0-rc.1")
            prerelease = subprocess.run(
                command, env=env, capture_output=True, text=True, check=False
            )
            self.assertNotEqual(prerelease.returncode, 0)
            self.assertIn("stable", prerelease.stderr)

            env["TEST_DRIVE_AGENT_BROWSER"] = str(root / "missing")
            missing = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
            self.assertNotEqual(missing.returncode, 0)
            self.assertEqual(missing.stdout, "")
