# VecGuide 实验汇总（cgo_minimal_evidence_p0_s122_clang17restored_20260619）

- 生成时间：2026-06-19T12:50:36.065312
- 函数数量：1
- 策略：origin, strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origin | 0 | 1 | 0 | 1 | - | - | 0 |
| strong_plain | 0 | 0 | 0 | 0 | - | - | 0 |
| diagnostic_only | 0 | 1 | 0 | 1 | 0.870 | 0.870 | 1 |
| case_card_only | 0 | 1 | 0 | 1 | 2.358 | 2.358 | 0 |
| full_method | 0 | 1 | 0 | 1 | 2.290 | 2.290 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| origin_vs_strong_plain | 0 | 0 | 0 | 0 | - |
| origin_vs_diagnostic_only | 1 | 1 | 0 | 0 | 0.130 |
| origin_vs_case_card_only | 1 | 0 | 0 | 1 | -1.358 |
| origin_vs_full_method | 1 | 0 | 0 | 1 | -1.290 |
| strong_plain_vs_diagnostic_only | 0 | 0 | 0 | 0 | - |
| strong_plain_vs_case_card_only | 0 | 0 | 0 | 0 | - |
| strong_plain_vs_full_method | 0 | 0 | 0 | 0 | - |
| diagnostic_only_vs_case_card_only | 1 | 0 | 0 | 1 | -1.488 |
| diagnostic_only_vs_full_method | 1 | 0 | 0 | 1 | -1.420 |
| case_card_only_vs_full_method | 1 | 1 | 0 | 0 | 0.068 |

## 函数级明细

| function | severity | origin | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- | --- |
| s122 | - | 1.000x / origin_not_vectorized_baseline | NA / correctness_failed | 0.870x / non_vectorized_slowdown | 2.358x / non_vectorized_speedup | 2.290x / non_vectorized_speedup |
