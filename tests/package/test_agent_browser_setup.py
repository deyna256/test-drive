import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


@unittest.skipIf(os.name == "nt", "POSIX executable stubs")
class SetupTests(unittest.TestCase):
    def test_existing_compatible_browser_needs_no_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            browser = root / "existing browser"
            browser.write_text(
                "#!/bin/sh\nprintf '%s\\n' 'agent-browser 0.40.0'\n", encoding="utf-8"
            )
            browser.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(root)
            env["TEST_DRIVE_AGENT_BROWSER"] = str(browser)
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "test_drive",
                    "setup-agent-browser",
                    "--directory",
                    str(root / "runtime"),
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(browser), result.stdout)
            self.assertFalse((root / "runtime").exists())

    def test_invalid_explicit_browser_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = os.environ.copy()
            env["PATH"] = str(root)
            env["TEST_DRIVE_AGENT_BROWSER"] = str(root / "missing")
            env["TEST_DRIVE_RUNTIME_DIR"] = str(root / "runtime")
            result = subprocess.run(
                [sys.executable, "-B", "-m", "test_drive", "setup-agent-browser"],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Cannot run agent-browser", result.stderr)
            self.assertFalse((root / "runtime").exists())

    def test_installs_in_an_isolated_directory_without_install_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary_dir = root / "bin"
            binary_dir.mkdir()
            node = binary_dir / "node"
            node.write_text("#!/bin/sh\nprintf '%s\\n' 'v24.0.0'\n", encoding="utf-8")
            node.chmod(0o755)
            fake_npm = root / "fake_npm.py"
            fake_npm.write_text(
                "import os, pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "pathlib.Path(os.environ['TEST_DRIVE_TEST_ARGS']).write_text('\\n'.join(args))\n"
                "prefix = pathlib.Path(args[args.index('--prefix') + 1])\n"
                "binary = prefix / 'node_modules' / '.bin' / 'agent-browser'\n"
                "binary.parent.mkdir(parents=True)\n"
                "binary.write_text(\"#!/bin/sh\\nprintf '%s\\\\n' 'agent-browser 0.40.0'\\n\")\n"
                "binary.chmod(0o755)\n",
                encoding="utf-8",
            )
            npm = binary_dir / "npm"
            npm.write_text(
                f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(fake_npm))} "$@"\n',
                encoding="utf-8",
            )
            npm.chmod(0o755)
            env = os.environ.copy()
            env.pop("TEST_DRIVE_AGENT_BROWSER", None)
            env["PATH"] = str(binary_dir)
            env["TEST_DRIVE_TEST_ARGS"] = str(root / "npm-args")
            runtime = root / "isolated runtime"
            env["TEST_DRIVE_RUNTIME_DIR"] = str(runtime)
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "test_drive",
                    "setup-agent-browser",
                    "--directory",
                    str(runtime),
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            args = (root / "npm-args").read_text(encoding="utf-8").splitlines()
            self.assertIn("--ignore-scripts", args)
            self.assertIn("--no-global", args)
            pinned = json.loads(
                (REPO / "tests" / "browser" / "package.json").read_text(encoding="utf-8")
            )["devDependencies"]["agent-browser"]
            self.assertIn(f"agent-browser@{pinned}", args)
            installed = runtime / "node_modules" / ".bin" / "agent-browser"
            self.assertTrue(installed.is_file())
            self.assertIn(str(installed), result.stdout)
            selected = subprocess.run(
                [sys.executable, "-m", "test_drive", "agent-browser-path"],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(selected.returncode, 0, selected.stderr)
            self.assertEqual(selected.stdout.strip(), str(installed))

    def test_existing_runtime_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "runtime"
            runtime.mkdir()
            marker = runtime / "keep.txt"
            marker.write_text("user data", encoding="utf-8")
            env = os.environ.copy()
            env.pop("TEST_DRIVE_AGENT_BROWSER", None)
            env["PATH"] = str(root)
            env["TEST_DRIVE_RUNTIME_DIR"] = str(runtime)
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "test_drive",
                    "setup-agent-browser",
                    "--directory",
                    str(runtime),
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(encoding="utf-8"), "user data")
            self.assertIn("not changed", result.stderr)

    def test_reuses_compatible_runtime_in_explicit_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "runtime"
            browser = runtime / "node_modules" / ".bin" / "agent-browser"
            browser.parent.mkdir(parents=True)
            browser.write_text(
                "#!/bin/sh\nprintf '%s\\n' 'agent-browser 0.40.0'\n", encoding="utf-8"
            )
            browser.chmod(0o755)
            env = os.environ.copy()
            env.pop("TEST_DRIVE_AGENT_BROWSER", None)
            env["TEST_DRIVE_RUNTIME_DIR"] = str(root / "other-runtime")
            env["PATH"] = str(root)
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "test_drive",
                    "setup-agent-browser",
                    "--directory",
                    str(runtime),
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(browser), result.stdout)

    def test_install_failure_reports_the_error_code_without_echoing_npm_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, script in (
                ("node", "printf '%s\\n' 'v24.0.0'"),
                ("npm", "printf '%s\\n' 'npm error code EAI_AGAIN' 'secret-sentinel' >&2; exit 1"),
            ):
                path = root / name
                path.write_text(f"#!/bin/sh\n{script}\n", encoding="utf-8")
                path.chmod(0o755)
            env = os.environ.copy()
            env.pop("TEST_DRIVE_AGENT_BROWSER", None)
            env["TEST_DRIVE_RUNTIME_DIR"] = str(root / "runtime")
            env["PATH"] = str(root)
            result = subprocess.run(
                [sys.executable, "-B", "-m", "test_drive", "setup-agent-browser"],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("EAI_AGAIN", result.stderr)
            self.assertNotIn("secret-sentinel", result.stdout + result.stderr)
            self.assertFalse((root / "runtime").exists())


@unittest.skipUnless(os.name == "nt" and shutil.which("node"), "requires Windows and Node.js")
class WindowsSetupTests(unittest.TestCase):
    def test_npm_runs_without_interpreting_runtime_path_as_shell_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary_dir = root / "bin"
            binary_dir.mkdir()
            npm = binary_dir / "npm.cmd"
            npm.write_text("@echo off\r\nexit /b 1\r\n", encoding="utf-8")
            npm_cli = binary_dir / "node_modules" / "npm" / "bin" / "npm-cli.js"
            npm_cli.parent.mkdir(parents=True)
            npm_cli.write_text(
                "const fs = require('fs'), path = require('path');\n"
                "const args = process.argv.slice(2);\n"
                "fs.writeFileSync(process.env.TEST_DRIVE_TEST_ARGS, JSON.stringify(args));\n"
                "const bin = path.join(args[args.indexOf('--prefix') + 1], 'node_modules', '.bin');\n"
                "fs.mkdirSync(bin, {recursive: true});\n"
                "fs.writeFileSync(path.join(bin, 'agent-browser.cmd'), '@echo off\\r\\necho agent-browser 0.40.0\\r\\n');\n",
                encoding="utf-8",
            )
            node = shutil.which("node")
            assert node is not None
            node_dir = str(Path(node).parent)
            env = os.environ.copy()
            env.pop("TEST_DRIVE_AGENT_BROWSER", None)
            runtime = root / "runtime & space"
            env["TEST_DRIVE_RUNTIME_DIR"] = str(runtime)
            env["TEST_DRIVE_TEST_ARGS"] = str(root / "args.json")
            env["PATH"] = str(binary_dir) + os.pathsep + node_dir
            result = subprocess.run(
                [sys.executable, "-B", "-m", "test_drive", "setup-agent-browser"],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((runtime / "node_modules" / ".bin" / "agent-browser.cmd").is_file())
            self.assertIn("--ignore-scripts", (root / "args.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
