// Round 1 optimization for s275
//
// Optimization Strategy:
//   识别到条件分支内的递推依赖阻碍向量化。根据案例卡，在 TSVC 初始化下 `aa[0][i]` 恒为正且未被修改，因此分支条件恒真。采用循环交换技术，将递推维度 `j` 置于外层，使内层 `i` 循环变为可向量化的连续内存访问模式。
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