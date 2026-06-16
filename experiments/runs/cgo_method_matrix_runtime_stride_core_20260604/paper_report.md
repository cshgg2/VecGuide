# VecGuide 实验汇总（cgo_method_matrix_runtime_stride_core_20260604）

- 生成时间：2026-06-04T12:36:57.206478
- 函数数量：3
- 策略：diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| diagnostic_only | 0 | 2 | 1 | 2 | 1.560 | 1.560 | 1 |
| case_card_only | 0 | 3 | 0 | 3 | 1.873 | 2.186 | 0 |
| full_method | 0 | 3 | 0 | 3 | 1.911 | 2.230 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| diagnostic_only_vs_case_card_only | 2 | 1 | 0 | 1 | -0.725 |
| diagnostic_only_vs_full_method | 2 | 1 | 0 | 1 | -0.757 |
| case_card_only_vs_full_method | 3 | 0 | 1 | 2 | -0.038 |

## 函数级明细

| function | severity | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- |
| s1113 | medium | NA / correctness_failed | 1.049x / non_vectorized_speedup | 1.099x / non_vectorized_speedup |
| s122 | high | 0.868x / non_vectorized_slowdown | 2.384x / non_vectorized_speedup | 2.403x / non_vectorized_speedup |
| s172 | high | 2.251x / non_vectorized_speedup | 2.186x / non_vectorized_speedup | 2.230x / non_vectorized_speedup |
