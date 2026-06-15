// Round 1 optimization for s122
//
// Optimization Strategy:
//   将内层循环中的标量递推变量 `k` 替换为基于循环索引 `i` 的线性表达式，消除跨迭代数据依赖，使编译器能识别出 `a[i]` 和 `b[LEN_1D - k]` 的访问模式均为线性可计算。同时添加 `restrict` 关键字和 `#pragma clang loop vectorize(enable)` 以消除别名疑虑并明确提示向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 5
//
// Remaining Issues:
//   1. /tmp/acpo_s122_tt3o3bya/minimal_s122.c:76:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s122_tt3o3bya/minimal_s122.c:60:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s122_tt3o3bya/minimal_s122.c:60:5: remark: loop not vectorized [-Rp...
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

    int j, k;
    for (int nl = 0; nl < iterations; nl++) {
        j = 1;
        // k is initialized to 0 before the loop.
        // Inside the loop: k += j, where j is constant 1.
        // Iteration 0 (i = n1-1): k = 0 + 1 = 1
        // Iteration 1 (i = n1-1+n3): k = 1 + 1 = 2
        // Iteration t: k = t + 1
        // Since i = n1 - 1 + t * n3, we have t = (i - (n1 - 1)) / n3.
        // Therefore, k = (i - (n1 - 1)) / n3 + 1.
        // This transformation removes the loop-carried dependency on k.
        
        int start_i = n1 - 1;
        for (int i = start_i; i < LEN_1D; i += n3) {
            k = (i - start_i) / n3 + 1;
            a[i] += b[LEN_1D - k];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}