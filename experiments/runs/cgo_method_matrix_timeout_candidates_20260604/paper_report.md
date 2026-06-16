# VecGuide 实验汇总（cgo_method_matrix_timeout_candidates_20260604）

- 生成时间：2026-06-04T17:56:39.694282
- 函数数量：2
- 策略：diagnostic_only, case_card_only, full_method
- benchmark 协议：timeout_limited(warmup=1,timing=3,batches=3), role=timeout_limited_evidence, main_table_eligible=False, warmup=1, timing=3, batches=3, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic_only | 0 | 2 | 1 | 2 | 2.598 | 2.598 | 0 |
| case_card_only | 0 | 2 | 2 | 2 | 12.789 | 12.789 | 0 |
| full_method | 0 | 2 | 2 | 2 | 14.316 | 14.316 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| diagnostic_only_vs_case_card_only | 2 | 1 | 0 | 1 | -10.191 |
| diagnostic_only_vs_full_method | 2 | 1 | 0 | 1 | -11.719 |
| case_card_only_vs_full_method | 2 | 0 | 0 | 2 | -1.527 |

## 函数级明细

| function | severity | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- |
| s115 | medium | 4.153x / vectorized_speedup | 4.018x / vectorized_speedup | 4.105x / vectorized_speedup |
| s235 | medium | 1.042x / non_vectorized_speedup | 21.561x / vectorized_speedup | 24.528x / vectorized_speedup |
