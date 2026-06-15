// Round 1 optimization for s293
//
// Optimization Strategy:
//   提取循环不变量 a[0] 到标量临时变量，消除循环内对全局数组的读取依赖，使内层循环变为纯写入操作，从而允许编译器进行自动向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s293(struct args_t * func_args)
{

//    loop peeling
//    a(i)=a(0) with actual dependence cycle, loop is vectorizable

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 4*iterations; nl++) {
        real_t val = a[0];
        for (int i = 0; i < LEN_1D; i++) {
            a[i] = val;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}