# ACPO-LLM 实验汇总（cgo_method_matrix_key_cases_20260604）

- 生成时间：2026-06-04T11:04:08.301847
- 函数数量：5
- 策略：diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic_only | 0 | 5 | 3 | 4 | 1.717 | 1.602 | 1 |
| case_card_only | 0 | 5 | 4 | 4 | 3.368 | 2.496 | 0 |
| full_method | 0 | 5 | 5 | 4 | 7.723 | 2.487 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| diagnostic_only_vs_case_card_only | 4 | 0 | 1 | 3 | -1.651 |
| diagnostic_only_vs_full_method | 4 | 1 | 0 | 3 | -6.006 |
| case_card_only_vs_full_method | 4 | 2 | 0 | 2 | -4.355 |

## 函数级明细

| function | severity | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- |
| s1244 | medium | 2.725x / vectorized_speedup | 2.730x / vectorized_speedup | 2.679x / vectorized_speedup |
| s231 | medium | NA / benchmark_failed | NA / benchmark_failed | NA / benchmark_failed |
| s275 | medium | 0.939x / non_vectorized_slowdown | 6.537x / non_vectorized_speedup | 24.118x / vectorized_speedup |
| s278 | low | 2.203x / vectorized_speedup | 2.262x / vectorized_speedup | 2.295x / vectorized_speedup |
| s293 | medium | 1.000x / non_vectorized_flat | 1.941x / vectorized_speedup | 1.799x / vectorized_speedup |
