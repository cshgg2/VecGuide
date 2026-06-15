// Round 3 optimization for s172
//
// Optimization Strategy:
//   针对通用 fallback 路径中编译器无法识别 `pa[k * stride]` 为连续内存访问的问题，放弃指针算术形式，恢复原始的数组索引形式。虽然这保留了运行时步长导致的迭代次数未知问题，但避免了因非连续寻址模式导致的额外向量化阻碍。同时保留 restrict 和 pragma，确保在编译器能够分析的情况下（如常量传播）仍有机会向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 3
//   Missed loops: 8
//
// Remaining Issues:
//   1. /tmp/acpo_s172_c6blhqyl/minimal_s172.c:93:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s172_c6blhqyl/minimal_s172.c:57:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s172_c6blhqyl/minimal_s172.c:57:5: remark: loop not vectorized [-Rp...
real_t s172(struct args_t * func_args)
{
    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ = a;
    real_t * __restrict__ b_ = b;

    for (int nl = 0; nl < iterations; nl++) {
        int start = n1 - 1;
        int stride = n3;

        if (stride == 1) {
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; ++i) {
                a_[i] += b_[i];
            }
        } else if (stride == 2) {
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; i += 2) {
                a_[i] += b_[i];
            }
        } else if (stride == 4) {
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; i += 4) {
                a_[i] += b_[i];
            }
        } else {
            // General fallback: revert to standard array indexing.
            // While trip count remains unknown at compile time,
            // this avoids the non-contiguous access pattern issues
            // introduced by pointer arithmetic with variable stride.
            if (stride > 0) {
                #pragma clang loop vectorize(enable)
                for (int i = start; i < LEN_1D; i += stride) {
                    a_[i] += b_[i];
                }
            } else {
                // Handle non-positive stride
                for (int i = start; i < LEN_1D; i += stride) {
                    a_[i] += b_[i];
                }
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}