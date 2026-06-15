// Round 2 optimization for s256
//
// Optimization Strategy:
//   针对 `a_ptr[j]` 的递推依赖无法消除，采用循环拆分策略。将内层循环拆分为两个独立循环：第一个循环仅处理标量递推 `a_ptr[j]`，第二个循环处理可向量化的数组运算 `aa_ptr[j][i]`。通过分离依赖和计算，最大化第二部分的向量化效率。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s256_x6u2gnbw/minimal_s256.c:64:42: remark: loop not vectorized: va...
//   2. /tmp/acpo_s256_x6u2gnbw/minimal_s256.c:63:13: remark: loop not vectorized [-R...
real_t s256(struct args_t * func_args)
{

//    scalar and array expansion
//    array expansion

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ d_ptr = d;
    real_t (* __restrict__ aa_ptr)[LEN_2D] = aa;
    real_t (* __restrict__ bb_ptr)[LEN_2D] = bb;

    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            // Loop 1: Handle the scalar recurrence on 'a'
            // This loop cannot be vectorized due to data dependency (a[j] depends on a[j-1])
            for (int j = 1; j < LEN_2D; j++) {
                a_ptr[j] = (real_t)1.0 - a_ptr[j - 1];
            }
            
            // Loop 2: Compute 'aa' using the updated 'a'
            // This loop is independent and can be vectorized
            #pragma clang loop vectorize(enable)
            for (int j = 1; j < LEN_2D; j++) {
                aa_ptr[j][i] = a_ptr[j] + bb_ptr[j][i]*d_ptr[j];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}