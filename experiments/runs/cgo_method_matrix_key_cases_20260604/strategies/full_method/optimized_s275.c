// Best optimization for s275
real_t s275(struct args_t * func_args)
{

//    control flow
//    if around inner loop, interchanging needed

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        for (int j = 1; j < LEN_2D; j++) {
            #pragma clang loop vectorize(enable)
            for (int i = 0; i < LEN_2D; i++) {
                aa[j][i] = aa[j-1][i] + bb[j][i] * cc[j][i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}