// Round 1 optimization for s122
//
// Optimization Strategy:
//   识别到归纳变量 k 参与反向索引导致循环携带依赖，且运行时步长 n3 阻碍迭代计数分析。采用两阶段重构：第一阶段按原顺序预计算索引 k 值，第二阶段基于预计算数组进行向量化数据访问，同时保留 stride==1 的快路径优化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 3
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s122_zo9h220x/minimal_s122.c:96:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s122_zo9h220x/minimal_s122.c:63:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s122_zo9h220x/minimal_s122.c:63:5: remark: loop not vectorized [-Rp...
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

    for (int nl = 0; nl < iterations; nl++) {
        j = 1;
        k = 0;

        if (stride == 1) {
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; i++) {
                k += j;
                a[i] += b[LEN_1D - k];
            }
        } else {
            // Phase 1: Precompute induction variable k
            // Calculate max possible iterations to size the helper array
            int max_iters = (LEN_1D - start + stride - 1) / stride;
            if (max_iters > 0) {
                int k_vals[max_iters];
                int idx = 0;
                int temp_k = 0;
                
                // Record k values in original order
                for (int i = start; i < LEN_1D; i += stride) {
                    temp_k += j;
                    k_vals[idx++] = temp_k;
                }

                // Phase 2: Vectorized data access using precomputed indices
                #pragma clang loop vectorize(enable)
                for (int t = 0; t < idx; t++) {
                    int i = start + t * stride;
                    a[i] += b[LEN_1D - k_vals[t]];
                }
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}