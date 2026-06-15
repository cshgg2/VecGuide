// Best optimization for s1232
real_t s1232(struct args_t * func_args)
{

//    loop interchange
//    interchanging of triangular loops

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ aa_flat = (real_t *)aa;
    real_t * __restrict__ bb_flat = (real_t *)bb;
    real_t * __restrict__ cc_flat = (real_t *)cc;

    for (int nl = 0; nl < 100*(iterations/LEN_2D); nl++) {
        for (int j = 0; j < LEN_2D; j++) {
            #pragma clang loop vectorize(enable)
            for (int i = j; i < LEN_2D; i++) {
                aa_flat[i * LEN_2D + j] = bb_flat[i * LEN_2D + j] + cc_flat[i * LEN_2D + j];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 1.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}