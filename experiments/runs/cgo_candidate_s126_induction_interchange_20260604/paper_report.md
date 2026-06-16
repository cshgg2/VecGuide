# VecGuide 实验汇总（cgo_candidate_s126_induction_interchange_20260604）

- 生成时间：2026-06-04T19:30:12.025878
- 函数数量：1
- 策略：strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| strong_plain | 0 | 0 | 0 | 0 | - | - | 0 |
| diagnostic_only | 0 | 1 | 0 | 1 | 0.996 | 0.996 | 1 |
| case_card_only | 0 | 1 | 0 | 1 | 1.000 | 1.000 | 0 |
| full_method | 0 | 1 | 0 | 1 | 1.035 | 1.035 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| strong_plain_vs_diagnostic_only | 0 | 0 | 0 | 0 | - |
| strong_plain_vs_case_card_only | 0 | 0 | 0 | 0 | - |
| strong_plain_vs_full_method | 0 | 0 | 0 | 0 | - |
| diagnostic_only_vs_case_card_only | 1 | 0 | 1 | 0 | -0.004 |
| diagnostic_only_vs_full_method | 1 | 0 | 0 | 1 | -0.039 |
| case_card_only_vs_full_method | 1 | 0 | 0 | 1 | -0.035 |

## 函数级明细

| function | severity | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- |
| s126 | medium | NA / correctness_failed | 0.996x / non_vectorized_flat | 1.000x / non_vectorized_flat | 1.035x / non_vectorized_speedup |
