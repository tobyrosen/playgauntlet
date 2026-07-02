import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app = load_module("gauntlet_app_under_test", ROOT / "app.py")


class GauntletSmokeTests(unittest.TestCase):
    def test_versions_match(self):
        version = (ROOT / "version.txt").read_text(encoding="utf-8").strip()
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertEqual(version, "0.1.0")
        self.assertIn(f'version = "{version}"', pyproject)

    def test_item_bank_has_valid_core_shape(self):
        data = app.load_items()
        domain_ids = {domain["id"] for domain in data["exam"]["domains"]}

        self.assertGreater(len(data["items"]), 0)
        self.assertTrue(domain_ids)

        for item in data["items"]:
            self.assertIn(item["domain"], domain_ids)
            self.assertIn(item["format"], {"mcq", "spot", "recall", "explain"})
            self.assertTrue(item["id"])
            self.assertTrue(item["prompt"])
            self.assertTrue(item["topic_cluster"])

    def test_heuristic_grade_counts_rubric_hits(self):
        result = app.heuristic_grade(
            "Use isolated context to save token budget and avoid confusion.",
            ["isolated context", "token budget", "avoid confusion"],
            "Reference answer",
        )

        self.assertTrue(result["correct"])
        self.assertEqual(result["grader"], "heuristic")
        self.assertGreaterEqual(result["score"], 0.6)

    def test_heuristic_grade_rejects_empty_answer(self):
        result = app.heuristic_grade("", ["key point"], "Reference answer")

        self.assertFalse(result["correct"])
        self.assertEqual(result["verdict"], "missed")

    def test_token_auth_gate(self):
        old_token = app.TOKEN
        try:
            app.TOKEN = ""
            self.assertTrue(app.authed("/"))

            app.TOKEN = "secret"
            self.assertTrue(app.authed("/?t=secret"))
            self.assertFalse(app.authed("/"))
        finally:
            app.TOKEN = old_token


if __name__ == "__main__":
    unittest.main()
