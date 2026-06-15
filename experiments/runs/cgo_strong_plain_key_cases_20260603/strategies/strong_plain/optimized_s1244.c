// Round 1 optimization for s1244
//
// Optimization Strategy:
//   采用循环分发策略，将原循环拆分为两个独立的循环：第一个循环仅计算数组 a，消除对 a[i+1] 的跨迭代依赖；第二个循环基于更新后的 a 计算数组 d。这种节点拆分使两个循环均具备连续内存访问模式且无循环携带依赖，从而允许编译器进行自动向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 2
//   Missed loops: 0
real_t s1244(struct args_t * func_args)
{

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