// Round 1 optimization for s211
//
// Optimization Strategy:
//   识别到循环内存在跨迭代的数组依赖（b[i] 依赖 b[i+1]），这属于真依赖，无法直接向量化。采用循环拆分技术，将依赖链断裂，拆分为两个独立的可向量化循环，并添加 restrict 和 pragma 指令。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 2
//   Missed loops: 0
real_t s211(struct args_t * func_args)
{

//    statement reordering
//    statement reordering allows vectorization

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ b_ptr = b;
    real_t * __restrict__ c_ptr = c;
    real_t * __restrict__ d_ptr = d;
    real_t * __restrict__ e_ptr = e;

    for (int nl = 0; nl < iterations; nl++) {
        #pragma clang loop vectorize(enable)
        for (int i = 1; i < LEN_1D-1; i++) {
            a_ptr[i] = b_ptr[i - 1] + c_ptr[i] * d_ptr[i];
        }
        #pragma clang loop vectorize(enable)
        for (int i = 1; i < LEN_1D-1; i++) {
            b_ptr[i] = b_ptr[i + 1] - e_ptr[i] * d_ptr[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}