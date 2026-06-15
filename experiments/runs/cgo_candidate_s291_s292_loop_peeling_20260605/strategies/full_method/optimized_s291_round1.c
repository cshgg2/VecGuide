// Round 1 optimization for s291
//
// Optimization Strategy:
//   识别到变量 `im1` 在循环中存在跨迭代递推依赖（`im1 = i`），导致编译器无法向量化。采用循环拆分技术，将索引计算与数据访问分离到两个循环中：第一个循环预计算索引，第二个循环执行向量化计算。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s291_ly66wf4x/minimal_s291.c:64:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s291_ly66wf4x/minimal_s291.c:64:9: remark: loop not vectorized [-Rp...
real_t s291(struct args_t * func_args)
{

//    loop peeling
//    wrap around variable, 1 level

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int im1;
    int im1_array[LEN_1D];
    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ b_ptr = b;

    for (int nl = 0; nl < 2*iterations; nl++) {
        im1 = LEN_1D-1;
        
        // First loop: precompute the index im1 for each iteration
        // This removes the recurrence from the data access loop
        for (int i = 0; i < LEN_1D; i++) {
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