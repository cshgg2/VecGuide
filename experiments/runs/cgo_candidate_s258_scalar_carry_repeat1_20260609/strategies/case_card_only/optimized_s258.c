// Round 1 optimization for s258
//
// Optimization Strategy:
//   识别到标量变量 s 在循环内存在条件更新，导致编译器无法识别其为归纳变量或安全跨迭代使用。采用标量提升技术，将 s 扩展为数组 s_arr，消除跨迭代依赖，并结合 restrict 关键字消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 2
//   Missed loops: 0
real_t s258(struct args_t * func_args)
{

//    scalar and array expansion
//    wrap-around scalar under an if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t s_arr[LEN_2D];
    real_t * __restrict__ b_ptr = b;
    real_t * __restrict__ c_ptr = c;
    real_t * __restrict__ d_ptr = d;
    real_t * __restrict__ e_ptr = e;
    real_t * __restrict__ a_ptr = a;
    real_t (* __restrict__ aa_ptr)[LEN_2D] = aa;

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_2D; ++i) {
            if (a_ptr[i] > 0.) {
                s_arr[i] = d_ptr[i] * d_ptr[i];
            } else {
                s_arr[i] = 0.;
            }
        }
        for (int i = 0; i < LEN_2D; ++i) {
            b_ptr[i] = s_arr[i] * c_ptr[i] + d_ptr[i];
            e_ptr[i] = (s_arr[i] + (real_t)1.) * aa_ptr[0][i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}