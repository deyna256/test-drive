import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_versions", REPO / "tools" / "check_versions.py"
)
assert SPEC and SPEC.loader
check_versions = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_versions)

FILES = {
    "python/pyproject.toml": '[project]\nname = "test-drive-skill"\nversion = "0.1.2"\n',
    "python/uv.lock": '[[package]]\nname = "test-drive-skill"\nversion = "0.1.2"\n',
    "python/src/test_drive/agent_browser_setup.py": 'VERSION = "0.40.0"\n',
    "README.md": "Install 'test-drive-skill>=0.1.0,<0.2.0'. Version 0.40.0 is tested.\n",
    "skills/test-drive/SKILL.md": "Use >=0.1.0,<0.2.0. 0.40.0 is the version tested.\n",
}


class VersionCheckTests(unittest.TestCase):
    def layout(self, root: Path, **changes: str) -> Path:
        for name, text in FILES.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(changes.get(path.name, text), encoding="utf-8")
        return root

    def test_consistent_versions_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.layout(Path(directory))
            self.assertEqual(check_versions.problems(root, ["v0.1.0", "v0.1.1"]), [])

    def test_each_mismatch_is_reported(self):
        cases = {
            "not newer": ({}, ["v0.1.2"]),
            "uv.lock": ({"uv.lock": FILES["python/uv.lock"].replace("0.1.2", "0.1.1")}, []),
            "differ": ({"README.md": FILES["README.md"].replace("0.2.0", "0.3.0")}, []),
            "does not include": (
                {
                    name: text.replace("0.1.0,<0.2.0", "0.2.0,<0.3.0")
                    for name, text in (
                        ("README.md", FILES["README.md"]),
                        ("SKILL.md", FILES["skills/test-drive/SKILL.md"]),
                    )
                },
                [],
            ),
            "tested version": (
                {"SKILL.md": FILES["skills/test-drive/SKILL.md"].replace("0.40.0", "0.41.0")},
                [],
            ),
        }
        for expected, (changes, tags) in cases.items():
            with self.subTest(expected), tempfile.TemporaryDirectory() as directory:
                root = self.layout(Path(directory), **changes)
                found = check_versions.problems(root, tags)
                self.assertTrue(any(expected in problem for problem in found), found)


if __name__ == "__main__":
    unittest.main()
