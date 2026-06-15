// Best optimization for s278
real_t s278(struct args_t * func_args)
{

//    control flow
//    if/goto to block if-then-else

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            real_t b_val = b[i];
            real_t c_val = c[i];
            
            if (a[i] > (real_t)0.) {
                c_val = -c_val + d[i] * e[i];
            } else {
                b_val = -b_val + d[i] * e[i];
            }
            
            a[i] = b_val + c_val * d[i];
            b[i] = b_val;
            c[i] = c_val;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}