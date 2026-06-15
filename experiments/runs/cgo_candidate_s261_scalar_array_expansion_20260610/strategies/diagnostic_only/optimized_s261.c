// Round 1 optimization for s261
//
// Optimization Strategy:
//   识别到标量变量 t 在循环内被重复定义且存在跨迭代数据流依赖，导致编译器无法识别为归约模式。采用标量提升技术，将标量 t 替换为临时数组 t_arr，消除跨迭代依赖，并结合 restrict 关键字消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s261_wkaw9drm/minimal_s261.c:64:35: remark: loop not vectorized: va...
//   2. /tmp/acpo_s261_wkaw9drm/minimal_s261.c:62:9: remark: loop not vectorized [-Rp...
real_t s261(struct args_t * func_args)
{

//    scalar and array expansion
//    wrap-around scalar under an if

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t t_arr[LEN_1D];
    for (int nl = 0; nl < iterations; nl++) {
        real_t * __restrict__ a_ptr = a;
        real_t * __restrict__ b_ptr = b;
        real_t * __restrict__ c_ptr = c;
        real_t * __restrict__ d_ptr = d;
        real_t * __restrict__ t_ptr = t_arr;

        for (int i = 1; i < LEN_1D; ++i) {
            t_ptr[i] = a_ptr[i] + b_ptr[i];
            a_ptr[i] = t_ptr[i] + c_ptr[i-1];
            t_ptr[i] = c_ptr[i] * d_ptr[i];
            c_ptr[i] = t_ptr[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}