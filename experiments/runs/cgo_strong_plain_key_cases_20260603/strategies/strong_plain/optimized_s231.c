// Round 1 optimization for s231
//
// Optimization Strategy:
//   识别到内层循环存在跨迭代递推依赖（aa[j][i] 依赖于 aa[j-1][i]），这阻碍了直接向量化。通过交换 i 和 j 循环的顺序，使递推依赖位于外层循环，而内层循环变为对数组 aa 和 bb 的连续内存访问，从而消除内层循环的依赖障碍，使其能够被自动向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s231(struct args_t * func_args)
{
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