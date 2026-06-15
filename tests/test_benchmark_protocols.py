import unittest

from benchmark_protocols import resolve_benchmark_protocol
from correctness_verifier import run_performance_benchmark
from experiment_runner import build_benchmark_config


class BenchmarkProtocolTests(unittest.TestCase):
    def test_formal_protocol_defaults_are_main_table_eligible(self):
        config = resolve_benchmark_protocol("formal")

        self.assertEqual(config["protocol_name"], "formal")
        self.assertEqual(config["warmup_runs"], 3)
        self.assertEqual(config["timing_runs"], 10)
        self.assertEqual(config["batches"], 5)
        self.assertTrue(config["paper_main_table_eligible"])

    def test_screening_protocol_is_not_main_table_eligible(self):
        config = resolve_benchmark_protocol("screening")

        self.assertEqual(config["protocol_role"], "candidate_screening")
        self.assertEqual(config["warmup_runs"], 1)
        self.assertEqual(config["timing_runs"], 3)
        self.assertEqual(config["batches"], 3)
        self.assertFalse(config["paper_main_table_eligible"])

    def test_timeout_limited_protocol_is_explicitly_not_main_table_eligible(self):
        config = resolve_benchmark_protocol("timeout_limited")

        self.assertEqual(config["protocol_role"], "timeout_limited_evidence")
        self.assertFalse(config["paper_main_table_eligible"])

    def test_numeric_override_marks_named_protocol_as_modified(self):
        config = resolve_benchmark_protocol("formal", batches=1)

        self.assertEqual(config["protocol_name"], "formal_modified")
        self.assertEqual(config["base_protocol_name"], "formal")
        self.assertFalse(config["paper_main_table_eligible"])
        self.assertIn("Numeric overrides", config["warning"])

    def test_experiment_runner_default_benchmark_config_is_formal(self):
        config = build_benchmark_config(None, None, None)

        self.assertEqual(config["protocol_name"], "formal")
        self.assertEqual(config["batches"], 5)
        self.assertTrue(config["paper_main_table_eligible"])

    def test_performance_benchmark_accepts_protocol_metadata(self):
        config = resolve_benchmark_protocol("formal")
        config["timing_runs"] = 2

        result = run_performance_benchmark("", "", "s000", "/unused/clang", **config)

        self.assertFalse(result["success"])
        self.assertEqual(result["protocol_name"], "formal")
        self.assertEqual(result["protocol_role"], "formal_main_table")
        self.assertIn("timing_runs", result["error"])


if __name__ == "__main__":
    unittest.main()
