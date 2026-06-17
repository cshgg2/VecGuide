# VecGuide Evidence Map

Updated: 2026-06-17

This document records the public evidence scope currently used for the VecGuide paper draft. It is intentionally compact: detailed daily notes, weekly reports, and terminal transcripts remain local-only.

## Main Formal Evidence

| Evidence | Runs | Tables | Current interpretation |
| --- | --- | --- | --- |
| `s275` | `cgo_method_matrix_key_cases_20260604`, `cgo_strong_plain_key_cases_20260603`, `cgo_repeat_s275_formal_clean_20260617` | `cgo_key_case_matrix_20260604`, `cgo_repeat_s275_formal_clean_20260617` | Primary method-advantage case; the clean repeat preserves speedup over strong_plain but does not repeat full vectorization. |
| `s258` | `cgo_candidate_s258_s256_scalar_array_20260608`, `cgo_candidate_s258_scalar_carry_repeat1_20260609`, `cgo_repeat_s258_formal_clean_20260617` | `cgo_s258_scalar_carry_20260609`, `cgo_repeat_s258_formal_clean_20260617` | Scalar-carry / scalar-expansion evidence; the clean repeat confirms vectorized speedups, but strong_plain is also competitive. |
| `s253` | `cgo_candidate_scalar_carry_s253_s254_s255_20260609` | `cgo_scalar_carry_s253_s254_s255_20260609` | Weaker same-family supplement for the scalar-carry story. |

## Supplemental Formal Evidence

| Evidence | Runs | Tables | Current interpretation |
| --- | --- | --- | --- |
| Runtime-stride group | `cgo_method_matrix_runtime_stride_core_20260604`, `cgo_strong_plain_runtime_stride_core_20260604` | `cgo_runtime_stride_matrix_20260604` | Useful supplement, but not the strongest main result group. |
| `s278` | `cgo_method_matrix_key_cases_20260604`, `cgo_strong_plain_key_cases_20260603` | `cgo_key_case_matrix_20260604` | Control-flow supplement; not an exclusive full-method advantage. |
| `s279` | `cgo_candidate_s279_complex_control_flow_20260609` | none frozen | Control-flow supplement; the strong plain baseline also succeeds. |
| `s2710` | `cgo_candidate_s274_s2710_control_flow_20260611`, `cgo_candidate_s2710_control_flow_repeat1_20260611` | `cgo_s274_s2710_control_flow_20260611`, `cgo_s2710_control_flow_repeat1_20260611` | Stability and boundary evidence; repeat result shows both strong_plain and full_method can speed up. |
| `s1232` | `cgo_candidate_s1232_triangular_loop_20260611` | `cgo_s1232_triangular_loop_20260611` | Loop-interchange / performance-selection boundary; case_card_only is fast, while other LLM strategies time out in the public table. |

## Timeout-Limited Evidence

| Evidence | Runs | Tables | Current interpretation |
| --- | --- | --- | --- |
| `s235/s115` strong baseline | `cgo_strong_plain_timeout_candidates_20260604` | `cgo_timeout_limited_candidates_20260604` | Protocol-limited strong-baseline comparison. |
| `s235/s115` method matrix | `cgo_method_matrix_timeout_candidates_20260604` | `cgo_timeout_limited_matrix_20260604` | Useful for discussion, but not eligible for the formal main table. |

## Boundary And Negative Evidence

| Evidence | Runs | Tables | Current interpretation |
| --- | --- | --- | --- |
| `s1161` | `cgo_candidate_s1161_control_flow_20260604` | `cgo_s1161_control_flow_20260604` | Earlier control-flow evidence downgraded after stronger baselines. |
| `s126` | `cgo_candidate_s126_induction_interchange_20260604` | `cgo_s126_induction_interchange_20260604` | Induction-variable / recurrence boundary. |
| `s277` | `cgo_candidate_s277_guard_goto_20260604` | `cgo_s277_guard_goto_20260604` | Guard/goto and performance-selection boundary. |
| `s291/s292` | `cgo_candidate_s291_s292_loop_peeling_20260605` | `cgo_s291_s292_loop_peeling_20260605` | Strong plain baseline can solve these; component over-materialization appears in some cases. |
| `s211` | `cgo_candidate_s211_statement_reordering_20260609` | none frozen | Correctness-feedback boundary; not an acceleration case. |
| `s261` | `cgo_candidate_s261_scalar_array_expansion_20260610` | none frozen | `inf/nan` correctness boundary. |
| `s274` | `cgo_candidate_s274_s2710_control_flow_20260611` | none frozen | Strong-baseline-solvable control-flow case. |

## Screening Runs

The following origin-only runs are retained for candidate screening only. They should not be mixed into the formal strategy matrix table.

- `cgo_probe_s252_origin_20260611`
- `cgo_probe_boundary_candidates_origin_20260611`
- `cgo_probe_light_candidates_origin_20260611`
- `cgo_probe_remaining_light_origin_20260611`
