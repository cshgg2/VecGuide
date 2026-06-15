// Round 1 optimization for s253
//
// Optimization Strategy:
//   识别到标量变量 `s` 在循环内被条件性更新并用于后续数组写入，这构成了循环携带依赖，阻碍了向量化。通过标量膨胀将 `s` 替换为临时数组 `s_arr`，消除跨迭代数据依赖，使内层循环变为独立的迭代区间，从而允许编译器安全向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 0
real_t s253(struct args_t * func_args)
{

//    scalar and array expansion
//    scalar expansio assigned under if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t s_arr[LEN_1D];
    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            if (a[i] > b[i]) {
                s_arr[i] = a[i] - b[i] * d[i];
                c[i] += s_arr[i];
                a[i] = s_arr[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}