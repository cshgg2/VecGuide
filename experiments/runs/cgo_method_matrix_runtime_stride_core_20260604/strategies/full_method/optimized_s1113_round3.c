// Round 3 optimization for s1113
//
// Optimization Strategy:
//   前两轮已通过循环拆分解决了语义依赖问题，但编译器仍因保守的内存依赖分析拒绝向量化。本轮在保留 restrict 和循环拆分结构的基础上，显式添加 `#pragma clang loop vectorize(enable)` 和 `interleave(enable)`，强制编译器对已隔离依赖的循环段进行向量化，以最大化性能。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 6
//
// Remaining Issues:
//   1. /tmp/acpo_s1113_mebtdduz/minimal_s1113.c:72:19: remark: loop not vectorized: ...
//   2. /tmp/acpo_s1113_mebtdduz/minimal_s1113.c:71:9: remark: loop not vectorized (F...
//   3. /tmp/acpo_s1113_mebtdduz/minimal_s1113.c:61:19: remark: loop not vectorized: ...
real_t s1113(struct args_t * func_args)
{
    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 2*iterations; nl++) {
        int mid = LEN_1D / 2;
        int i;

        real_t * __restrict__ a_ = a;
        real_t * __restrict__ b_ = b;

        // Phase 1: i < mid
        // a[i] uses the original value of a[mid] before it is overwritten
        #pragma clang loop vectorize(enable) interleave(enable)
        for (i = 0; i < mid; i++) {
            a_[i] = a_[mid] + b_[i];
        }

        // Phase 2: i == mid
        // a[mid] is updated here. Subsequent reads must see this new value.
        a_[mid] = a_[mid] + b_[mid];

        // Phase 3: i > mid
        // a[i] uses the updated value of a[mid]
        #pragma clang loop vectorize(enable) interleave(enable)
        for (i = mid + 1; i < LEN_1D; i++) {
            a_[i] = a_[mid] + b_[i];
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}