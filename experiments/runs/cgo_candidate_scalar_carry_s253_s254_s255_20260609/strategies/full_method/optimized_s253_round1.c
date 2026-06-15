// Round 1 optimization for s253
//
// Optimization Strategy:
//   识别到条件分支内的标量变量 `s` 存在跨迭代依赖，阻碍了向量化。采用标量提升技术，将 `s` 替换为临时数组 `s_arr`，消除循环携带的依赖，并结合 restrict 指针和 pragma 指令强制向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s253(struct args_t * func_args)
{

//    scalar and array expansion
//    scalar expansio assigned under if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ = a;
    real_t * __restrict__ b_ = b;
    real_t * __restrict__ c_ = c;
    real_t * __restrict__ d_ = d;

    real_t s_arr[LEN_1D];

    for (int nl = 0; nl < iterations; nl++) {
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            if (a_[i] > b_[i]) {
                s_arr[i] = a_[i] - b_[i] * d_[i];
                c_[i] += s_arr[i];
                a_[i] = s_arr[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}