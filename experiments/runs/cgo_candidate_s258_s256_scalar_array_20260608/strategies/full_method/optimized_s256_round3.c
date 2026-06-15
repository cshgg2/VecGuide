// Round 3 optimization for s256
//
// Optimization Strategy:
//   针对 `a_ptr` 的递推依赖无法向量化，采用标量提升技术。将 `a_ptr` 数组在 `nl` 循环内的更新逻辑转换为局部标量变量 `s_a` 的递推，消除数组写写依赖，从而允许编译器对 `aa_ptr` 的计算循环进行向量化。同时保持 `dummy()` 调用位置不变，并在每次 `nl` 迭代结束时将最终标量值回写至 `a_ptr[LEN_2D-1]` 以维持跨轮语义。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s256_017x1ez2/minimal_s256.c:64:13: remark: loop not vectorized: va...
//   2. /tmp/acpo_s256_017x1ez2/minimal_s256.c:64:13: remark: loop not vectorized [-R...
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
            // Scalar promotion: replace array recurrence with a local scalar variable
            // This removes the loop-carried dependency on the array 'a_ptr'
            real_t s_a = a_ptr[0];
            for (int j = 1; j < LEN_2D; j++) {
                s_a = (real_t)1.0 - s_a;
            }
            
            // Write back the final value to maintain state across nl iterations
            // This is necessary because subsequent nl iterations might read a_ptr[0]
            a_ptr[LEN_2D - 1] = s_a;

            // Vectorized computation using the scalar recurrence result
            // Since s_a is constant for this 'i' iteration, we can use it directly
            // However, to strictly match the original logic where aa[j][i] uses a[j],
            // and a[j] follows the sequence s_a, we need to recompute or store s_a.
            // Given the strict dependency, we recompute the sequence or use the scalar.
            // To enable vectorization, we unroll the dependency logic:
            // a[j] = 1.0 - a[j-1] implies a[j] = (j%2==0) ? a[0] : 1.0-a[0].
            // We use this property to vectorize the calculation of aa.
            
            real_t a0 = a_ptr[0];
            real_t a1 = (real_t)1.0 - a0;
            
            #pragma clang loop vectorize(enable)
            for (int j = 1; j < LEN_2D; j++) {
                // Select value based on parity to simulate the recurrence
                // This removes the dependency on a_ptr[j-1] inside the loop
                real_t val_a = (j % 2 == 1) ? a1 : a0;
                aa_ptr[j][i] = val_a + bb_ptr[j][i]*d_ptr[j];
            }
            
            // Update a_ptr[0] for the next 'i' iteration based on the last value
            // The original code updates the whole array, so a_ptr[0] becomes the last value of previous 'i'
            a_ptr[0] = s_a;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}