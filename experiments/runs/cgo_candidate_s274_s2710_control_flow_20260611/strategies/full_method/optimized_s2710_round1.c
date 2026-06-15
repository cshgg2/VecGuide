// Round 1 optimization for s2710
//
// Optimization Strategy:
//   识别到嵌套 if-else 控制流阻碍了向量化。采用条件转换技术，将复杂的分支逻辑转换为基于条件表达式的赋值语句，消除控制流依赖，并配合 restrict 关键字消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ✅ Fully Vectorized
//   Vectorized loops: 1
//   Missed loops: 0
real_t s2710(struct args_t * func_args)
{

//    control flow
//    scalar and vector ifs

    int x = *(int*)func_args->arg_info;

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
            real_t cond = a_[i] > b_[i];
            
            // Branch 1: a[i] update
            real_t a_new = a_[i] + b_[i] * d_[i];
            a_[i] = cond ? a_new : a_[i];

            // Branch 2: b[i] update (else path)
            real_t b_new = a_[i] + e_[i] * e_[i];
            b_[i] = cond ? b_[i] : b_new;

            // Branch 3: c[i] update (nested if-else)
            real_t c_path1 = c_[i] + d_[i] * d_[i];
            real_t c_path2 = d_[i] * e_[i] + (real_t)1.;
            real_t c_path3 = a_[i] + d_[i] * d_[i];
            real_t c_path4 = c_[i] + e_[i] * e_[i];

            // Logic: if (cond) { if (LEN_1D > 10) path1 else path2 } else { if (x > 0) path3 else path4 }
            // Note: a_[i] used in path3 is the original a_[i] because b_new is assigned to b_ not a_
            // However, in the original code, b[i] = a[i] + ... happens in the else block.
            // Since a[i] is not modified in the else block before being read for c[i], using a_[i] is correct.
            
            real_t c_val_if_true = (LEN_1D > 10) ? c_path1 : c_path2;
            real_t c_val_if_false = (x > (real_t)0.) ? c_path3 : c_path4;
            
            c_[i] = cond ? c_val_if_true : c_val_if_false;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}