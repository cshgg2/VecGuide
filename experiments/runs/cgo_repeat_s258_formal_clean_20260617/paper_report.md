# VecGuide 实验汇总（cgo_repeat_s258_formal_clean_20260617）

- 生成时间：2026-06-17T23:25:25.875160
- 函数数量：1
- 策略：origin, strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origin | 0 | 1 | 0 | 1 | - | - | 0 |
| strong_plain | 0 | 1 | 1 | 1 | 5.855 | 5.855 | 0 |
| diagnostic_only | 0 | 1 | 0 | 1 | 1.459 | 1.459 | 0 |
| case_card_only | 0 | 1 | 1 | 1 | 5.545 | 5.545 | 0 |
| full_method | 0 | 1 | 1 | 1 | 5.678 | 5.678 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| origin_vs_strong_plain | 1 | 0 | 0 | 1 | -4.855 |
| origin_vs_diagnostic_only | 1 | 0 | 0 | 1 | -0.459 |
| origin_vs_case_card_only | 1 | 0 | 0 | 1 | -4.545 |
| origin_vs_full_method | 1 | 0 | 0 | 1 | -4.678 |
| strong_plain_vs_diagnostic_only | 1 | 1 | 0 | 0 | 4.396 |
| strong_plain_vs_case_card_only | 1 | 1 | 0 | 0 | 0.310 |
| strong_plain_vs_full_method | 1 | 1 | 0 | 0 | 0.177 |
| diagnostic_only_vs_case_card_only | 1 | 0 | 0 | 1 | -4.086 |
| diagnostic_only_vs_full_method | 1 | 0 | 0 | 1 | -4.219 |
| case_card_only_vs_full_method | 1 | 0 | 0 | 1 | -0.133 |

## 函数级明细

| function | severity | origin | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- | --- |
| s258 | - | 1.000x / origin_not_vectorized_baseline | 5.855x / vectorized_speedup | 1.459x / non_vectorized_speedup | 5.545x / vectorized_speedup | 5.678x / vectorized_speedup |
