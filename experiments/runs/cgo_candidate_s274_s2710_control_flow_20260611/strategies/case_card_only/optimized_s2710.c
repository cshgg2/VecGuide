// Round 1 optimization for s2710
//
// Optimization Strategy:
//   识别到嵌套 if-else 结构阻碍了编译器的 if-conversion。采用谓词执行优化，将条件分支转换为三元运算符，消除控制流依赖，同时添加 restrict 关键字和编译器指令以强制向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s2710(struct args_t * func_args)
{

//    control flow
//    scalar and vector ifs

    int x = *(int*)func_args->arg_info;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_p = a;
    real_t * __restrict__ b_p = b;
    real_t * __restrict__ c_p = c;
    real_t * __restrict__ d_p = d;
    real_t * __restrict__ e_p = e;

    for (int nl = 0; nl < iterations/2; nl++) {
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            real_t cond = a_p[i] > b_p[i];
            
            real_t new_a = cond ? (a_p[i] + b_p[i] * d_p[i]) : a_p[i];
            real_t new_b = cond ? b_p[i] : (a_p[i] + e_p[i] * e_p[i]);
            
            real_t new_c;
            if (cond) {
                new_c = (LEN_1D > 10) ? (c_p[i] + d_p[i] * d_p[i]) : (d_p[i] * e_p[i] + (real_t)1.);
            } else {
                new_c = (x > (real_t)0.) ? (a_p[i] + d_p[i] * d_p[i]) : (c_p[i] + e_p[i] * e_p[i]);
            }
            
            a_p[i] = new_a;
            b_p[i] = new_b;
            c_p[i] = new_c;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}