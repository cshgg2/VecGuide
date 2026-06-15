// Round 1 optimization for s211
//
// Optimization Strategy:
//   说明：
//   原循环中 `a[i]` 和 `b[i]` 的写入存在跨迭代依赖（`b[i]` 依赖 `b[i+1]`），阻碍了自动向量化。
//   采用循环分发策略，将原循环拆分为两个独立的循环：第一个循环计算 `a`，第二个循环计算 `b`。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 2
//   Missed loops: 0
real_t s211(struct args_t * func_args)
{

//    statement reordering
//    statement reordering allows vectorization

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 1; i < LEN_1D-1; i++) {
            a[i] = b[i - 1] + c[i] * d[i];
        }
        for (int i = 1; i < LEN_1D-1; i++) {
            b[i] = b[i + 1] - e[i] * d[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}