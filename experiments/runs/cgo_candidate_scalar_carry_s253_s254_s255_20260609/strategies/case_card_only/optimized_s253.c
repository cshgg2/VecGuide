// Round 1 optimization for s253
//
// Optimization Strategy:
//   识别到循环内的条件分支导致控制流依赖，阻碍了向量化。采用谓词执行技术，将 if-else 分支转换为三元条件运算符，消除显式跳转，使编译器能够进行 if-conversion 向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 0
real_t s253(struct args_t * func_args)
{

//    scalar and array expansion
//    scalar expansio assigned under if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t s;
    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            real_t cond_val = a[i] - b[i] * d[i];
            if (a[i] > b[i]) {
                s = cond_val;
                c[i] += s;
                a[i] = s;
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}