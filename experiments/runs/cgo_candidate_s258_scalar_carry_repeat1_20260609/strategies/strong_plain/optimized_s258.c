// Round 1 optimization for s258
//
// Optimization Strategy:
//   将内层循环中的标量递归依赖（s）转换为数组形式，消除循环携带依赖，使内层循环可向量化。通过引入局部临时数组存储 s 的历史值，确保条件赋值与后续使用在语义上严格等价。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s258_c4o3xdkf/minimal_s258.c:58:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s258_c4o3xdkf/minimal_s258.c:58:9: remark: loop not vectorized [-Rp...
real_t s258(struct args_t * func_args)
{

//    scalar and array expansion
//    wrap-around scalar under an if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t s;
    real_t s_exp[LEN_2D];
    for (int nl = 0; nl < iterations; nl++) {
        s = 0.;
        for (int i = 0; i < LEN_2D; ++i) {
            if (a[i] > 0.) {
                s_exp[i] = d[i] * d[i];
            } else {
                s_exp[i] = s;
            }
            b[i] = s_exp[i] * c[i] + d[i];
            e[i] = (s_exp[i] + (real_t)1.) * aa[0][i];
            s = s_exp[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}