import unittest

from experiment_config import (
    LEGACY_STRATEGY_NAME_MAP,
    PAPER_STRATEGY_NAMES,
    get_experiment_strategy,
    get_publication_strategy_definition,
    list_publication_strategy_definitions,
)


class ExperimentStrategyConfigTests(unittest.TestCase):
    def test_full_method_is_publication_name_for_legacy_ours_full(self):
        legacy = get_experiment_strategy("ours_full")
        canonical = get_experiment_strategy("full_method")

        self.assertEqual(legacy["publication_name"], "full_method")
        self.assertEqual(canonical["publication_name"], "full_method")
        self.assertTrue(canonical["performance_guard"]["enabled"])
        self.assertTrue(canonical["prompt_options"]["include_knowledge"])
        self.assertTrue(canonical["prompt_options"]["include_examples"])
        self.assertFalse(canonical["single_round"])

    def test_diagnostic_only_matches_legacy_llm_plain_role(self):
        legacy = get_experiment_strategy("llm_plain")
        diagnostic = get_experiment_strategy("diagnostic_only")

        self.assertEqual(legacy["publication_name"], "diagnostic_only")
        self.assertEqual(diagnostic["publication_name"], "diagnostic_only")
        self.assertTrue(diagnostic["prompt_options"]["include_diagnostics"])
        self.assertTrue(diagnostic["prompt_options"]["include_structured_feedback"])
        self.assertFalse(diagnostic["prompt_options"]["include_knowledge"])
        self.assertFalse(diagnostic["prompt_options"]["include_examples"])
        self.assertTrue(diagnostic["single_round"])

    def test_strong_plain_uses_strong_generic_prompt_without_method_signals(self):
        strategy = get_experiment_strategy("strong_plain")

        self.assertEqual(strategy["publication_name"], "strong_plain")
        self.assertEqual(strategy["implementation_status"], "ready")
        self.assertEqual(strategy["prompt_version"], "strong_plain_v1_20260601")
        self.assertEqual(strategy["prompt_options"]["system_prompt_profile"], "strong_plain")
        self.assertTrue(strategy["prompt_options"]["include_strong_baseline_guidance"])
        self.assertFalse(strategy["prompt_options"]["include_diagnostics"])
        self.assertFalse(strategy["prompt_options"]["include_structured_feedback"])
        self.assertFalse(strategy["prompt_options"]["include_semantic_hints"])
        self.assertFalse(strategy["prompt_options"]["include_knowledge"])
        self.assertFalse(strategy["prompt_options"]["include_examples"])

    def test_case_card_only_keeps_cards_but_removes_multiround(self):
        strategy = get_experiment_strategy("case_card_only")

        self.assertEqual(strategy["publication_name"], "case_card_only")
        self.assertTrue(strategy["prompt_options"]["include_diagnostics"])
        self.assertTrue(strategy["prompt_options"]["include_structured_feedback"])
        self.assertTrue(strategy["prompt_options"]["include_knowledge"])
        self.assertFalse(strategy["prompt_options"]["include_examples"])
        self.assertFalse(strategy["prompt_options"]["include_history"])
        self.assertTrue(strategy["single_round"])

    def test_optimizer_default_strategy_uses_publication_name(self):
        from optimizer_pipeline import DEFAULT_OPTIMIZATION_STRATEGY

        self.assertEqual(DEFAULT_OPTIMIZATION_STRATEGY, "full_method")
        self.assertEqual(
            get_experiment_strategy(DEFAULT_OPTIMIZATION_STRATEGY)["publication_name"],
            "full_method",
        )

    def test_publication_strategy_definitions_use_paper_order(self):
        definitions = list_publication_strategy_definitions()

        self.assertEqual(
            [item["name"] for item in definitions],
            PAPER_STRATEGY_NAMES,
        )

    def test_publication_strategy_definitions_include_legacy_mapping(self):
        definitions = {
            item["name"]: item for item in list_publication_strategy_definitions()
        }

        self.assertEqual(LEGACY_STRATEGY_NAME_MAP["ours_full"], "full_method")
        self.assertEqual(LEGACY_STRATEGY_NAME_MAP["llm_plain"], "diagnostic_only")
        self.assertIn("ours_full", definitions["full_method"]["legacy_names"])
        self.assertIn("llm_plain", definitions["diagnostic_only"]["legacy_names"])
        self.assertEqual(
            get_publication_strategy_definition("strong_plain")["status"],
            "ready",
        )

    def test_publication_strategy_switch_matrix_is_locked(self):
        expected = {
            "origin": {
                "optimizer_enabled": False,
                "single_round": True,
                "max_rounds": 0,
                "performance_guard": False,
            },
            "strong_plain": {
                "optimizer_enabled": True,
                "single_round": True,
                "max_rounds": 1,
                "performance_guard": False,
                "system_prompt_profile": "strong_plain",
                "include_strong_baseline_guidance": True,
                "include_diagnostics": False,
                "include_structured_feedback": False,
                "include_semantic_hints": False,
                "include_knowledge": False,
                "include_examples": False,
                "include_history": False,
                "include_progress_analysis": False,
                "use_multi_round_system_prompt": False,
            },
            "diagnostic_only": {
                "optimizer_enabled": True,
                "single_round": True,
                "max_rounds": 1,
                "performance_guard": False,
                "system_prompt_profile": "method",
                "include_strong_baseline_guidance": False,
                "include_diagnostics": True,
                "include_structured_feedback": True,
                "include_semantic_hints": True,
                "include_knowledge": False,
                "include_examples": False,
                "include_history": False,
                "include_progress_analysis": False,
                "use_multi_round_system_prompt": False,
            },
            "case_card_only": {
                "optimizer_enabled": True,
                "single_round": True,
                "max_rounds": 1,
                "performance_guard": False,
                "system_prompt_profile": "method",
                "include_strong_baseline_guidance": False,
                "include_diagnostics": True,
                "include_structured_feedback": True,
                "include_semantic_hints": True,
                "include_knowledge": True,
                "include_examples": False,
                "include_history": False,
                "include_progress_analysis": False,
                "use_multi_round_system_prompt": False,
            },
            "full_method": {
                "optimizer_enabled": True,
                "single_round": False,
                "max_rounds": None,
                "performance_guard": True,
                "system_prompt_profile": "method",
                "include_strong_baseline_guidance": False,
                "include_diagnostics": True,
                "include_structured_feedback": True,
                "include_semantic_hints": True,
                "include_knowledge": True,
                "include_examples": True,
                "include_history": True,
                "include_progress_analysis": True,
                "use_multi_round_system_prompt": True,
            },
        }

        for strategy_name, expected_values in expected.items():
            with self.subTest(strategy=strategy_name):
                strategy = get_experiment_strategy(strategy_name)
                prompt_options = strategy["prompt_options"]

                self.assertEqual(
                    strategy["publication_name"],
                    strategy_name,
                )
                self.assertEqual(
                    strategy["optimizer_enabled"],
                    expected_values["optimizer_enabled"],
                )
                self.assertEqual(strategy["single_round"], expected_values["single_round"])
                self.assertEqual(strategy["max_rounds"], expected_values["max_rounds"])
                self.assertEqual(
                    strategy["performance_guard"]["enabled"],
                    expected_values["performance_guard"],
                )

                for option_name, expected_value in expected_values.items():
                    if option_name in {
                        "optimizer_enabled",
                        "single_round",
                        "max_rounds",
                        "performance_guard",
                    }:
                        continue
                    self.assertEqual(prompt_options[option_name], expected_value)


if __name__ == "__main__":
    unittest.main()
