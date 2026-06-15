// Round 1 optimization for s291
//
// Optimization Strategy:
//   识别到变量 im1 在循环内形成跨迭代递推依赖，阻止了向量化。采用循环拆分技术，将索引计算预计算到临时数组中，消除数据依赖，并使用 restrict 消除指针别名顾虑。
//
// Compilation: ✅ Success
// Vectorization: ⚠️ Partial
//   Vectorized loops: 0
//   Missed loops: 2
//
// Remaining Issues:
//   1. /tmp/acpo_s291_igqbh41z/minimal_s291.c:58:9: remark: loop not vectorized: val...
//   2. /tmp/acpo_s291_igqbh41z/minimal_s291.c:58:9: remark: loop not vectorized [-Rp...
real_t s291(struct args_t * func_args)
{

//    loop peeling
//    wrap around variable, 1 level

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int im1;
    int idx_array[LEN_1D];
    for (int nl = 0; nl < 2*iterations; nl++) {
        im1 = LEN_1D - 1;
        for (int i = 0; i < LEN_1D; i++) {
            idx_array[i] = im1;
            im1 = i;
        }
        
        real_t * __restrict__ a_ptr = a;
        real_t * __restrict__ b_ptr = b;
        
        for (int i = 0; i < LEN_1D; i++) {
            a_ptr[i] = (b_ptr[i] + b_ptr[idx_array[i]]) * (real_t).5;
        }
        
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}