// Round 1 optimization for s115
//
// Optimization Strategy:
//   识别到内层循环中 `a[j]` 是不变量但编译器无法确认其未被修改，且存在潜在别名。采用标量提升技术，将 `a[j]` 预取为局部标量 `a_j`，并使用 restrict 指针消除别名顾虑，从而暴露内层循环的可向量化特性。
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
            real_t * __restrict__ aa_row = aa[j];
            real_t a_j = a[j];
            #pragma clang loop vectorize(enable)
            for (int i = j+1; i < LEN_2D; i++) {
                a[i] -= aa_row[i] * a_j;
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}