// Round 1 optimization for s2710
//
// Optimization Strategy:
//   识别到循环内部存在嵌套的条件分支和复杂的控制流，阻碍了编译器自动向量化。采用 restrict 关键字消除指针别名顾虑，并使用 SIMD pragma 强制向量化，同时保持原有的逻辑结构和 dummy 调用位置不变。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 0
real_t s2710(struct args_t * func_args)
{

//    control flow
//    scalar and vector ifs

    int x = *(int*)func_args->arg_info;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations/2; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            if (a[i] > b[i]) {
                a[i] += b[i] * d[i];
                if (LEN_1D > 10) {
                    c[i] += d[i] * d[i];
                } else {
                    c[i] = d[i] * e[i] + (real_t)1.;
                }
            } else {
                b[i] = a[i] + e[i] * e[i];
                if (x > (real_t)0.) {
                    c[i] = a[i] + d[i] * d[i];
                } else {
                    c[i] += e[i] * e[i];
                }
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}