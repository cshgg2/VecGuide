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
            "docs/submission_readiness.md",
            "docs/formal_repeat_plan.md",
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
            "docs/submission_readiness.md",
            "docs/formal_repeat_plan.md",
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

    def test_submission_readiness_links_protocol_and_api_boundary(self):
        doc = (REPO_ROOT / "docs" / "submission_readiness.md").read_text(encoding="utf-8")

        self.assertIn("docs/experiment_protocol.md", doc)
        self.assertIn("docs/api_boundary.md", doc)
        self.assertIn("s275", doc)
        self.assertIn("s258", doc)
        self.assertIn("Timeout-limited", doc)
        self.assertIn("cgo_s2710_control_flow_repeat1_20260611", doc)
        self.assertIn("cgo_s1232_triangular_loop_20260611", doc)

    def test_formal_repeat_plan_is_minimal_and_manual(self):
        doc = (REPO_ROOT / "docs" / "formal_repeat_plan.md").read_text(encoding="utf-8")

        self.assertIn("docs/api_boundary.md", doc)
        self.assertIn("python3 main.py experiment s275", doc)
        self.assertIn("python3 main.py experiment s258", doc)
        self.assertIn("cgo_repeat_s275_formal_<date>", doc)
        self.assertIn("cgo_repeat_s258_formal_<date>", doc)
        self.assertIn("python3 main.py results-table", doc)
        self.assertIn("cgo_repeat_s275_formal_clean_20260617", doc)


if __name__ == "__main__":
    unittest.main()
