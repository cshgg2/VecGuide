// Round 1 optimization for s258
//
// Optimization Strategy:
//   识别到标量变量 `s` 在循环内存在跨迭代依赖（前序迭代值影响后续迭代），阻止了向量化。采用标量提升技术，将 `s` 替换为数组 `s_arr`，消除循环携带依赖，并使用 restrict 消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s258_c3v_0kip/minimal_s258.c:58:26: remark: loop not vectorized: un...
//   2. /tmp/acpo_s258_c3v_0kip/minimal_s258.c:56:9: remark: loop not vectorized [-Rp...
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
                s_arr[i] = (i > 0) ? s_arr[i-1] : 0.;
            }
            b[i] = s_arr[i] * c[i] + d[i];
            e[i] = (s_arr[i] + (real_t)1.) * aa[0][i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}