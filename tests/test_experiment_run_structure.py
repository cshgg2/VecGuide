from contextlib import redirect_stdout
from io import StringIO
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmark_protocols import resolve_benchmark_protocol
from experiment_config import get_experiment_strategy
from experiment_runner import (
    PAPER_ROW_FIELDS,
    build_artifact_index_payload,
    build_strategy_config_payload,
    collect_existing_run,
    initialize_run_directory_contract,
    write_run_prompt_snapshot_index,
)


class ExperimentRunStructureTests(unittest.TestCase):
    def test_strategy_config_payload_freezes_publication_metadata(self):
        strategies = [
            get_experiment_strategy("strong_plain"),
            get_experiment_strategy("full_method"),
        ]

        payload = build_strategy_config_payload("unit_run", strategies)

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["run_id"], "unit_run")
        by_name = {item["name"]: item for item in payload["strategies"]}
        self.assertEqual(by_name["strong_plain"]["prompt_version"], "strong_plain_v1_20260601")
        self.assertEqual(by_name["full_method"]["publication_name"], "full_method")
        self.assertTrue(by_name["full_method"]["performance_guard"]["enabled"])

    def test_run_directory_contract_creates_expected_scaffold(self):
        strategies = [
            get_experiment_strategy("origin"),
            get_experiment_strategy("diagnostic_only"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            strategy_root = run_dir / "strategies"
            initialize_run_directory_contract(run_dir, strategy_root, strategies)

            self.assertTrue((run_dir / "shared").is_dir())
            self.assertTrue((run_dir / "prompt_snapshot").is_dir())
            self.assertTrue((run_dir / "raw_logs" / "README.md").is_file())
            self.assertTrue((run_dir / "raw_logs" / "external_log_path.txt").is_file())
            self.assertTrue((strategy_root / "origin" / "prompt_snapshot").is_dir())
            self.assertTrue((strategy_root / "diagnostic_only" / "reports").is_dir())

    def test_run_prompt_snapshot_index_summarizes_strategy_indexes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            strategy_snapshot_dir = run_dir / "strategies" / "case_card_only" / "prompt_snapshot"
            strategy_snapshot_dir.mkdir(parents=True)
            strategy_index = {
                "snapshots": [
                    {
                        "function": "s172",
                        "selected_case_card_ids": ["runtime_stride_simple_multiversion"],
                    },
                    {
                        "function": "s278",
                        "selected_case_card_ids": ["goto_if_else_structuring"],
                    },
                ]
            }
            (strategy_snapshot_dir / "index.json").write_text(
                json.dumps(strategy_index),
                encoding="utf-8",
            )

            index_file = write_run_prompt_snapshot_index(
                run_dir=run_dir,
                run_id="unit_run",
                strategy_results=[
                    {
                        "strategy": "case_card_only",
                        "prompt_snapshot_dir": str(strategy_snapshot_dir),
                    }
                ],
            )

            payload = json.loads(index_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], "unit_run")
            self.assertEqual(payload["strategies"][0]["snapshot_count"], 2)
            self.assertIn(
                "runtime_stride_simple_multiversion",
                payload["strategies"][0]["selected_case_card_ids"],
            )

    def test_artifact_index_payload_lists_fixed_files_and_strategy_artifacts(self):
        strategies = [get_experiment_strategy("full_method")]

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            strategy_root = run_dir / "strategies"
            initialize_run_directory_contract(run_dir, strategy_root, strategies)
            (run_dir / "manifest.json").write_text("{}", encoding="utf-8")
            (run_dir / "strategy_config.json").write_text("{}", encoding="utf-8")
            (run_dir / "summary.json").write_text("{}", encoding="utf-8")
            (run_dir / "prompt_snapshot" / "index.json").write_text("{}", encoding="utf-8")

            state_file = strategy_root / "full_method" / "optimization_state.json"
            state_file.write_text("{}", encoding="utf-8")

            payload = build_artifact_index_payload(
                run_id="unit_run",
                run_dir=run_dir,
                strategies=strategies,
                strategy_results=[
                    {
                        "strategy": "full_method",
                        "state_file": str(state_file),
                        "prompt_snapshot_dir": str(strategy_root / "full_method" / "prompt_snapshot"),
                    }
                ],
                dry_run=False,
            )

            self.assertTrue(payload["fixed_files"]["manifest"]["exists"])
            self.assertTrue(payload["directories"]["raw_logs"]["exists"])
            self.assertEqual(payload["strategies"][0]["strategy"], "full_method")
            self.assertTrue(payload["strategies"][0]["state_file"]["exists"])

    def test_paper_results_fields_include_benchmark_protocol_metadata(self):
        self.assertIn("benchmark_protocol", PAPER_ROW_FIELDS)
        self.assertIn("benchmark_protocol_role", PAPER_ROW_FIELDS)
        self.assertIn("paper_main_table_eligible", PAPER_ROW_FIELDS)

    def test_collect_only_recovers_existing_strategy_outputs_without_rerun(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            run_dir = repo_root / "experiments" / "runs" / "unit_run"
            strategy_dir = run_dir / "strategies" / "strong_plain"
            strategy_dir.mkdir(parents=True)
            (run_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "run_id": "unit_run",
                        "functions": ["s278"],
                        "benchmark_config": resolve_benchmark_protocol("formal"),
                        "shared_problem_map": {"path": None},
                        "strategies": [{"name": "strong_plain"}],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "strategy_config.json").write_text(
                json.dumps({"strategies": [{"name": "strong_plain"}]}),
                encoding="utf-8",
            )
            (strategy_dir / "summary.json").write_text("{}", encoding="utf-8")
            (strategy_dir / "optimization_state.json").write_text("{}", encoding="utf-8")

            def fake_collect(**kwargs):
                result = dict(kwargs["strategy_result"])
                result["metrics"] = {"benchmark_success_count": 1}
                return result, [
                    {
                        "run_id": "unit_run",
                        "strategy": kwargs["strategy"]["name"],
                        "function": "s278",
                        "status": "success",
                        "correctness_overall": True,
                        "benchmark_success": True,
                        "speedup": 1.25,
                    }
                ]

            with (
                patch("experiment_runner.collect_strategy_artifacts", side_effect=fake_collect) as collect_mock,
                patch("experiment_runner.run_strategy") as run_strategy_mock,
            ):
                with redirect_stdout(StringIO()):
                    exit_code = collect_existing_run(
                        repo_root=repo_root,
                        run_id="unit_run",
                        clang_path="/unused/clang",
                        fallback_benchmark_config=resolve_benchmark_protocol("formal"),
                    )

            self.assertEqual(exit_code, 0)
            collect_mock.assert_called_once()
            run_strategy_mock.assert_not_called()
            self.assertTrue((run_dir / "paper_results.csv").is_file())
            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["functions"], ["s278"])


if __name__ == "__main__":
    unittest.main()
