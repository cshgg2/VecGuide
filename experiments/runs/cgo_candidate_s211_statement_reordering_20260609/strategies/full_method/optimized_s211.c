// Best optimization for s211
real_t s211(struct args_t * func_args)
{

//    statement reordering
//    statement reordering allows vectorization

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        real_t * __restrict__ a_ = a;
        real_t * __restrict__ b_ = b;
        real_t * __restrict__ c_ = c;
        real_t * __restrict__ d_ = d;
        real_t * __restrict__ e_ = e;

        #pragma clang loop vectorize(enable) interleave(enable)
        for (int i = 1; i < LEN_1D-1; i++) {
            a_[i] = b_[i - 1] + c_[i] * d_[i];
            b_[i] = b_[i + 1] - e_[i] * d_[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}