// Round 1 optimization for s1113
//
// Optimization Strategy:
//   识别到循环在写 a[i] 的同时读固定位置 a[LEN_1D/2]，当 i 命中该位置时存在写后读依赖。采用循环拆分技术，将循环分为 i < mid、i == mid 和 i > mid 三段，确保各段内无依赖，从而安全向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 6
//
// Remaining Issues:
//   1. /tmp/acpo_s1113_v3xb53kc/minimal_s1113.c:72:18: remark: loop not vectorized: ...
//   2. /tmp/acpo_s1113_v3xb53kc/minimal_s1113.c:71:9: remark: loop not vectorized (F...
//   3. /tmp/acpo_s1113_v3xb53kc/minimal_s1113.c:61:18: remark: loop not vectorized: ...
real_t s1113(struct args_t * func_args)
{

//    linear dependence testing
//    one iteration dependency on a(LEN_1D/2) but still vectorizable

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 2*iterations; nl++) {
        int mid = LEN_1D / 2;
        
        // Phase 1: i < mid
        // a[mid] is not written yet, safe to read and vectorize
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < mid; i++) {
            a[i] = a[mid] + b[i];
        }

        // Phase 2: i == mid
        // Read the original a[mid] (which is still valid here) and write it
        a[mid] = a[mid] + b[mid];

        // Phase 3: i > mid
        // a[mid] has been updated, subsequent iterations read the new value
        #pragma clang loop vectorize(enable)
        for (int i = mid + 1; i < LEN_1D; i++) {
            a[i] = a[mid] + b[i];
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}