# ACPO-LLM 实验汇总（cgo_candidate_s2710_control_flow_repeat1_20260611）

- 生成时间：2026-06-11T22:47:56.612317
- 函数数量：1
- 策略：origin, strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origin | 0 | 1 | 0 | 1 | - | - | 0 |
| strong_plain | 0 | 1 | 1 | 1 | 1.728 | 1.728 | 0 |
| diagnostic_only | 0 | 1 | 1 | 1 | 0.404 | 0.404 | 1 |
| case_card_only | 0 | 1 | 1 | 1 | 1.138 | 1.138 | 0 |
| full_method | 0 | 1 | 1 | 1 | 1.655 | 1.655 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| origin_vs_strong_plain | 1 | 0 | 0 | 1 | -0.728 |
| origin_vs_diagnostic_only | 1 | 1 | 0 | 0 | 0.596 |
| origin_vs_case_card_only | 1 | 0 | 0 | 1 | -0.138 |
| origin_vs_full_method | 1 | 0 | 0 | 1 | -0.655 |
| strong_plain_vs_diagnostic_only | 1 | 1 | 0 | 0 | 1.324 |
| strong_plain_vs_case_card_only | 1 | 1 | 0 | 0 | 0.590 |
| strong_plain_vs_full_method | 1 | 1 | 0 | 0 | 0.074 |
| diagnostic_only_vs_case_card_only | 1 | 0 | 0 | 1 | -0.734 |
| diagnostic_only_vs_full_method | 1 | 0 | 0 | 1 | -1.251 |
| case_card_only_vs_full_method | 1 | 0 | 0 | 1 | -0.516 |

## 函数级明细

| function | severity | origin | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- | --- |
| s2710 | - | 1.000x / origin_not_vectorized_baseline | 1.728x / vectorized_speedup | 0.404x / vectorized_slowdown | 1.138x / vectorized_speedup | 1.655x / vectorized_speedup |
