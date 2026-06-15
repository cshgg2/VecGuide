// Round 1 optimization for s274
//
// Optimization Strategy:
//   将循环内的条件分支转换为使用三元运算符的标量表达式，消除控制流对自动向量化的阻碍。这种改写在语义上完全等价，且允许编译器生成掩码指令或无分支代码，从而安全地进行向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s274(struct args_t * func_args)
{

//    control flow
//    complex loop with dependent conditional

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            real_t temp_a = c[i] + e[i] * d[i];
            a[i] = (temp_a > (real_t)0.) ? temp_a : d[i] * e[i];
            b[i] = (temp_a > (real_t)0.) ? temp_a + b[i] : b[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}