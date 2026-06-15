// Round 1 optimization for s115
//
// Optimization Strategy:
//   识别到内层循环中 `a[j]` 是固定源且不会被内层循环修改，将其标量提升以消除依赖。使用 restrict 指针消除别名顾虑，并对内层循环启用向量化指令。
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
            real_t (* __restrict__ aa_ptr)[LEN_2D] = aa;
            real_t a_j = a_ptr[j];
            #pragma clang loop vectorize(enable)
            for (int i = j+1; i < LEN_2D; i++) {
                a_ptr[i] -= aa_ptr[j][i] * a_j;
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}