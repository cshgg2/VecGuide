// Round 3 optimization for s122
//
// Optimization Strategy:
//   针对编译器报告的“unsafe dependent memory operations”和“call instruction cannot be vectorized”问题，采取以下措施：1. 在 n3==1 的快路径中，由于索引计算 `LEN_1D - k` 可能导致编译器误判依赖，添加 `#pragma clang loop distribute(enable)` 允许循环分布以隔离潜在依赖；2. 在 n3!=1 的通用路径中，将预计算循环的索引变量 `i` 和 `k` 声明为 `register` 以优化寄存器分配，并确保预计算循环结构紧凑；3. 保留 `restrict` 和 `vectorize` pragma 以维持已成功的向量化部分，同时尝试解决剩余的依赖分析失败。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 2
//   Missed loops: 6
//
// Remaining Issues:
//   1. /tmp/acpo_s122_sbf8i7xy/minimal_s122.c:91:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s122_sbf8i7xy/minimal_s122.c:57:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s122_sbf8i7xy/minimal_s122.c:57:5: remark: loop not vectorized [-Rp...
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
            // Specialized path for stride 1
            // Use distribute pragma to isolate potential memory dependencies
            #pragma clang loop vectorize(enable) interleave(enable) distribute(enable)
            for (int i = n1 - 1; i < LEN_1D; i++) {
                int k = i - n1 + 2;
                a_ptr[i] += b_ptr[LEN_1D - k];
            }
        } else {
            // General path for stride > 1
            // Precompute indices to break the recurrence chain
            int k_values[LEN_1D];
            int i_values[LEN_1D];
            int idx = 0;
            register int k = 0;
            register int j = 1;

            // Phase 1: Scalar precomputation
            for (register int i = n1 - 1; i < LEN_1D; i += n3) {
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