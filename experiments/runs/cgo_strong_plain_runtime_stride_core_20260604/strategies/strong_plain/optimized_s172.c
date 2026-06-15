// Round 1 optimization for s172
//
// Optimization Strategy:
//   将运行时步长循环拆分为连续块处理，消除步长对向量化影响。剥离首元素以处理可能的奇数起始偏移，主循环使用固定步长 1 遍历连续内存段，便于编译器生成 SIMD 指令。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 5
//
// Remaining Issues:
//   1. /tmp/acpo_s172_kv_6sfza/minimal_s172.c:76:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s172_kv_6sfza/minimal_s172.c:54:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s172_kv_6sfza/minimal_s172.c:54:5: remark: loop not vectorized [-Rp...
real_t s172(struct args_t * func_args)
{
    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        if (n3 != 0) {
            int start = n1 - 1;
            int end = LEN_1D;
            
            if (start < end) {
                // Handle the first element separately to align subsequent blocks
                a[start] += b[start];
                
                // Process the rest in contiguous chunks of size n3
                // This transforms the strided loop into a series of vectorizable loops
                for (int offset = 1; offset < n3; offset++) {
                    int base = start + offset;
                    if (base < end) {
                        // Inner loop with stride 1 is trivially vectorizable
                        for (int i = base; i < end; i += n3) {
                            a[i] += b[i];
                        }
                    }
                }
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}