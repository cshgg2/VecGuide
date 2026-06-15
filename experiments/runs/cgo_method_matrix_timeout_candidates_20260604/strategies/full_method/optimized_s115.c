// Best optimization for s115
real_t s115(struct args_t * func_args)
{

//    linear dependence testing
//    triangular saxpy loop

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 1000*(iterations/LEN_2D); nl++) {
        for (int j = 0; j < LEN_2D; j++) {
            real_t * __restrict__ a_ptr = a;
            real_t (* __restrict__ aa_ptr)[LEN_2D] = aa;
            real_t a_j = a_ptr[j];
            #pragma clang loop vectorize(enable)
            for (int i = j+1; i < LEN_2D; i++) {
                a_ptr[i] -= aa_ptr[j][i] * a_j;
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}