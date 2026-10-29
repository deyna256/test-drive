import json
import subprocess
import sys
import unittest


class CliTests(unittest.TestCase):
    def test_version_and_labels_are_available_through_the_installed_package(self):
        command = [sys.executable, "-B", "-m", "test_drive"]
        version = subprocess.run(
            [*command, "--version"], capture_output=True, text=True, check=False
        )
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertRegex(version.stdout, r"^test-drive-skill \d+\.\d+\.\d+")
        labels = subprocess.run(
            [*command, "report-labels"], capture_output=True, text=True, check=False
        )
        self.assertEqual(labels.returncode, 0, labels.stderr)
        self.assertEqual(json.loads(labels.stdout)["criteria"], "Acceptance criteria")

    def test_subcommand_help_and_invalid_command(self):
        command = [sys.executable, "-B", "-m", "test_drive"]
        for name in (
            "agent-browser-path",
            "setup-agent-browser",
            "check-scenarios",
            "render-report",
            "report-labels",
        ):
            with self.subTest(command=name):
                help_result = subprocess.run(
                    [*command, name, "--help"], capture_output=True, text=True, check=False
                )
                self.assertEqual(help_result.returncode, 0, help_result.stderr)
                self.assertIn("usage:", help_result.stdout)
        invalid = subprocess.run([*command, "missing"], capture_output=True, text=True, check=False)
        self.assertEqual(invalid.returncode, 2)


if __name__ == "__main__":
    unittest.main()
