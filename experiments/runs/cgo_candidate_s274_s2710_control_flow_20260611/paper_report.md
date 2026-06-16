# VecGuide 实验汇总（cgo_candidate_s274_s2710_control_flow_20260611）

- 生成时间：2026-06-11T19:11:40.615165
- 函数数量：2
- 策略：origin, strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origin | 0 | 2 | 0 | 2 | - | - | 0 |
| strong_plain | 0 | 2 | 1 | 2 | 1.862 | 1.862 | 1 |
| diagnostic_only | 0 | 2 | 1 | 2 | 1.132 | 1.132 | 0 |
| case_card_only | 0 | 2 | 2 | 2 | 1.423 | 1.423 | 0 |
| full_method | 0 | 2 | 2 | 2 | 1.367 | 1.367 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| origin_vs_strong_plain | 2 | 0 | 1 | 1 | -0.862 |
| origin_vs_diagnostic_only | 2 | 0 | 1 | 1 | -0.132 |
| origin_vs_case_card_only | 2 | 0 | 0 | 2 | -0.423 |
| origin_vs_full_method | 2 | 0 | 0 | 2 | -0.367 |
| strong_plain_vs_diagnostic_only | 2 | 1 | 1 | 0 | 0.730 |
| strong_plain_vs_case_card_only | 2 | 1 | 0 | 1 | 0.439 |
| strong_plain_vs_full_method | 2 | 1 | 0 | 1 | 0.495 |
| diagnostic_only_vs_case_card_only | 2 | 1 | 0 | 1 | -0.290 |
| diagnostic_only_vs_full_method | 2 | 1 | 0 | 1 | -0.234 |
| case_card_only_vs_full_method | 2 | 1 | 1 | 0 | 0.056 |

## 函数级明细

| function | severity | origin | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- | --- |
| s2710 | - | 1.000x / origin_not_vectorized_baseline | 0.999x / non_vectorized_flat | 1.000x / non_vectorized_flat | 1.604x / vectorized_speedup | 1.592x / vectorized_speedup |
| s274 | - | 1.000x / origin_not_vectorized_baseline | 2.726x / vectorized_speedup | 1.265x / vectorized_speedup | 1.241x / vectorized_speedup | 1.141x / vectorized_speedup |
