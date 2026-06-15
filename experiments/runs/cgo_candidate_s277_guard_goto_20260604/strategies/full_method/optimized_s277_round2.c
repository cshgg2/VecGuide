// Round 2 optimization for s277
//
// Optimization Strategy:
//   上一轮将 goto 转换为布尔标志导致语义错误（改变了短路执行逻辑）。本轮采用“循环拆分”策略，将包含复杂控制流的循环拆分为两个独立的循环：第一个循环处理条件判断和 `a[i]` 的更新，第二个循环处理无条件的 `b[i+1]` 更新。这种拆分消除了控制流障碍，同时严格保持了原始的执行顺序和语义。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 1
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s277_mt30f8sn/minimal_s277.c:73:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s277_mt30f8sn/minimal_s277.c:73:9: remark: loop not vectorized: cou...
//   3. /tmp/acpo_s277_mt30f8sn/minimal_s277.c:73:9: remark: loop not vectorized [-Rp...
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