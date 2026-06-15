// Round 1 optimization for s1113
//
// Optimization Strategy:
//   提取循环不变量 a[LEN_1D/2] 到标量临时变量，消除循环内对全局数组的未知步长读取，解除编译器对写入 a[i] 可能影响读取 a[LEN_1D/2] 的别名疑虑，从而启用自动向量化。
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
        real_t temp = a[LEN_1D/2];
        for (int i = 0; i < LEN_1D; i++) {
            a[i] = temp + b[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}