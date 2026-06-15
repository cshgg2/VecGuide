// Round 1 optimization for s122
//
// Optimization Strategy:
//   识别到归纳变量 k 参与反向索引导致循环携带依赖，且步长 n3 为运行时变量。采用两阶段重构：第一阶段预计算索引 k 的序列，第二阶段基于预计算索引进行向量化数据访问，同时保留 stride==1 的快路径优化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 3
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s122_wffmtvqx/minimal_s122.c:96:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s122_wffmtvqx/minimal_s122.c:67:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s122_wffmtvqx/minimal_s122.c:67:5: remark: loop not vectorized [-Rp...
real_t s122(struct args_t * func_args)
{

//    induction variable recognition
//    variable lower and upper bound, and stride
//    reverse data access and jump in data access

    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int j, k;
    int start = n1 - 1;
    int stride = n3;
    
    // Helper array for precomputing indices
    // LEN_1D is the maximum possible number of iterations
    static int k_vals[LEN_1D];

    for (int nl = 0; nl < iterations; nl++) {
        j = 1;
        k = 0;
        
        if (stride == 1) {
            // Fast path for stride 1: direct vectorization
            // k follows sequence 1, 2, 3... relative to loop start
            // k = (i - start) + 1
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; i++) {
                int current_k = (i - start) + 1;
                a[i] += b[LEN_1D - current_k];
            }
        } else {
            // Generic path: two-phase approach
            // Phase 1: Precompute k values
            int idx = 0;
            for (int i = start; i < LEN_1D; i += stride) {
                k += j;
                k_vals[idx++] = k;
            }
            
            // Phase 2: Vectorized data access using precomputed indices
            #pragma clang loop vectorize(enable)
            for (int t = 0; t < idx; t++) {
                int i = start + t * stride;
                a[i] += b[LEN_1D - k_vals[t]];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}