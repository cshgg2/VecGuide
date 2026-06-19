// Round 1 optimization for s1232
//
// Optimization Strategy:
//   识别到内层循环存在非单位步长（`i = j`）的起始条件，阻碍了自动向量化。采用循环归一化技术，将循环索引转换为从 0 开始的标准形式，并配合 restrict 关键字消除指针别名顾虑。
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
        for (int j = 0; j < LEN_2D; j++) {
            int len = LEN_2D - j;
            real_t * __restrict__ aa_ptr = &aa[j][j];
            real_t * __restrict__ bb_ptr = &bb[j][j];
            real_t * __restrict__ cc_ptr = &cc[j][j];
            #pragma clang loop vectorize(enable)
            for (int i = 0; i < len; i++) {
                aa_ptr[i] = bb_ptr[i] + cc_ptr[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 1.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}