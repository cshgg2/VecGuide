# ACPO-LLM 实验汇总（cgo_candidate_s279_complex_control_flow_20260609）

- 生成时间：2026-06-10T11:59:55.108564
- 函数数量：1
- 策略：origin, strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origin | 0 | 1 | 0 | 1 | - | - | 0 |
| strong_plain | 0 | 1 | 1 | 1 | 1.086 | 1.086 | 0 |
| diagnostic_only | 0 | 1 | 0 | 1 | 1.079 | 1.079 | 0 |
| case_card_only | 0 | 1 | 1 | 1 | 1.188 | 1.188 | 0 |
| full_method | 0 | 1 | 1 | 1 | 1.556 | 1.556 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| origin_vs_strong_plain | 1 | 0 | 0 | 1 | -0.086 |
| origin_vs_diagnostic_only | 1 | 0 | 0 | 1 | -0.079 |
| origin_vs_case_card_only | 1 | 0 | 0 | 1 | -0.188 |
| origin_vs_full_method | 1 | 0 | 0 | 1 | -0.556 |
| strong_plain_vs_diagnostic_only | 1 | 0 | 1 | 0 | 0.007 |
| strong_plain_vs_case_card_only | 1 | 0 | 0 | 1 | -0.102 |
| strong_plain_vs_full_method | 1 | 0 | 0 | 1 | -0.470 |
| diagnostic_only_vs_case_card_only | 1 | 0 | 0 | 1 | -0.108 |
| diagnostic_only_vs_full_method | 1 | 0 | 0 | 1 | -0.477 |
| case_card_only_vs_full_method | 1 | 0 | 0 | 1 | -0.369 |

## 函数级明细

| function | severity | origin | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- | --- |
| s279 | - | 1.000x / origin_not_vectorized_baseline | 1.086x / vectorized_speedup | 1.079x / non_vectorized_speedup | 1.188x / vectorized_speedup | 1.556x / vectorized_speedup |
