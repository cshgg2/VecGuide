// Round 1 optimization for s126
//
// Optimization Strategy:
//   识别到归纳变量 k 跨内层循环递增，且用于索引 flat_2d_array，导致编译器无法确定内存访问模式。采用索引预计算技术，将 k 的线性计算转换为基于 i 和 j 的直接索引，消除跨迭代递推依赖，从而允许向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s126_p5qqmh_2/minimal_s126.c:62:28: remark: loop not vectorized: va...
//   2. /tmp/acpo_s126_p5qqmh_2/minimal_s126.c:57:13: remark: loop not vectorized (Fo...
real_t s126(struct args_t * func_args)
{

//    induction variable recognition
//    induction variable in two loops; recurrence in inner loop

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            #pragma clang loop vectorize(enable)
            for (int j = 1; j < LEN_2D; j++) {
                // k = 1 + i * (LEN_2D - 1 + 1) + (j - 1)
                // k = 1 + i * LEN_2D + j - 1
                // k = i * LEN_2D + j
                int k = i * LEN_2D + j;
                bb[j][i] = bb[j-1][i] + flat_2d_array[k-1] * cc[j][i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}