// Round 1 optimization for s258
//
// Optimization Strategy:
//   将内层循环中的条件更新语句拆分为单独的循环，消除控制流对后续语句的阻碍；在主循环中引入临时标量变量缓存 `s` 的值，消除跨迭代依赖，从而允许编译器对计算密集的数组赋值语句进行自动向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s258_m9y75mgc/minimal_s258.c:57:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s258_m9y75mgc/minimal_s258.c:57:9: remark: loop not vectorized [-Rp...
real_t s258(struct args_t * func_args)
{

//    scalar and array expansion
//    wrap-around scalar under an if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t s;
    for (int nl = 0; nl < iterations; nl++) {
        s = 0.;
        for (int i = 0; i < LEN_2D; ++i) {
            if (a[i] > 0.) {
                s = d[i] * d[i];
            }
        }
        for (int i = 0; i < LEN_2D; ++i) {
            real_t s_val = s;
            b[i] = s_val * c[i] + d[i];
            e[i] = (s_val + (real_t)1.) * aa[0][i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}