import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from test_drive.report import LABELS, LEGACY_RU_LABELS, render

VIDEO_FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "recording.webm"


class Page(HTMLParser):
    def __init__(self, document: str):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.content = []
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.content.append(data)


class ReportTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg"), "requires ffmpeg")
    def test_playlist_referencing_an_external_video_is_not_embedded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report"
            report.mkdir()
            segment = root / "outside.ts"
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
            (report / "playlist.m3u8").write_text(
                f"#EXTM3U\n#EXT-X-TARGETDURATION:3\n#EXTINF:3.0,\n{segment.as_uri()}\n#EXT-X-ENDLIST\n",
                encoding="utf-8",
            )
            run = {
                "site": {"name": "Shop"},
                "scenarios": [
                    {
                        "name": "Cart",
                        "status": "passed",
                        "expected": "Success",
                        "actual": "Success",
                        "video": "playlist.m3u8",
                    }
                ],
            }
            page = Page(render(run, report.resolve()))
            self.assertFalse(any(tag == "video" for tag, _ in page.tags))

    def test_corrupt_recording_is_not_presented_as_video(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "bad.webm").write_bytes(b"not a recording")
            run = {
                "site": {"name": "Shop"},
                "scenarios": [
                    {
                        "name": "Cart",
                        "status": "passed",
                        "expected": "Success",
                        "actual": "Success",
                        "video": "bad.webm",
                        "steps": [{"name": "Submit", "at": 1}],
                    }
                ],
            }
            page = Page(render(run, root))
            self.assertFalse(any(tag == "video" for tag, _ in page.tags))
            self.assertFalse(any(attrs.get("class") == "seek" for _, attrs in page.tags))
            self.assertIn("Recording unavailable", " ".join(page.content))

    def test_recording_is_unverified_when_ffmpeg_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(VIDEO_FIXTURE, root / "recording.webm")
            (root / "run.json").write_text(
                json.dumps(
                    {
                        "site": {"name": "Shop"},
                        "scenarios": [
                            {
                                "name": "Cart",
                                "status": "passed",
                                "expected": "Success",
                                "actual": "Success",
                                "video": "recording.webm",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PATH"] = str(root)
            result = subprocess.run(
                [sys.executable, "-m", "test_drive", "render-report", str(root / "run.json")],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            page = Page((root / "report.html").read_text(encoding="utf-8"))
            self.assertFalse(any(tag == "video" for tag, _ in page.tags))
            self.assertIn("could not be verified", " ".join(page.content))

    def test_multiple_criteria_keep_individual_results_and_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            shutil.copyfile(VIDEO_FIXTURE, root / "run.webm")
            (root / "result.png").write_bytes(b"image")
            run = {
                "site": {"name": "Shop"},
                "scenarios": [
                    {
                        "name": "Cart",
                        "status": "failed",
                        "video": "run.webm",
                        "video_started_at": 10,
                        "criteria": [
                            {
                                "expected": "One item",
                                "status": "passed",
                                "actual": "One item shown",
                                "recorded_at": 12.5,
                            },
                            {
                                "expected": "Total is 100",
                                "status": "failed",
                                "actual": "Total is <200>",
                                "screenshot": "result.png",
                            },
                            {
                                "expected": "Confirmation arrives",
                                "status": "blocked",
                                "reason": "No access",
                            },
                        ],
                    }
                ],
            }
            page = Page(render(run, root))
            content = " ".join(page.content)
            for expected in (
                "One item",
                "One item shown",
                "Total is <200>",
                "Confirmation arrives",
                "No access",
            ):
                self.assertIn(expected, content)
            expected_times = ["2.500"] if shutil.which("ffmpeg") else []
            self.assertEqual(
                [
                    a["data-time"]
                    for t, a in page.tags
                    if t == "button" and a.get("class") == "seek"
                ],
                expected_times,
            )
            self.assertTrue(any(t == "a" and a.get("href") == "result.png" for t, a in page.tags))
            self.assertEqual(sum(t == "script" for t, _ in page.tags), 1)

    def test_scenario_status_must_match_all_criterion_results(self):
        combinations = [
            (["passed", "passed"], "passed"),
            (["passed", "blocked"], "blocked"),
            (["not_run", "not_run"], "not_run"),
            (["failed", "blocked"], "failed"),
            (["passed", "not_run"], "blocked"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for statuses, overall in combinations:
                with self.subTest(statuses=statuses):
                    criteria = [
                        {
                            "expected": f"Criterion {i}",
                            "status": status,
                            ("actual" if status in ("passed", "failed") else "reason"): "Result",
                        }
                        for i, status in enumerate(statuses)
                    ]
                    scenario = {"name": "Test", "status": overall, "criteria": criteria}
                    run = {"site": {"name": "Shop"}, "scenarios": [scenario]}
                    render(run, Path(directory).resolve())
                    scenario["status"] = "passed" if overall != "passed" else "failed"
                    with self.assertRaisesRegex(ValueError, "status does not match its criteria"):
                        render(run, Path(directory).resolve())

    def test_report_labels_and_language_are_localizable_and_escaped(self):
        with tempfile.TemporaryDirectory() as directory:
            labels = {key: f"Translation {key}" for key in LABELS}
            labels["video"] = "Video <script>bad()</script>"
            labels["scope"] = "Scope <img src=x onerror=bad()>"
            run = {
                "site": {"name": "Shop"},
                "language": "ar",
                "direction": "rtl",
                "labels": labels,
                "scope": "Cart",
                "scenarios": [{"name": "Cart", "status": "not_run", "reason": "Not started"}],
            }
            page = Page(render(run, Path(directory).resolve()))
            self.assertTrue(
                any(
                    tag == "html" and attrs.get("lang") == "ar" and attrs.get("dir") == "rtl"
                    for tag, attrs in page.tags
                )
            )
            self.assertIn("Video <script>bad()</script>", " ".join(page.content))
            self.assertIn("Scope <img src=x onerror=bad()>", " ".join(page.content))
            self.assertIn("Translation not_run", " ".join(page.content))
            self.assertEqual(sum(tag == "script" for tag, _ in page.tags), 1)
            self.assertFalse(any(tag == "img" for tag, _ in page.tags))
            run["labels"] = {"report": "Test report"}
            with self.assertRaisesRegex(ValueError, "translations for all labels"):
                render(run, Path(directory).resolve())

    def test_default_english_and_legacy_russian_report(self):
        with tempfile.TemporaryDirectory() as directory:
            run = {
                "site": {"name": "Shop"},
                "scenarios": [
                    {
                        "name": "Cart",
                        "status": "passed",
                        "expected": "One item",
                        "actual": "One item",
                    }
                ],
            }
            root = Path(directory).resolve()
            english = Page(render(run, root))
            self.assertTrue(
                any(tag == "html" and attrs.get("lang") == "en" for tag, attrs in english.tags)
            )
            self.assertIn("Passed", " ".join(english.content))
            # Existing run.json files could select Russian without providing labels.
            run["language"] = "ru"
            russian = Page(render(run, root))
            self.assertTrue(
                any(tag == "html" and attrs.get("lang") == "ru" for tag, attrs in russian.tags)
            )
            self.assertIn("Пройден", " ".join(russian.content))
            self.assertEqual(LABELS.keys(), LEGACY_RU_LABELS.keys())
            run["labels"] = {"report": "Custom"}
            self.assertIn("Пройден", " ".join(Page(render(run, root)).content))

    def test_report_preserves_results_and_escapes_untrusted_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "videos").mkdir()
            shutil.copyfile(VIDEO_FIXTURE, root / "videos" / "test #1.webm")
            # Preserve arbitrary Unicode and untrusted text in report data.
            run = {
                "site": {"name": "Магазин $content", "url": "https://shop.example"},
                "scope": "Поиск и корзина",
                "assumptions": "Тестовый аккаунт <script>bad()</script>",
                "limitations": "Оплата не проверялась",
                "scenarios": [
                    {
                        "name": "Поиск <script>bad()</script>",
                        "status": "passed",
                        "expected": "Найден товар",
                        "actual": "Найден товар",
                        "video": "videos/test #1.webm",
                        "video_started_at": 1234.5,
                        "steps": [
                            {"name": "Найти товар", "status": "passed", "recorded_at": 1236.9}
                        ],
                    },
                    {
                        "name": "Корзина",
                        "status": "failed",
                        "expected": "Открыта форма",
                        "actual": "Осталась корзина",
                        "reproduction": ["Нажать <Оформить>"],
                    },
                    {"name": "Оплата", "status": "blocked", "reason": "Нет тестового доступа"},
                ],
            }
            page = Page(render(run, root))
            visible_text = " ".join(page.content)
            self.assertIn("Магазин $content", visible_text)
            self.assertIn("Поиск <script>bad()</script>", visible_text)
            self.assertIn("Нажать <Оформить>", visible_text)
            self.assertIn("Нет тестового доступа", visible_text)
            self.assertIn("Поиск и корзина", visible_text)
            self.assertIn("Тестовый аккаунт <script>bad()</script>", visible_text)
            self.assertIn("Оплата не проверялась", visible_text)
            self.assertEqual(sum(tag == "script" for tag, _ in page.tags), 1)
            self.assertEqual(
                [attrs["src"] for tag, attrs in page.tags if tag == "video"],
                ["videos/test%20%231.webm"] if shutil.which("ffmpeg") else [],
            )
            self.assertEqual(
                [
                    attrs["data-time"]
                    for tag, attrs in page.tags
                    if tag == "button" and attrs.get("class") == "seek"
                ],
                ["2.400"] if shutil.which("ffmpeg") else [],
            )
            self.assertEqual(
                [attrs["href"] for tag, attrs in page.tags if "data-default" in attrs],
                ["#scenario-2"],
            )

    def test_missing_empty_and_external_evidence_do_not_become_links(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory).resolve()
            (root / "empty.webm").write_bytes(b"")
            secret = Path(outside) / "secret.png"
            secret.write_bytes(b"not an attachment")
            try:
                (root / "escape.png").symlink_to(secret)
                screenshot = "escape.png"
            except OSError:
                screenshot = str(secret)
            run = {
                "site": {"name": "Shop"},
                "scenarios": [
                    {
                        "name": "Test",
                        "status": "failed",
                        "expected": "Success",
                        "actual": "Error",
                        "video": "empty.webm",
                        "video_reason": "Recording <error>",
                        "screenshot": screenshot,
                        "steps": [{"name": "Submit", "at": 1}],
                    }
                ],
            }
            page = Page(render(run, root))
            self.assertFalse(any(tag in {"video", "img"} for tag, _ in page.tags))
            self.assertFalse(any(attrs.get("class") == "seek" for _, attrs in page.tags))
            self.assertIn("Recording unavailable", " ".join(page.content))
            self.assertIn("Recording <error>", " ".join(page.content))
            self.assertIn("Screenshot unavailable", " ".join(page.content))

    def test_invalid_results_keep_previous_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "report.html").write_text("previous report", encoding="utf-8")
            (root / "run.json").write_text(
                json.dumps(
                    {
                        "site": {"name": "Shop"},
                        "scenarios": [
                            {"name": "Login", "status": "passed", "expected": "Signed in"}
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
            self.assertEqual(result.returncode, 2)
            self.assertIn("expected and actual", result.stderr)
            self.assertEqual((root / "report.html").read_text(encoding="utf-8"), "previous report")

    def test_input_named_report_html_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "report.html"
            contents = json.dumps({"site": {"name": "Shop"}, "scenarios": []})
            source.write_text(contents, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "test_drive", "render-report", str(source)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(source.read_text(encoding="utf-8"), contents)

    def test_existing_temporary_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "report.html.tmp"
            existing.write_text("user data", encoding="utf-8")
            source = root / "run.json"
            source.write_text(
                json.dumps({"site": {"name": "Shop"}, "scenarios": []}), encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, "-m", "test_drive", "render-report", str(source)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(existing.read_text(encoding="utf-8"), "user data")
            self.assertIn("Shop", (root / "report.html").read_text(encoding="utf-8"))

    def test_existing_temporary_symlink_does_not_modify_its_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "valuable.txt"
            target.write_text("user data", encoding="utf-8")
            link = root / "report.html.tmp"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable")
            source = root / "run.json"
            source.write_text(
                json.dumps({"site": {"name": "Shop"}, "scenarios": []}), encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, "-m", "test_drive", "render-report", str(source)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "user data")
            self.assertTrue(link.is_symlink())
            self.assertFalse((root / "report.html").is_symlink())

    def test_address_with_credentials_never_reaches_report_or_log(self):
        urls = (
            "https://shop.example/?token=secret-sentinel",
            "https://user:secret-sentinel@shop.example/",
            "https://shop.example/#access_token=secret-sentinel",
        )
        for url in urls:
            with (
                self.subTest(url_kind=url.split("secret-sentinel")[0]),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                source = root / "run.json"
                source.write_text(
                    json.dumps({"site": {"name": "Shop", "url": url}, "scenarios": []}),
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [sys.executable, "-m", "test_drive", "render-report", str(source)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("secret-sentinel", result.stdout + result.stderr)
                self.assertFalse((root / "report.html").exists())
                self.assertIn("secret-sentinel", source.read_text(encoding="utf-8"))

    def test_sensitive_address_in_observation_is_not_written_to_report_or_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "run.json"
            source.write_text(
                json.dumps(
                    {
                        "site": {"name": "Shop", "url": "https://shop.example/"},
                        "scenarios": [
                            {
                                "name": "Login",
                                "status": "passed",
                                "expected": "Signed in",
                                "actual": "Opened https://shop.example/account?token=secret-sentinel",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-m", "test_drive", "render-report", str(source)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("secret-sentinel", result.stdout + result.stderr)
            self.assertFalse((root / "report.html").exists())

    def test_url_with_apostrophe_and_secret_query_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "run.json"
            source.write_text(
                json.dumps(
                    {
                        "site": {"name": "Shop"},
                        "scenarios": [
                            {
                                "name": "Login",
                                "status": "passed",
                                "expected": "Signed in",
                                "actual": "Opened https://shop.example/o'neil?token=secret-sentinel",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-m", "test_drive", "render-report", str(source)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("secret-sentinel", result.stdout + result.stderr)
            self.assertFalse((root / "report.html").exists())

    def test_addresses_in_criterion_observations_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            run = {
                "site": {"name": "Shop"},
                "scenarios": [
                    {
                        "name": "Login",
                        "status": "passed",
                        "criteria": [
                            {
                                "expected": "Signed in",
                                "status": "passed",
                                "actual": "Opened HTTPS://shop.example/account#token=secret",
                            }
                        ],
                    }
                ],
            }
            with self.assertRaisesRegex(ValueError, "Saved URLs"):
                render(run, Path(directory).resolve())
            run["scenarios"][0]["criteria"][0]["actual"] = "Opened https://shop.example/account."
            self.assertIn("https://shop.example/account.", render(run, Path(directory).resolve()))

    def test_invalid_step_times_are_rejected(self):
        for value in (-1, True, float("nan"), float("inf"), 10**1000):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                run = {
                    "site": {"name": "Shop"},
                    "scenarios": [
                        {
                            "name": "Test",
                            "status": "passed",
                            "expected": "Yes",
                            "actual": "Yes",
                            "steps": [{"name": "Step", "at": value}],
                        }
                    ],
                }
                with self.assertRaisesRegex(ValueError, "step or criterion time"):
                    render(run, Path(directory).resolve())

    def test_recorded_time_requires_a_matching_start(self):
        with tempfile.TemporaryDirectory() as directory:
            run = {
                "site": {"name": "Shop"},
                "scenarios": [
                    {
                        "name": "Test",
                        "status": "passed",
                        "expected": "Yes",
                        "actual": "Yes",
                        "steps": [{"name": "Step", "recorded_at": 3}],
                    }
                ],
            }
            with self.assertRaisesRegex(ValueError, "recording start"):
                render(run, Path(directory).resolve())


if __name__ == "__main__":
    unittest.main()
