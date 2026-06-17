import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicDocsEntrypointTests(unittest.TestCase):
    def test_readme_links_core_public_docs(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        for relative_path in [
            "PROJECT_INDEX.md",
            "docs/reproduction.md",
            "docs/api_boundary.md",
            "docs/current_status.md",
            "docs/evidence_map.md",
            "docs/experiment_protocol.md",
            "docs/engineering_boundaries.md",
            "docs/artifact_index.md",
        ]:
            self.assertIn(relative_path, readme)

    def test_project_index_links_core_public_docs(self):
        index = (REPO_ROOT / "PROJECT_INDEX.md").read_text(encoding="utf-8")

        for relative_path in [
            "README.md",
            "docs/reproduction.md",
            "docs/api_boundary.md",
            "docs/current_status.md",
            "docs/evidence_map.md",
            "docs/experiment_protocol.md",
            "docs/engineering_boundaries.md",
            "docs/artifact_index.md",
        ]:
            self.assertIn(relative_path, index)

    def test_public_test_command_mentions_api_boundary_test(self):
        for relative_path in [
            "README.md",
            "docs/current_status.md",
            "docs/reproduction.md",
            "docs/experiment_protocol.md",
        ]:
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("tests.test_public_api_boundary", text)


if __name__ == "__main__":
    unittest.main()
