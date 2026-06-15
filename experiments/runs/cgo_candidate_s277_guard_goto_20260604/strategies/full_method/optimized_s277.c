// Best optimization for s277
real_t s277(struct args_t * func_args)
{

//    control flow
//    test for dependences arising from guard variable computation.

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        // Split loop part 1: Handle conditional logic for a[i]
        // This isolates the control flow that prevents vectorization
        for (int i = 0; i < LEN_1D-1; i++) {
            if (a[i] >= (real_t)0.) {
                // Original logic: goto L20 skips the rest of the body
                // We achieve this by using 'continue' here
                continue;
            }
            if (b[i] >= (real_t)0.) {
                // Original logic: goto L30 skips a[i] update but goes to b[i+1] update
                // We achieve this by skipping the a[i] assignment
                continue;
            }
            a[i] += c[i] * d[i];
        }

        // Split loop part 2: Handle unconditional logic for b[i+1]
        // This part is loop-carried dependence free and easily vectorizable
        for (int i = 0; i < LEN_1D-1; i++) {
            if (a[i] >= (real_t)0.) {
                // Original logic: goto L20 skips b[i+1] update
                continue;
            }
            // Note: The second 'if (b[i] >= 0.)' in original code just skipped a[i] update
            // and fell through to here. Since we are in a separate loop, we must replicate
            // the exact condition that guards the b[i+1] update.
            // In original code: if (a[i]>=0) -> L20 (skip b). if (b[i]>=0) -> L30 (do b).
            // So b[i+1] is skipped ONLY if a[i] >= 0.
            b[i+1] = c[i] + d[i] * e[i];
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}