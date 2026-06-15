// Best optimization for s291
real_t s291(struct args_t * func_args)
{

//    loop peeling
//    wrap around variable, 1 level

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ptr = a;
    real_t * __restrict__ b_ptr = b;

    for (int nl = 0; nl < 2*iterations; nl++) {
        
        // The recurrence im1 = i implies im1_hist[i] = i-1 (with im1_hist[0] = LEN_1D-1).
        // We can initialize the first element directly to match the original semantic.
        // This eliminates the loop-carried dependency.
        int im1_hist_0 = LEN_1D - 1;

        // Main loop: vectorized using the mathematical equivalence im1 = i-1
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            int idx = (i == 0) ? im1_hist_0 : (i - 1);
            a_ptr[i] = (b_ptr[i] + b_ptr[idx]) * (real_t).5;
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}