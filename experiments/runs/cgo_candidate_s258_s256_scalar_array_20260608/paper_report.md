# ACPO-LLM 实验汇总（cgo_candidate_s258_s256_scalar_array_20260608）

- 生成时间：2026-06-08T23:21:53.619844
- 函数数量：2
- 策略：origin, strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origin | 0 | 2 | 0 | 2 | - | - | 0 |
| strong_plain | 0 | 1 | 0 | 1 | 1.802 | 1.802 | 0 |
| diagnostic_only | 0 | 1 | 1 | 1 | 4.347 | 4.347 | 0 |
| case_card_only | 0 | 2 | 1 | 2 | 3.061 | 3.061 | 0 |
| full_method | 0 | 2 | 1 | 2 | 3.212 | 3.212 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| origin_vs_strong_plain | 1 | 0 | 0 | 1 | -0.802 |
| origin_vs_diagnostic_only | 1 | 0 | 0 | 1 | -3.347 |
| origin_vs_case_card_only | 2 | 0 | 0 | 2 | -2.061 |
| origin_vs_full_method | 2 | 0 | 0 | 2 | -2.212 |
| strong_plain_vs_diagnostic_only | 0 | 0 | 0 | 0 | - |
| strong_plain_vs_case_card_only | 1 | 0 | 1 | 0 | 0.005 |
| strong_plain_vs_full_method | 1 | 0 | 0 | 1 | -0.055 |
| diagnostic_only_vs_case_card_only | 1 | 1 | 0 | 0 | 0.022 |
| diagnostic_only_vs_full_method | 1 | 0 | 0 | 1 | -0.221 |
| case_card_only_vs_full_method | 2 | 0 | 0 | 2 | -0.152 |

## 函数级明细

| function | severity | origin | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- | --- |
| s256 | - | 1.000x / origin_not_vectorized_baseline | 1.802x / non_vectorized_speedup | NA / correctness_failed | 1.797x / non_vectorized_speedup | 1.857x / non_vectorized_speedup |
| s258 | - | 1.000x / origin_not_vectorized_baseline | NA / correctness_failed | 4.347x / vectorized_speedup | 4.325x / vectorized_speedup | 4.567x / vectorized_speedup |
