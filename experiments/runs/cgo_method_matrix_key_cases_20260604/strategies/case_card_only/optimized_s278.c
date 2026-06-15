// Round 1 optimization for s278
//
// Optimization Strategy:
//   识别到循环体内的 goto 结构阻碍了向量化。采用标量提升技术，将条件分支内的数组读写转换为局部标量操作，消除控制流跳转，使编译器能够进行 if-conversion 和向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s278(struct args_t * func_args)
{

//    control flow
//    if/goto to block if-then-else

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            real_t a_val = a[i];
            real_t b_val = b[i];
            real_t c_val = c[i];
            real_t d_val = d[i];
            real_t e_val = e[i];

            if (a_val > (real_t)0.) {
                c_val = -c_val + d_val * e_val;
            } else {
                b_val = -b_val + d_val * e_val;
            }
            a_val = b_val + c_val * d_val;

            a[i] = a_val;
            b[i] = b_val;
            c[i] = c_val;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}