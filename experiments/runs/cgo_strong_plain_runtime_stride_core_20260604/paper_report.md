# ACPO-LLM 实验汇总（cgo_strong_plain_runtime_stride_core_20260604）

- 生成时间：2026-06-04T11:42:03.202523
- 函数数量：3
- 策略：strong_plain
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| strong_plain | 0 | 1 | 1 | 1 | 0.351 | 0.351 | 1 |

## 跨策略对比

本次 run 只有单个策略，没有可计算的跨策略对比。

## 函数级明细

| function | severity | strong_plain |
| --- | --- | --- |
| s1113 | medium | NA / correctness_failed |
| s122 | high | 0.351x / non_vectorized_slowdown |
| s172 | high | NA / correctness_failed |
