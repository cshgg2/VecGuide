# VecGuide 实验汇总（cgo_strong_plain_timeout_candidates_20260604）

- 生成时间：2026-06-04T16:50:43.232707
- 函数数量：2
- 策略：strong_plain
- benchmark 协议：timeout_limited(warmup=1,timing=3,batches=3), role=timeout_limited_evidence, main_table_eligible=False, warmup=1, timing=3, batches=3, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| strong_plain | 0 | 1 | 0 | 1 | 0.646 | 0.646 | 1 |

## 跨策略对比

本次 run 只有单个策略，没有可计算的跨策略对比。

## 函数级明细

| function | severity | strong_plain |
| --- | --- | --- |
| s115 | medium | 0.646x / non_vectorized_slowdown |
| s235 | medium | NA / correctness_failed |
