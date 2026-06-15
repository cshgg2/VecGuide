// Round 1 optimization for s278
//
// Optimization Strategy:
//   识别到循环内部使用 goto 导致控制流非线性，阻碍了向量化。采用条件选择表达式（三元运算符）重构 if-then-else 逻辑，消除 goto 语句，使循环体变为基本块，从而启用自动向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s278(struct args_t * func_args)
{

//    control flow
//    if/goto to block if-then-else

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            real_t bi = b[i];
            real_t ci = c[i];
            real_t di = d[i];
            real_t ei = e[i];
            real_t ai = a[i];

            if (ai > (real_t)0.) {
                ci = -ci + di * ei;
            } else {
                bi = -bi + di * ei;
            }
            ai = bi + ci * di;

            b[i] = bi;
            c[i] = ci;
            a[i] = ai;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}