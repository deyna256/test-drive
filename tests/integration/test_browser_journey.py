"""Opt-in integration test using the real local browser and recording tools."""

import functools
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


@unittest.skipUnless(
    os.environ.get("TEST_DRIVE_E2E") == "1", "set TEST_DRIVE_E2E=1 for real browser tests"
)
class BrowserIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [sys.executable, "-m", "test_drive", "agent-browser-path"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        cls.browser = result.stdout.strip()
        cls.socket_directory = tempfile.TemporaryDirectory(prefix="test-drive-sockets-")
        cls.addClassCleanup(cls.socket_directory.cleanup)
        cls.browser_env = os.environ.copy()
        cls.browser_env["AGENT_BROWSER_SOCKET_DIR"] = cls.socket_directory.name
        handler = functools.partial(QuietHandler, directory=str(REPO / "tests" / "evals" / "site"))
        try:
            cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        except PermissionError:
            cls.server = None
            cls.url = (REPO / "tests" / "evals" / "site" / "index.html").as_uri()
            cls.flags = ["--allow-file-access"]
        else:
            cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
            cls.thread.start()
            cls.url = f"http://127.0.0.1:{cls.server.server_port}/"
            cls.flags = []

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.shutdown()
            cls.server.server_close()
            cls.thread.join()

    def test_real_journey_recording_and_report(self):
        session = "td" + uuid.uuid4().hex[:8]

        def browser(*args, check=True):
            result = subprocess.run(
                [
                    self.browser,
                    "--session",
                    session,
                    "--namespace",
                    session,
                    *self.flags,
                    *map(str, args),
                ],
                env=self.browser_env,
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
            if check:
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            return result.stdout.strip()

        self.addCleanup(lambda: browser("close", check=False))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            browser("open", self.url)
            browser("record", "start", root / "run.webm", "--cursor")
            try:
                browser("type", "#search", "mug", "--delay", "50")
                browser("click", "#search-form button", "--human")
                browser("click", "#add", "--human")
                self.assertEqual(browser("get", "text", "#count"), "1")
                self.assertEqual(browser("get", "text", "#total"), "$12.00")
                browser("type", "#coupon", "SAVE10", "--delay", "50")
                browser("click", "#coupon-form button", "--human")
                self.assertEqual(browser("get", "text", "#coupon-status"), "Code accepted")
                self.assertEqual(browser("get", "text", "#total"), "$12.00")
                browser("screenshot", root / "result.png")
            finally:
                browser("record", "stop")

            (root / "run.json").write_text(
                json.dumps(
                    {
                        "site": {"name": "Test Drive Shop", "url": self.url},
                        "scenarios": [
                            {
                                "name": "Discount",
                                "status": "failed",
                                "video": "run.webm",
                                "screenshot": "result.png",
                                "criteria": [
                                    {
                                        "expected": "Code accepted",
                                        "status": "passed",
                                        "actual": "Code accepted",
                                    },
                                    {
                                        "expected": "Total is $10.80",
                                        "status": "failed",
                                        "actual": "Total is $12.00",
                                    },
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-m", "test_drive", "render-report", str(root / "run.json")],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = (root / "report.html").read_text(encoding="utf-8")
            self.assertIn("<video controls", report)
            self.assertIn("Total is $10.80", report)
            self.assertIn("Total is $12.00", report)
            self.assertGreater((root / "run.webm").stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
