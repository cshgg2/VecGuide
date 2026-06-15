// Round 3 optimization for s292
//
// Optimization Strategy:
//   回退到第2轮的正确标量提升方案，但针对预计算循环的向量化失败进行针对性修复。移除预计算循环上的强制 pragma，因为该循环包含跨迭代依赖（im2=im1, im1=i），无法向量化。保留数据访问循环的向量化，该循环已成功向量化。通过移除无效的强制指令，消除编译器警告，同时保持代码语义正确。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s292_qe3a7xb5/minimal_s292.c:66:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s292_qe3a7xb5/minimal_s292.c:66:9: remark: loop not vectorized [-Rp...
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
        // 移除 vectorize(enable)，因为此循环包含跨迭代依赖 (im2=im1, im1=i)，无法向量化
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