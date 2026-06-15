// Round 1 optimization for s258
//
// Optimization Strategy:
//   识别到标量变量 `s` 在循环内存在条件更新（跨迭代依赖），导致编译器无法识别为归约模式。采用标量提升技术，将 `s` 替换为临时数组 `s_arr`，消除跨迭代的数据依赖，从而启用向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 2
//   Missed loops: 0
real_t s258(struct args_t * func_args)
{

//    scalar and array expansion
//    wrap-around scalar under an if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t s_arr[LEN_2D];
    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_2D; ++i) {
            if (a[i] > 0.) {
                s_arr[i] = d[i] * d[i];
            } else {
                s_arr[i] = 0.;
            }
        }
        for (int i = 0; i < LEN_2D; ++i) {
            b[i] = s_arr[i] * c[i] + d[i];
            e[i] = (s_arr[i] + (real_t)1.) * aa[0][i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}