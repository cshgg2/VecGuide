// Round 1 optimization for s231
//
// Optimization Strategy:
//   识别到内层循环存在跨迭代的数据依赖（递推关系），导致无法直接向量化。采用循环交换技术，将 `j` 维度的递推依赖移至外层，使最内层 `i` 循环变为无依赖的并行循环，从而启用向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s231(struct args_t * func_args)
{
//    loop interchange
//    loop with data dependency

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 100*(iterations/LEN_2D); nl++) {
        for (int j = 1; j < LEN_2D; j++) {
            for (int i = 0; i < LEN_2D; ++i) {
                aa[j][i] = aa[j - 1][i] + bb[j][i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}