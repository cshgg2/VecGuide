// Round 1 optimization for s279
//
// Optimization Strategy:
//   识别到循环内包含复杂的控制流（goto/label）导致向量化失败。采用条件转换技术，将基于标签的跳转逻辑转换为等价的条件选择表达式（三元运算符），消除控制流障碍，并添加 restrict 指针和编译器指令以辅助向量化。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s279(struct args_t * func_args)
{
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
            real_t ai = a_[i];
            real_t bi = b_[i];
            real_t ci = c_[i];
            real_t di = d_[i];
            real_t ei = e_[i];

            // Original logic:
            // if (a[i] > 0) goto L20;
            // b[i] = -b[i] + d[i] * d[i];
            // if (b[i] <= a[i]) goto L30;
            // c[i] += d[i] * e[i];
            // goto L30;
            // L20: c[i] = -c[i] + e[i] * e[i];
            // L30: a[i] = b[i] + c[i] * d[i];

            int cond_a = (ai > (real_t)0.);
            
            // Path 1: cond_a is false
            real_t b_new = -bi + di * di;
            int cond_b = (b_new <= ai);
            
            // Path 1a: cond_a is false, cond_b is false
            real_t c_path1a = ci + di * ei;
            
            // Path 1b: cond_a is false, cond_b is true
            real_t c_path1b = ci;

            // Path 2: cond_a is true
            real_t c_path2 = -ci + ei * ei;

            // Merge c based on conditions
            // If cond_a is true, c = c_path2
            // If cond_a is false and cond_b is false, c = c_path1a
            // If cond_a is false and cond_b is true, c = c_path1b
            real_t c_final = cond_a ? c_path2 : (cond_b ? c_path1b : c_path1a);
            
            // Merge b based on cond_a
            real_t b_final = cond_a ? bi : b_new;

            // Final assignment
            a_[i] = b_final + c_final * di;
            b_[i] = b_final;
            c_[i] = c_final;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}