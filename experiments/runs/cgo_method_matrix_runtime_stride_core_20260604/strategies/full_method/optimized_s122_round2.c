// Round 2 optimization for s122
//
// Optimization Strategy:
//   针对运行时步长循环，采用多版本化策略。当步长 stride == 1 时，使用紧凑的向量化快路径以最大化性能；当 stride > 1 时，保留第 1 轮验证过的两阶段预计算路径以确保正确性和通用性。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 3
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s122_gptq54bz/minimal_s122.c:99:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s122_gptq54bz/minimal_s122.c:63:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s122_gptq54bz/minimal_s122.c:63:5: remark: loop not vectorized [-Rp...
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

    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ b_ptr = b;

    int j, k;
    for (int nl = 0; nl < iterations; nl++) {
        j = 1;
        k = 0;
        
        int start = n1 - 1;
        int stride = n3;

        if (stride == 1) {
            // Fast path for stride == 1: Direct vectorization
            // k = i - start + 1 (since k starts at 0, i starts at start)
            // a[i] += b[LEN_1D - k]
            // a[i] += b[LEN_1D - (i - start + 1)]
            // a[i] += b[LEN_1D - i + start - 1]
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; i++) {
                a_ptr[i] += b_ptr[LEN_1D - (i - start) - 1];
            }
        } else {
            // Generic path for stride > 1: Two-phase precomputation
            int k_vals[LEN_1D];
            int idx = 0;

            // Phase 1: Precompute induction variable k
            for (int i = start; i < LEN_1D; i += stride) {
                k += j;
                k_vals[idx++] = k;
            }

            // Phase 2: Vectorized data access
            #pragma clang loop vectorize(enable)
            for (int t = 0; t < idx; t++) {
                int i = start + t * stride;
                a_ptr[i] += b_ptr[LEN_1D - k_vals[t]];
            }
        }
        
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}