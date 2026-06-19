// Best optimization for s1232
real_t s1232(struct args_t * func_args)
{

//    loop interchange
//    interchanging of triangular loops

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t (* __restrict__ aa_)[LEN_2D] = aa;
    real_t (* __restrict__ bb_)[LEN_2D] = bb;
    real_t (* __restrict__ cc_)[LEN_2D] = cc;

    for (int nl = 0; nl < 100*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            #pragma clang loop vectorize(enable)
            for (int j = 0; j <= i; j++) {
                aa_[i][j] = bb_[i][j] + cc_[i][j];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 1.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}