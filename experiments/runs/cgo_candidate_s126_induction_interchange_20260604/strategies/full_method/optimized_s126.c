// Best optimization for s126
real_t s126(struct args_t * func_args)
{

//    induction variable recognition
//    induction variable in two loops; recurrence in inner loop

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            // Precompute the base index for the flat array for this row i
            // k_base = i * LEN_2D
            int k_base = i * LEN_2D;
            
            // The recurrence bb[j][i] = bb[j-1][i] + ... prevents vectorization.
            // We keep the loop structure but ensure the index calculation is clean.
            for (int j = 1; j < LEN_2D; j++) {
                // k = k_base + j
                int k = k_base + j;
                bb[j][i] = bb[j-1][i] + flat_2d_array[k-1] * cc[j][i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}