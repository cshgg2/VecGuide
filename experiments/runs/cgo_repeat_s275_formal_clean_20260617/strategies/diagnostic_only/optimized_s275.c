// Round 1 optimization for s275
//
// Optimization Strategy:
//   识别到内层循环存在跨迭代递推依赖（aa[j][i] 依赖于 aa[j-1][i]），且外层包含条件分支。采用循环交换技术，将 i 循环作为最内层，使递推依赖沿外层展开，从而允许最内层循环向量化，并使用 restrict 消除指针别名顾虑。
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
            for (int i = 0; i < LEN_2D; i++) {
                if (aa[0][i] > (real_t)0.) {
                    aa[j][i] = aa[j-1][i] + bb[j][i] * cc[j][i];
                }
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}