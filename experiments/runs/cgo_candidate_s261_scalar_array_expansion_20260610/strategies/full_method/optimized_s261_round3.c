// Round 3 optimization for s261
//
// Optimization Strategy:
//   分析发现标量 `t` 的跨语句使用阻碍了向量化。采用语句融合策略，将中间变量 `t` 的计算直接内联到目标数组 `a` 和 `c` 的赋值表达式中，消除标量依赖，使循环体变为纯粹的数组操作，从而允许编译器进行自动向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s261_1matsevo/minimal_s261.c:56:36: remark: loop not vectorized: va...
//   2. /tmp/acpo_s261_1matsevo/minimal_s261.c:55:9: remark: loop not vectorized [-Rp...
real_t s261(struct args_t * func_args)
{

//    scalar and array expansion
//    wrap-around scalar under an if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 1; i < LEN_1D; ++i) {
            a[i] = (a[i] + b[i]) + c[i-1];
            c[i] = c[i] * d[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}