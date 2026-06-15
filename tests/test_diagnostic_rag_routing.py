import unittest

import optimizer_pipeline
from feedback_structuring import categorize_reason, parse_diagnostic_line
from optimizer_pipeline import build_structured_feedback
from prompts.knowledge_base import select_experiment_case_cards


def card_ids(structured_feedback):
    return [card["id"] for card in select_experiment_case_cards(structured_feedback, limit=4)]


def eval_result(*, categories=None, missed_entries=None, vectorized_count=0, missed_count=1):
    return {
        "compilable": True,
        "vectorized_count": vectorized_count,
        "missed_count": missed_count,
        "diagnostics": {
            "missed_categories": categories or [],
            "missed_entries": missed_entries or [],
        },
    }


class DiagnosticCategoryTests(unittest.TestCase):
    def test_trip_count_bounds_reason(self):
        self.assertEqual(
            categorize_reason("could not determine number of loop iterations"),
            ["trip_count_bounds"],
        )

    def test_dependency_unsafe_reason(self):
        self.assertEqual(
            categorize_reason("unsafe dependent memory operations in loop"),
            ["dependency_unsafe"],
        )

    def test_control_flow_reason(self):
        self.assertEqual(
            categorize_reason("loop contains a switch statement and control flow"),
            ["control_flow"],
        )

    def test_recurrence_reduction_reason(self):
        self.assertEqual(
            categorize_reason("value that could not be identified as reduction"),
            ["recurrence_reduction"],
        )

    def test_parse_diagnostic_line_extracts_reason_and_category(self):
        parsed = parse_diagnostic_line(
            "/tmp/minimal.c:88:9: remark: loop not vectorized: call instruction cannot be vectorized [-Rpass-analysis=loop-vectorize]"
        )
        self.assertEqual(parsed["line"], 88)
        self.assertEqual(parsed["column"], 9)
        self.assertIn("call instruction cannot be vectorized", parsed["reason"])
        self.assertIn("call_side_effect", parsed["categories"])


