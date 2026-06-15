// Round 1 optimization for s292
//
// Optimization Strategy:
//   识别到循环携带的递推依赖（im1, im2）阻止向量化。采用循环拆分技术，将索引预计算阶段与数据计算阶段分离，消除依赖关系，并使用 restrict 消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s292_wu59w0v8/minimal_s292.c:66:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s292_wu59w0v8/minimal_s292.c:66:9: remark: loop not vectorized [-Rp...
real_t s292(struct args_t * func_args)
{

//    loop peeling
//    wrap around variable, 2 levels
//    similar to S291

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int im1, im2;
    for (int nl = 0; nl < iterations; nl++) {
        im1 = LEN_1D-1;
        im2 = LEN_1D-2;
        
        // Phase 1: Precompute indices
        // Create temporary arrays to store the indices im1 and im2 for each iteration i
        // This breaks the loop-carried dependency
        int idx_im1[LEN_1D];
        int idx_im2[LEN_1D];
        
        for (int i = 0; i < LEN_1D; i++) {
            idx_im1[i] = im1;
            idx_im2[i] = im2;
            im2 = im1;
            im1 = i;
        }

        // Phase 2: Vectorized computation
        // Use precomputed indices to access array b
        real_t * __restrict__ a_ptr = a;
        real_t * __restrict__ b_ptr = b;
        
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            a_ptr[i] = (b_ptr[i] + b_ptr[idx_im1[i]] + b_ptr[idx_im2[i]]) * (real_t).333;
        }
        
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}