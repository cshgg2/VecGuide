// Best optimization for s292
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