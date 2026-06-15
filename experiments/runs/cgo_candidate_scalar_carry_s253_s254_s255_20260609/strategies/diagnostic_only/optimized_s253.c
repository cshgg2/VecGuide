// Round 1 optimization for s253
//
// Optimization Strategy:
//   识别到标量变量 `s` 在条件分支内被定义并跨迭代使用，导致编译器无法确定其是否具有流依赖。采用标量提升技术，将 `s` 替换为数组 `s_arr`，消除跨迭代依赖，并使用 restrict 关键字消除指针别名顾虑，从而启用向量化。
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

    real_t s_arr[LEN_1D];
    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ b_ptr = b;
    real_t * __restrict__ c_ptr = c;
    real_t * __restrict__ d_ptr = d;

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            if (a_ptr[i] > b_ptr[i]) {
                s_arr[i] = a_ptr[i] - b_ptr[i] * d_ptr[i];
                c_ptr[i] += s_arr[i];
                a_ptr[i] = s_arr[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}