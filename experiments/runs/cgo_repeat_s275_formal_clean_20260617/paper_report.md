# VecGuide 实验汇总（cgo_repeat_s275_formal_clean_20260617）

- 生成时间：2026-06-17T22:58:34.256871
- 函数数量：1
- 策略：origin, strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origin | 0 | 1 | 0 | 1 | - | - | 0 |
| strong_plain | 0 | 1 | 0 | 1 | 1.000 | 1.000 | 0 |
| diagnostic_only | 0 | 1 | 0 | 1 | 6.757 | 6.757 | 0 |
| case_card_only | 0 | 1 | 0 | 1 | 5.474 | 5.474 | 0 |
| full_method | 0 | 1 | 0 | 1 | 7.682 | 7.682 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| origin_vs_strong_plain | 1 | 0 | 1 | 0 | 0.000 |
| origin_vs_diagnostic_only | 1 | 0 | 0 | 1 | -5.757 |
| origin_vs_case_card_only | 1 | 0 | 0 | 1 | -4.474 |
| origin_vs_full_method | 1 | 0 | 0 | 1 | -6.682 |
| strong_plain_vs_diagnostic_only | 1 | 0 | 0 | 1 | -5.757 |
| strong_plain_vs_case_card_only | 1 | 0 | 0 | 1 | -4.474 |
| strong_plain_vs_full_method | 1 | 0 | 0 | 1 | -6.682 |
| diagnostic_only_vs_case_card_only | 1 | 1 | 0 | 0 | 1.283 |
| diagnostic_only_vs_full_method | 1 | 0 | 0 | 1 | -0.925 |
| case_card_only_vs_full_method | 1 | 0 | 0 | 1 | -2.208 |

## 函数级明细

| function | severity | origin | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- | --- |
| s275 | - | 1.000x / origin_not_vectorized_baseline | 1.000x / non_vectorized_flat | 6.757x / non_vectorized_speedup | 5.474x / non_vectorized_speedup | 7.682x / non_vectorized_speedup |
