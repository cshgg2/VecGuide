# ACPO-LLM 实验汇总（cgo_strong_plain_key_cases_20260603）

- 生成时间：2026-06-04T00:15:24.059888
- 函数数量：5
- 策略：strong_plain
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| strong_plain | 0 | 5 | 3 | 4 | 3.036 | 2.551 | 0 |

## 跨策略对比

本次 run 只有单个策略，没有可计算的跨策略对比。

## 函数级明细

| function | severity | strong_plain |
| --- | --- | --- |
| s1244 | - | 2.700x / vectorized_speedup |
| s231 | - | NA / benchmark_failed |
| s275 | - | 6.042x / non_vectorized_speedup |
| s278 | - | 1.000x / non_vectorized_flat |
| s293 | - | 2.403x / vectorized_speedup |
