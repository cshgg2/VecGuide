// Round 1 optimization for s1232
//
// Optimization Strategy:
//   识别到内层循环 `i` 从 `j` 开始递增，且仅写入 `aa[i][j]`，不存在跨迭代写后写依赖。通过交换 `j` 和 `i` 循环的顺序，使内层循环变为步长为 1 的完整遍历，从而允许编译器对内存访问进行向量化。外层循环保持不变以维持 `dummy()` 调用频率和整体迭代次数。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s1232(struct args_t * func_args)
{

//    loop interchange
//    interchanging of triangular loops

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 100*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            for (int j = 0; j <= i; j++) {
                aa[i][j] = bb[i][j] + cc[i][j];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 1.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}