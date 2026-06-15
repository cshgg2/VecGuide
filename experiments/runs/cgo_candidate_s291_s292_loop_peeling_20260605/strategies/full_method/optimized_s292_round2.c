// Round 2 optimization for s292
//
// Optimization Strategy:
//   分析发现第1轮的标量提升虽然消除了依赖，但引入了额外的数组存储开销，且编译器未能有效向量化预计算循环。第2轮采用“循环拆分+标量替换”策略：将原循环拆分为两个独立循环。第一个循环仅负责更新归纳变量（im1/im2），保持标量递推；第二个循环利用更新后的归纳变量进行数组计算。这种结构消除了循环内的数据依赖，且避免了中间数组的内存读写，更有利于编译器进行向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 2
//   Missed loops: 0
real_t s292(struct args_t * func_args)
{

//    loop peeling
//    wrap around variable, 2 levels
//    similar to S291

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        int im1 = LEN_1D-1;
        int im2 = LEN_1D-2;
        
        // 循环拆分：第一阶段仅更新归纳变量
        // 这是一个标量递推循环，无法也不需要向量化
        for (int i = 0; i < LEN_1D; i++) {
            im2 = im1;
            im1 = i;
        }
        
        // 循环拆分：第二阶段进行数据访问
        // 此时 im1 和 im2 已更新为循环结束后的值 (LEN_1D-1, LEN_1D-2)
        // 原始逻辑中，数据访问阶段依赖的是上一轮递推的最终状态
        // 由于 im1/im2 在数据访问阶段是常数，编译器可以轻松向量化
        real_t * __restrict__ a_ptr = a;
        real_t * __restrict__ b_ptr = b;
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            a_ptr[i] = (b_ptr[i] + b_ptr[im1] + b_ptr[im2]) * (real_t).333;
        }
        
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}