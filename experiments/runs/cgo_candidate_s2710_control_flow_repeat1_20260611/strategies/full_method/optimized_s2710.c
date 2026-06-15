// Best optimization for s2710
real_t s2710(struct args_t * func_args)
{

//    control flow
//    scalar and vector ifs

    int x = *(int*)func_args->arg_info;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ = a;
    real_t * __restrict__ b_ = b;
    real_t * __restrict__ c_ = c;
    real_t * __restrict__ d_ = d;
    real_t * __restrict__ e_ = e;

    for (int nl = 0; nl < iterations/2; nl++) {
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            real_t cond = a_[i] > b_[i];
            
            real_t new_a = cond ? (a_[i] + b_[i] * d_[i]) : a_[i];
            real_t new_b = cond ? b_[i] : (a_[i] + e_[i] * e_[i]);
            
            real_t new_c;
            if (cond) {
                if (LEN_1D > 10) {
                    new_c = c_[i] + d_[i] * d_[i];
                } else {
                    new_c = d_[i] * e_[i] + (real_t)1.;
                }
            } else {
                if (x > (real_t)0.) {
                    new_c = a_[i] + d_[i] * d_[i];
                } else {
                    new_c = c_[i] + e_[i] * e_[i];
                }
            }
            
            a_[i] = new_a;
            b_[i] = new_b;
            c_[i] = new_c;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}