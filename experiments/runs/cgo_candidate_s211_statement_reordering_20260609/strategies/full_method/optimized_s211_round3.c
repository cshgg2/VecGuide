// Round 3 optimization for s211
//
// Optimization Strategy:
//   分析发现循环内存在 `b[i]` 依赖 `b[i+1]` 的反向真依赖，这是阻碍向量化的根本原因。由于无法通过简单的 pragma 消除这种数据流依赖，且循环拆分已被验证会破坏语义，本轮采用保守策略：移除可能干扰编译器分析的 `interleave` pragma，保留 `restrict` 和基础的 `vectorize(enable)` 指令。这旨在让编译器在保证语义正确的前提下，尽可能对无依赖部分（如 `a[i]` 的计算）进行向量化，同时接受 `b[i]` 部分无法向量化的结果。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s211_gisa8m66/minimal_s211.c:63:21: remark: loop not vectorized: va...
//   2. /tmp/acpo_s211_gisa8m66/minimal_s211.c:62:9: remark: loop not vectorized (For...
//   3. /tmp/acpo_s211_gisa8m66/minimal_s211.c:62:9: warning: loop not vectorized: th...
real_t s211(struct args_t * func_args)
{

//    statement reordering
//    statement reordering allows vectorization

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        real_t * __restrict__ a_ = a;
        real_t * __restrict__ b_ = b;
        real_t * __restrict__ c_ = c;
        real_t * __restrict__ d_ = d;
        real_t * __restrict__ e_ = e;

        #pragma clang loop vectorize(enable)
        for (int i = 1; i < LEN_1D-1; i++) {
            a_[i] = b_[i - 1] + c_[i] * d_[i];
            b_[i] = b_[i + 1] - e_[i] * d_[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}