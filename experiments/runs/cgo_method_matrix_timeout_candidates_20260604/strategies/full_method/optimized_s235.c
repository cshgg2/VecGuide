// Best optimization for s235
real_t s235(struct args_t * func_args)
{

//    loop interchanging
//    imperfectly nested loops

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 200*(iterations/LEN_2D); nl++) {
        // Loop Distribution: Separate the producer of a[i]
        for (int i = 0; i < LEN_2D; i++) {
            a[i] += b[i] * c[i];
        }

        // Loop Interchange: Swap i and j loops.
        // The recurrence is on j (aa[j][i] depends on aa[j-1][i]).
        // By making j the outer loop, the inner i loop becomes vectorizable.
        for (int j = 1; j < LEN_2D; j++) {
            #pragma clang loop vectorize(enable)
            for (int i = 0; i < LEN_2D; i++) {
                aa[j][i] = aa[j-1][i] + bb[j][i] * a[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}