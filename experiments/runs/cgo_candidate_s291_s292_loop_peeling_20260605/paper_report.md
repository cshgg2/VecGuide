# VecGuide 实验汇总（cgo_candidate_s291_s292_loop_peeling_20260605）

- 生成时间：2026-06-05T11:24:42.454608
- 函数数量：2
- 策略：strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| strong_plain | 0 | 2 | 2 | 2 | 2.327 | 2.327 | 0 |
| diagnostic_only | 0 | 2 | 0 | 2 | 0.439 | 0.439 | 2 |
| case_card_only | 0 | 2 | 0 | 2 | 0.440 | 0.440 | 2 |
| full_method | 0 | 2 | 1 | 1 | 1.584 | 1.584 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| strong_plain_vs_diagnostic_only | 2 | 2 | 0 | 0 | 1.889 |
| strong_plain_vs_case_card_only | 2 | 2 | 0 | 0 | 1.888 |
| strong_plain_vs_full_method | 1 | 1 | 0 | 0 | 0.749 |
| diagnostic_only_vs_case_card_only | 2 | 0 | 2 | 0 | -0.001 |
| diagnostic_only_vs_full_method | 1 | 0 | 0 | 1 | -1.061 |
| case_card_only_vs_full_method | 1 | 0 | 0 | 1 | -1.070 |

## 函数级明细

| function | severity | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- |
| s291 | medium | 2.333x / vectorized_speedup | 0.523x / non_vectorized_slowdown | 0.514x / non_vectorized_slowdown | 1.584x / vectorized_speedup |
| s292 | medium | 2.322x / vectorized_speedup | 0.354x / non_vectorized_slowdown | 0.366x / non_vectorized_slowdown | NA / performance_guard_rejected |
