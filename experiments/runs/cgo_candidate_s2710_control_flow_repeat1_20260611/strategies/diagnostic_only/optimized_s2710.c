// Round 1 optimization for s2710
//
// Optimization Strategy:
//   识别到循环内部包含复杂的嵌套条件分支和标量变量 x 的依赖，阻碍了自动向量化。采用 restrict 关键字消除指针别名顾虑，并使用 #pragma clang loop vectorize(enable) 指示编译器对内层循环进行强制向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s2710(struct args_t * func_args)
{

//    control flow
//    scalar and vector ifs

    int x = *(int*)func_args->arg_info;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations/2; nl++) {
        real_t * __restrict__ a_ptr = a;
        real_t * __restrict__ b_ptr = b;
        real_t * __restrict__ c_ptr = c;
        real_t * __restrict__ d_ptr = d;
        real_t * __restrict__ e_ptr = e;

        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            if (a_ptr[i] > b_ptr[i]) {
                a_ptr[i] += b_ptr[i] * d_ptr[i];
                if (LEN_1D > 10) {
                    c_ptr[i] += d_ptr[i] * d_ptr[i];
                } else {
                    c_ptr[i] = d_ptr[i] * e_ptr[i] + (real_t)1.;
                }
            } else {
                b_ptr[i] = a_ptr[i] + e_ptr[i] * e_ptr[i];
                if (x > (real_t)0.) {
                    c_ptr[i] = a_ptr[i] + d_ptr[i] * d_ptr[i];
                } else {
                    c_ptr[i] += e_ptr[i] * e_ptr[i];
                }
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}