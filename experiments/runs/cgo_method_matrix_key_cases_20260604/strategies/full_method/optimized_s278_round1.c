// Round 1 optimization for s278
//
// Optimization Strategy:
//   识别到循环体内的 goto 结构阻碍了向量化。采用结构化重构，将 goto 转换为 if-else 块，并引入局部标量暂存更新值，确保分支合并后的赋值逻辑与原始代码语义一致，从而支持编译器的 if-conversion。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s278(struct args_t * func_args)
{

//    control flow
//    if/goto to block if-then-else

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            real_t b_val = b[i];
            real_t c_val = c[i];
            
            if (a[i] > (real_t)0.) {
                c_val = -c_val + d[i] * e[i];
            } else {
                b_val = -b_val + d[i] * e[i];
            }
            
            a[i] = b_val + c_val * d[i];
            b[i] = b_val;
            c[i] = c_val;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}