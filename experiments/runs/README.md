# Experiments Run Index

Updated: 2026-06-12

This directory stores public run-level artifacts. The current paper draft should use the `cgo_*` runs listed below together with `docs/evidence_map.md`, `docs/experiment_protocol.md`, and the table artifacts under `experiments/tables/`.

Each formal run usually contains:

- `manifest.json`: functions, strategies, protocol, and environment summary.
- `strategy_config.json`: strategy configuration snapshot.
- `paper_results.csv`: per-function, per-strategy results.
- `paper_report.md`: readable summary.
- `paper_summary.json` / `paper_comparison.json`: structured summaries.
- `artifact_index.json`: artifact inventory.

Main-table eligibility requires `paper_main_table_eligible=true`, passing correctness, successful benchmark execution, and an available speedup value. See `docs/experiment_protocol.md` for details.

## A. Current Formal Method-Advantage Evidence

| Run | Functions | Protocol | Current use |
| --- | --- | --- | --- |
| `cgo_method_matrix_key_cases_20260604` | `s278/s231/s275/s1244/s293` | formal | `s275` is the clearest current formal method-advantage case; other functions are supplements or boundaries. |
| `cgo_strong_plain_key_cases_20260603` | `s278/s231/s275/s1244/s293` | formal | Strong plain baseline for the key cases above. |
| `cgo_candidate_s258_s256_scalar_array_20260608` | `s258/s256` | formal | `s258` scalar-carry / scalar-expansion candidate, first run. |
| `cgo_candidate_s258_scalar_carry_repeat1_20260609` | `s258` | formal | Repeat run supporting `s258`. |
| `cgo_candidate_scalar_carry_s253_s254_s255_20260609` | `s253/s254/s255` | formal | `s253` is a weaker same-family supplement; `s254/s255` are not method-advantage cases. |

## B. Formal Supplements, Stability Evidence, And Performance Boundaries

| Run | Functions | Protocol | Current use |
| --- | --- | --- | --- |
| `cgo_method_matrix_runtime_stride_core_20260604` | `s172/s1113/s122` | formal | Runtime-stride method matrix; supplemental evidence. |
| `cgo_strong_plain_runtime_stride_core_20260604` | `s172/s1113/s122` | formal | Runtime-stride strong baseline. |
| `cgo_candidate_s279_complex_control_flow_20260609` | `s279` | formal | Control-flow supplement; strong baseline also succeeds. |
| `cgo_candidate_s274_s2710_control_flow_20260611` | `s274/s2710` | formal | `s274` is strong-baseline-solvable; `s2710` is stability/boundary evidence. |
| `cgo_candidate_s2710_control_flow_repeat1_20260611` | `s2710` | formal | Repeat run that downgrades `s2710` from a main advantage case. |
| `cgo_candidate_s1232_triangular_loop_20260611` | `s1232` | formal | Loop-interchange / performance-selection boundary. |

## C. Timeout-Limited Or Protocol-Limited Candidates

| Run | Functions | Protocol | Current use |
| --- | --- | --- | --- |
| `cgo_strong_plain_timeout_candidates_20260604` | `s115/s235` | timeout_limited | Protocol-limited strong-baseline comparison. |
| `cgo_method_matrix_timeout_candidates_20260604` | `s115/s235` | timeout_limited | Discussion evidence, not formal main-table evidence. |

## D. Formal Boundary And Negative Evidence

| Run | Functions | Protocol | Current use |
| --- | --- | --- | --- |
| `cgo_candidate_s1161_control_flow_20260604` | `s1161` | formal | Downgraded control-flow evidence. |
| `cgo_candidate_s126_induction_interchange_20260604` | `s126` | formal | Induction-variable / recurrence boundary. |
| `cgo_candidate_s277_guard_goto_20260604` | `s277` | formal | Guard/goto performance boundary. |
| `cgo_candidate_s291_s292_loop_peeling_20260605` | `s291/s292` | formal | Strong-baseline-solvable loop-peeling cases. |
| `cgo_candidate_s211_statement_reordering_20260609` | `s211` | formal | Correctness-feedback boundary. |
| `cgo_candidate_s261_scalar_array_expansion_20260610` | `s261` | formal | `inf/nan` correctness boundary. |

## E. Origin-Only Screening Runs

These runs are retained for candidate screening only and should not replace a full strategy matrix.

| Run | Functions | Protocol |
| --- | --- | --- |
| `cgo_probe_s252_origin_20260611` | `s252` | formal |
| `cgo_probe_boundary_candidates_origin_20260611` | `s242/s3112/s3113/s341/s342/s343` | formal |
| `cgo_probe_light_candidates_origin_20260611` | `s243/s2244/s271/s273/s274/s1279/s2710/s2711` | formal |
| `cgo_probe_remaining_light_origin_20260611` | `s1221/s1232/s257/s3251` | formal |

## F. Dry-Run And Configuration Checks

| Run | Use |
| --- | --- |
| `cgo_strategy_names_dryrun_20260601` | Strategy-name and run-structure dry run. |
| `cgo_strong_plain_dryrun_20260601` | `strong_plain` prompt and run-structure dry run. |

Older exploratory runs may remain useful locally, but the public paper evidence should be selected through the documents listed at the top of this file.
