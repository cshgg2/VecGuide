// Best optimization for s122
real_t s122(struct args_t * func_args)
{

//    induction variable recognition
//    variable lower and upper bound, and stride
//    reverse data access and jump in data access

    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ b_ptr = b;

    int j, k;
    for (int nl = 0; nl < iterations; nl++) {
        j = 1;
        k = 0;
        
        int start = n1 - 1;
        int stride = n3;

        if (stride == 1) {
            // Fast path for stride == 1: Direct vectorization
            // k = i - start + 1 (since k starts at 0, i starts at start)
            // a[i] += b[LEN_1D - k]
            // a[i] += b[LEN_1D - (i - start + 1)]
            // a[i] += b[LEN_1D - i + start - 1]
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; i++) {
                a_ptr[i] += b_ptr[LEN_1D - (i - start) - 1];
            }
        } else {
            // Generic path for stride > 1: Two-phase precomputation
            int k_vals[LEN_1D];
            int idx = 0;

            // Phase 1: Precompute induction variable k
            for (int i = start; i < LEN_1D; i += stride) {
                k += j;
                k_vals[idx++] = k;
            }

            // Phase 2: Vectorized data access
            #pragma clang loop vectorize(enable)
            for (int t = 0; t < idx; t++) {
                int i = start + t * stride;
                a_ptr[i] += b_ptr[LEN_1D - k_vals[t]];
            }
        }
        
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}