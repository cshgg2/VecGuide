// Round 1 optimization for s122
//
// Optimization Strategy:
//   识别到递推变量 k 导致的循环依赖及运行时步长阻碍向量化。采用索引预计算技术，将 k 的计算拆分到单独循环中，消除内层循环的跨迭代依赖，并使用 restrict 消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 6
//
// Remaining Issues:
//   1. /tmp/acpo_s122_0e_o40z3/minimal_s122.c:85:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s122_0e_o40z3/minimal_s122.c:64:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s122_0e_o40z3/minimal_s122.c:64:5: remark: loop not vectorized [-Rp...
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
    int k_vals[LEN_1D];
    int idx_vals[LEN_1D];
    int count;

    for (int nl = 0; nl < iterations; nl++) {
        j = 1;
        k = 0;
        
        // Precompute indices to break recurrence dependency
        count = 0;
        for (int i = n1-1; i < LEN_1D; i += n3) {
            k += j;
            k_vals[count] = k;
            idx_vals[count] = i;
            count++;
        }

        // Vectorizable loop using precomputed indices
        real_t * __restrict__ a_ptr = a;
        real_t * __restrict__ b_ptr = b;
        #pragma clang loop vectorize(enable)
        for (int c = 0; c < count; c++) {
            a_ptr[idx_vals[c]] += b_ptr[LEN_1D - k_vals[c]];
        }
        
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}