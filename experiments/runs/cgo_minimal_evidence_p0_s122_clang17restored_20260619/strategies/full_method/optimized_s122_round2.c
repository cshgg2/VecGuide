// Round 2 optimization for s122
//
// Optimization Strategy:
//   针对运行时步长 n3，采用保守的特化策略：当 n3 == 1 时，利用归纳变量 k 的线性特性（k = i - n1 + 2）消除预计算开销，直接向量化主循环；当 n3 != 1 时，保留第 1 轮验证安全的两阶段预计算逻辑。同时添加 interleave pragma 以提升指令级并行。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 2
//   Missed loops: 6
//
// Remaining Issues:
//   1. /tmp/acpo_s122_xiykvydt/minimal_s122.c:91:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s122_xiykvydt/minimal_s122.c:57:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s122_xiykvydt/minimal_s122.c:57:5: remark: loop not vectorized [-Rp...
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
        if (n3 == 1) {
            // Specialized path for stride 1: k is linear (k = i - n1 + 2)
            // This allows direct vectorization without precomputation
            #pragma clang loop vectorize(enable) interleave(enable)
            for (int i = n1 - 1; i < LEN_1D; i++) {
                int k = i - n1 + 2;
                a_ptr[i] += b_ptr[LEN_1D - k];
            }
        } else {
            // General path for stride > 1: Use two-phase precomputation
            // to handle complex induction variable and indirect indexing
            int k_values[LEN_1D];
            int i_values[LEN_1D];
            int idx = 0;
            int k = 0;
            int j = 1;

            // Phase 1: Scalar precomputation of indices
            for (int i = n1 - 1; i < LEN_1D; i += n3) {
                k += j;
                k_values[idx] = k;
                i_values[idx] = i;
                idx++;
            }

            // Phase 2: Vectorized data access
            int loop_count = idx;
            #pragma clang loop vectorize(enable) interleave(enable)
            for (int t = 0; t < loop_count; t++) {
                a_ptr[i_values[t]] += b_ptr[LEN_1D - k_values[t]];
            }
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}