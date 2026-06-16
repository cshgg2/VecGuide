# VecGuide 实验汇总（cgo_candidate_s258_scalar_carry_repeat1_20260609）

- 生成时间：2026-06-09T11:02:57.333194
- 函数数量：1
- 策略：origin, strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origin | 0 | 1 | 0 | 1 | - | - | 0 |
| strong_plain | 0 | 1 | 0 | 1 | 0.997 | 0.997 | 1 |
| diagnostic_only | 0 | 1 | 1 | 1 | 4.234 | 4.234 | 0 |
| case_card_only | 0 | 1 | 1 | 1 | 4.311 | 4.311 | 0 |
| full_method | 0 | 1 | 1 | 1 | 4.306 | 4.306 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| origin_vs_strong_plain | 1 | 0 | 1 | 0 | 0.003 |
| origin_vs_diagnostic_only | 1 | 0 | 0 | 1 | -3.234 |
| origin_vs_case_card_only | 1 | 0 | 0 | 1 | -3.311 |
| origin_vs_full_method | 1 | 0 | 0 | 1 | -3.306 |
| strong_plain_vs_diagnostic_only | 1 | 0 | 0 | 1 | -3.236 |
| strong_plain_vs_case_card_only | 1 | 0 | 0 | 1 | -3.314 |
| strong_plain_vs_full_method | 1 | 0 | 0 | 1 | -3.308 |
| diagnostic_only_vs_case_card_only | 1 | 0 | 0 | 1 | -0.077 |
| diagnostic_only_vs_full_method | 1 | 0 | 0 | 1 | -0.072 |
| case_card_only_vs_full_method | 1 | 0 | 1 | 0 | 0.006 |

## 函数级明细

| function | severity | origin | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- | --- |
| s258 | - | 1.000x / origin_not_vectorized_baseline | 0.997x / non_vectorized_flat | 4.234x / vectorized_speedup | 4.311x / vectorized_speedup | 4.306x / vectorized_speedup |
