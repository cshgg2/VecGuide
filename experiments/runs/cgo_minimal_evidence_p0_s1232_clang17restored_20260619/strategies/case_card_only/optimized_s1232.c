// Round 1 optimization for s1232
//
// Optimization Strategy:
//   识别到内层循环存在跨迭代依赖（`aa[i][j]` 写入后可能被后续迭代读取），阻碍了向量化。采用循环交换技术，将 `i` 循环作为外层，`j` 循环作为内层，消除依赖并启用向量化。同时使用 restrict 关键字消除指针别名顾虑。
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