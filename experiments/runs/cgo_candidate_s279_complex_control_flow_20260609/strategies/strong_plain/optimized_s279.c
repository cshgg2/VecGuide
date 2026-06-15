// Round 1 optimization for s279
//
// Optimization Strategy:
//   将循环内的 `goto` 控制流重构为等价的 `if-else` 嵌套结构，消除非结构化跳转，使编译器能识别基本块。将复杂的条件赋值语句拆分为独立的计算步骤，减少单条指令的依赖深度，从而提升自动向量化能力。
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
            real_t t_a, t_b, t_c, t_d, t_e;
            real_t val_b, val_c;

            t_a = a[i];
            t_b = b[i];
            t_c = c[i];
            t_d = d[i];
            t_e = e[i];

            if (t_a > (real_t)0.) {
                // Path corresponding to L20
                val_c = -t_c + t_e * t_e;
                val_b = t_b;
            } else {
                // Path corresponding to the else branch
                val_b = -t_b + t_d * t_d;
                if (val_b <= t_a) {
                    // goto L30
                    val_c = t_c;
                } else {
                    val_c = t_c + t_d * t_e;
                }
            }

            // L30
            a[i] = val_b + val_c * t_d;
            b[i] = val_b;
            c[i] = val_c;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}