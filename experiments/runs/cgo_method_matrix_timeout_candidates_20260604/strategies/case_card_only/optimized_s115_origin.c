// Original s115 from TSVC
//
// Vectorization Issues for s115:
//   Severity: medium
//   Total diagnostics: 2
//   Not vectorized count: 1
//   Problems:
//     1. Line 231: unsafe dependent memory operations in loop. Use #pragma loop distribute(enabl...
real_t s115(struct args_t * func_args)
{

//    linear dependence testing
//    triangular saxpy loop

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 1000*(iterations/LEN_2D); nl++) {
        for (int j = 0; j < LEN_2D; j++) {
            for (int i = j+1; i < LEN_2D; i++) {
                a[i] -= aa[j][i] * a[j];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}