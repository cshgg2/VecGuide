// Round 2 optimization for s211
//
// Optimization Strategy:
//   上一轮循环拆分破坏了跨迭代的数据依赖语义。本轮采用指针别名消除（restrict）和显式向量化指令，同时保持原始循环结构不变，确保 `b[i]` 的读写顺序正确，让编译器在保证语义安全的前提下尝试向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s211_r3xvpst7/minimal_s211.c:63:21: remark: loop not vectorized: va...
//   2. /tmp/acpo_s211_r3xvpst7/minimal_s211.c:62:9: remark: loop not vectorized (For...
//   3. /tmp/acpo_s211_r3xvpst7/minimal_s211.c:62:9: warning: loop not vectorized: th...
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

        #pragma clang loop vectorize(enable) interleave(enable)
        for (int i = 1; i < LEN_1D-1; i++) {
            a_[i] = b_[i - 1] + c_[i] * d_[i];
            b_[i] = b_[i + 1] - e_[i] * d_[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}