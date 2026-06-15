import json
import os
import tempfile
import unittest
from pathlib import Path

from experiment_config import get_experiment_strategy
from optimizer_pipeline import write_prompt_snapshot
from prompts.knowledge_base import (
    CASE_CARD_FORMAT_VERSION,
    EXPERIMENT_CASE_CARD_SET_VERSION,
    build_case_card_audit_snapshot,
)
from prompts.templates import build_optimization_prompt, get_prompt_template_versions


def runtime_stride_diagnostics():
    return {
        "missed": ["loop not vectorized: could not determine number of loop iterations"],
        "vectorized": [],
        "structured_feedback": {
            "severity": "medium",
            "primary_categories": ["trip_count_bounds"],
            "pattern_family": "runtime_stride_simple",
            "compile_level": {"compilable": True},
            "vectorization_level": {
                "vectorized_count": 0,
                "missed_count": 1,
                "missed_categories": ["trip_count_bounds"],
                "dynamic_missed_reasons": [
                    "could not determine number of loop iterations",
                ],
            },
            "performance_level": {"anti_patterns": []},
            "code_facts": {"has_runtime_stride": True},
        },
    }


class PromptSnapshotTests(unittest.TestCase):
    def test_case_card_audit_snapshot_records_versions_and_selected_cards(self):
        diagnostics = runtime_stride_diagnostics()

        snapshot = build_case_card_audit_snapshot(
            diagnostics["structured_feedback"],
            limit=2,
        )

        self.assertEqual(snapshot["case_card_set_version"], EXPERIMENT_CASE_CARD_SET_VERSION)
        self.assertEqual(snapshot["case_card_format_version"], CASE_CARD_FORMAT_VERSION)
        self.assertGreaterEqual(snapshot["selected_count"], 1)
        self.assertEqual(snapshot["selected_cards"][0]["id"], "runtime_stride_simple_multiversion")
        self.assertIn("代表函数: s172", snapshot["formatted_text"])

    def test_write_prompt_snapshot_persists_exact_prompt_and_case_cards(self):
        diagnostics = runtime_stride_diagnostics()
        strategy = get_experiment_strategy("case_card_only")
        system_prompt, user_prompt = build_optimization_prompt(
            code="for (int i = n1 - 1; i < LEN_1D; i += n3) { a[i] += b[i]; }",
            func_name="s172",
            diagnostics=diagnostics,
            round_num=1,
            max_rounds=1,
            prompt_options=strategy["prompt_options"],
        )

        old_snapshot_dir = os.environ.get("PROMPT_SNAPSHOT_DIR")
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["PROMPT_SNAPSHOT_DIR"] = tmpdir
            try:
                snapshot_info = write_prompt_snapshot(
                    func_name="s172",
                    strategy_config=strategy,
                    round_num=1,
                    max_rounds=1,
                    prompt_kind="optimization",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    diagnostics=diagnostics,
                    previous_rounds=None,
                    prompt_options=strategy["prompt_options"],
                )
            finally:
                if old_snapshot_dir is None:
                    os.environ.pop("PROMPT_SNAPSHOT_DIR", None)
                else:
                    os.environ["PROMPT_SNAPSHOT_DIR"] = old_snapshot_dir

            self.assertIsNotNone(snapshot_info)
            json_path = Path(snapshot_info["json_file"])
            markdown_path = Path(snapshot_info["markdown_file"])
            case_card_path = Path(snapshot_info["case_card_file"])
            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertTrue(case_card_path.exists())

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            template_versions = get_prompt_template_versions()
            self.assertEqual(payload["prompt_version"], "case_card_only_v1_20260601")
            self.assertEqual(payload["system_prompt"], system_prompt)
            self.assertEqual(payload["user_prompt"], user_prompt)
            self.assertEqual(
                payload["user_prompt_template"]["version"],
                template_versions["optimization_user"],
            )
            self.assertTrue(payload["case_cards"]["included"])
            self.assertIn(
                "runtime_stride_simple_multiversion",
                snapshot_info["selected_case_card_ids"],
            )

            index_payload = json.loads((Path(tmpdir) / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(len(index_payload["snapshots"]), 1)
            self.assertEqual(index_payload["snapshots"][0]["function"], "s172")

    def test_write_prompt_snapshot_records_no_case_cards_for_strong_plain(self):
        diagnostics = runtime_stride_diagnostics()
        strategy = get_experiment_strategy("strong_plain")
        system_prompt, user_prompt = build_optimization_prompt(
            code="for (int i = n1 - 1; i < LEN_1D; i += n3) { a[i] += b[i]; }",
            func_name="s172",
            diagnostics=diagnostics,
            round_num=1,
            max_rounds=1,
            prompt_options=strategy["prompt_options"],
        )

        old_snapshot_dir = os.environ.get("PROMPT_SNAPSHOT_DIR")
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["PROMPT_SNAPSHOT_DIR"] = tmpdir
            try:
                snapshot_info = write_prompt_snapshot(
                    func_name="s172",
                    strategy_config=strategy,
                    round_num=1,
                    max_rounds=1,
                    prompt_kind="optimization",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    diagnostics=diagnostics,
                    previous_rounds=None,
                    prompt_options=strategy["prompt_options"],
                )
            finally:
                if old_snapshot_dir is None:
                    os.environ.pop("PROMPT_SNAPSHOT_DIR", None)
                else:
                    os.environ["PROMPT_SNAPSHOT_DIR"] = old_snapshot_dir

            payload = json.loads(Path(snapshot_info["json_file"]).read_text(encoding="utf-8"))
            self.assertFalse(payload["case_cards"]["included"])
            self.assertEqual(payload["case_cards"]["reason"], "include_knowledge_disabled")
            self.assertEqual(
                payload["system_prompt_template"]["version"],
                get_prompt_template_versions()["strong_plain_system"],
            )


if __name__ == "__main__":
    unittest.main()
