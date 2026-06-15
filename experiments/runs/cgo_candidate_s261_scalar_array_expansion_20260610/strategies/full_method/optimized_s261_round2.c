// Round 2 optimization for s261
//
// Optimization Strategy:
//   分析发现标量变量 `t` 在循环内存在跨迭代依赖（先写后读再写），导致编译器无法向量化。采用循环拆分策略，将原循环拆分为两个独立的循环：第一个循环处理 `a` 和 `c` 的更新，第二个循环处理 `c` 的乘法更新，从而消除数据依赖，使两个循环均可独立向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 2
//   Missed loops: 0
real_t s261(struct args_t * func_args)
{

//    scalar and array expansion
//    wrap-around scalar under an if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t t;
    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 1; i < LEN_1D; ++i) {
            t = a[i] + b[i];
            a[i] = t + c[i-1];
        }
        for (int i = 1; i < LEN_1D; ++i) {
            t = c[i] * d[i];
            c[i] = t;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}