class CaseCardRoutingTests(unittest.TestCase):
    def test_s172_routes_to_simple_runtime_stride_card(self):
        ids = card_ids(
            {
                "primary_categories": ["trip_count_bounds"],
                "pattern_family": "runtime_stride_simple",
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_runtime_stride": True},
            }
        )
        self.assertEqual(ids[0], "runtime_stride_simple_multiversion")

    def test_s122_routes_to_complex_runtime_stride_card(self):
        ids = card_ids(
            {
                "primary_categories": ["trip_count_bounds", "instruction_shape"],
                "pattern_family": "runtime_stride_complex",
                "performance_level": {"anti_patterns": ["avoid_closed_form_recurrence_rewrite"]},
                "code_facts": {
                    "has_runtime_stride": True,
                    "has_indexed_recurrence": True,
                },
            }
        )
        self.assertEqual(ids[0], "runtime_stride_complex_two_phase")
        self.assertIn("runtime_stride_simple_multiversion", ids)

    def test_s1113_routes_to_loop_distribution_card(self):
        ids = card_ids(
            {
                "func_name": "s1113",
                "primary_categories": ["dependency_unsafe"],
                "pattern_family": "loop_distribution_dependence_isolation",
                "performance_level": {"anti_patterns": ["avoid_fixed_index_self_read_hoist"]},
                "code_facts": {"has_fixed_index_self_read_hazard": True},
            }
        )
        self.assertEqual(ids[0], "loop_distribution_dependency_isolation")

    def test_s115_routes_to_triangular_saxpy_card(self):
        ids = card_ids(
            {
                "func_name": "s115",
                "primary_categories": ["dependency_unsafe"],
                "pattern_family": "loop_distribution_dependence_isolation",
                "performance_level": {"anti_patterns": []},
                "code_facts": {},
            }
        )
        self.assertEqual(ids[0], "triangular_saxpy_inner_loop_scalarization")
        self.assertIn("loop_distribution_dependency_isolation", ids)

    def test_s1161_routes_to_branch_predication_without_slowdown_signal(self):
        ids = card_ids(
            {
                "primary_categories": ["control_flow", "trip_count_bounds"],
                "pattern_family": "branch_hoisting",
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_control_flow": True},
            }
        )
        self.assertEqual(ids[0], "branch_hoisting_predication")

    def test_s123_routes_to_slowdown_guard_when_materialization_risk_exists(self):
        ids = card_ids(
            {
                "primary_categories": ["control_flow", "trip_count_bounds"],
                "pattern_family": "branch_hoisting",
                "performance_level": {"anti_patterns": ["avoid_large_materialization"]},
                "code_facts": {"has_control_flow": True},
            }
        )
        self.assertEqual(ids[0], "slowdown_guard_materialization")
        self.assertIn("branch_hoisting_predication", ids)

    def test_s278_routes_to_goto_structuring_card(self):
        ids = card_ids(
            {
                "func_name": "s278",
                "primary_categories": ["control_flow"],
                "pattern_family": "branch_hoisting",
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_control_flow": True},
            }
        )
        self.assertEqual(ids[0], "goto_if_else_structuring")
        self.assertIn("branch_hoisting_predication", ids)

    def test_s231_routes_to_row_recurrence_loop_interchange_card(self):
        ids = card_ids(
            {
                "func_name": "s231",
                "primary_categories": ["recurrence_reduction"],
                "pattern_family": "reduction_or_recurrence",
                "performance_level": {"anti_patterns": []},
                "code_facts": {},
            }
        )
        self.assertEqual(ids[0], "row_recurrence_loop_interchange")

    def test_s235_routes_to_imperfect_nested_distribution_card(self):
        ids = card_ids(
            {
                "func_name": "s235",
                "primary_categories": ["recurrence_reduction"],
                "pattern_family": "reduction_or_recurrence",
                "performance_level": {"anti_patterns": []},
                "code_facts": {},
            }
        )
        self.assertEqual(ids[0], "imperfect_nested_distribution_interchange")
        self.assertIn("reduction_or_recurrence_boundary", ids)

    def test_s2233_routes_to_selective_interchange_card(self):
        ids = card_ids(
            {
                "func_name": "s2233",
                "primary_categories": ["recurrence_reduction"],
                "pattern_family": "reduction_or_recurrence",
                "performance_level": {"anti_patterns": []},
                "code_facts": {},
            }
        )
        self.assertEqual(ids[0], "selective_interchange_two_inner_loops")

    def test_s1244_routes_to_node_splitting_card(self):
        ids = card_ids(
            {
                "func_name": "s1244",
                "primary_categories": ["dependency_unsafe"],
                "pattern_family": "loop_distribution_dependence_isolation",
                "performance_level": {"anti_patterns": []},
                "code_facts": {},
            }
        )
        self.assertEqual(ids[0], "node_splitting_true_anti_dependency")
        self.assertIn("loop_distribution_dependency_isolation", ids)

    def test_s293_routes_to_loop_peeling_card(self):
        ids = card_ids(
            {
                "func_name": "s293",
                "primary_categories": ["dependency_unsafe"],
                "pattern_family": "loop_distribution_dependence_isolation",
                "performance_level": {"anti_patterns": []},
                "code_facts": {},
            }
        )
        self.assertEqual(ids[0], "loop_peeling_fixed_source_scalarization")
        self.assertIn("loop_distribution_dependency_isolation", ids)

    def test_s275_routes_to_guarded_loop_interchange_card(self):
        ids = card_ids(
            {
                "func_name": "s275",
                "primary_categories": ["recurrence_reduction"],
                "pattern_family": "reduction_or_recurrence",
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_control_flow": True},
            }
        )
        self.assertEqual(ids[0], "guarded_loop_interchange_invariant_branch")

    def test_s321_routes_to_recurrence_boundary_card(self):
        ids = card_ids(
            {
                "primary_categories": ["recurrence_reduction"],
                "pattern_family": "recurrence_boundary",
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_indexed_recurrence": True},
            }
        )
        self.assertEqual(ids[0], "reduction_or_recurrence_boundary")

    def test_s222_routes_to_partial_vectorization_slowdown_card(self):
        ids = card_ids(
            {
                "func_name": "s222",
                "primary_categories": ["recurrence_reduction"],
                "pattern_family": "reduction_or_recurrence",
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_indexed_recurrence": True},
            }
        )
        self.assertEqual(ids[0], "partial_vectorization_slowdown_boundary")
        self.assertIn("reduction_or_recurrence_boundary", ids)

    def test_call_side_effect_routes_to_boundary_card(self):
        ids = card_ids(
            {
                "primary_categories": ["call_side_effect"],
                "pattern_family": None,
                "performance_level": {"anti_patterns": []},
                "code_facts": {"has_outer_iterations_loop": True},
            }
        )
        self.assertEqual(ids[0], "call_side_effect_boundary")


class StructuredFeedbackIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._old_problem_map_cache = optimizer_pipeline._problem_map_cache
        optimizer_pipeline._problem_map_cache = {}

    def tearDown(self):
        optimizer_pipeline._problem_map_cache = self._old_problem_map_cache

    def test_simple_runtime_stride_feedback_routes_to_s172_card(self):
        code = """
real_t s172(struct args_t * func_args) {
    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;
    for (int i = n1-1; i < LEN_1D; i += n3) {
        a[i] += b[i];
    }
    return calc_checksum(__func__);
}
"""
        structured = build_structured_feedback(
            "s172",
            eval_result(categories=["trip_count_bounds"], vectorized_count=0, missed_count=5),
            code,
        )
        self.assertEqual(structured["pattern_family"], "runtime_stride_simple")
        self.assertTrue(structured["code_facts"]["has_runtime_stride"])
        self.assertFalse(structured["code_facts"]["has_indexed_recurrence"])
        self.assertEqual(card_ids(structured)[0], "runtime_stride_simple_multiversion")

    def test_complex_runtime_stride_feedback_routes_to_s122_card(self):
        code = """
real_t s122(struct args_t * func_args) {
    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;
    int j = 1;
    int k = 0;
    for (int i = n1-1; i < LEN_1D; i += n3) {
        k += j;
        a[i] += b[LEN_1D - k];
    }
    return calc_checksum(__func__);
}
"""
        structured = build_structured_feedback(
            "s122",
            eval_result(categories=["trip_count_bounds", "instruction_shape"], missed_count=3),
            code,
        )
        self.assertEqual(structured["pattern_family"], "runtime_stride_complex")
        self.assertTrue(structured["code_facts"]["has_runtime_stride"])
        self.assertTrue(structured["code_facts"]["has_indexed_recurrence"])
        self.assertIn(
            "avoid_closed_form_recurrence_rewrite",
            structured["performance_level"]["anti_patterns"],
        )
        self.assertEqual(card_ids(structured)[0], "runtime_stride_complex_two_phase")

    def test_fixed_index_self_read_feedback_routes_to_s1113_card(self):
        code = """
real_t s1113(struct args_t * func_args) {
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = a[LEN_1D/2] + b[i];
    }
    return calc_checksum(__func__);
}
"""
        structured = build_structured_feedback(
            "s1113",
            eval_result(categories=["dependency_unsafe"], missed_count=2),
            code,
        )
        self.assertEqual(structured["pattern_family"], "loop_distribution_dependence_isolation")
        self.assertTrue(structured["code_facts"]["has_fixed_index_self_read_hazard"])
        self.assertIn(
            "avoid_fixed_index_self_read_hoist",
            structured["performance_level"]["anti_patterns"],
        )
        self.assertEqual(card_ids(structured)[0], "loop_distribution_dependency_isolation")

    def test_control_flow_feedback_adds_materialization_risk_and_routes_to_guard(self):
        code = """
real_t s123(struct args_t * func_args) {
    int j = -1;
    for (int i = 0; i < LEN_1D/2; i++) {
        j++;
        a[j] = b[i] + d[i] * e[i];
        if (c[i] > (real_t)0.) {
            j++;
            a[j] = c[i] + d[i] * e[i];
        }
    }
    return calc_checksum(__func__);
}
"""
        structured = build_structured_feedback(
            "s123",
            eval_result(categories=["trip_count_bounds"], missed_count=4),
            code,
        )
        self.assertEqual(structured["pattern_family"], "branch_hoisting")
        self.assertTrue(structured["code_facts"]["has_control_flow"])
        self.assertIn(
            "avoid_large_materialization",
            structured["performance_level"]["anti_patterns"],
        )
        self.assertEqual(card_ids(structured)[0], "slowdown_guard_materialization")

    def test_static_problem_map_categories_are_merged_when_dynamic_categories_missing(self):
        optimizer_pipeline._problem_map_cache = {
            "s1113": {
                "severity": "high",
                "problems": [
                    {
                        "reason": "unsafe dependent memory operations in loop. Use #pragma loop distribute(enable)"
                    }
                ],
            }
        }
        code = """
real_t s1113(struct args_t * func_args) {
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = a[LEN_1D/2] + b[i];
    }
    return calc_checksum(__func__);
}
"""
        structured = build_structured_feedback(
            "s1113",
            eval_result(categories=[], missed_count=2),
            code,
        )
        self.assertEqual(structured["severity"], "high")
        self.assertEqual(structured["primary_categories"], ["dependency_unsafe"])
        self.assertEqual(card_ids(structured)[0], "loop_distribution_dependency_isolation")


if __name__ == "__main__":
    unittest.main()
