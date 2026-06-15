import unittest

from prompts.knowledge_base import format_case_cards_for_prompt
from prompts.templates import build_optimization_prompt


class CaseCardPromptFormattingTests(unittest.TestCase):
    def test_case_card_prompt_includes_evidence_and_risk_constraints(self):
        text = format_case_cards_for_prompt(
            {
                "primary_categories": ["dependency_unsafe"],
                "pattern_family": "loop_distribution_dependence_isolation",
                "performance_level": {
                    "anti_patterns": ["avoid_fixed_index_self_read_hoist"]
                },
                "code_facts": {"has_fixed_index_self_read_hazard": True},
            },
            limit=1,
        )

        self.assertIn("代表函数: s1113", text)
        self.assertIn("2.95x", text)
        self.assertIn("语义安全理由", text)
        self.assertIn("有利于向量化的原因", text)
        self.assertIn("性能风险", text)
        self.assertIn("关键风险约束", text)
        self.assertIn("Must NOT hoist", text)

    def test_case_card_prompt_avoids_raw_placeholder_ellipsis(self):
        text = format_case_cards_for_prompt(
            {
                "primary_categories": ["trip_count_bounds"],
                "pattern_family": "runtime_stride_simple",
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_runtime_stride": True},
            },
            limit=1,
        )

        self.assertIn("unit-stride loop", text)
        self.assertNotIn("...", text)

    def test_build_optimization_prompt_injects_structured_cards(self):
        diagnostics = {
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
                        "could not determine number of loop iterations"
                    ],
                },
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_runtime_stride": True},
            },
        }

        _, user_prompt = build_optimization_prompt(
            code="for (int i = n1 - 1; i < LEN_1D; i += n3) { a[i] += b[i]; }",
            func_name="s172",
            diagnostics=diagnostics,
            round_num=1,
            max_rounds=3,
            prompt_options={
                "include_examples": False,
                "include_history": False,
                "include_progress_analysis": False,
            },
        )

        self.assertIn("【结构化反馈摘要】", user_prompt)
        self.assertIn("【类别化案例卡】", user_prompt)
        self.assertIn("runtime-stride simple", user_prompt)
        self.assertIn("代表函数: s172", user_prompt)
        self.assertIn("语义安全理由", user_prompt)

    def test_prompt_options_can_disable_structured_feedback_and_semantic_hints(self):
        diagnostics = {
            "missed": ["loop not vectorized: could not determine number of loop iterations"],
            "vectorized": [],
            "structured_feedback": {
                "primary_categories": ["trip_count_bounds"],
                "pattern_family": "runtime_stride_simple",
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_runtime_stride": True},
            },
        }

        _, user_prompt = build_optimization_prompt(
            code="for (int i = n1 - 1; i < LEN_1D; i += n3) { a[i] += b[i]; }",
            func_name="s172",
            diagnostics=diagnostics,
            round_num=1,
            max_rounds=1,
            prompt_options={
                "include_diagnostics": False,
                "include_structured_feedback": False,
                "include_semantic_hints": False,
                "include_knowledge": False,
                "include_examples": False,
                "include_history": False,
                "include_progress_analysis": False,
                "use_multi_round_system_prompt": False,
            },
            semantic_hints=["检测到运行时参数 `n3` 控制的变步长循环。"],
        )

        self.assertIn("【待优化代码】", user_prompt)
        self.assertNotIn("【向量化失败原因】", user_prompt)
        self.assertNotIn("【结构化反馈摘要】", user_prompt)
        self.assertNotIn("【语义安全提示】", user_prompt)
        self.assertNotIn("【类别化案例卡】", user_prompt)

    def test_strong_plain_prompt_is_strong_but_does_not_leak_method_context(self):
        diagnostics = {
            "missed": ["loop not vectorized: unsafe dependent memory operations in loop"],
            "vectorized": [],
            "structured_feedback": {
                "primary_categories": ["dependency_unsafe"],
                "pattern_family": "loop_distribution_dependence_isolation",
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_fixed_index_self_read_hazard": True},
            },
        }

        system_prompt, user_prompt = build_optimization_prompt(
            code="for (int i = 0; i < LEN_1D; i++) { a[i] = a[0]; }",
            func_name="s293",
            diagnostics=diagnostics,
            round_num=1,
            max_rounds=1,
            prompt_options={
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
        )

        self.assertIn("通用自动向量化改写建议", user_prompt)
        self.assertIn("循环交换", system_prompt)
        self.assertIn("循环分发", system_prompt)
        self.assertIn("循环剥离", system_prompt)
        self.assertIn("节点拆分", system_prompt)
        self.assertNotIn("【向量化失败原因】", user_prompt)
        self.assertNotIn("【结构化反馈摘要】", user_prompt)
        self.assertNotIn("【类别化案例卡】", user_prompt)
        self.assertNotIn("代表函数", user_prompt)

    def test_strong_plain_prompt_keeps_core_safety_constraints(self):
        system_prompt, user_prompt = build_optimization_prompt(
            code="for (int i = 0; i < LEN_1D; i++) { a[i] = b[i] + c[i]; }",
            func_name="s111",
            diagnostics={"missed": [], "vectorized": []},
            round_num=1,
            max_rounds=1,
            prompt_options={
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
        )

        self.assertIn("必须遵守的正确性约束", system_prompt)
        self.assertIn("TSVC", system_prompt)
        self.assertIn("不硬编码", system_prompt)
        self.assertIn("dummy() 调用层级", system_prompt)
        self.assertIn("循环分发/拆分", system_prompt)
        self.assertIn("标量临时变量", system_prompt)
        self.assertIn("循环交换", system_prompt)
        self.assertIn("通用自动向量化改写建议", user_prompt)

    def test_s123_guard_card_includes_negative_oracle_evidence(self):
        text = format_case_cards_for_prompt(
            {
                "primary_categories": ["control_flow", "trip_count_bounds"],
                "pattern_family": "branch_hoisting",
                "performance_level": {"anti_patterns": ["avoid_large_materialization"]},
                "code_facts": {"has_control_flow": True},
            },
            limit=1,
        )

        self.assertIn("代表函数: s123", text)
        self.assertIn("失败证据", text)
        self.assertIn("0.854x", text)
        self.assertIn("performance guard", text)

    def test_s115_card_includes_plain_baseline_contrast(self):
        text = format_case_cards_for_prompt(
            {
                "func_name": "s115",
                "primary_categories": ["dependency_unsafe"],
                "pattern_family": "loop_distribution_dependence_isolation",
                "performance_level": {"anti_patterns": []},
                "code_facts": {},
            },
            limit=1,
        )

        self.assertIn("代表函数: s115", text)
        self.assertIn("4.045x", text)
        self.assertIn("llm_plain", text)
        self.assertIn("benchmark timeout", text)
        self.assertIn("The important transformation is not loop interchange", text)

    def test_s222_card_includes_partial_vectorization_slowdown_evidence(self):
        text = format_case_cards_for_prompt(
            {
                "func_name": "s222",
                "primary_categories": ["recurrence_reduction"],
                "pattern_family": "reduction_or_recurrence",
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_indexed_recurrence": True},
            },
            limit=1,
        )

        self.assertIn("代表函数: s222", text)
        self.assertIn("失败证据", text)
        self.assertIn("0.885x", text)
        self.assertIn("partial vectorization", text)
        self.assertIn("not evidence to accept", text)

    def test_s278_card_includes_goto_rewrite_evidence_and_s272_risk(self):
        text = format_case_cards_for_prompt(
            {
                "func_name": "s278",
                "primary_categories": ["control_flow"],
                "pattern_family": "branch_hoisting",
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_control_flow": True},
            },
            limit=1,
        )

        self.assertIn("代表函数: s278", text)
        self.assertIn("2.163x", text)
        self.assertIn("2.201x", text)
        self.assertIn("1.952x", text)
        self.assertIn("llm_plain", text)
        self.assertIn("1.451x", text)
        self.assertIn("s272", text)
        self.assertIn("0.330x", text)
        self.assertIn("local value preservation", text)

    def test_s275_card_includes_guarded_loop_interchange_evidence(self):
        text = format_case_cards_for_prompt(
            {
                "func_name": "s275",
                "primary_categories": ["recurrence_reduction"],
                "pattern_family": "reduction_or_recurrence",
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_control_flow": True},
            },
            limit=1,
        )

        self.assertIn("代表函数: s275", text)
        self.assertIn("25.667x", text)
        self.assertIn("26.344x", text)
        self.assertIn("llm_plain", text)
        self.assertIn("5.819x", text)
        self.assertIn("TSVC s275 initializing aa", text)
        self.assertIn("non-vectorized", text)

    def test_s2233_card_includes_selective_interchange_retry_warning(self):
        text = format_case_cards_for_prompt(
            {
                "func_name": "s2233",
                "primary_categories": ["recurrence_reduction"],
                "pattern_family": "reduction_or_recurrence",
                "performance_level": {"anti_patterns": []},
                "code_facts": {},
            },
            limit=1,
        )

        self.assertIn("代表函数: s2233", text)
        self.assertIn("selective interchange", text)
        self.assertIn("0.533x", text)
        self.assertIn("benchmark timeout", text)
        self.assertIn("partial vectorization", text)
        self.assertIn("boundary/steering card", text)

    def test_s1244_card_includes_node_splitting_evidence_and_plain_baseline(self):
        text = format_case_cards_for_prompt(
            {
                "func_name": "s1244",
                "primary_categories": ["dependency_unsafe"],
                "pattern_family": "loop_distribution_dependence_isolation",
                "performance_level": {"anti_patterns": []},
                "code_facts": {},
            },
            limit=1,
        )

        self.assertIn("代表函数: s1244", text)
        self.assertIn("2.561x", text)
        self.assertIn("2.612x", text)
        self.assertIn("llm_plain", text)
        self.assertIn("2.442x", text)
        self.assertIn("2.559x", text)
        self.assertIn("transform-family positive example", text)
        self.assertIn("s212", text)
        self.assertIn("runtime verification failed", text)

    def test_s293_card_includes_loop_peeling_evidence_and_plain_baseline(self):
        text = format_case_cards_for_prompt(
            {
                "func_name": "s293",
                "primary_categories": ["dependency_unsafe"],
                "pattern_family": "loop_distribution_dependence_isolation",
                "performance_level": {"anti_patterns": []},
                "code_facts": {},
            },
            limit=1,
        )

        self.assertIn("代表函数: s293", text)
        self.assertIn("loop peeling", text)
        self.assertIn("1.910x", text)
        self.assertIn("1.830x", text)
        self.assertIn("llm_plain", text)
        self.assertIn("2.428x", text)
        self.assertIn("2.403x", text)
        self.assertIn("first = a[0]", text)
        self.assertIn("transform-family positive example", text)
        self.assertIn("Do not claim full-method advantage", text)

    def test_s235_card_includes_distribution_interchange_evidence_and_plain_baseline(self):
        text = format_case_cards_for_prompt(
            {
                "func_name": "s235",
                "primary_categories": ["recurrence_reduction"],
                "pattern_family": "reduction_or_recurrence",
                "performance_level": {"anti_patterns": []},
                "code_facts": {},
            },
            limit=1,
        )

        self.assertIn("代表函数: s235", text)
        self.assertIn("imperfect nested loop", text)
        self.assertIn("21.752x", text)
        self.assertIn("22.074x", text)
        self.assertIn("21.210x", text)
        self.assertIn("21.393x", text)
        self.assertIn("llm_plain", text)
        self.assertIn("1.000x", text)
        self.assertIn("non-vectorized", text)
        self.assertIn("method-advantage strong candidate", text)
        self.assertIn("original-function timeout", text)
        self.assertIn("120-second process timeout", text)


if __name__ == "__main__":
    unittest.main()
