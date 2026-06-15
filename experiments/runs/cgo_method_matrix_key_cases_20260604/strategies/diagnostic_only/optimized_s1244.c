// Round 1 optimization for s1244
//
// Optimization Strategy:
//   识别到循环内存在流依赖（a[i]写入后立即被d[i]读取）和反依赖（a[i+1]写入与d[i]读取冲突）。采用循环拆分技术，将计算拆分为两个独立循环，消除依赖链以启用向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 2
//   Missed loops: 0
real_t s1244(struct args_t * func_args)
{

//    node splitting
//    cycle with ture and anti dependency

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D-1; i++) {
            a[i] = b[i] + c[i] * c[i] + b[i]*b[i] + c[i];
        }
        for (int i = 0; i < LEN_1D-1; i++) {
            d[i] = a[i] + a[i+1];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}