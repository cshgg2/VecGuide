// Round 1 optimization for s211
//
// Optimization Strategy:
//   识别到循环体内存在跨迭代的数据流依赖（b[i]的读取依赖于b[i+1]的写入），阻止了向量化。采用循环拆分技术，将原循环拆分为两个独立的循环，消除循环携带依赖，并添加 restrict 关键字消除指针别名顾虑。
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

    for (int nl = 0; nl < iterations; nl++) {
        real_t * __restrict__ a_p = a;
        real_t * __restrict__ b_p = b;
        real_t * __restrict__ c_p = c;
        real_t * __restrict__ d_p = d;
        real_t * __restrict__ e_p = e;

        for (int i = 1; i < LEN_1D-1; i++) {
            a_p[i] = b_p[i - 1] + c_p[i] * d_p[i];
        }
        for (int i = 1; i < LEN_1D-1; i++) {
            b_p[i] = b_p[i + 1] - e_p[i] * d_p[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}