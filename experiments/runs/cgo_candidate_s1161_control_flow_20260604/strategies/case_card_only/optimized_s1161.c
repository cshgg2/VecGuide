// Round 1 optimization for s1161
//
// Optimization Strategy:
//   识别到循环内部使用 `goto` 构成的互斥分支结构阻碍了向量化。采用结构化重构技术，将 `goto` 逻辑转换为标准的 `if-else` 块，消除控制流跳转，使编译器能够进行 if-conversion 从而实现向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s1161_xvz_utmx/minimal_s1161.c:45:8: remark: loop not vectorized: c...
//   2. /tmp/acpo_s1161_xvz_utmx/minimal_s1161.c:56:9: remark: loop not vectorized [-...
real_t s1161(struct args_t * func_args)
{

//    control flow
//    tests for recognition of loop independent dependences
//    between statements in mutually exclusive regions.

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D-1; ++i) {
            if (c[i] < (real_t)0.) {
                b[i] = a[i] + d[i] * d[i];
            } else {
                a[i] = c[i] + d[i] * e[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}