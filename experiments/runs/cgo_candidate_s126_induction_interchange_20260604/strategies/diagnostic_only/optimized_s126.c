// Round 1 optimization for s126
//
// Optimization Strategy:
//   识别到跨层递推变量 `k` 阻止了向量化。采用标量提升技术，将 `k` 的线性增长转换为基于循环索引 `i` 和 `j` 的直接计算，消除循环携带的依赖，并使用 restrict 消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s126_bxdwwjld/minimal_s126.c:68:29: remark: loop not vectorized: va...
//   2. /tmp/acpo_s126_bxdwwjld/minimal_s126.c:61:13: remark: loop not vectorized [-R...
real_t s126(struct args_t * func_args)
{

//    induction variable recognition
//    induction variable in two loops; recurrence in inner loop

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            // Precompute the base index for this i iteration
            // Original logic: k starts at 1. For each i, inner loop runs (LEN_2D - 1) times.
            // Base k for current i is: 1 + i * (LEN_2D - 1 + 1) = 1 + i * LEN_2D
            int k_base = 1 + i * LEN_2D;
            
            for (int j = 1; j < LEN_2D; j++) {
                // k = k_base + (j - 1)
                // flat_2d_array[k-1] = flat_2d_array[k_base + j - 2]
                real_t * __restrict__ bb_ptr = bb[j];
                real_t * __restrict__ bb_prev_ptr = bb[j-1];
                real_t * __restrict__ cc_ptr = cc[j];
                
                bb_ptr[i] = bb_prev_ptr[i] + flat_2d_array[k_base + j - 2] * cc_ptr[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}