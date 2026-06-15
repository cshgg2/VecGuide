// Round 1 optimization for s292
//
// Optimization Strategy:
//   识别到循环携带的归纳变量依赖（im1/im2 递推更新）阻止了向量化。由于依赖是固有的且涉及跨迭代状态，采用标量提升技术，将递推变量 im1/im2 转换为数组，消除循环内的数据依赖，从而允许向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s292_c018ramr/minimal_s292.c:66:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s292_c018ramr/minimal_s292.c:66:9: remark: loop not vectorized (For...
//   3. /tmp/acpo_s292_c018ramr/minimal_s292.c:66:9: warning: loop not vectorized: th...
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
        
        // Scalar Promotion: 将递推变量转换为数组以消除循环携带依赖
        int im1_arr[LEN_1D];
        int im2_arr[LEN_1D];
        
        // 预计算索引阶段
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            im1_arr[i] = im1;
            im2_arr[i] = im2;
            im2 = im1;
            im1 = i;
        }
        
        // 数据访问阶段
        real_t * __restrict__ a_ptr = a;
        real_t * __restrict__ b_ptr = b;
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            a_ptr[i] = (b_ptr[i] + b_ptr[im1_arr[i]] + b_ptr[im2_arr[i]]) * (real_t).333;
        }
        
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}