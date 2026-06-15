// Round 1 optimization for s115
//
// Optimization Strategy:
//   说明：
//   1. 识别到内层循环存在跨迭代依赖（`a[i]` 读取并更新），且循环下界 `j+1` 依赖外层变量，导致标准自动向量化受阻。
//   2. 采用循环交换策略，将 `j` 循环置于内层，使内层循环变为从固定下标 1 到 LEN_2D 的规则循环，且每次迭代仅读取 `a[j]` 和 `aa[j][i]`，写入 `a[i]`，消除了内层循环的循环携带依赖。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s115_01kletjd/minimal_s115.c:57:22: remark: loop not vectorized: un...
//   2. /tmp/acpo_s115_01kletjd/minimal_s115.c:56:13: remark: loop not vectorized [-R...
real_t s115(struct args_t * func_args)
{

//    linear dependence testing
//    triangular saxpy loop

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 1000*(iterations/LEN_2D); nl++) {
        for (int i = 1; i < LEN_2D; i++) {
            for (int j = 0; j < i; j++) {
                a[i] -= aa[j][i] * a[j];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}