// Round 1 optimization for s292
//
// Optimization Strategy:
//   识别到循环内存在跨迭代的索引递推依赖，阻止了向量化。采用循环拆分技术，将索引计算与数据访问分离到两个独立循环中，并使用 restrict 消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s292_lel6ke_l/minimal_s292.c:76:17: remark: loop not vectorized: lo...
//   2. /tmp/acpo_s292_lel6ke_l/minimal_s292.c:83:28: remark: loop not vectorized: un...
//   3. /tmp/acpo_s292_lel6ke_l/minimal_s292.c:75:9: remark: loop not vectorized [-Rp...
real_t s292(struct args_t * func_args)
{

//    loop peeling
//    wrap around variable, 2 levels
//    similar to S291

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int im1, im2;
    for (int nl = 0; nl < iterations; nl++) {
        // First loop: Precompute indices
        // im1 tracks i-1, im2 tracks i-2
        // We need im1[i] and im2[i] for each iteration i
        // Since im1 and im2 are just shifted versions of i, we can compute them directly
        // or use a temporary array to store the indices if the relationship was complex.
        // Here, the relationship is simple: im1[i] = i-1, im2[i] = i-2.
        // However, to strictly follow the "precompute" pattern for safety and clarity
        // without assuming the compiler can deduce the shift, we use a local array.
        // Note: TSVC arrays are global, we use a local stack array for indices.
        int idx_im1[LEN_1D];
        int idx_im2[LEN_1D];

        // Initialize indices for the first two iterations manually to match the loop logic
        // Iteration 0: im1 = LEN_1D-1, im2 = LEN_1D-2
        // Iteration 1: im1 = 0, im2 = LEN_1D-1
        // Iteration i: im1 = i-1, im2 = i-2
        
        // We can just fill the arrays based on the loop logic
        for (int i = 0; i < LEN_1D; i++) {
            if (i == 0) {
                idx_im1[i] = LEN_1D - 1;
                idx_im2[i] = LEN_1D - 2;
            } else if (i == 1) {
                idx_im1[i] = 0;
                idx_im2[i] = LEN_1D - 1;
            } else {
                idx_im1[i] = i - 1;
                idx_im2[i] = i - 2;
            }
        }

        // Second loop: Vectorized data access
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