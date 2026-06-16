# VecGuide 实验汇总（cgo_candidate_scalar_carry_s253_s254_s255_20260609）

- 生成时间：2026-06-09T17:10:23.258245
- 函数数量：3
- 策略：origin, strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origin | 0 | 3 | 2 | 3 | - | - | 0 |
| strong_plain | 0 | 3 | 0 | 3 | 1.145 | 1.145 | 0 |
| diagnostic_only | 0 | 3 | 0 | 3 | 1.010 | 1.010 | 0 |
| case_card_only | 0 | 3 | 0 | 3 | 1.171 | 1.171 | 0 |
| full_method | 0 | 3 | 1 | 3 | 1.232 | 1.232 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| origin_vs_strong_plain | 1 | 0 | 0 | 1 | -0.145 |
| origin_vs_diagnostic_only | 1 | 0 | 1 | 0 | -0.010 |
| origin_vs_case_card_only | 1 | 0 | 0 | 1 | -0.171 |
| origin_vs_full_method | 1 | 0 | 0 | 1 | -0.232 |
| strong_plain_vs_diagnostic_only | 1 | 1 | 0 | 0 | 0.135 |
| strong_plain_vs_case_card_only | 1 | 0 | 0 | 1 | -0.027 |
| strong_plain_vs_full_method | 1 | 0 | 0 | 1 | -0.088 |
| diagnostic_only_vs_case_card_only | 1 | 0 | 0 | 1 | -0.162 |
| diagnostic_only_vs_full_method | 1 | 0 | 0 | 1 | -0.223 |
| case_card_only_vs_full_method | 1 | 0 | 0 | 1 | -0.061 |

## 函数级明细

| function | severity | origin | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- | --- |
| s253 | - | 1.000x / origin_not_vectorized_baseline | 1.145x / non_vectorized_speedup | 1.010x / non_vectorized_flat | 1.171x / non_vectorized_speedup | 1.232x / vectorized_speedup |
| s254 | - | 1.000x / origin_vectorized_baseline | 1.000x / already_vectorized_skipped | 1.000x / already_vectorized_skipped | 1.000x / already_vectorized_skipped | 1.000x / already_vectorized_skipped |
| s255 | - | 1.000x / origin_vectorized_baseline | 1.000x / already_vectorized_skipped | 1.000x / already_vectorized_skipped | 1.000x / already_vectorized_skipped | 1.000x / already_vectorized_skipped |
