// Round 1 optimization for s256
//
// Optimization Strategy:
//   识别到内层循环中存在对一维数组 `a` 的跨迭代递推依赖（`a[j]` 依赖 `a[j-1]`），这阻止了向量化。采用循环拆分技术，将独立的二维数组 `aa` 的计算分离到外层循环，使其可向量化；保留 `a` 的递推计算在内层标量循环中，确保语义正确。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s256_mploem7l/minimal_s256.c:57:38: remark: loop not vectorized: va...
//   2. /tmp/acpo_s256_mploem7l/minimal_s256.c:56:13: remark: loop not vectorized [-R...
real_t s256(struct args_t * func_args)
{

//    scalar and array expansion
//    array expansion

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            for (int j = 1; j < LEN_2D; j++) {
                a[j] = (real_t)1.0 - a[j - 1];
            }
        }
        for (int i = 0; i < LEN_2D; i++) {
            #pragma clang loop vectorize(enable)
            for (int j = 1; j < LEN_2D; j++) {
                aa[j][i] = a[j] + bb[j][i]*d[j];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}