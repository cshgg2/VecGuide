// Round 2 optimization for s291
//
// Optimization Strategy:
//   针对第一个循环的“跨迭代递推”障碍，采用标量提升技术，将递推变量 `im1` 的历史值存储到局部数组 `im1_hist` 中，从而消除循环携带的依赖，使该循环可向量化；第二个循环保持已优化的预计算索引访问方式。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s291_2evjbtut/minimal_s291.c:66:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s291_2evjbtut/minimal_s291.c:66:9: remark: loop not vectorized (For...
//   3. /tmp/acpo_s291_2evjbtut/minimal_s291.c:66:9: warning: loop not vectorized: th...
real_t s291(struct args_t * func_args)
{

//    loop peeling
//    wrap around variable, 1 level

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int im1;
    int im1_array[LEN_1D];
    int im1_hist[LEN_1D];
    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ b_ptr = b;

    for (int nl = 0; nl < 2*iterations; nl++) {
        im1 = LEN_1D-1;
        
        // First loop: precompute the index im1 for each iteration
        // Store the history of im1 to break the loop-carried dependency
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            im1_hist[i] = im1;
            im1_array[i] = im1;
            im1 = i;
        }

        // Second loop: perform the calculation using precomputed indices
        // This loop is now vectorizable
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            a_ptr[i] = (b_ptr[i] + b_ptr[im1_array[i]]) * (real_t).5;
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}