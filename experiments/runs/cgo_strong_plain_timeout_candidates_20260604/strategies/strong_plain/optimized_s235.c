// Round 1 optimization for s235
//
// Optimization Strategy:
//   将内层循环中不变的标量加载 a[i] 提取到临时变量中，减少内存访问并消除部分别名疑虑；同时添加 restrict 限定符帮助编译器识别指针独立性；保留原始循环结构以维持递推依赖的正确性。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s235_pnod6gnw/minimal_s235.c:58:27: remark: loop not vectorized: va...
//   2. /tmp/acpo_s235_pnod6gnw/minimal_s235.c:57:13: remark: loop not vectorized [-R...
real_t s235(struct args_t * func_args)
{
    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 200*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            real_t * restrict aa_i = &aa[0][i];
            real_t * restrict bb_i = &bb[0][i];
            real_t a_val = a[i] + b[i] * c[i];
            a[i] = a_val;

            for (int j = 1; j < LEN_2D; j++) {
                aa_i[j] = aa_i[j-1] + bb_i[j] * a_val;
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}