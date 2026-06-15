// Round 1 optimization for s277
//
// Optimization Strategy:
//   识别到循环内存在 `goto` 导致的非结构化控制流，阻碍了向量化。采用标量提升技术，将标签 `L20` 和 `L30` 转换为布尔标志变量，消除显式跳转，使循环体变为线性结构，从而允许编译器进行 if-conversion 和向量化。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s277_4wxnw715/minimal_s277.c:55:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s277_4wxnw715/minimal_s277.c:55:9: remark: loop not vectorized: cou...
//   3. /tmp/acpo_s277_4wxnw715/minimal_s277.c:55:9: remark: loop not vectorized [-Rp...
real_t s277(struct args_t * func_args)
{

//    control flow
//    test for dependences arising from guard variable computation.

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D-1; i++) {
                int l20_reached = 0;
                int l30_reached = 0;

                if (a[i] >= (real_t)0.) {
                    l20_reached = 1;
                }
                if (!l20_reached && b[i] >= (real_t)0.) {
                    l30_reached = 1;
                }
                if (!l20_reached && !l30_reached) {
                    a[i] += c[i] * d[i];
                }
                if (!l20_reached) {
                    b[i+1] = c[i] + d[i] * e[i];
                }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}