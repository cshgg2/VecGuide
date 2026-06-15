// Round 1 optimization for s115
//
// Optimization Strategy:
//   识别到内层循环中存在流依赖（a[i] 读取 a[j] 且 j < i），导致无法直接向量化。采用循环拆分技术，将索引预计算与数据访问分离，并使用 restrict 消除别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s115(struct args_t * func_args)
{

//    linear dependence testing
//    triangular saxpy loop

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 1000*(iterations/LEN_2D); nl++) {
        for (int j = 0; j < LEN_2D; j++) {
            real_t * __restrict__ a_ptr = a;
            real_t * __restrict__ aa_ptr = aa[j];
            real_t a_j = a[j];
            int i;
            #pragma clang loop vectorize(enable)
            for (i = j+1; i < LEN_2D; i++) {
                a_ptr[i] -= aa_ptr[i] * a_j;
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}