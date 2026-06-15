// Round 1 optimization for s277
//
// Optimization Strategy:
//   识别到循环内 `goto` 语句导致控制流非线性，阻碍向量化。采用条件选择表达式重构逻辑，消除显式跳转，并使用 restrict 关键字消除指针别名顾虑，使循环体变为标准线性流。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s277_8hysbuqm/minimal_s277.c:61:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s277_8hysbuqm/minimal_s277.c:61:9: remark: loop not vectorized: cou...
//   3. /tmp/acpo_s277_8hysbuqm/minimal_s277.c:61:9: remark: loop not vectorized [-Rp...
real_t s277(struct args_t * func_args)
{

//    control flow
//    test for dependences arising from guard variable computation.

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        real_t * __restrict__ a_p = a;
        real_t * __restrict__ b_p = b;
        real_t * __restrict__ c_p = c;
        real_t * __restrict__ d_p = d;
        real_t * __restrict__ e_p = e;

        for (int i = 0; i < LEN_1D-1; i++) {
                real_t ai = a_p[i];
                real_t bi = b_p[i];
                real_t ci = c_p[i];
                real_t di = d_p[i];
                real_t ei = e_p[i];

                if (ai >= (real_t)0.) {
                    // Corresponds to goto L20 (skip both updates)
                    // No-op
                } else if (bi >= (real_t)0.) {
                    // Corresponds to goto L30 (skip a[i] update, do b[i+1] update)
                    b_p[i+1] = ci + di * ei;
                } else {
                    // Execute both statements
                    a_p[i] = ai + ci * di;
                    b_p[i+1] = ci + di * ei;
                }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}