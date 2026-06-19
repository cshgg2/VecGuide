// Round 1 optimization for s122
//
// Optimization Strategy:
//   将内层循环中的递推变量 `k` 展开为基于循环索引 `i` 的线性表达式，消除跨迭代数据依赖，使循环体变为纯数组操作。同时，将 `b` 数组的反向索引计算移至循环内部，确保编译器能识别内存访问模式，从而启用自动向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 5
//
// Remaining Issues:
//   1. /tmp/acpo_s122_m5o3494n/minimal_s122.c:77:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s122_m5o3494n/minimal_s122.c:60:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s122_m5o3494n/minimal_s122.c:60:5: remark: loop not vectorized [-Rp...
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
        // k = 0 initially, k += j per iteration => k = iteration_count
        // i starts at n1-1, step n3
        // iteration_count = (i - (n1 - 1)) / n3
        // k = (i - n1 + 1) / n3
        // b index = LEN_1D - k = LEN_1D - (i - n1 + 1) / n3
        
        // Calculate start and end for the loop to maintain exact iteration space
        int start = n1 - 1;
        int end = LEN_1D;
        int step = n3;

        for (int i = start; i < end; i += step) {
            k = (i - start) / step;
            a[i] += b[LEN_1D - k];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}