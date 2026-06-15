// Round 1 optimization for s235
//
// Optimization Strategy:
//   识别到内层循环存在基于 `j-1` 的递推依赖，且外层 `i` 循环包含生产者语句阻碍向量化。采用循环分布技术，将独立的 `a[i]` 更新分离到前置循环，并将递推循环 `j` 提至外层，使内层 `i` 循环变为可向量化的独立列访问。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 2
//   Missed loops: 0
real_t s235(struct args_t * func_args)
{

//    loop interchanging
//    imperfectly nested loops

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 200*(iterations/LEN_2D); nl++) {
        // Loop Distribution: Separate the producer of a[i]
        for (int i = 0; i < LEN_2D; i++) {
            a[i] += b[i] * c[i];
        }

        // Loop Interchange: Move the recurrence-carrying dimension j outside
        // to allow the inner i loop to be vectorized.
        for (int j = 1; j < LEN_2D; j++) {
            #pragma clang loop vectorize(enable)
            for (int i = 0; i < LEN_2D; i++) {
                aa[j][i] = aa[j-1][i] + bb[j][i] * a[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}