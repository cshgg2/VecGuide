// Round 1 optimization for s277
//
// Optimization Strategy:
//   将循环内的 `goto` 控制流转换为等价的 `if-else` 条件结构，消除非结构化跳转对自动向量化的阻碍。将原本位于标签后的语句合并到条件分支中，保持原有的执行逻辑和依赖顺序，使循环体变为基本块。由于存在跨迭代依赖（`b[i+1]` 依赖于当前迭代），不添加强制向量化 pragma，保持语义安全。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 3
//
// Remaining Issues:
//   1. /tmp/acpo_s277_mveqak5i/minimal_s277.c:55:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s277_mveqak5i/minimal_s277.c:55:9: remark: loop not vectorized: cou...
//   3. /tmp/acpo_s277_mveqak5i/minimal_s277.c:55:9: remark: loop not vectorized [-Rp...
real_t s277(struct args_t * func_args)
{

//    control flow
//    test for dependences arising from guard variable computation.

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D-1; i++) {
                if (a[i] >= (real_t)0.) {
                    // L20 target: do nothing (fall through)
                } else {
                    if (b[i] >= (real_t)0.) {
                        // L30 target: skip a[i] update
                    } else {
                        a[i] += c[i] * d[i];
                    }
                    b[i+1] = c[i] + d[i] * e[i];
                }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}