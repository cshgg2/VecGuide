// Round 1 optimization for s291
//
// Optimization Strategy:
//   识别到内层循环存在跨迭代数据依赖（`im1` 更新依赖于当前迭代索引 `i`），导致无法直接向量化。采用循环剥离策略，将首尾元素处理剥离出主循环，使主循环变为规整的滑动窗口模式，消除循环携带依赖，从而允许编译器对主循环进行自动向量化。
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

    int im1;
    for (int nl = 0; nl < 2*iterations; nl++) {
        // Peel the first iteration to handle the wrap-around case (im1 = LEN_1D-1)
        // This sets up the state for the vectorizable loop
        im1 = LEN_1D - 1;
        a[0] = (b[0] + b[im1]) * (real_t).5;
        
        // Main loop: regular dependency pattern a[i] = (b[i] + b[i-1]) * 0.5
        // No loop-carried dependencies on 'a' or 'b' writes, only on read indices.
        // This structure is friendly to auto-vectorization.
        #pragma clang loop vectorize(enable)
        for (int i = 1; i < LEN_1D; i++) {
            a[i] = (b[i] + b[i-1]) * (real_t).5;
        }
        
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}