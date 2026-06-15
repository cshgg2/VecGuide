// Round 1 optimization for s274
//
// Optimization Strategy:
//   识别到循环内条件分支阻碍了向量化。采用谓词执行技术，将 if-else 分支转换为三元条件运算符，消除控制流依赖，使编译器能够进行 if-conversion 向量化。
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
            a[i] = temp_a;
            b[i] = (temp_a > (real_t)0.) ? (temp_a + b[i]) : b[i];
            a[i] = (temp_a > (real_t)0.) ? temp_a : (d[i] * e[i]);
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}