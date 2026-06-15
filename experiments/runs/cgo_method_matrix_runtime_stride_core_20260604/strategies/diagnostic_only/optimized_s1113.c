// Round 1 optimization for s1113
//
// Optimization Strategy:
//   识别到循环内存在写 `a[i]` 与读固定位置 `a[LEN_1D/2]` 的潜在重叠依赖。采用标量提升技术，在循环前将 `a[LEN_1D/2]` 读取到局部标量变量，消除循环内的内存依赖，从而启用向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s1113(struct args_t * func_args)
{

//    linear dependence testing
//    one iteration dependency on a(LEN_1D/2) but still vectorizable

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 2*iterations; nl++) {
        real_t temp_val = a[LEN_1D/2];
        for (int i = 0; i < LEN_1D; i++) {
            a[i] = temp_val + b[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}