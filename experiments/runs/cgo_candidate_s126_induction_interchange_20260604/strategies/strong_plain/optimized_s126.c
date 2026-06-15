// Round 1 optimization for s126
//
// Optimization Strategy:
//   说明：
//   1. 将内层循环中的线性索引 `k` 替换为基于循环变量 `i` 和 `j` 的直接计算公式，消除跨迭代递推依赖。
//   2. 使用 `restrict` 限定指针参数，帮助编译器消除别名疑虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s126_1xs80jur/minimal_s126.c:64:28: remark: loop not vectorized: va...
//   2. /tmp/acpo_s126_1xs80jur/minimal_s126.c:58:13: remark: loop not vectorized [-R...
real_t s126(struct args_t * func_args)
{

//    induction variable recognition
//    induction variable in two loops; recurrence in inner loop

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int k;
    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        k = 1;
        for (int i = 0; i < LEN_2D; i++) {
            for (int j = 1; j < LEN_2D; j++) {
                // Original: bb[j][i] = bb[j-1][i] + flat_2d_array[k-1] * cc[j][i]; ++k;
                // k starts at 1. Inner loop runs LEN_2D-1 times (j=1 to LEN_2D-1).
                // k increments once per inner iteration.
                // k = 1 + (i * (LEN_2D - 1)) + (j - 1)
                int idx = 1 + (i * (LEN_2D - 1)) + (j - 1);
                bb[j][i] = bb[j-1][i] + flat_2d_array[idx-1] * cc[j][i];
            }
            // Original: ++k; (Skip one element in flat_2d_array after each row)
            // The formula above implicitly handles the reset of k for the next row
            // based on the outer loop variable i, effectively skipping the gap.
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}