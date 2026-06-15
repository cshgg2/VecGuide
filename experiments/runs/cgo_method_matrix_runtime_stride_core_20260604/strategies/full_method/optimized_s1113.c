// Best optimization for s1113
real_t s1113(struct args_t * func_args)
{
    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 2*iterations; nl++) {
        int mid = LEN_1D / 2;
        int i;

        real_t * __restrict__ a_ = a;
        real_t * __restrict__ b_ = b;

        // Phase 1: i < mid
        // a[i] uses the original value of a[mid] before it is overwritten
        #pragma clang loop vectorize(enable) interleave(enable)
        for (i = 0; i < mid; i++) {
            a_[i] = a_[mid] + b_[i];
        }

        // Phase 2: i == mid
        // a[mid] is updated here. Subsequent reads must see this new value.
        a_[mid] = a_[mid] + b_[mid];

        // Phase 3: i > mid
        // a[i] uses the updated value of a[mid]
        #pragma clang loop vectorize(enable) interleave(enable)
        for (i = mid + 1; i < LEN_1D; i++) {
            a_[i] = a_[mid] + b_[i];
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}