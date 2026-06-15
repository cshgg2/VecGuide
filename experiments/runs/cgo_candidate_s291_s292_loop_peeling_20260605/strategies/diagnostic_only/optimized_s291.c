// Round 1 optimization for s291
//
// Optimization Strategy:
//   识别到变量 im1 在循环内形成跨迭代递推依赖，导致无法向量化。采用标量提升技术，将 im1 的历史值预计算到临时数组中，消除循环内的数据依赖，从而启用向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s291_afn0si2t/minimal_s291.c:58:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s291_afn0si2t/minimal_s291.c:58:9: remark: loop not vectorized [-Rp...
real_t s291(struct args_t * func_args)
{

//    loop peeling
//    wrap around variable, 1 level

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int im1;
    int im1_array[LEN_1D];
    for (int nl = 0; nl < 2*iterations; nl++) {
        im1 = LEN_1D-1;
        for (int i = 0; i < LEN_1D; i++) {
            im1_array[i] = im1;
            im1 = i;
        }
        for (int i = 0; i < LEN_1D; i++) {
            a[i] = (b[i] + b[im1_array[i]]) * (real_t).5;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}