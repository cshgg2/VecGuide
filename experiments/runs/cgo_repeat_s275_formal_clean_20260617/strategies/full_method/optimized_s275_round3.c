// Round 3 optimization for s275
//
// Optimization Strategy:
//   针对循环交换后内层循环中 `aa[j-1][i]` 的读取与 `aa[j][i]` 的写入可能存在的重叠依赖，引入局部指针并使用 `restrict` 关键字，向编译器显式承诺不同行的内存区域不重叠，从而消除别名分析导致的向量化阻塞。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 0
real_t s275(struct args_t * func_args)
{

//    control flow
//    if around inner loop, interchanging needed

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        for (int j = 1; j < LEN_2D; j++) {
            real_t * __restrict__ aa_curr = aa[j];
            real_t * __restrict__ aa_prev = aa[j-1];
            real_t * __restrict__ bb_curr = bb[j];
            real_t * __restrict__ cc_curr = cc[j];
            real_t * __restrict__ aa_0 = aa[0];

            for (int i = 0; i < LEN_2D; i++) {
                aa_curr[i] = (aa_0[i] > (real_t)0.) ? (aa_prev[i] + bb_curr[i] * cc_curr[i]) : aa_curr[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}