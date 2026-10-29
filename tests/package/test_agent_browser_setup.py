import contextlib
import hashlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_drive import agent_browser_setup

FAKE_BROWSER = b"#!/bin/sh\nprintf '%s\\n' 'agent-browser 0.40.0'\n"


def setup(directory: Path, env: dict, download: bytes | Exception = FAKE_BROWSER):
    """Run setup-agent-browser in-process with a fake release download."""
    requested = []

    def urlopen(url, timeout):
        requested.append(url)
        if isinstance(download, Exception):
            raise download
        return io.BytesIO(download)

    stdout, stderr = io.StringIO(), io.StringIO()
    digests = {"test-x64": hashlib.sha256(FAKE_BROWSER).hexdigest()}
    with (
        mock.patch.dict(os.environ, env, clear=True),
        mock.patch.object(sys, "argv", ["setup", "--directory", str(directory)]),
        mock.patch.object(agent_browser_setup, "platform_name", return_value="test-x64"),
        mock.patch.object(agent_browser_setup, "DIGESTS", digests),
        mock.patch("urllib.request.urlopen", urlopen),
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(stderr),
    ):
        code = agent_browser_setup.main()
    return code, stdout.getvalue(), stderr.getvalue(), requested


@unittest.skipIf(os.name == "nt", "POSIX executable stubs")
class SetupTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.env = {"PATH": str(self.root), "HOME": str(self.root)}

    def write_browser(self, path: Path, version: str = "0.40.0") -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"#!/bin/sh\nprintf '%s\\n' 'agent-browser {version}'\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_existing_compatible_browser_needs_no_download(self):
        browser = self.write_browser(self.root / "existing browser")
        self.env["TEST_DRIVE_AGENT_BROWSER"] = str(browser)
        code, stdout, stderr, requested = setup(self.root / "runtime", self.env)
        self.assertEqual(code, 0, stderr)
        self.assertIn(str(browser), stdout)
        self.assertEqual(requested, [])
        self.assertFalse((self.root / "runtime").exists())

    def test_invalid_explicit_browser_is_not_replaced(self):
        self.env["TEST_DRIVE_AGENT_BROWSER"] = str(self.root / "missing")
        code, _, stderr, requested = setup(self.root / "runtime", self.env)
        self.assertNotEqual(code, 0)
        self.assertIn("Cannot run agent-browser", stderr)
        self.assertEqual(requested, [])
        self.assertFalse((self.root / "runtime").exists())

    def test_downloads_the_pinned_release_into_an_existing_directory(self):
        self.write_browser(self.root / "agent-browser", "0.34.0")  # an old browser on PATH
        alias = self.root / "runtime parent alias"
        alias.symlink_to(self.root, target_is_directory=True)
        runtime = alias / "isolated runtime"
        runtime.mkdir()
        (runtime / "keep.txt").write_text("user data", encoding="utf-8")
        self.env["TEST_DRIVE_RUNTIME_DIR"] = str(runtime)
        code, stdout, stderr, requested = setup(runtime, self.env)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(
            requested,
            [
                "https://github.com/vercel-labs/agent-browser/releases/download/"
                f"v{agent_browser_setup.VERSION}/agent-browser-test-x64"
            ],
        )
        installed = runtime.resolve() / "agent-browser"
        self.assertIn(str(installed), stdout)
        self.assertEqual((runtime / "keep.txt").read_text(encoding="utf-8"), "user data")
        self.assertEqual(
            sorted(path.name for path in runtime.iterdir()), ["agent-browser", "keep.txt"]
        )
        selected = subprocess.run(
            [sys.executable, "-m", "test_drive", "agent-browser-path"],
            env={**os.environ, **self.env},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.assertEqual(selected.stdout.strip(), str(installed))

    def test_digest_mismatch_leaves_nothing_behind(self):
        runtime = self.root / "runtime"
        code, _, stderr, _ = setup(runtime, self.env, download=b"tampered")
        self.assertNotEqual(code, 0)
        self.assertIn("SHA-256", stderr)
        self.assertEqual(list(runtime.iterdir()), [])

    def test_download_failure_is_reported_without_partial_files(self):
        runtime = self.root / "runtime"
        code, _, stderr, _ = setup(runtime, self.env, download=OSError("network unreachable"))
        self.assertNotEqual(code, 0)
        self.assertIn("network unreachable", stderr)
        self.assertEqual(list(runtime.iterdir()), [])

    def test_incompatible_managed_binary_is_not_overwritten(self):
        runtime = self.root / "runtime"
        binary = self.write_browser(runtime / "agent-browser", "0.34.0")
        code, _, stderr, requested = setup(runtime, self.env)
        self.assertNotEqual(code, 0)
        self.assertIn("not changed", stderr)
        self.assertEqual(requested, [])
        self.assertIn("0.34.0", binary.read_text(encoding="utf-8"))

    def test_reuses_compatible_runtime_in_explicit_directory(self):
        runtime = self.root / "runtime"
        browser = self.write_browser(runtime / "agent-browser")
        self.env["TEST_DRIVE_RUNTIME_DIR"] = str(self.root / "other-runtime")
        code, stdout, stderr, requested = setup(runtime, self.env)
        self.assertEqual(code, 0, stderr)
        self.assertIn(str(browser), stdout)
        self.assertEqual(requested, [])

    def test_earlier_npm_layout_is_still_found(self):
        runtime = self.root / "runtime"
        legacy = self.write_browser(runtime / "node_modules" / ".bin" / "agent-browser")
        self.env["TEST_DRIVE_RUNTIME_DIR"] = str(runtime)
        code, stdout, stderr, requested = setup(runtime, self.env)
        self.assertEqual(code, 0, stderr)
        self.assertIn(str(legacy), stdout)
        self.assertEqual(requested, [])

    def test_unusable_npm_layout_gets_a_native_binary_beside_it(self):
        runtime = self.root / "runtime"
        legacy = runtime / "node_modules" / ".bin" / "agent-browser"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("#!/bin/sh\nexit 127\n", encoding="utf-8")  # Node.js was removed
        legacy.chmod(0o755)
        self.env["TEST_DRIVE_RUNTIME_DIR"] = str(runtime)
        code, stdout, stderr, _ = setup(runtime, self.env)
        self.assertEqual(code, 0, stderr)
        self.assertIn(str(runtime / "agent-browser"), stdout)
        self.assertTrue(legacy.is_file())


class PlatformTests(unittest.TestCase):
    def test_release_names_follow_the_launcher(self):
        cases = (
            ("linux", "x86_64", "glibc", "linux-x64"),
            ("linux", "aarch64", "glibc", "linux-arm64"),
            ("linux", "x86_64", "", "linux-musl-x64"),
            ("darwin", "arm64", "", "darwin-arm64"),
            ("darwin", "x86_64", "", "darwin-x64"),
            ("win32", "AMD64", "", "win32-x64.exe"),
            ("win32", "ARM64", "", None),
            ("freebsd14", "amd64", "", None),
            ("linux", "riscv64", "glibc", None),
        )
        for system, machine, libc, expected in cases:
            with (
                self.subTest(system=system, machine=machine),
                mock.patch.object(sys, "platform", system),
                mock.patch("platform.machine", return_value=machine),
                mock.patch("platform.libc_ver", return_value=(libc, "")),
            ):
                self.assertEqual(agent_browser_setup.platform_name(), expected)
        self.assertTrue({name for *_, name in cases if name} <= agent_browser_setup.DIGESTS.keys())


if __name__ == "__main__":
    unittest.main()
