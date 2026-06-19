import csv
import json
import tempfile
import unittest
from pathlib import Path

from paper_table_builder import build_and_write_tables, collect_result_rows


def write_rows(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class PaperTableBuilderTests(unittest.TestCase):
    def test_enriches_legacy_rows_with_protocol_and_blocker_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            problem_map = {
                "s115": {
                    "severity": "medium",
                    "not_vectorized_count": 1,
                    "problems": [
                        {
                            "reason": (
                                "unsafe dependent memory operations in loop. "
                                "Use #pragma loop distribute(enable)"
                            )
                        }
                    ],
                }
            }
            problem_map_file = root / "problem_map.json"
            problem_map_file.write_text(json.dumps(problem_map), encoding="utf-8")

            run_dir = root / "run"
            write_rows(
                run_dir / "paper_results.csv",
                [
                    {
                        "run_id": "legacy_run",
                        "strategy": "ours_full",
                        "function": "s115",
                        "severity": "medium",
                        "problem_count": "1",
                        "status": "success",
                        "correctness_overall": "True",
                        "analysis_vectorized": "True",
                        "analysis_vectorized_count": "1",
                        "analysis_missed_count": "0",
                        "benchmark_success": "True",
                        "benchmark_warmup_runs": "3",
                        "benchmark_timing_runs": "10",
                        "benchmark_batches": "5",
                        "speedup": "4.045",
                        "speedup_median": "4.030",
                        "observed_outcome": "vectorized_speedup",
                    }
                ],
            )

            rows = collect_result_rows([run_dir], json.loads(problem_map_file.read_text()))

            self.assertEqual(rows[0]["canonical_strategy"], "full_method")
            self.assertEqual(rows[0]["primary_blocker"], "dependency_unsafe")
            self.assertEqual(rows[0]["benchmark_protocol"], "formal")
            self.assertTrue(rows[0]["main_table_result_usable"])

    def test_fills_problem_metadata_when_result_row_omits_it(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            problem_map = {
                "s1232": {
                    "severity": "low",
                    "not_vectorized_count": 0,
                    "problems": [],
                }
            }
            run_dir = root / "run"
            write_rows(
                run_dir / "paper_results.csv",
                [
                    {
                        "run_id": "metadata_gap",
                        "strategy": "full_method",
                        "function": "s1232",
                        "status": "success",
                        "correctness_overall": "True",
                        "analysis_vectorized": "True",
                        "analysis_vectorized_count": "1",
                        "analysis_missed_count": "0",
                        "benchmark_success": "True",
                        "benchmark_warmup_runs": "3",
                        "benchmark_timing_runs": "10",
                        "benchmark_batches": "5",
                        "speedup": "24.866",
                    }
                ],
            )

            rows = collect_result_rows([run_dir], problem_map)

            self.assertEqual(rows[0]["severity"], "low")
            self.assertEqual(rows[0]["problem_count"], "0")
            self.assertEqual(rows[0]["primary_blocker"], "unknown_or_already_vectorized")

    def test_builds_all_and_main_tables_with_nonformal_rows_filtered(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            problem_map_file = root / "problem_map.json"
            problem_map_file.write_text(
                json.dumps(
                    {
                        "s235": {
                            "severity": "medium",
                            "not_vectorized_count": 1,
                            "problems": [
                                {"reason": "value that could not be identified as reduction"}
                            ],
                        }
                    }
                ),
                encoding="utf-8",
            )
            run_dir = root / "run"
            write_rows(
                run_dir / "paper_results.csv",
                [
                    {
                        "run_id": "screening_run",
                        "strategy": "full_method",
                        "function": "s235",
                        "severity": "medium",
                        "status": "success",
                        "correctness_overall": "True",
                        "analysis_vectorized": "True",
                        "analysis_vectorized_count": "2",
                        "analysis_missed_count": "0",
                        "benchmark_success": "True",
                        "benchmark_protocol": "screening",
                        "benchmark_protocol_role": "candidate_screening",
                        "paper_main_table_eligible": "False",
                        "benchmark_warmup_runs": "1",
                        "benchmark_timing_runs": "3",
                        "benchmark_batches": "3",
                        "speedup": "21.752",
                        "observed_outcome": "vectorized_speedup",
                    }
                ],
            )
            output_dir = root / "tables"

            result = build_and_write_tables(
                run_dirs=[run_dir],
                problem_map_file=problem_map_file,
                output_dir=output_dir,
                strategies=["full_method", "strong_plain"],
            )

            self.assertEqual(result["summary"]["total_long_rows"], 1)
            self.assertEqual(result["summary"]["total_main_table_wide_rows"], 0)
            all_csv = (output_dir / "result_table_wide.csv").read_text(encoding="utf-8")
            main_csv = (output_dir / "result_table_main_wide.csv").read_text(encoding="utf-8")
            self.assertIn("s235", all_csv)
            self.assertNotIn("s235", main_csv)

    def test_supplemental_rows_are_merged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            problem_map_file = root / "problem_map.json"
            problem_map_file.write_text("{}", encoding="utf-8")
            run_dir = root / "run"
            (run_dir).mkdir(parents=True)
            (run_dir / "paper_results.csv").write_text("run_id,strategy,function\n", encoding="utf-8")
            supplemental_file = root / "supplemental.csv"
            write_rows(
                supplemental_file,
                [
                    {
                        "run_id": "manual_probe",
                        "strategy": "full_method",
                        "function": "s999",
                        "correctness_overall": "True",
                        "analysis_vectorized_count": "1",
                        "analysis_missed_count": "0",
                        "benchmark_success": "True",
                        "benchmark_protocol": "timeout_limited",
                        "benchmark_protocol_role": "timeout_limited_evidence",
                        "paper_main_table_eligible": "False",
                        "benchmark_warmup_runs": "1",
                        "benchmark_timing_runs": "3",
                        "benchmark_batches": "3",
                        "speedup": "2.0",
                    }
                ],
            )

            result = build_and_write_tables(
                run_dirs=[run_dir],
                problem_map_file=problem_map_file,
                output_dir=root / "tables",
                strategies=["full_method"],
                supplemental_row_files=[supplemental_file],
            )

            self.assertEqual(result["summary"]["total_long_rows"], 1)
            self.assertEqual(result["summary"]["total_main_table_wide_rows"], 0)


if __name__ == "__main__":
    unittest.main()
