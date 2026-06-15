// Round 1 optimization for s293
//
// Optimization Strategy:
//   识别到循环内写 `a[i]` 且读 `a[0]` 的自依赖模式。采用循环剥离技术，将 `i=0` 的迭代单独处理，并将 `a[0]` 的值缓存为标量，使剩余循环变为无依赖的广播赋值，从而实现向量化。
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
        // Peel the first iteration to capture the value of a[0] before it is potentially overwritten
        // and to resolve the loop-carried dependence for the compiler.
        real_t first_val = a[0];
        a[0] = first_val;

        // Vectorize the rest of the loop using the cached scalar value.
        // This is safe because i=0 is handled, and i>0 does not write to a[0].
        #pragma clang loop vectorize(enable)
        for (int i = 1; i < LEN_1D; i++) {
            a[i] = first_val;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}