// Round 1 optimization for s122
//
// Optimization Strategy:
//   识别到归纳变量 k 导致的跨迭代依赖和运行时变步长阻碍向量化。采用两阶段重构：阶段1预计算索引值以消除递推依赖，阶段2使用 restrict 指针和 pragma 强制向量化数据访问循环。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 2
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s122_s2hmtpe1/minimal_s122.c:85:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s122_s2hmtpe1/minimal_s122.c:63:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s122_s2hmtpe1/minimal_s122.c:63:5: remark: loop not vectorized [-Rp...
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
        
        int k_vals[LEN_1D];
        int idx = 0;
        int start = n1 - 1;
        int stride = n3;

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
        
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}