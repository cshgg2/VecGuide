// Round 1 optimization for s1232
//
// Optimization Strategy:
//   检测到最内层循环存在反向依赖（`aa[i][j]` 写入与 `bb/cc[i][j]` 读取索引相同），且循环下界 `i=j` 依赖于外层循环变量，导致编译器无法向量化。采用循环交换技术，将 `j` 循环作为最内层，使其变为规范循环，并添加 restrict 关键字消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s1232(struct args_t * func_args)
{

//    loop interchange
//    interchanging of triangular loops

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 100*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            real_t * __restrict__ aa_ptr = aa[i];
            real_t * __restrict__ bb_ptr = bb[i];
            real_t * __restrict__ cc_ptr = cc[i];
            for (int j = 0; j <= i; j++) {
                aa_ptr[j] = bb_ptr[j] + cc_ptr[j];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 1.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}