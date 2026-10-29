import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_drive.scenarios import check

# Legacy Russian headings are retained to check language-independent parsing.
INDEX = "# Магазин\n\n## Адрес\nhttps://shop.example\n\n## Доступ\nsecret-sentinel\n"
SCENARIO = """# Корзина

## Цель
Добавить товар.

## Начальное состояние
Корзина пуста.

## Шаги
1. Добавить товар.
2. Открыть корзину.

## Ожидаемый результат
В корзине один товар.
"""


class ScenarioTests(unittest.TestCase):
    def test_setext_titles_are_supported_without_counting_code_fences_as_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.md").write_text(
                "Магазин\n=======\n\nAddress: https://shop.example\n", encoding="utf-8"
            )
            (root / "cart.md").write_text(
                "Корзина\n=======\n\nAdd an item; one item appears.\n", encoding="utf-8"
            )
            result = check(root)
            self.assertEqual(result["site"]["name"], "Магазин")
            self.assertEqual(result["scenarios"][0]["name"], "Корзина")
            self.assertFalse(result["site"]["errors"])
            self.assertFalse(result["scenarios"][0]["errors"])

            (root / "cart.md").write_text(
                "Корзина\n=======\n\n```\nExample\n=======\n```\n", encoding="utf-8"
            )
            errors = check(root)["scenarios"][0]["errors"]
            self.assertTrue(any("no content" in error for error in errors))

    def test_folder_and_single_file_share_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.md").write_text(INDEX, encoding="utf-8")
            (root / "cart.md").write_text(SCENARIO, encoding="utf-8")
            (root / "search.md").write_text(
                SCENARIO.replace("# Корзина", "# Поиск"), encoding="utf-8"
            )
            folder = check(root)
            single = check(root / "search.md")
            self.assertEqual(folder["site"]["name"], "Магазин")
            self.assertEqual([case["name"] for case in folder["scenarios"]], ["Корзина", "Поиск"])
            self.assertEqual([case["name"] for case in single["scenarios"]], ["Поиск"])
            self.assertFalse(folder["site"]["errors"])
            self.assertTrue(all(not case["errors"] for case in folder["scenarios"]))

    def test_invalid_scenario_does_not_hide_valid_scenario_or_expose_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.md").write_text(INDEX, encoding="utf-8")
            (root / "good.md").write_text(SCENARIO, encoding="utf-8")
            (root / "bad.md").write_text("## Goal\nTest", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "test_drive", "check-scenarios", str(root)],
                env={**os.environ, "PYTHONIOENCODING": "ascii"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertNotIn("secret-sentinel", result.stdout)
            cases = {case["name"]: case for case in json.loads(result.stdout)["scenarios"]}
            self.assertFalse(cases["Корзина"]["errors"])
            self.assertEqual(json.loads(result.stdout)["validation"], "structure_only")
            self.assertTrue(cases[""]["errors"])

    def test_headings_inside_code_fences_do_not_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.md").write_text(INDEX, encoding="utf-8")
            scenario = "```markdown\n# This is an example, not a scenario title\n```\nText"
            (root / "cart.md").write_text(scenario, encoding="utf-8")
            errors = check(root)["scenarios"][0]["errors"]
            self.assertTrue(any("title is missing" in error for error in errors))

    def test_code_example_alone_is_not_scenario_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.md").write_text(INDEX, encoding="utf-8")
            scenario = "# Scenario\n\n```\n1. Example, not scenario content.\n```"
            (root / "cart.md").write_text(scenario, encoding="utf-8")
            errors = check(root)["scenarios"][0]["errors"]
            self.assertTrue(any("no content" in error for error in errors))

    def test_multilingual_headings_do_not_change_structural_validation(self):
        translations = [
            (
                "# Shop\n## Address\nhttps://shop.example",
                "# Basket\n## Goal\nAdd item\n## Steps\n1. Add item\n## Acceptance criteria\n- One item is visible",
            ),
            (
                "# 商店\n## 地址\nhttps://shop.example",
                "# 购物车\n## 目标\n加入商品\n## 步骤\n1. 加入商品\n## 验收标准\n- 显示一个商品",
            ),
            (
                "# متجر\n## العنوان\nhttps://shop.example",
                "# السلة\n## الهدف\nإضافة منتج\n## الخطوات\n1. أضف منتجًا\n## معايير القبول\n- يظهر منتج واحد",
            ),
        ]
        for index, scenario in translations:
            with self.subTest(index=index), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "index.md").write_text(index, encoding="utf-8")
                (root / "cart.md").write_text(scenario, encoding="utf-8")
                result = check(root)
                self.assertEqual(result["validation"], "structure_only")
                self.assertFalse(result["site"]["errors"])
                self.assertFalse(result["scenarios"][0]["errors"])

    def test_missing_index_blocks_site(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "cart.md").write_text(SCENARIO, encoding="utf-8")
            result = check(root)
            self.assertTrue(result["site"]["errors"])
            self.assertFalse(result["scenarios"][0]["errors"])

    def test_backtick_line_with_backticks_in_its_info_string_is_not_a_fence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.md").write_text(INDEX, encoding="utf-8")
            (root / "install.md").write_text(
                "# Install\n\n```npm i```\n\nCriterion: shows ok\n", encoding="utf-8"
            )
            self.assertFalse(check(root)["scenarios"][0]["errors"])

            (root / "install.md").write_text(
                "# Install\n\n```npm i```\n\n# Other\n\nText\n", encoding="utf-8"
            )
            errors = check(root)["scenarios"][0]["errors"]
            self.assertTrue(any("multiple top-level headings" in error for error in errors))

            # A tab indent makes an indented code block, not a fence that hides the rest.
            (root / "install.md").write_text("# Install\n\n\t```\n\nText\n", encoding="utf-8")
            self.assertFalse(check(root)["scenarios"][0]["errors"])

    def test_heading_text_follows_commonmark_closing_sequences(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.md").write_text(INDEX, encoding="utf-8")
            for heading, name in (
                ("# Learn C#", "Learn C#"),
                ("# Title ##", "Title"),
                ("#\tTitle\t#", "Title"),
                ("# foo \\#", "foo \\#"),
                ("# ### b", "### b"),
            ):
                (root / "case.md").write_text(f"{heading}\n\nText\n", encoding="utf-8")
                result = check(root)["scenarios"][0]
                self.assertEqual(result["name"], name, heading)
                self.assertFalse(result["errors"], heading)
            for heading in ("# #", "#"):
                (root / "case.md").write_text(f"{heading}\n\nText\n", encoding="utf-8")
                errors = check(root)["scenarios"][0]["errors"]
                self.assertTrue(any("title is missing" in error for error in errors), heading)


if __name__ == "__main__":
    unittest.main()
