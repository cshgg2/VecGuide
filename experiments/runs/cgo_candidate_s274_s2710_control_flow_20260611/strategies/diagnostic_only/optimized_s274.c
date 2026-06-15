// Round 1 optimization for s274
//
// Optimization Strategy:
//   识别到循环内存在对数组 a 的写后读依赖（流依赖），阻碍了向量化。采用标量提升技术，将 a[i] 提升为局部标量变量，消除跨迭代依赖，并使用 restrict 消除指针别名顾虑。
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

    real_t * __restrict__ a_p = a;
    real_t * __restrict__ b_p = b;
    real_t * __restrict__ c_p = c;
    real_t * __restrict__ d_p = d;
    real_t * __restrict__ e_p = e;

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            real_t a_val = c_p[i] + e_p[i] * d_p[i];
            if (a_val > (real_t)0.) {
                b_p[i] = a_val + b_p[i];
            } else {
                a_val = d_p[i] * e_p[i];
            }
            a_p[i] = a_val;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}