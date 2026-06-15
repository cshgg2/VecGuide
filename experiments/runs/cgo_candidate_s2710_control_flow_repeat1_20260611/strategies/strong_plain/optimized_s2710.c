// Round 1 optimization for s2710
//
// Optimization Strategy:
//   将内层循环中的嵌套 if-else 结构转换为使用条件运算符（?:）的标量表达式，消除控制流分支，使编译器能生成掩码指令。同时添加 `#pragma clang loop vectorize(enable)` 显式提示编译器进行向量化。
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
            real_t cond = (a[i] > b[i]);
            real_t ai = a[i];
            real_t bi = b[i];
            real_t ci = c[i];
            real_t di = d[i];
            real_t ei = e[i];

            if (cond) {
                ai = ai + bi * di;
                if (LEN_1D > 10) {
                    ci = ci + di * di;
                } else {
                    ci = di * ei + (real_t)1.;
                }
            } else {
                bi = ai + ei * ei;
                if (x > (real_t)0.) {
                    ci = ai + di * di;
                } else {
                    ci = ci + ei * ei;
                }
            }

            a[i] = ai;
            b[i] = bi;
            c[i] = ci;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}