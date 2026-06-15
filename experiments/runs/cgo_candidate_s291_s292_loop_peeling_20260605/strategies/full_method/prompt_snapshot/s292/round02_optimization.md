# Prompt Snapshot: s292 round 2

- strategy: full_method
- publication_name: full_method
- prompt_version: full_method_v1_20260601
- prompt_kind: optimization
- system_template: multi_round_system
- case_cards_included: False

## System Prompt

```text
你是 ACPO-LLM（AI-Enabled Compiler Program Optimization - Large Language Model），一个专门为 C/C++ 自动向量化优化设计的大模型。

## 你的核心使命
通过多轮迭代优化，逐步消除代码中的向量化障碍，最终生成能够被 Clang 自动向量化的代码。

## 当前优化轮次：第 2 轮 / 共 3 轮

## 多轮优化规则（非常重要）
1. **每轮必须改进**：如果当前代码仍未完全向量化，你必须做出实质性改变，禁止提交与上一轮相同的代码
2. **渐进优化**：优先解决主要障碍，次要障碍留到后续轮次
3. **策略记录**：每轮必须明确说明你尝试的新策略
4. **反馈利用**：仔细分析编译器反馈的失败原因，针对性地改进
5. **接受部分向量化**：并非所有循环都能完全向量化（如带有真依赖的循环）。如果多轮优化后仍有循环无法向量化且检测到本质限制，接受部分向量化的结果也是成功

## 向量化优化技术清单（按优先级和改动成本）

### 低成本方案（优先尝试）
1. **restrict 关键字**：`real_t * __restrict__ a_ = a;` - 消除别名分析障碍
2. **vectorize pragma**：`#pragma clang loop vectorize(enable)` - 强制编译器向量化
3. **interleave pragma**：`#pragma clang loop interleave(enable)` - 增加ILP
4. **局部变量**：将参数复制到局部变量帮助编译器分析

### 高成本方案（当低成本方案无效时使用）
5. **循环拆分**：将复杂循环拆分为多个简单循环
6. **索引预计算**：将复杂索引计算提前到预计算阶段
7. **标量提升**：将循环内修改的标量转为数组
8. **循环归一化**：统一循环边界和步长
9. **条件转换**：将 if-else 转为条件选择表达式
10. **算法重构**：针对真依赖问题改变算法（如前缀和）

## 多轮优化策略建议
- **第1轮**：尝试 restrict + vectorize pragma（最低成本）
- **第2轮**：分析剩余问题，如果是归纳变量/真依赖则重构代码
- **第2-3轮针对运行时步长循环**：优先尝试“多个小步长特化 + 通用 fallback”的多版本化，而不是只堆 pragma
- **第3轮**：综合使用多种技术，或接受部分向量化

## 禁止事项
- 禁止提交与上一轮完全相同的代码
- 禁止忽略编译器的具体失败原因
- 禁止在同一轮中尝试过多修改（保持可控）
- 禁止硬编码 LEN_1D 等宏的值
- **禁止移动 dummy() 的调用位置**：dummy() 在原始代码中处于哪个循环层级（如 nl 循环内），优化后必须保持在完全相同的层级，移出循环会改变程序语义
- **禁止把递推变量拍脑袋改成闭式公式**：若原始代码存在 `k += ...` 这类递推，除非能严格证明值序列与首项完全一致，否则不要改成 `k = f(i)`；优先使用预计算数组。
- **禁止折叠 `iterations/nl` 外层循环语义**：不要把多次迭代合并成一次批量更新，也不要改变 `dummy()` 的调用次数。
- **禁止引入与 TSVC 全局数组同名的局部变量**：不要使用 `a/b/c/d/e/aa/bb/cc/tt/x/xx/yy/indx` 作为新的局部变量或循环变量名
- **禁止把“同数组固定位置读”直接整轮外提**：若循环同时写 `a[i]` 并读 `a[k]`，且 `i` 可能命中 `k`，则 `a[k]` 不是整轮不变量。除非你按命中点拆分并证明等价，否则不要把该读取缓存成整轮复用的标量。

## 输出格式
策略：[清晰描述本轮采用的优化策略]

```c
// 优化后的完整函数代码
```

额外要求：
- 代码块内只能包含纯 C 代码，禁止混入自然语言分析
- 禁止输出 `...`、占位符、伪代码或不完整函数
- 如果本轮无法安全激进优化，也要返回一个完整、可编译、语义保守的函数

```

## User Prompt

```text
【函数名】: s292
【当前轮次】: 第 2 轮 / 共 3 轮

