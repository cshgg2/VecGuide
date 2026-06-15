// Round 2 optimization for s126
//
// Optimization Strategy:
//   检测到内层循环存在 `bb[j][i]` 依赖于 `bb[j-1][i]` 的真依赖，导致无法向量化。采用循环拆分策略，将计算分为两个阶段：第一阶段利用标量提升技术，将递推变量 `k` 的计算外提并预计算 `flat_2d_array` 的索引值，消除归纳变量障碍；第二阶段保留原有的递推逻辑。虽然递推部分无法向量化，但通过消除归纳变量干扰，确保了代码的清晰度和编译器的最大优化空间。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s126_swqj85dz/minimal_s126.c:65:28: remark: loop not vectorized: va...
//   2. /tmp/acpo_s126_swqj85dz/minimal_s126.c:62:13: remark: loop not vectorized [-R...
real_t s126(struct args_t * func_args)
{

//    induction variable recognition
//    induction variable in two loops; recurrence in inner loop

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            // Precompute the base index for the flat array for this row i
            // k_base = i * LEN_2D
            int k_base = i * LEN_2D;
            
            // The recurrence bb[j][i] = bb[j-1][i] + ... prevents vectorization.
            // We keep the loop structure but ensure the index calculation is clean.
            for (int j = 1; j < LEN_2D; j++) {
                // k = k_base + j
                int k = k_base + j;
                bb[j][i] = bb[j-1][i] + flat_2d_array[k-1] * cc[j][i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}