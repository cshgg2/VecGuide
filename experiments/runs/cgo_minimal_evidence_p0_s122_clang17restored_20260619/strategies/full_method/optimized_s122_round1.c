// Round 1 optimization for s122
//
// Optimization Strategy:
//   识别到归纳变量 k 导致的循环携带依赖，结合运行时步长 n3 阻碍了向量化。采用两阶段循环拆分策略：第一阶段按原顺序预计算索引 k 值，第二阶段基于预计算的索引数组进行向量化数据访问，并使用 restrict 消除指针别名。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 6
//
// Remaining Issues:
//   1. /tmp/acpo_s122_8m3p0sz1/minimal_s122.c:80:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s122_8m3p0sz1/minimal_s122.c:57:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s122_8m3p0sz1/minimal_s122.c:57:5: remark: loop not vectorized [-Rp...
real_t s122(struct args_t * func_args)
{
    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ b_ptr = b;

    for (int nl = 0; nl < iterations; nl++) {
        int j = 1;
        int k = 0;
        int idx = 0;
        
        // Phase 1: Precompute induction variable k
        // This loop remains scalar to preserve the exact sequence of k
        int k_values[LEN_1D];
        int i_values[LEN_1D];
        for (int i = n1 - 1; i < LEN_1D; i += n3) {
            k += j;
            k_values[idx] = k;
            i_values[idx] = i;
            idx++;
        }

        // Phase 2: Vectorized data access using precomputed indices
        int loop_count = idx;
        #pragma clang loop vectorize(enable)
        for (int t = 0; t < loop_count; t++) {
            a_ptr[i_values[t]] += b_ptr[LEN_1D - k_values[t]];
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}