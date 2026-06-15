// Round 3 optimization for s122
//
// Optimization Strategy:
//   针对第3轮反馈中“call instruction cannot be vectorized”的问题，分析发现 `dummy()` 调用位于 `nl` 循环内，且 `nl` 循环本身包含控制流和函数调用，这本质上是无法向量化的。真正的优化目标是 `nl` 内部的计算循环。上一轮已成功向量化了 `stride=1` 和 `stride>1` 的预计算循环。本轮将移除 `nl` 循环上无效的 pragma，并进一步优化 `stride>1` 路径：将预计算循环与计算循环合并，减少内存访问开销，同时保持 `k` 的递推逻辑正确性，以最大化计算密集型部分的性能。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 6
//
// Remaining Issues:
//   1. /tmp/acpo_s122_i0r2z2rn/minimal_s122.c:87:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s122_i0r2z2rn/minimal_s122.c:63:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s122_i0r2z2rn/minimal_s122.c:63:5: remark: loop not vectorized [-Rp...
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
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; i++) {
                a_ptr[i] += b_ptr[LEN_1D - (i - start) - 1];
            }
        } else {
            // Generic path for stride > 1: Fused loop
            // We maintain the induction variable k and compute the index i on the fly.
            // This avoids the intermediate array k_vals[].
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; i += stride) {
                k += j;
                a_ptr[i] += b_ptr[LEN_1D - k];
            }
        }
        
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}