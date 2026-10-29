import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "test-drive"


class SkillInstallationTests(unittest.TestCase):
    def test_copied_skill_runs_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "installed skill" / "test-drive"
            shutil.copytree(SKILL, skill)
            self.assertFalse((skill / "tests").exists())
            text = (skill / "SKILL.md").read_text(encoding="utf-8")
            links = set(re.findall(r"\]\(([^)#:]+)\)", text))
            self.assertIn("references/run-json.md", links)
            for link in links:
                self.assertTrue((skill / link).is_file(), link)
            compatibility = re.search(r"(?m)^compatibility: (.+)$", text)
            self.assertTrue(compatibility and len(compatibility.group(1)) <= 500)
            workspace = root / "workspace"
            workspace.mkdir()
            shutil.copytree(REPO / "examples" / "shop", workspace / "site")
            scenario = subprocess.run(
                [sys.executable, "-m", "test_drive", "check-scenarios", "site"],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(scenario.returncode, 0, scenario.stderr)
            self.assertEqual(len(json.loads(scenario.stdout)["scenarios"]), 1)

            (workspace / "run.json").write_text(
                json.dumps(
                    {
                        "site": {"name": "Offline example"},
                        "scenarios": [
                            {"name": "Cart", "status": "not_run", "reason": "Not run yet"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = subprocess.run(
                [sys.executable, "-m", "test_drive", "render-report", "run.json"],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(report.returncode, 0, report.stderr)
            self.assertIn(
                "Offline example", (workspace / "report.html").read_text(encoding="utf-8")
            )
            self.assertEqual((skill / "LICENSE").read_bytes(), (REPO / "LICENSE").read_bytes())
