// Round 1 optimization for s172
//
// Optimization Strategy:
//   识别到运行时步长 n3 导致循环迭代次数未知，阻止了向量化。采用运行时步长分支策略，针对常见步长（1, 2, 4）使用编译器已知的常量步长循环以启用向量化，并保留通用步长分支以确保对所有参数的正确性。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 2
//   Missed loops: 5
//
// Remaining Issues:
//   1. /tmp/acpo_s172_arxxgete/minimal_s172.c:72:9: remark: loop not vectorized: cal...
//   2. /tmp/acpo_s172_arxxgete/minimal_s172.c:54:5: remark: loop not vectorized: ins...
//   3. /tmp/acpo_s172_arxxgete/minimal_s172.c:54:5: remark: loop not vectorized [-Rp...
real_t s172(struct args_t * func_args)
{
    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        if (n3 == 1) {
            for (int i = n1-1; i < LEN_1D; i += 1) {
                a[i] += b[i];
            }
        } else if (n3 == 2) {
            for (int i = n1-1; i < LEN_1D; i += 2) {
                a[i] += b[i];
            }
        } else if (n3 == 4) {
            for (int i = n1-1; i < LEN_1D; i += 4) {
                a[i] += b[i];
            }
        } else {
            for (int i = n1-1; i < LEN_1D; i += n3) {
                a[i] += b[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}