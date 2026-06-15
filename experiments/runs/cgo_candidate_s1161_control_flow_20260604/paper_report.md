# ACPO-LLM 实验汇总（cgo_candidate_s1161_control_flow_20260604）

- 生成时间：2026-06-04T23:39:43.527355
- 函数数量：1
- 策略：strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| strong_plain | 0 | 1 | 0 | 1 | 1.112 | 1.112 | 0 |
| diagnostic_only | 0 | 1 | 0 | 1 | 1.091 | 1.091 | 0 |
| case_card_only | 0 | 1 | 0 | 1 | 1.073 | 1.073 | 0 |
| full_method | 0 | 1 | 0 | 1 | 1.101 | 1.101 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| strong_plain_vs_diagnostic_only | 1 | 1 | 0 | 0 | 0.021 |
| strong_plain_vs_case_card_only | 1 | 1 | 0 | 0 | 0.039 |
| strong_plain_vs_full_method | 1 | 0 | 1 | 0 | 0.011 |
| diagnostic_only_vs_case_card_only | 1 | 0 | 1 | 0 | 0.018 |
| diagnostic_only_vs_full_method | 1 | 0 | 1 | 0 | -0.009 |
| case_card_only_vs_full_method | 1 | 0 | 0 | 1 | -0.027 |

## 函数级明细

| function | severity | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- |
| s1161 | medium | 1.112x / non_vectorized_speedup | 1.091x / non_vectorized_speedup | 1.073x / non_vectorized_speedup | 1.101x / non_vectorized_speedup |
