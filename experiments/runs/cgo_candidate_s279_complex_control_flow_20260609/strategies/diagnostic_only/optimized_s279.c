// Round 1 optimization for s279
//
// Optimization Strategy:
//   识别到循环内部存在 goto 跳转导致的控制流依赖，阻碍了向量化。采用结构化重构技术，将 if-goto 逻辑转换为等价的 if-else 条件分支，消除显式跳转，并使用 restrict 关键字消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 0
real_t s279(struct args_t * func_args)
{

//    control flow
//    vector if/gotos

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations/2; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            real_t * __restrict__ a_ptr = a;
            real_t * __restrict__ b_ptr = b;
            real_t * __restrict__ c_ptr = c;
            real_t * __restrict__ d_ptr = d;
            real_t * __restrict__ e_ptr = e;

            if (a_ptr[i] > (real_t)0.) {
                c_ptr[i] = -c_ptr[i] + e_ptr[i] * e_ptr[i];
            } else {
                b_ptr[i] = -b_ptr[i] + d_ptr[i] * d_ptr[i];
                if (b_ptr[i] <= a_ptr[i]) {
                    // Do nothing, corresponds to falling through to L30
                } else {
                    c_ptr[i] += d_ptr[i] * e_ptr[i];
                }
            }
            a_ptr[i] = b_ptr[i] + c_ptr[i] * d_ptr[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}