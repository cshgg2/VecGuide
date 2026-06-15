# CGO 2027 Current Evidence Package (2026-06-12)

This directory freezes the public evidence scope used by the current VecGuide paper draft. It fixes which runs, tables, and documents may be cited from this package.

Frozen basis:

- `docs/evidence_map.md`
- `experiments/runs/README.md`
- `docs/reproduction.md`
- `docs/experiment_protocol.md`
- `docs/artifact_index.md`

## Usage Rules

1. Formal main-table results should come from the primary formal evidence listed below.
2. Timeout-limited, origin-only screening, and boundary/negative evidence must not be mixed into the formal main table.
3. If new experiments are promoted later, create a new frozen package or document the replacement explicitly.
4. Older exploratory runs and ad-hoc reports are outside this package unless promoted into a public artifact list.
5. LLM experiment commands are run manually; this package only freezes existing results.

## Primary Formal Evidence

| Evidence | Run | Table | Current use |
| --- | --- | --- | --- |
| `s275` | `experiments/runs/cgo_method_matrix_key_cases_20260604` + `experiments/runs/cgo_strong_plain_key_cases_20260603` | `experiments/tables/cgo_key_case_matrix_20260604` | Clearest current formal method-advantage case. |
| `s258` | `experiments/runs/cgo_candidate_s258_s256_scalar_array_20260608` + `experiments/runs/cgo_candidate_s258_scalar_carry_repeat1_20260609` | `experiments/tables/cgo_s258_scalar_carry_20260609` | Scalar-carry / scalar-expansion formal candidate. |
| `s253` | `experiments/runs/cgo_candidate_scalar_carry_s253_s254_s255_20260609` | `experiments/tables/cgo_scalar_carry_s253_s254_s255_20260609` | Weaker same-family supplement for `s258`. |

## Supplemental Formal Evidence

| Evidence | Run | Table | Current use |
| --- | --- | --- | --- |
| Runtime-stride group | `experiments/runs/cgo_method_matrix_runtime_stride_core_20260604` + `experiments/runs/cgo_strong_plain_runtime_stride_core_20260604` | `experiments/tables/cgo_runtime_stride_matrix_20260604` | Runtime-stride supplement. |
| `s278` | `experiments/runs/cgo_method_matrix_key_cases_20260604` + `experiments/runs/cgo_strong_plain_key_cases_20260603` | `experiments/tables/cgo_key_case_matrix_20260604` | Control-flow supplement. |
| `s279` | `experiments/runs/cgo_candidate_s279_complex_control_flow_20260609` | none frozen | Control-flow supplement; strong baseline also succeeds. |
| `s2710` | `experiments/runs/cgo_candidate_s274_s2710_control_flow_20260611` + `experiments/runs/cgo_candidate_s2710_control_flow_repeat1_20260611` | none frozen | Stability and boundary evidence. |
| `s1232` | `experiments/runs/cgo_candidate_s1232_triangular_loop_20260611` | none frozen | Loop-interchange and performance-selection boundary. |

## Timeout-Limited Evidence

| Evidence | Run | Table | Current use |
| --- | --- | --- | --- |
| `s235/s115` strong baseline | `experiments/runs/cgo_strong_plain_timeout_candidates_20260604` | `experiments/tables/cgo_timeout_limited_candidates_20260604` | Protocol-limited comparison. |
| `s235/s115` method matrix | `experiments/runs/cgo_method_matrix_timeout_candidates_20260604` | `experiments/tables/cgo_timeout_limited_matrix_20260604` | Discussion evidence, not formal main-table evidence. |

## Boundary And Negative Evidence

| Evidence | Run | Table | Current use |
| --- | --- | --- | --- |
| `s1161` | `experiments/runs/cgo_candidate_s1161_control_flow_20260604` | `experiments/tables/cgo_s1161_control_flow_20260604` | Downgraded control-flow evidence. |
| `s126` | `experiments/runs/cgo_candidate_s126_induction_interchange_20260604` | `experiments/tables/cgo_s126_induction_interchange_20260604` | Induction-variable / recurrence boundary. |
| `s277` | `experiments/runs/cgo_candidate_s277_guard_goto_20260604` | `experiments/tables/cgo_s277_guard_goto_20260604` | Guard/goto performance boundary. |
| `s291/s292` | `experiments/runs/cgo_candidate_s291_s292_loop_peeling_20260605` | `experiments/tables/cgo_s291_s292_loop_peeling_20260605` | Strong-baseline-solvable loop peeling cases. |
| `s211` | `experiments/runs/cgo_candidate_s211_statement_reordering_20260609` | none frozen | Correctness-feedback boundary. |
| `s261` | `experiments/runs/cgo_candidate_s261_scalar_array_expansion_20260610` | none frozen | `inf/nan` correctness boundary. |
| `s274` | `experiments/runs/cgo_candidate_s274_s2710_control_flow_20260611` | none frozen | Strong-baseline-solvable control-flow case. |

## Screening Evidence

These origin-only runs are retained for candidate screening only:

- `experiments/runs/cgo_probe_s252_origin_20260611`
- `experiments/runs/cgo_probe_boundary_candidates_origin_20260611`
- `experiments/runs/cgo_probe_light_candidates_origin_20260611`
- `experiments/runs/cgo_probe_remaining_light_origin_20260611`

## Frozen Documentation

- `docs/evidence_map.md`
- `experiments/runs/README.md`
- `docs/reproduction.md`
- `docs/experiment_protocol.md`
- `docs/artifact_index.md`
- `PROJECT_INDEX.md`

## Known Gaps

- The 2026-06-11 control-flow and triangular-loop runs are frozen as run artifacts, but do not yet have table artifacts in this package.
- This package freezes the 2026-06-12 evidence scope, not a camera-ready final paper table.
