// Best optimization for s172
real_t s172(struct args_t * func_args)
{
    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ = a;
    real_t * __restrict__ b_ = b;

    for (int nl = 0; nl < iterations; nl++) {
        int start = n1 - 1;
        int stride = n3;

        if (stride == 1) {
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; ++i) {
                a_[i] += b_[i];
            }
        } else if (stride == 2) {
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; i += 2) {
                a_[i] += b_[i];
            }
        } else if (stride == 4) {
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; i += 4) {
                a_[i] += b_[i];
            }
        } else {
            // General fallback: use pointer arithmetic and explicit trip count
            // to help the compiler vectorize variable stride loops
            if (stride > 0) {
                int limit = LEN_1D;
                int offset = start;
                // Calculate the number of iterations
                int trip_count = (limit - offset + stride - 1) / stride;
                if (trip_count > 0) {
                    real_t * __restrict__ pa = a_ + offset;
                    real_t * __restrict__ pb = b_ + offset;
                    #pragma clang loop vectorize(enable)
                    for (int k = 0; k < trip_count; ++k) {
                        pa[k * stride] += pb[k * stride];
                    }
                }
            } else {
                // Handle non-positive stride (though unlikely in this benchmark)
                for (int i = start; i < LEN_1D; i += stride) {
                    a_[i] += b_[i];
                }
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}