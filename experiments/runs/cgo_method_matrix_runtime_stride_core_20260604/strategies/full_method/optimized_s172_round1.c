// Round 1 optimization for s172
//
// Optimization Strategy:
//   识别到运行时步长 `n3` 导致循环边界未知，阻碍向量化。采用多版本化策略，针对常见步长（1/2/4）生成专用分支并启用 pragma，同时保留通用 fallback 路径以覆盖所有参数情况。使用 restrict 消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 3
//   Missed loops: 5
//
// Remaining Issues:
//   1. /tmp/acpo_s172_k5zjn9d3/minimal_s172.c:81:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s172_k5zjn9d3/minimal_s172.c:57:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s172_k5zjn9d3/minimal_s172.c:57:5: remark: loop not vectorized [-Rp...
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
            for (int i = start; i < LEN_1D; i += stride) {
                a_[i] += b_[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}