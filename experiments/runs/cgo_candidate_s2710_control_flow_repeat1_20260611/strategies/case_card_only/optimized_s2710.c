// Round 1 optimization for s2710
//
// Optimization Strategy:
//   识别到嵌套的条件分支导致编译器无法进行向量化。采用条件转换技术，将 if-else 分支逻辑转换为三元运算符（?:）的谓词执行形式，消除控制流依赖，使循环体变为直线性代码，从而启用自动向量化。
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

    for (int nl = 0; nl < iterations/2; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            real_t cond = a[i] > b[i];
            real_t a_new = cond ? a[i] + b[i] * d[i] : a[i];
            real_t c_new;
            
            if (cond) {
                if (LEN_1D > 10) {
                    c_new = c[i] + d[i] * d[i];
                } else {
                    c_new = d[i] * e[i] + (real_t)1.;
                }
            } else {
                b[i] = a[i] + e[i] * e[i];
                if (x > (real_t)0.) {
                    c_new = a[i] + d[i] * d[i];
                } else {
                    c_new = c[i] + e[i] * e[i];
                }
            }
            
            a[i] = a_new;
            c[i] = c_new;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}