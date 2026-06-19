// Round 1 optimization for s122
//
// Optimization Strategy:
//   识别到递推变量 k 导致的循环依赖和运行时步长 n3 导致的迭代次数未知。采用循环拆分技术，将索引预计算与数据访问分离到两个循环中，消除依赖并使编译器能确定迭代次数，同时使用 restrict 消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 5
//
// Remaining Issues:
//   1. /tmp/acpo_s122_9onnqh8a/minimal_s122.c:84:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s122_9onnqh8a/minimal_s122.c:64:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s122_9onnqh8a/minimal_s122.c:64:5: remark: loop not vectorized [-Rp...
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
    int i_vals[LEN_1D];
    int count;

    for (int nl = 0; nl < iterations; nl++) {
        j = 1;
        k = 0;
        count = 0;
        
        // First loop: Precompute indices and k values
        for (int i = n1-1; i < LEN_1D; i += n3) {
            k += j;
            i_vals[count] = i;
            k_vals[count] = k;
            count++;
        }

        // Second loop: Perform data access using precomputed values
        real_t * __restrict__ a_ptr = a;
        real_t * __restrict__ b_ptr = b;
        for (int c = 0; c < count; c++) {
            a_ptr[i_vals[c]] += b_ptr[LEN_1D - k_vals[c]];
        }
        
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}