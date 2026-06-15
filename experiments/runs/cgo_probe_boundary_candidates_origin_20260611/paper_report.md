# ACPO-LLM 实验汇总（cgo_probe_boundary_candidates_origin_20260611）

- 生成时间：2026-06-11T17:42:36.887932
- 函数数量：6
- 策略：origin
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origin | 0 | 6 | 0 | 5 | - | - | 0 |

## 跨策略对比

本次 run 只有单个策略，没有可计算的跨策略对比。

## 函数级明细

| function | severity | origin |
| --- | --- | --- |
| s242 | - | 1.000x / origin_not_vectorized_baseline |
| s3112 | - | 1.000x / origin_not_vectorized_baseline |
| s3113 | - | NA / origin_benchmark_failed |
| s341 | - | 1.000x / origin_not_vectorized_baseline |
| s342 | - | 1.000x / origin_not_vectorized_baseline |
| s343 | - | 1.000x / origin_not_vectorized_baseline |
