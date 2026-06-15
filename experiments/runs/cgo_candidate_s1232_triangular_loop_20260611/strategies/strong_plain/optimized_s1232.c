// Round 1 optimization for s1232
//
// Optimization Strategy:
//   将内层循环的起始索引 `i = j` 替换为 `i = 0`，并增加条件判断 `if (i >= j)`。这种循环标准化技术将不规则循环边界转换为规则边界，配合 `#pragma clang loop vectorize(enable)`，能显著提升 Clang 自动向量化的能力，同时保持原始语义和迭代空间不变。
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
        for (int j = 0; j < LEN_2D; j++) {
            #pragma clang loop vectorize(enable)
            for (int i = 0; i < LEN_2D; i++) {
                if (i >= j) {
                    aa[i][j] = bb[i][j] + cc[i][j];
                }
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 1.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}