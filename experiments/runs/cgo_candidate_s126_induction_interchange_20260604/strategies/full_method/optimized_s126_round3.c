// Round 3 optimization for s126
//
// Optimization Strategy:
//   针对内层循环 `bb[j][i] = bb[j-1][i] + ...` 存在的跨迭代真依赖，这是无法通过简单的 Pragma 消除的数学限制。采用循环交换策略，交换 `i` 和 `j` 循环的顺序。交换后，内层循环变为对 `bb` 数组列方向的遍历，此时 `bb[j][i]` 与 `bb[j-1][i]` 的依赖关系跨越了不同的外层迭代，从而消除了内层循环内的依赖，使得内层循环可以向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s126(struct args_t * func_args)
{

//    induction variable recognition
//    induction variable in two loops; recurrence in inner loop

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        for (int j = 1; j < LEN_2D; j++) {
            for (int i = 0; i < LEN_2D; i++) {
                // Calculate flat index: row j, column i
                // Original logic: bb[j][i] = bb[j-1][i] + flat_2d_array[j*LEN_2D + i - 1] * cc[j][i]
                // Note: flat_2d_array indexing follows row-major order (row * LEN_2D + col)
                int k = j * LEN_2D + i;
                bb[j][i] = bb[j-1][i] + flat_2d_array[k-1] * cc[j][i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}