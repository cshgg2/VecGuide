// Round 1 optimization for s1161
//
// Optimization Strategy:
//   识别到 goto 语句导致的控制流阻塞和数组别名问题。采用条件选择表达式消除显式跳转，将控制流转换为数据流，并使用 restrict 关键字消除指针别名顾虑，以启用向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s1161_iwakmxvo/minimal_s1161.c:45:8: remark: loop not vectorized: c...
//   2. /tmp/acpo_s1161_iwakmxvo/minimal_s1161.c:62:9: remark: loop not vectorized [-...
real_t s1161(struct args_t * func_args)
{

//    control flow
//    tests for recognition of loop independent dependences
//    between statements in mutually exclusive regions.

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        real_t * __restrict__ a_ptr = a;
        real_t * __restrict__ b_ptr = b;
        real_t * __restrict__ c_ptr = c;
        real_t * __restrict__ d_ptr = d;
        real_t * __restrict__ e_ptr = e;

        for (int i = 0; i < LEN_1D-1; ++i) {
            if (c_ptr[i] < (real_t)0.) {
                b_ptr[i] = a_ptr[i] + d_ptr[i] * d_ptr[i];
            } else {
                a_ptr[i] = c_ptr[i] + d_ptr[i] * e_ptr[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}