# VecGuide 实验汇总（cgo_minimal_evidence_p0_s1232_clang17restored_20260619）

- 生成时间：2026-06-19T13:38:26.495081
- 函数数量：1
- 策略：origin, strong_plain, diagnostic_only, case_card_only, full_method
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origin | 0 | 1 | 0 | 1 | - | - | 0 |
| strong_plain | 0 | 1 | 1 | 0 | - | - | 0 |
| diagnostic_only | 0 | 1 | 1 | 0 | - | - | 0 |
| case_card_only | 0 | 1 | 1 | 0 | - | - | 0 |
| full_method | 0 | 1 | 1 | 1 | 24.866 | 24.866 | 0 |

## 跨策略对比

| pair | comparable | better | tie | worse | avg_delta_speedup |
| --- | --- | --- | --- | --- | --- |
| origin_vs_strong_plain | 0 | 0 | 0 | 0 | - |
| origin_vs_diagnostic_only | 0 | 0 | 0 | 0 | - |
| origin_vs_case_card_only | 0 | 0 | 0 | 0 | - |
| origin_vs_full_method | 1 | 0 | 0 | 1 | -23.866 |
| strong_plain_vs_diagnostic_only | 0 | 0 | 0 | 0 | - |
| strong_plain_vs_case_card_only | 0 | 0 | 0 | 0 | - |
| strong_plain_vs_full_method | 0 | 0 | 0 | 0 | - |
| diagnostic_only_vs_case_card_only | 0 | 0 | 0 | 0 | - |
| diagnostic_only_vs_full_method | 0 | 0 | 0 | 0 | - |
| case_card_only_vs_full_method | 0 | 0 | 0 | 0 | - |

## 函数级明细

| function | severity | origin | strong_plain | diagnostic_only | case_card_only | full_method |
| --- | --- | --- | --- | --- | --- | --- |
| s1232 | - | 1.000x / origin_not_vectorized_baseline | NA / benchmark_failed | NA / benchmark_failed | NA / benchmark_failed | 24.866x / vectorized_speedup |
