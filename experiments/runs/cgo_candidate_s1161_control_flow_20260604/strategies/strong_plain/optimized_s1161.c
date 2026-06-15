// Round 1 optimization for s1161
//
// Optimization Strategy:
//   将循环内的 `goto` 控制流转换为等价的 `if-else` 结构，消除非结构化跳转，使编译器能识别基本块。
//   由于 `a[i]` 和 `b[i]` 的写入在互斥分支中，不存在写后写（WAW）冲突，且读取依赖仅限于当前迭代，因此循环可以向量化。
//   添加 `#pragma clang loop vectorize(enable)` 显式提示编译器进行向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s1161_wjfdvi99/minimal_s1161.c:45:8: remark: loop not vectorized: c...
//   2. /tmp/acpo_s1161_wjfdvi99/minimal_s1161.c:57:9: remark: loop not vectorized (F...
//   3. /tmp/acpo_s1161_wjfdvi99/minimal_s1161.c:57:9: warning: loop not vectorized: ...
real_t s1161(struct args_t * func_args)
{

//    control flow
//    tests for recognition of loop independent dependences
//    between statements in mutually exclusive regions.

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D-1; ++i) {
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