// Round 1 optimization for s1232
//
// Optimization Strategy:
//   识别到三角循环结构中内层循环存在跨迭代依赖，阻止了向量化。采用循环交换技术，将 i 循环作为外层，j 循环作为内层，使内层循环变为规范形式，并使用 restrict 消除别名顾虑。
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

    real_t (* __restrict__ aa_)[LEN_2D] = aa;
    real_t (* __restrict__ bb_)[LEN_2D] = bb;
    real_t (* __restrict__ cc_)[LEN_2D] = cc;

    for (int nl = 0; nl < 100*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            #pragma clang loop vectorize(enable)
            for (int j = 0; j <= i; j++) {
                aa_[i][j] = bb_[i][j] + cc_[i][j];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 1.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}