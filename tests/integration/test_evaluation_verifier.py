import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


class BlockedEvaluationTests(unittest.TestCase):
    def test_blocked_criterion_is_checked_by_its_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = {
                "site": {"name": "Shop"},
                "scenarios": [
                    {
                        "name": "Private orders",
                        "status": "blocked",
                        "criteria": [
                            {
                                "expected": "The customer's private orders are visible.",
                                "status": "blocked",
                                "actual": "Stale observation",
                                "reason": "No credentials were supplied",
                            }
                        ],
                    }
                ],
            }
            source = root / "run.json"
            source.write_text(json.dumps(run), encoding="utf-8")
            report = subprocess.run(
                [sys.executable, "-m", "test_drive", "render-report", str(source)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(report.returncode, 0, report.stderr)
            verified = subprocess.run(
                [
                    sys.executable,
                    str(REPO / "tests" / "evals" / "verify.py"),
                    "missing-access",
                    str(root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)


@unittest.skipUnless(
    shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires ffmpeg and ffprobe"
)
class EvaluationContractTests(unittest.TestCase):
    def test_verifier_checks_results_and_real_recording(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "report"
            root.mkdir()
            shutil.copyfile(REPO / "tests" / "fixtures" / "recording.webm", root / "run.webm")
            run = {
                "site": {"name": "Shop"},
                "scenarios": [
                    {
                        "name": "Discount",
                        "status": "failed",
                        "video": "run.webm",
                        "criteria": [
                            {
                                "expected": "Отображается сообщение `Code accepted`.",
                                "status": "passed",
                                "actual": "Code accepted",
                            },
                            {
                                "expected": "Итоговая цена составляет $10.80.",
                                "status": "failed",
                                "actual": "Total: $12.00",
                            },
                        ],
                    }
                ],
            }
            source = root / "run.json"
            source.write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")
            report = subprocess.run(
                [sys.executable, "-m", "test_drive", "render-report", str(source)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(report.returncode, 0, report.stderr)
            command = [
                sys.executable,
                str(REPO / "tests" / "evals" / "verify.py"),
                "saved-discount-ru",
                str(root),
            ]
            passed = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(passed.returncode, 0, passed.stderr)

            run["scenarios"][0]["criteria"][0]["status"] = "failed"
            run["scenarios"][0]["criteria"][1]["status"] = "passed"
            source.write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")
            stale_report = subprocess.run(
                [sys.executable, "-m", "test_drive", "render-report", str(source)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(stale_report.returncode, 0, stale_report.stderr)
            run["scenarios"][0]["criteria"][0]["status"] = "passed"
            run["scenarios"][0]["criteria"][1]["status"] = "failed"
            source.write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")
            mismatched = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(mismatched.returncode, 0)
            restored = subprocess.run(
                [sys.executable, "-m", "test_drive", "render-report", str(source)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(restored.returncode, 0, restored.stderr)

            segment = root.parent / "outside.ts"
            encoded = subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-nostdin",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=32x32:r=10:d=3",
                    "-c:v",
                    "mpeg2video",
                    "-f",
                    "mpegts",
                    str(segment),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(encoded.returncode, 0, encoded.stderr)
            (root / "playlist.m3u8").write_text(
                f"#EXTM3U\n#EXT-X-TARGETDURATION:3\n#EXTINF:3.0,\n{segment.as_uri()}\n#EXT-X-ENDLIST\n",
                encoding="utf-8",
            )
            old_time = time.time_ns() - 172800 * 1_000_000_000
            os.utime(segment, ns=(old_time, old_time))
            initial_access = segment.stat().st_atime_ns
            segment.read_bytes()
            # Some filesystems do not record access times.
            tracks_access = segment.stat().st_atime_ns > initial_access
            os.utime(segment, ns=(old_time, old_time))
            initial_access = segment.stat().st_atime_ns
            run["scenarios"][0]["video"] = "playlist.m3u8"
            source.write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")
            external = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(external.returncode, 0)
            self.assertIn("Recording has no readable video stream", external.stderr)
            if tracks_access:
                self.assertEqual(segment.stat().st_atime_ns, initial_access)
            run["scenarios"][0]["video"] = "run.webm"

            run["scenarios"][0]["criteria"][1]["status"] = "passed"
            source.write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")
            wrong = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(wrong.returncode, 0)

            run["scenarios"][0]["criteria"][1]["status"] = "failed"
            source.write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")
            (root / "run.webm").write_bytes(b"not a recording")
            corrupt = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(corrupt.returncode, 0)


if __name__ == "__main__":
    unittest.main()
