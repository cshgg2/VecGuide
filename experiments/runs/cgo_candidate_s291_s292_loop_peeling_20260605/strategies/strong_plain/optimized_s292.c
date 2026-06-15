// Round 1 optimization for s292
//
// Optimization Strategy:
//   该循环存在跨迭代的数据依赖（`im1` 和 `im2` 携带前两次迭代的索引），导致无法直接向量化。通过循环剥离技术，将前两次迭代单独处理，使得主循环中的索引计算变为固定偏移量（`i-1` 和 `i-2`），从而消除循环携带依赖，允许编译器对主循环进行自动向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
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
        
        // Peeling the first two iterations to resolve loop-carried dependencies
        // Iteration i = 0
        a[0] = (b[0] + b[im1] + b[im2]) * (real_t).333;
        im2 = im1;
        im1 = 0;

        // Iteration i = 1
        a[1] = (b[1] + b[im1] + b[im2]) * (real_t).333;
        im2 = im1;
        im1 = 1;

        // Main loop: dependencies are resolved, im1=i-1, im2=i-2
        // Vectorizable
        for (int i = 2; i < LEN_1D; i++) {
            a[i] = (b[i] + b[i-1] + b[i-2]) * (real_t).333;
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}