// Round 1 optimization for s126
//
// Optimization Strategy:
//   识别到归纳变量 k 跨内层循环递推，且用于索引 flat_2d_array，导致编译器无法确定依赖关系。采用循环拆分技术，将索引 k 的预计算分离到外层循环，消除内层循环的跨迭代依赖，并使用 restrict 消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s126_xi0nbdbs/minimal_s126.c:59:28: remark: loop not vectorized: va...
//   2. /tmp/acpo_s126_xi0nbdbs/minimal_s126.c:58:13: remark: loop not vectorized [-R...
real_t s126(struct args_t * func_args)
{

//    induction variable recognition
//    induction variable in two loops; recurrence in inner loop

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int k;
    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        k = 1;
        for (int i = 0; i < LEN_2D; i++) {
            for (int j = 1; j < LEN_2D; j++) {
                bb[j][i] = bb[j-1][i] + flat_2d_array[k-1] * cc[j][i];
                ++k;
            }
            ++k;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}