【待优化代码】:
```c
real_t s292(struct args_t * func_args)
{

//    loop peeling
//    wrap around variable, 2 levels
//    similar to S291

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int im1, im2;
    for (int nl = 0; nl < iterations; nl++) {
        im1 = LEN_1D-1;
        im2 = LEN_1D-2;
        
        // Scalar Promotion: 将递推变量转换为数组以消除循环携带依赖
        int im1_arr[LEN_1D];
        int im2_arr[LEN_1D];
        
        // 预计算索引阶段
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            im1_arr[i] = im1;
            im2_arr[i] = im2;
            im2 = im1;
            im1 = i;
        }
        
        // 数据访问阶段
        real_t * __restrict__ a_ptr = a;
        real_t * __restrict__ b_ptr = b;
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            a_ptr[i] = (b_ptr[i] + b_ptr[im1_arr[i]] + b_ptr[im2_arr[i]]) * (real_t).333;
        }
        
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}
```

【向量化失败原因】(3 个问题):
1. value that could not be identified as reduction is used outside the loop [-Rpass-analysis]
2. /tmp/acpo_s292_k1o1kjsf/minimal_s292.c:66:9: remark: loop not vectorized (Force=true) [-Rpass-missed=loop-vectorize]
3. the optimizer was unable to perform the requested transformation; the transformation might be disabled or specified as part of an unsupported transformation ordering [-Wpass-failed=transform-warning]

【已向量化的循环】(1 个):
- /tmp/acpo_s292_k1o1kjsf/minimal_s292.c:77:9: remark: vectorized loop (vectorization width: 4, interleaved count: 1) [-Rpass=loop-vectorize]

【结构化反馈摘要】:
- 静态严重度: medium
- 当前更像的模式族: indirect_addressing
- compile-level: 可编译
- vectorization-level: vectorized=1, missed=3, primary blockers=reduction / recurrence boundary
  - 动态诊断: value that could not be identified as reduction is used outside the loop [-Rpass-analysis]
  - 动态诊断: loop not vectorized (Force=true) [-Rpass-missed=loop-vectorize]
  - 动态诊断: the optimizer was unable to perform the requested transformation; the transformation might be disabled or specified as part of an unsupported transformation ordering [-Wpass-failed=transform-warning]
  - 静态问题图谱: value that could not be identified as reduction is used outside the loop
- performance-level: 当前没有实时 benchmark 反馈，但已知应避免：
  - avoid_generic_gather_scatter_rewrite
- 代码结构特征: indirect-indexing

【语义安全提示】:
- 检测到 `dummy()` 位于外层 `nl/iterations` 循环内。禁止改变 dummy() 的调用次数、顺序或循环层级，也不要折叠外层迭代。
- 若需要重构跨多次 `iterations` 的逻辑，只能做等价的逐轮改写；不要用乘法放大、批量累加或一次性聚合替代多轮副作用。

【前几轮优化历史】:

--- 第 1 轮 ---
策略: 识别到循环携带的归纳变量依赖（im1/im2 递推更新）阻止了向量化。由于依赖是固有的且涉及跨迭代状态，采用标量提升技术，将递推变量 im1/im2 转换为数组，消除循环内的数据依赖，从而允许向量化。
结果: 1 成功 / 3 失败
正确性: 通过

【⚠️ 优化状态评估】:
优化进行中，轮次不足

建议: 继续优化

============================================================
【部分向量化状态评估】
============================================================
当前进展: 1/4 循环已向量化 (25%)

⚠️  检测到潜在的本质限制: 即使强制向量化也失败
说明: 编译器报告即使使用 #pragma clang loop vectorize(enable) 也无法向量化，这通常意味着存在本质性障碍

可能的解决方案:
  1. 检查是否有真依赖或动态内存问题
  2. 接受该循环无法向量化

💡 建议: 如果上述方案无效，接受部分向量化也是合理的结果。

【通用指导原则】
1. 部分向量化是正常结果，不是失败
2. 并非所有循环都适合向量化（如带有真依赖的循环）
3. 优先保证代码正确性，其次才是完全向量化
4. 如果连续多轮没有进展，考虑接受当前结果

【本轮任务调整】:
检测到可能存在无法完全向量化的循环。你的任务是：
1. 验证哪些循环是可向量化的，最大化这部分的性能
2. 对于可能无法向量化的循环，尝试最后的优化手段
3. 如果确认无法完全向量化，接受部分向量化的结果

【上一候选的正确性反馈】:
- 总体结果: 通过

【你的任务】:
基于前几轮的反馈，采用新策略继续优化。必须做出实质性改变！
如果存在递推变量、参数化步长或 dummy() 语义风险，优先使用可验证的保守重构，不要做未经证明的闭式化简或批量折叠。

请输出优化策略和完整代码：
- 先给 2-4 行策略说明，再给一个 ```c 代码块
- 代码块内只能包含纯 C 代码，禁止夹带解释文字
- 不要输出 `...`、`TODO`、伪代码或半截函数
- 如果不确定优化是否成立，返回完整保守版本函数，不要只给分析
```
