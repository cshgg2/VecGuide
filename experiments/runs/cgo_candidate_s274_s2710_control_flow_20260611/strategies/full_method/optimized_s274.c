// Best optimization for s274
real_t s274(struct args_t * func_args)
{

//    control flow
//    complex loop with dependent conditional

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ = a;
    real_t * __restrict__ b_ = b;
    real_t * __restrict__ c_ = c;
    real_t * __restrict__ d_ = d;
    real_t * __restrict__ e_ = e;

    for (int nl = 0; nl < iterations; nl++) {
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            real_t temp_a = c_[i] + e_[i] * d_[i];
            a_[i] = temp_a;
            if (temp_a > (real_t)0.) {
                b_[i] = temp_a + b_[i];
            } else {
                a_[i] = d_[i] * e_[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}