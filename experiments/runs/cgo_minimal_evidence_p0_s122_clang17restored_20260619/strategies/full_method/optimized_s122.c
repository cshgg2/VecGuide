// Best optimization for s122
real_t s122(struct args_t * func_args)
{
    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ b_ptr = b;

    for (int nl = 0; nl < iterations; nl++) {
        if (n3 == 1) {
            // Specialized path for stride 1: k is linear (k = i - n1 + 2)
            // This allows direct vectorization without precomputation
            #pragma clang loop vectorize(enable) interleave(enable)
            for (int i = n1 - 1; i < LEN_1D; i++) {
                int k = i - n1 + 2;
                a_ptr[i] += b_ptr[LEN_1D - k];
            }
        } else {
            // General path for stride > 1: Use two-phase precomputation
            // to handle complex induction variable and indirect indexing
            int k_values[LEN_1D];
            int i_values[LEN_1D];
            int idx = 0;
            int k = 0;
            int j = 1;

            // Phase 1: Scalar precomputation of indices
            for (int i = n1 - 1; i < LEN_1D; i += n3) {
                k += j;
                k_values[idx] = k;
                i_values[idx] = i;
                idx++;
            }

            // Phase 2: Vectorized data access
            int loop_count = idx;
            #pragma clang loop vectorize(enable) interleave(enable)
            for (int t = 0; t < loop_count; t++) {
                a_ptr[i_values[t]] += b_ptr[LEN_1D - k_values[t]];
            }
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}