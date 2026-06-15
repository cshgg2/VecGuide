// Round 2 optimization for s1161
//
// Optimization Strategy:
//   针对编译器报告的“无法识别数组边界”错误，显式将指针参数复制到局部受限指针变量，并使用常量边界变量辅助编译器进行依赖分析，同时保留 restrict 和 pragma 以确保向量化意图。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s1161_6_ez1pd4/minimal_s1161.c:45:8: remark: loop not vectorized: c...
//   2. /tmp/acpo_s1161_6_ez1pd4/minimal_s1161.c:73:9: remark: loop not vectorized (F...
//   3. /tmp/acpo_s1161_6_ez1pd4/minimal_s1161.c:73:9: warning: loop not vectorized: ...
real_t s1161(struct args_t * func_args)
{

//    control flow
//    tests for recognition of loop independent dependences
//    between statements in mutually exclusive regions.

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ b_ptr = b;
    real_t * __restrict__ c_ptr = c;
    real_t * __restrict__ d_ptr = d;
    real_t * __restrict__ e_ptr = e;

    // Copy to local restricted pointers to help compiler identify array bounds
    real_t * __restrict__ la = a_ptr;
    real_t * __restrict__ lb = b_ptr;
    real_t * __restrict__ lc = c_ptr;
    real_t * __restrict__ ld = d_ptr;
    real_t * __restrict__ le = e_ptr;

    // Use a local constant for the loop bound to assist analysis
    const int len = LEN_1D - 1;

    for (int nl = 0; nl < iterations; nl++) {
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < len; ++i) {
            if (lc[i] < (real_t)0.) {
                lb[i] = la[i] + ld[i] * ld[i];
            } else {
                la[i] = lc[i] + ld[i] * le[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}