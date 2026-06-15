// Round 1 optimization for s261
//
// Optimization Strategy:
//   采用循环分发策略，将原始循环拆分为两个独立的循环：第一个循环处理 `a` 和 `b` 的更新，第二个循环处理 `c` 和 `d` 的更新。这种拆分消除了标量临时变量 `t` 在不同计算阶段之间的复用冲突，使每个循环内部的数据依赖更加清晰，从而便于编译器进行自动向量化。
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

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 1; i < LEN_1D; ++i) {
            a[i] = a[i] + b[i] + c[i-1];
        }
        for (int i = 1; i < LEN_1D; ++i) {
            c[i] = c[i] * d[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}