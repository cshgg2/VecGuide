# Submission Readiness Check

Updated: 2026-06-17

This document summarizes the current public evidence against the paper-facing submission threshold. It does not add new experiments; it classifies existing public artifacts for paper use.

## Main-Table Eligibility Rule

A row can support the main result table only when it follows `docs/experiment_protocol.md`:

- benchmark protocol is formal or otherwise marked `paper_main_table_eligible=true`;
- correctness passes;
- benchmark succeeds;
- speedup is available;
- the result is not a screening-only, timeout-limited, or boundary-only artifact.

## Current Main Evidence Candidates

| Candidate | Public tables | Current status | Paper-use note |
| --- | --- | --- | --- |
| `s275` | `cgo_key_case_matrix_20260604`, `cgo_repeat_s275_formal_clean_20260617` | primary method-advantage case with mixed repeat | The repeat keeps the speedup advantage over strong_plain, but the full-vectorization claim should be weakened. |
| `s258` | `cgo_s258_scalar_carry_20260609`, `cgo_repeat_s258_formal_clean_20260617` | scalar-carry case with clean repeat | Use as scalar-carry evidence, but not as an exclusive VecGuide advantage because strong_plain is competitive in the repeat. |
| `s253` | `cgo_scalar_carry_s253_s254_s255_20260609` | weaker same-family supplement | Useful as supporting evidence, not as the headline claim. |

## Supplemental Evidence

| Evidence | Public tables | Current status | Paper-use note |
| --- | --- | --- | --- |
| Runtime-stride group | `cgo_runtime_stride_matrix_20260604` | formal supplemental group | Useful for breadth, but not the clearest contribution example. |
| `s278` | `cgo_key_case_matrix_20260604` | control-flow supplement | Use carefully because strong baselines are also competitive. |
| `s2710` | `cgo_s274_s2710_control_flow_20260611`, `cgo_s2710_control_flow_repeat1_20260611` | stability and boundary evidence | Repeat evidence is useful, but strong_plain is also competitive. |
| `s1232` | `cgo_s1232_triangular_loop_20260611` | loop-interchange / timeout boundary | Do not report the case_card_only speedup without the timeout context for other LLM strategies. |

## Not Main-Table Evidence

| Evidence | Reason |
| --- | --- |
| Timeout-limited `s235/s115` material | protocol-limited; should stay out of the formal main table. |
| Origin-only probe runs | screening-only; useful for candidate selection, not method comparison. |
| Boundary cases such as `s1161`, `s126`, `s277`, `s291/s292`, `s211`, `s261`, `s274` | useful for limitations, negative evidence, or failure-mode discussion. |

## Current Gap

The public evidence is enough to describe a credible focused story, but it is still narrow. The `s2710` and `s1232` run-only cases have now been promoted into public tables as supplemental or boundary evidence. The clean `s275` repeat supports the performance-benefit story, but it weakens any claim that full vectorization reliably repeats. The clean `s258` repeat confirms scalar-carry speedups, but it also shows that strong_plain is competitive. Before submission, the safest next evidence step is to keep claims focused on compiler-diagnostic guidance and case-card usefulness rather than claiming broad dominance over strong prompting.

Any new LLM experiment should follow `docs/api_boundary.md`: run manually, use a deliberate `--run-id`, and promote results only after correctness, benchmark protocol, and table eligibility checks. The current minimal repeat plan is `docs/formal_repeat_plan.md`.
