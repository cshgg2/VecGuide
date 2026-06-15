# Prompt Snapshot: s277 round 3

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

## 当前优化轮次：第 3 轮 / 共 3 轮

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
【函数名】: s277
【当前轮次】: 第 3 轮 / 共 3 轮

【待优化代码】:
```c
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
```

【向量化失败原因】(3 个问题):
1. value that could not be identified as reduction is used outside the loop [-Rpass-analysis=loop-vectorize]
2. could not determine number of loop iterations [-Rpass-analysis=loop-vectorize]
3. /tmp/acpo_s277_rjjwaccy/minimal_s277.c:73:9: remark: loop not vectorized [-Rpass-missed=loop-vectorize]

【已向量化的循环】(1 个):
- /tmp/acpo_s277_rjjwaccy/minimal_s277.c:57:9: remark: vectorized loop (vectorization width: 4, interleaved count: 1) [-Rpass=loop-vectorize]

【结构化反馈摘要】:
- 静态严重度: medium
- 当前更像的模式族: branch_hoisting
- compile-level: 可编译
- vectorization-level: vectorized=1, missed=3, primary blockers=reduction / recurrence boundary, trip count or bounds unknown
  - 动态诊断: value that could not be identified as reduction is used outside the loop [-Rpass-analysis=loop-vectorize]
  - 动态诊断: could not determine number of loop iterations [-Rpass-analysis=loop-vectorize]
  - 静态问题图谱: value that could not be identified as reduction is used outside the loop
  - 静态问题图谱: could not determine number of loop iterations
- performance-level: 当前没有实时 benchmark 反馈，但已知应避免：
  - avoid_large_materialization
- 代码结构特征: control-flow

【语义安全提示】:
- 检测到 `dummy()` 位于外层 `nl/iterations` 循环内。禁止改变 dummy() 的调用次数、顺序或循环层级，也不要折叠外层迭代。
- 若需要重构跨多次 `iterations` 的逻辑，只能做等价的逐轮改写；不要用乘法放大、批量累加或一次性聚合替代多轮副作用。

【前几轮优化历史】:

--- 第 2 轮 ---
策略: 识别到循环内部包含 `goto` 跳转标签导致控制流复杂，阻碍了向量化。采用标量提升技术，将标签 `L20` 和 `L30` 转换为布尔标志变量，将控制流依赖转换为数据依赖，从而允许编译器进行向量化。
结果: 0 成功 / 2 失败
正确性: 失败
失败原因: [n1=1, n3=1] STATE_SUM 不匹配: 原始=2828955042.056498, 优化=10928567889166.056641, diff=10925738934124.000000, tol=109285678.891661

--- 第 3 轮 ---
策略: 上一轮将 goto 转换为布尔标志导致语义错误（改变了短路执行逻辑）。本轮采用“循环拆分”策略，将包含复杂控制流的循环拆分为两个独立的循环：第一个循环处理条件判断和 `a[i]` 的更新，第二个循环处理无条件的 `b[i+1]` 更新。这种拆分消除了控制流障碍，同时严格保持了原始的执行顺序和语义。
结果: 1 成功 / 3 失败
正确性: 通过

【本轮要求】:
上一轮优化后仍未完全向量化。你必须：
1. 分析剩余失败原因
2. 采用与之前不同的策略
3. 做出实质性代码改变
4. 禁止提交与之前完全相同的代码

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
