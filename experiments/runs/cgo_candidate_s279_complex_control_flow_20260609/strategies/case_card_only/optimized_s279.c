// Round 1 optimization for s279
//
// Optimization Strategy:
//   识别到循环内复杂的 `goto` 控制流阻碍了向量化。采用结构化重构，将 `goto` 逻辑转换为等价的 `if-else` 条件分支，并使用三元运算符（?:）进行谓词执行，消除控制流依赖，使编译器能够进行向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s279(struct args_t * func_args)
{

//    control flow
//    vector if/gotos

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations/2; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            real_t ai = a[i];
            real_t bi = b[i];
            real_t ci = c[i];
            real_t di = d[i];
            real_t ei = e[i];

            if (ai > (real_t)0.) {
                ci = -ci + ei * ei;
            } else {
                bi = -bi + di * di;
                if (bi <= ai) {
                    // Do nothing, ci remains unchanged
                } else {
                    ci += di * ei;
                }
            }
            ai = bi + ci * di;

            a[i] = ai;
            b[i] = bi;
            c[i] = ci;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}