// Round 3 optimization for s1161
//
// Optimization Strategy:
//   针对编译器仍无法识别数组边界的问题，放弃使用全局指针和局部指针副本，直接在循环内部使用原始全局数组名 `a/b/c/d/e`。这利用了 TSVC 基准测试中全局数组大小在编译期已知的特性，消除指针边界分析的不确定性，同时保留 restrict 语义和强制向量化 pragma。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s1161_nktrumrj/minimal_s1161.c:45:8: remark: loop not vectorized: c...
//   2. /tmp/acpo_s1161_nktrumrj/minimal_s1161.c:59:9: remark: loop not vectorized (F...
//   3. /tmp/acpo_s1161_nktrumrj/minimal_s1161.c:59:9: warning: loop not vectorized: ...
real_t s1161(struct args_t * func_args)
{

//    control flow
//    tests for recognition of loop independent dependences
//    between statements in mutually exclusive regions.

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    const int len = LEN_1D - 1;

    for (int nl = 0; nl < iterations; nl++) {
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < len; ++i) {
            if (c[i] < (real_t)0.) {
                b[i] = a[i] + d[i] * d[i];
            } else {
                a[i] = c[i] + d[i] * e[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}