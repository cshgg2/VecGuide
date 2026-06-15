// Round 3 optimization for s291
//
// Optimization Strategy:
//   分析发现第一个循环中 `im1` 的递推模式（`im1 = i`）实际上是一个简单的归纳变量，其历史值 `im1_hist[i]` 在数学上等价于 `i-1`（首项为 `LEN_1D-1`）。利用这一数学特性，将第一个循环替换为简单的初始化赋值，彻底消除循环携带依赖；第二个循环利用 `im1` 的数学等价性，直接使用 `i-1` 作为索引，从而移除中间数组 `im1_array`，实现完全向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s291(struct args_t * func_args)
{

//    loop peeling
//    wrap around variable, 1 level

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ b_ptr = b;

    for (int nl = 0; nl < 2*iterations; nl++) {
        
        // The recurrence im1 = i implies im1_hist[i] = i-1 (with im1_hist[0] = LEN_1D-1).
        // We can initialize the first element directly to match the original semantic.
        // This eliminates the loop-carried dependency.
        int im1_hist_0 = LEN_1D - 1;

        // Main loop: vectorized using the mathematical equivalence im1 = i-1
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            int idx = (i == 0) ? im1_hist_0 : (i - 1);
            a_ptr[i] = (b_ptr[i] + b_ptr[idx]) * (real_t).5;
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}