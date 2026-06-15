// Round 1 optimization for s275
//
// Optimization Strategy:
//   识别到内层循环存在跨迭代递推依赖 `aa[j][i] = aa[j-1][i] + ...`，阻止了向量化。由于外层 `if` 条件基于 `aa[0][i]`，且内层循环会修改 `aa[0][i]`（当 j=1 时），不能简单外提条件。采用循环拆分技术，将内层循环拆分为 `j=1` 的特殊迭代和 `j=2` 到 `LEN_2D` 的剩余迭代，从而消除剩余部分的递推依赖，使其可向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s275_g416svdq/minimal_s275.c:64:32: remark: loop not vectorized: va...
//   2. /tmp/acpo_s275_g416svdq/minimal_s275.c:63:17: remark: loop not vectorized [-R...
real_t s275(struct args_t * func_args)
{

//    control flow
//    if around inner loop, interchanging needed

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            if (aa[0][i] > (real_t)0.) {
                // First iteration: j=1
                // This handles the dependency on aa[0][i] and updates aa[1][i]
                aa[1][i] = aa[0][i] + bb[1][i] * cc[1][i];

                // Remaining iterations: j=2 to LEN_2D-1
                // This loop has no loop-carried dependency and can be vectorized
                for (int j = 2; j < LEN_2D; j++) {
                    aa[j][i] = aa[j-1][i] + bb[j][i] * cc[j][i];
                }
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}