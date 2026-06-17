// Round 2 optimization for s275
//
// Optimization Strategy:
//   上一轮循环交换后，内层循环仍包含条件分支，阻碍了 SIMD 指令的生成。本轮采用条件转换技术，将 `if-else` 逻辑替换为三元条件运算符 `? :`，帮助编译器生成掩码向量指令，从而消除控制流障碍。
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
                aa[j][i] = (aa[0][i] > (real_t)0.) ? (aa[j-1][i] + bb[j][i] * cc[j][i]) : aa[j][i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}