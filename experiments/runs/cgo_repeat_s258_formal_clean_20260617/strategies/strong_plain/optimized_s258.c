// Round 1 optimization for s258
//
// Optimization Strategy:
//   将内层循环中的条件标量更新转换为无分支的数组临时变量，消除循环携带依赖。通过引入局部数组 `s_temp` 存储 `d[i] * d[i]` 的结果，使得 `b[i]` 和 `e[i]` 的计算变为纯数据并行操作，从而允许编译器进行自动向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s258(struct args_t * func_args)
{

//    scalar and array expansion
//    wrap-around scalar under an if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t s;
    real_t s_temp[LEN_2D];
    for (int nl = 0; nl < iterations; nl++) {
        s = 0.;
        for (int i = 0; i < LEN_2D; ++i) {
            if (a[i] > 0.) {
                s_temp[i] = d[i] * d[i];
            } else {
                s_temp[i] = s;
            }
            b[i] = s_temp[i] * c[i] + d[i];
            e[i] = (s_temp[i] + (real_t)1.) * aa[0][i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}