// Round 1 optimization for s278
//
// Optimization Strategy:
//   将循环内的 `goto` 控制流转换为等价的 `if-else` 结构，消除非结构化跳转对自动向量化的阻碍。由于 `a[i]` 的赋值依赖于 `b[i]` 和 `c[i]` 的更新，且两者互斥，这种条件结构化是安全的。保留 `restrict` 修饰符以帮助编译器消除指针别名疑虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 0
real_t s278(struct args_t * func_args)
{

//    control flow
//    if/goto to block if-then-else

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            if (a[i] > (real_t)0.) {
                c[i] = -c[i] + d[i] * e[i];
            } else {
                b[i] = -b[i] + d[i] * e[i];
            }
            a[i] = b[i] + c[i] * d[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}