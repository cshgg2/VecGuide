// Round 1 optimization for s1232
//
// Optimization Strategy:
//   识别到最内层循环 `i` 的起始点依赖于外层循环变量 `j`，导致循环边界非规范化，阻碍编译器向量化。采用循环归一化技术，将内层循环转换为从 0 开始的标准形式，并调整数组索引以保持语义等价。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 0
real_t s1232(struct args_t * func_args)
{

//    loop interchange
//    interchanging of triangular loops

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 100*(iterations/LEN_2D); nl++) {
        for (int j = 0; j < LEN_2D; j++) {
            int len = LEN_2D - j;
            for (int i = 0; i < len; i++) {
                aa[i + j][j] = bb[i + j][j] + cc[i + j][j];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 1.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}