// Original s293 from TSVC
//
// Vectorization Issues for s293:
//   Severity: medium
//   Total diagnostics: 4
//   Not vectorized count: 2
//   Problems:
//     1. Line 2165: unsafe dependent memory operations in loop. Use #pragma loop distribute(enabl...
real_t s293(struct args_t * func_args)
{

//    loop peeling
//    a(i)=a(0) with actual dependence cycle, loop is vectorizable

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 4*iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            a[i] = a[0];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}