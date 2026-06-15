// Round 1 optimization for s1113
//
// Optimization Strategy:
//   检测到循环内对 `a[LEN_1D/2]` 的读取与对 `a[i]` 的写入存在潜在重叠，导致编译器报告不安全依赖。采用循环拆分技术，将循环分为 `i < mid`、`i == mid` 和 `i > mid` 三个阶段，确保向量化的同时严格保持原始语义中 `a[mid]` 更新前后的读取逻辑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 6
//
// Remaining Issues:
//   1. /tmp/acpo_s1113_0jl3vh5h/minimal_s1113.c:69:18: remark: loop not vectorized: ...
//   2. /tmp/acpo_s1113_0jl3vh5h/minimal_s1113.c:68:9: remark: loop not vectorized (F...
//   3. /tmp/acpo_s1113_0jl3vh5h/minimal_s1113.c:58:18: remark: loop not vectorized: ...
real_t s1113(struct args_t * func_args)
{
    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 2*iterations; nl++) {
        int mid = LEN_1D / 2;
        int i;

        // Phase 1: i < mid
        // a[i] uses the original value of a[mid] before it is overwritten
        #pragma clang loop vectorize(enable)
        for (i = 0; i < mid; i++) {
            a[i] = a[mid] + b[i];
        }

        // Phase 2: i == mid
        // a[mid] is updated here. Subsequent reads must see this new value.
        a[mid] = a[mid] + b[mid];

        // Phase 3: i > mid
        // a[i] uses the updated value of a[mid]
        #pragma clang loop vectorize(enable)
        for (i = mid + 1; i < LEN_1D; i++) {
            a[i] = a[mid] + b[i];
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}