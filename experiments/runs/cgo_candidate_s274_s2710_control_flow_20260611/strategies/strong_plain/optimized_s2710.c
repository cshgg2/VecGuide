// Round 1 optimization for s2710
//
// Optimization Strategy:
//   将内层循环中的嵌套 if-else 结构改写为使用临时变量计算结果，最后统一写入数组，消除循环内的控制流依赖，从而便于编译器进行自动向量化。
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
            real_t a_val, b_val, c_val;
            real_t cond = a[i] > b[i];
            if (cond) {
                a_val = a[i] + b[i] * d[i];
                if (LEN_1D > 10) {
                    c_val = c[i] + d[i] * d[i];
                } else {
                    c_val = d[i] * e[i] + (real_t)1.;
                }
            } else {
                b_val = a[i] + e[i] * e[i];
                if (x > (real_t)0.) {
                    c_val = a[i] + d[i] * d[i];
                } else {
                    c_val = c[i] + e[i] * e[i];
                }
            }
            if (cond) {
                a[i] = a_val;
                c[i] = c_val;
            } else {
                b[i] = b_val;
                c[i] = c_val;
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}