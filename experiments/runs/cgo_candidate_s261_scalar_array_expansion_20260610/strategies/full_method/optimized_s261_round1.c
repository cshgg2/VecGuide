// Round 1 optimization for s261
//
// Optimization Strategy:
//   识别到标量变量 t 在循环内被重复定义且跨语句使用，导致编译器无法识别其为归纳变量。采用标量提升技术，将 t 替换为临时数组 temp_t，消除跨语句依赖，并结合 restrict 消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s261_6rv96y3y/minimal_s261.c:64:36: remark: loop not vectorized: va...
//   2. /tmp/acpo_s261_6rv96y3y/minimal_s261.c:62:9: remark: loop not vectorized (For...
//   3. /tmp/acpo_s261_6rv96y3y/minimal_s261.c:62:9: warning: loop not vectorized: th...
real_t s261(struct args_t * func_args)
{

//    scalar and array expansion
//    wrap-around scalar under an if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ b_ptr = b;
    real_t * __restrict__ c_ptr = c;
    real_t * __restrict__ d_ptr = d;
    real_t temp_t[LEN_1D];

    for (int nl = 0; nl < iterations; nl++) {
        #pragma clang loop vectorize(enable)
        for (int i = 1; i < LEN_1D; ++i) {
            temp_t[i] = a_ptr[i] + b_ptr[i];
            a_ptr[i] = temp_t[i] + c_ptr[i-1];
            temp_t[i] = c_ptr[i] * d_ptr[i];
            c_ptr[i] = temp_t[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}