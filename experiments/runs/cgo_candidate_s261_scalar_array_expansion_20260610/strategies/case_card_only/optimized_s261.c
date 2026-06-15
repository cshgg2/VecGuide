// Round 1 optimization for s261
//
// Optimization Strategy:
//   识别到标量变量 t 在循环内被重复定义且跨语句使用，导致编译器无法识别其生命周期。通过将 t 声明为局部循环变量，消除跨迭代的潜在依赖，并配合 restrict 关键字和编译器指令强制向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s261_vqam6bwq/minimal_s261.c:63:26: remark: loop not vectorized: va...
//   2. /tmp/acpo_s261_vqam6bwq/minimal_s261.c:61:9: remark: loop not vectorized (For...
//   3. /tmp/acpo_s261_vqam6bwq/minimal_s261.c:61:9: warning: loop not vectorized: th...
real_t s261(struct args_t * func_args)
{

//    scalar and array expansion
//    wrap-around scalar under an if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_p = a;
    real_t * __restrict__ b_p = b;
    real_t * __restrict__ c_p = c;
    real_t * __restrict__ d_p = d;

    for (int nl = 0; nl < iterations; nl++) {
        #pragma clang loop vectorize(enable)
        for (int i = 1; i < LEN_1D; ++i) {
            real_t t = a_p[i] + b_p[i];
            a_p[i] = t + c_p[i-1];
            t = c_p[i] * d_p[i];
            c_p[i] = t;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}