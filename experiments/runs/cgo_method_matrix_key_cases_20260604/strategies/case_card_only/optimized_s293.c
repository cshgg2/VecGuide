// Round 1 optimization for s293
//
// Optimization Strategy:
//   识别到循环中存在对 a[0] 的读取与对 a[i] 的写入之间的潜在依赖。采用循环剥离技术，单独处理 i=0 的情况，并将 a[0] 缓存为标量，消除剩余循环的依赖以启用向量化。
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
        // Peel the first iteration to capture the value of a[0]
        // before the vectorized loop starts.
        real_t val = a[0];
        a[0] = val;

        // Vectorized loop: writes a[1..LEN_1D-1] using the invariant scalar 'val'.
        // This removes the unsafe dependence on a[0].
        #pragma clang loop vectorize(enable)
        for (int i = 1; i < LEN_1D; i++) {
            a[i] = val;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}