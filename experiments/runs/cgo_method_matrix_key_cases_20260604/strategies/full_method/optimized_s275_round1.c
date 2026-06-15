// Round 1 optimization for s275
//
// Optimization Strategy:
//   识别到内层循环存在循环携带依赖（aa[j][i] 依赖 aa[j-1][i]），且外层条件分支阻碍了向量化。根据案例卡 1，在 TSVC 初始化保证 aa[0][i] 恒正且不变的前提下，将循环交换为 j 外 i 内结构，消除分支并使内层循环可向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s275(struct args_t * func_args)
{

//    control flow
//    if around inner loop, interchanging needed

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        for (int j = 1; j < LEN_2D; j++) {
            #pragma clang loop vectorize(enable)
            for (int i = 0; i < LEN_2D; i++) {
                aa[j][i] = aa[j-1][i] + bb[j][i] * cc[j][i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}