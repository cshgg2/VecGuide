import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicApiBoundaryTests(unittest.TestCase):
    def test_api_boundary_doc_records_safe_and_api_commands(self):
        doc = (REPO_ROOT / "docs" / "api_boundary.md").read_text(encoding="utf-8")

        self.assertIn("Does Not Call An LLM API", doc)
        self.assertIn("May Call An LLM API", doc)
        self.assertIn("python3 main.py results-table", doc)
        self.assertIn("python3 main.py experiment --dry-run", doc)
        self.assertIn("python3 main.py experiment --collect-only --run-id <run_id>", doc)
        self.assertIn("python3 main.py optimize", doc)
        self.assertIn("python3 main.py pipeline", doc)

    def test_experiment_help_keeps_non_api_modes_visible(self):
        result = subprocess.run(
            [sys.executable, "main.py", "experiment", "--help"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        help_text = result.stdout

        self.assertIn("--collect-only", help_text)
        self.assertIn("不调用优化/API", help_text)
        self.assertIn("--dry-run", help_text)
        self.assertIn("只生成 manifest", help_text)
        self.assertIn("--cleanup-run-id", help_text)

    def test_public_docs_link_api_boundary(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        reproduction = (REPO_ROOT / "docs" / "reproduction.md").read_text(encoding="utf-8")

        self.assertIn("docs/api_boundary.md", readme)
        self.assertIn("api_boundary.md", docs_readme)
        self.assertIn("docs/api_boundary.md", reproduction)


if __name__ == "__main__":
    unittest.main()
