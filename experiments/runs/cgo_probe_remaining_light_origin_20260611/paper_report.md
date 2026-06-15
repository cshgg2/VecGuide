# ACPO-LLM 实验汇总（cgo_probe_remaining_light_origin_20260611）

- 生成时间：2026-06-11T23:11:49.065232
- 函数数量：4
- 策略：origin
- benchmark 协议：formal(warmup=3,timing=10,batches=5), role=formal_main_table, main_table_eligible=True, warmup=3, timing=10, batches=5, arg_info=per-function protocol (default uses (1,1); parameterized kernels use verifier-defined multi-case sets)

## 策略级汇总

| strategy | exit | correctness_passed | fully_vectorized | benchmark_success | avg_speedup | median_speedup | negative_opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| origin | 0 | 4 | 3 | 4 | - | - | 0 |

## 跨策略对比

本次 run 只有单个策略，没有可计算的跨策略对比。

## 函数级明细

| function | severity | origin |
| --- | --- | --- |
| s1221 | - | 1.000x / origin_vectorized_baseline |
| s1232 | - | 1.000x / origin_not_vectorized_baseline |
| s257 | - | 1.000x / origin_vectorized_baseline |
| s3251 | - | 1.000x / origin_vectorized_baseline |
