// Best optimization for s256
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