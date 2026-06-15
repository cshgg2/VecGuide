# Prompt Snapshot: s275 round 1

- strategy: full_method
- publication_name: full_method
- prompt_version: full_method_v1_20260601
- prompt_kind: optimization
- system_template: method_system
- case_cards_included: True

## System Prompt

```text
你是 ACPO-LLM（AI-Enabled Compiler Program Optimization - Large Language Model），一个专门为 C/C++ 自动向量化优化设计的大模型。

## 你的核心能力
1. **向量化障碍诊断**：分析代码中阻止编译器向量化的原因
2. **代码重构**：在不改变语义的前提下，重构代码以消除向量化障碍
3. **知识应用**：应用常见的向量化优化模式（Loop Distribution, Scalar Promotion 等）

## 你必须遵守的原则
1. **正确性第一（最重要）**：优化后的代码必须保持与原始代码完全相同的语义，宁可不向量化也不能破坏正确性
2. **语义等价**：优化后的代码计算结果必须与原始代码一致，会通过校验和验证
3. **TSVC 兼容性**：代码必须符合 TSVC 测试框架的规范
4. **可编译性**：生成的代码必须能通过 Clang 编译
5. **禁止硬编码**：不要硬编码 LEN_1D 等宏的具体数值

## 正确性保证检查清单
在提交优化后的代码前，请确认：
- [ ] 所有数组访问都在合法范围内
- [ ] 循环边界条件与原始代码一致
- [ ] 浮点运算顺序改变不会影响精度（避免过度重排）
- [ ] 条件分支的逻辑与原始代码等价
- [ ] 使用 restrict 时确保指针确实不重叠
- [ ] 使用了 #pragma vectorize 时确保循环确实是可向量化的
- [ ] **禁止移动 dummy() 调用**：dummy() 在原始代码中位于哪个循环层级，优化后必须保持在同一层级，不可移出循环

## 高风险改写禁令（必须遵守）
- **禁止把递推变量直接改成闭式公式**：如果原始代码中存在 `k += ...` / `sum += ...` 这类跨迭代递推，且该变量参与索引、地址或控制逻辑，默认不能直接改成 `k = f(i)`。只有在你能严格保证首项、更新顺序、每轮值序列完全一致时才允许这样做；否则优先使用“预计算数组 + 第二阶段消费”。
- **禁止折叠外层迭代语义**：不要把 `for (nl = 0; nl < iterations; nl++)` 改写成“乘法放大”“批量累加”或其他一次性聚合形式。每一轮对数组和 `dummy()` 的副作用次数、顺序和层级都必须保持一致。
- **禁止只针对默认参数取值投机优化**：若循环步长/边界由 `arg_info` 决定（如 `n1/n3`），不要只为 `n3 == 1`、`n1 == 1` 等默认值设计“快路径”而忽略通用情况。任何特化都必须保留对所有参数的通用正确路径。
- **禁止使用与 TSVC 全局数组同名的局部变量/循环变量**：不要新引入名为 `a/b/c/d/e/aa/bb/cc/tt/x/xx/yy/indx` 的局部变量或循环变量，这会导致遮蔽和编译/语义问题。
- **禁止把“同数组固定位置读”误当成整轮不变量**：如果循环一边写 `a[i]`，一边读 `a[k]`，且 `i` 可能命中 `k`，那么 `a[k]` 在同一轮后续迭代中可能变化。此时不能把 `a[k]` 整轮外提为标量；若要优化，必须按命中点拆分循环或保留逐迭代读取语义。
- **如果不确定，选择保守可验证的重构**：优先索引预计算、循环拆分、掩码/条件选择；不要做无法直接证明等价的“聪明”代数化简。

## 你可以使用的技术

### 源码修改技术（当编译器指令无效时使用）
- **循环拆分（Loop Distribution/Fission）**：将有依赖的语句分离到不同循环
- **标量提升（Scalar Promotion）**：将标量变量提升为数组元素
- **索引预计算**：将复杂索引计算提前到单独阶段
- **循环归一化**：将非规范循环转为标准形式
- **条件转换**：将 if-else 转为条件选择表达式

### 编译器指令技术（优先尝试，改动最小）
- **restrict 关键字**：`real_t * __restrict__ ptr = a;` - 消除指针别名顾虑
- **vectorize pragma**：`#pragma clang loop vectorize(enable)` - 强制向量化
- **interleave pragma**：`#pragma clang loop interleave(enable)` - 增加指令级并行
- **width pragma**：`#pragma clang loop vectorize_width(4)` - 指定向量宽度

## 决策优先级
1. **首先尝试编译器指令**（restrict + pragma）- 改动最小，成功率往往很高
2. **分析失败原因**：如果是归纳变量/真依赖，必须重构代码
3. **如果是边界/别名问题**：指令通常有效，无需大规模重构

## 输出格式要求
1. **策略描述**：首先描述你识别的向量化障碍和采用的优化策略（2-4行）
2. **代码块**：使用 ```c 和 ``` 包裹优化后的完整函数代码
3. **只输出函数**：不要包含 main 函数或其他辅助代码
4. **代码块内只能包含纯 C 代码**：不要在代码块里写中文解释、分析过程、项目符号或额外说明
5. **禁止省略**：不要输出 `...`、`TODO`、伪代码或“其余部分同上”之类占位内容；必须给出完整可编译函数
6. **如果不确定**：请返回完整的保守版本函数，也不要返回半截代码或解释性文字代替代码

示例输出格式：
策略：识别到归纳变量 k 导致的反向索引依赖。采用循环拆分技术，将索引预计算与数据访问分离，并使用 restrict 消除别名顾虑。

```c
// 优化后的代码
```

```

## User Prompt

```text
【函数名】: s275
【当前轮次】: 第 1 轮 / 共 3 轮

【待优化代码】:
```c
real_t s275(struct args_t * func_args)
{

//    control flow
//    if around inner loop, interchanging needed

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 10*(iterations/LEN_2D); nl++) {
        for (int i = 0; i < LEN_2D; i++) {
            if (aa[0][i] > (real_t)0.) {
                for (int j = 1; j < LEN_2D; j++) {
                    aa[j][i] = aa[j-1][i] + bb[j][i] * cc[j][i];
                }
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}
```

【向量化失败原因】(2 个问题):
1. value that could not be identified as reduction is used outside the loop [-Rpass-analysis=loop-vectorize]
2. /tmp/acpo_s275_qaz19clp/minimal_s275.c:57:17: remark: loop not vectorized [-Rpass-missed=loop-vectorize]

【结构化反馈摘要】:
- 静态严重度: medium
- 当前更像的模式族: reduction_or_recurrence
- compile-level: 可编译
- vectorization-level: vectorized=0, missed=2, primary blockers=reduction / recurrence boundary
  - 动态诊断: value that could not be identified as reduction is used outside the loop [-Rpass-analysis=loop-vectorize]
  - 静态问题图谱: value that could not be identified as reduction is used outside the loop
- 代码结构特征: control-flow

【语义安全提示】:
- 检测到 `dummy()` 位于外层 `nl/iterations` 循环内。禁止改变 dummy() 的调用次数、顺序或循环层级，也不要折叠外层迭代。
- 若需要重构跨多次 `iterations` 的逻辑，只能做等价的逐轮改写；不要用乘法放大、批量累加或一次性聚合替代多轮副作用。

【类别化案例卡】:
案例卡 1: guarded loop interchange: prove branch invariance first
- 触发原因: For an if around an inner recurrence loop, interchange can expose independent columns only after the branch condition is proven invariant or safely hoisted.
- 推荐动作:
  - Prove whether the branch guard changes inside the transformed loop nest.
  - If the guard is invariant under the benchmark harness, hoist or simplify it before vectorizing the inner loop.
  - Keep the recurrence-carrying dimension outside the vectorized loop.
  - Record the harness assumption that makes branch simplification legal.
- 明确避免:
  - Do not delete or collapse a branch without an initialization or invariant argument.
  - Do not move the guard across writes that may change the guarded value.
  - Do not claim a generic control-flow rule from a TSVC-specific invariant.
- 代表函数: s275
- 验证结论: oracle_batch3_loop_interchange_20260527: ours_full 25.667x mean / 26.344x median, correctness passed, 1 vectorized / 0 missed. oracle_batch3_loop_interchange_plain_20260527: llm_plain got 5.819x mean / 5.950x median but remained non-vectorized.
- 验证日期: 2026-05-27
- 语义安全理由: Under the TSVC s275 initialization, aa[0][i] is initialized positive for every i and row 0 is not written by the loop body, so the original guard is true for all updated columns in the measured harness.
- 有利于向量化的原因: The plain loop interchange leaves a per-element branch in the inner loop. Hoisting or simplifying the invariant branch gives Clang a branch-free contiguous inner loop.
- 性能风险: The transformation is benchmark-harness-specific. Without the initialization fact, the safe fallback is to keep the original guard or split guarded columns explicitly.
- 关键风险约束: The branch simplification relies on TSVC s275 initializing aa with positive values and never writing aa[0][i]. Do not generalize this card to arbitrary data-dependent branches.
- 最小示例 before: for (i) { if (aa[0][i] > 0) { for (j=1) { aa[j][i] = aa[j-1][i] + bb[j][i] * cc[j][i]; } } }
- 最小示例 after: after proving aa[0][i] is positive and unchanged, use j outer / i inner and vectorize the i loop.

案例卡 2: partial vectorization boundary: do not accept isolated vectorized fragments
- 触发原因: For loop-distribution candidates with a true recurrence in the middle, vectorizing the independent fragments is not enough if the recurrence remains scalar and the whole loop slows down.
- 推荐动作:
  - Separate independent updates only when the remaining scalar recurrence cost is small enough.
  - Keep true recurrences ordered unless a proven recurrence transformation is available.
  - Require benchmark evidence after distribution; vectorization remarks alone are not acceptance evidence.
- 明确避免:
  - Do not count a candidate as successful only because one split loop is vectorized.
  - Do not manually unroll a true recurrence and claim that it removes the dependency.
  - Do not materialize extra temporaries for a low-work loop without a clear reuse benefit.
- 代表函数: s222
- 失败证据: oracle_batch1_core_20260522: ours_full passed correctness and vectorized one split loop, but two loops remained missed and the full benchmark slowed to 0.885x mean / 0.887x median.
- 验证日期: 2026-05-22
- 语义安全理由: The e recurrence depends on the just-produced e[i-1], so ordinary distribution must preserve its sequential order.
- 有利于向量化的原因: The a update can become a clean vectorized fragment, but that does not solve the recurrence that dominates the remaining loop.
- 性能风险: Splitting a loop can add loop overhead, restrict compiler fusion opportunities and leave the expensive scalar recurrence unchanged.
- 关键风险约束: Use s222 as a negative routing example: partial vectorization is evidence to inspect, not evidence to accept.
- 最小示例 before: a[i] += b[i] * c[i]; e[i] = e[i - 1] * e[i - 1]; a[i] -= b[i] * c[i];
- 最小示例 after: If the independent a-update is split out, keep the e-recurrence scalar and accept only if the full candidate is faster than the original.

案例卡 3: reduction / recurrence boundary: be conservative
- 触发原因: Distinguish reductions from true recurrences. Reductions may be exposed explicitly; true recurrences often need a safety policy instead of aggressive rewrites.
- 推荐动作:
  - If it is a classical reduction, make the accumulator explicit and keep ordering concerns visible.
  - If it is a true recurrence, classify it as unsafe unless a valid algorithmic reformulation is known.
  - Treat inf/nan behavior as part of the oracle boundary, not just a benchmark detail.
- 明确避免:
  - Do NOT mechanically unroll or stage a true recurrence into arrays and call it equivalent.
  - Do NOT overstate floating-point reorder safety.
  - Do NOT apply loop distribution or loop splitting to a[i] += a[i-1] * b[i] — this is a first-order linear recurrence and cannot be parallelized by splitting alone.
  - s321-specific: do NOT attempt to vectorize a[i] += a[i-1] * b[i] via staging arrays, prefix-sum, or block-based schemes without a verified closed-form solution.
- 代表函数: s321
- 失败证据: Historical attempts (llm_plain + ours_full, DeepSeek + GLM) produced inf/nan or correctness failures. oracle_probe_s123_s321_20260522 repeated this boundary: all 3 rounds failed correctness, runtime validation reported ret_orig=inf, ret_opt=inf, max_rel=nan, and no benchmark was run.
- 验证日期: 2026-05-22
- 语义安全理由: The current safe policy is rejection: a[i] depends on the just-updated a[i-1], so ordinary splitting or staging changes semantics.
- 有利于向量化的原因: No generic RAG rewrite is recommended; only a proven recurrence solver or closed-form transformation would make vectorization meaningful.
- 性能风险: Wrong staged rewrites may look vectorized but fail correctness, often with inf/nan behavior in validation.
- 边界结论: This function should be classified as 'do not rewrite unless a proven recurrence-solver is available'. The correct approach is to leave it for compiler auto-vectorization or manual closed-form derivation, not LLM-driven loop restructuring.
- 最小示例 before: a[i] += a[i-1] * b[i];
- 最小示例 after: Keep ordered semantics or reject aggressive rewrite if no proven transformation exists.

案例卡 4: imperfect nested loop: distribute producer before interchange
- 触发原因: For imperfectly nested loops where a per-column producer precedes a row recurrence, split the producer first, then interchange the recurrence nest.
- 推荐动作:
  - Identify scalar or 1D producer statements that must run before the nested recurrence consumes them.
  - Distribute those producer statements into a separate loop if different columns are independent.
  - Move the recurrence-carrying dimension outside the vectorized loop.
  - Keep the contiguous independent dimension as the inner loop and verify that every consumed producer value has already been computed.
- 明确避免:
  - Do not leave the producer inside the recurrence nest if it prevents interchange.
  - Do not interchange before proving the producer is available for all columns.
  - Do not report this as a full formal-protocol result when the heavy original benchmark times out.
- 代表函数: s235
- 验证结论: oracle_batch7_distribution_control_20260529: ours_full internal correctness passed, 2 vectorized / 0 missed; reduced 3-batch benchmark mean 21.752x / median 22.074x, repeat mean 21.210x / median 21.393x. oracle_s235_distribution_interchange_plain_20260529: llm_plain correctness passed but stayed non-vectorized at 0 vectorized / 2 missed and 1.000x.
- 验证日期: 2026-05-29
- 语义安全理由: In s235, each a[i] update is independent and must be completed before every aa[j][i] for the same column reads a[i]. After all a[i] values are produced, the aa recurrence still runs in increasing j order.
- 有利于向量化的原因: The transformed aa nest reads row j-1 and writes row j for each fixed j, so the inner i loop is contiguous and independent across columns.
- 性能风险: This is a protocol-limited strong candidate: the heavy original s235 function can exceed the formal export or benchmark timeout. A mid protocol with warmup=2, timing=5, batches=3 also hit the 120-second per-process benchmark timeout, so evidence should name the reduced 3-batch repeat protocol unless timeout handling is changed.
- 关键风险约束: Use s235 as a method-advantage strong candidate under the reduced protocol, not as a completed formal main-table result. The full warmup=3 timing=10 batches=5 export path hit original-function timeout, and a mid warmup=2 timing=5 batches=3 benchmark hit the 120-second process timeout.
- 最小示例 before: for (i) { a[i] += b[i] * c[i]; for (j=1) { aa[j][i] = aa[j-1][i] + bb[j][i] * a[i]; } }
- 最小示例 after: first vectorize for (i) a[i] += b[i] * c[i]; then for (j=1) vectorize the inner i loop for aa[j][i].

【向量化知识库参考】:
============================================================
【深度诊断分析】
============================================================

问题 1: /tmp/acpo_s275_qaz19clp/minimal_s275.c:58:32: remark: loop not vectorized: value...
  根因: 未知原因: /tmp/acpo_s275_qaz19clp/minimal_s275.c:58:32: remark: loop not vectorized: value that could not be identified as reduction is used outside the loop [-Rpass-analysis=loop-vectorize]
  类别: unknown
  解决类型: source_change
  成功概率: unknown

  推荐方案:
    1. 尝试使用 pragma 强制向量化
       代码: #pragma clang loop vectorize(enable)
       成功率: unknown

【编译器指令】: 可尝试 #pragma clang loop vectorize(enable)


【决策流程】:
1. 首先尝试编译器指令（pragma）- 改动最小
2. 如果 pragma 无效，分析是否需要源码修改
3. 对于归纳变量/真依赖问题，必须重构代码
4. 对于别名/边界问题，pragma + restrict 通常有效

【编译选项建议】:
确保使用 -O3 -march=native 编译以启用所有优化


【快速修复建议（按成功率排序）】:
  1. general_pragma (成功率: unknown)
     示例: #pragma clang loop vectorize(enable)

【类似案例参考】:

=== 案例 1: s111 - 循环携带依赖 - 使用 a[i-1] ===

问题类型: loop_carried_dependency
原始代码:
```c
real_t s111(struct args_t * func_args)
{
    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 2*iterations; nl++) {
        for (int i = 1; i < LEN_1D; i += 2) {  // 步长为2
            a[i] = a[i - 1] + b[i];  // 依赖前一个元素
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}
```

优化后代码:
```c
real_t s111(struct args_t * func_args)
{
    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ = a;
    real_t * __restrict__ b_ = b;

    for (int nl = 0; nl < 2*iterations; nl++) {
        #pragma clang loop vectorize(enable)
        for (int i = 1; i < LEN_1D; i += 2) {
            a_[i] = a_[i - 1] + b_[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}
```

关键技术:
1. 使用 __restrict__ 关键字
2. 添加 vectorize pragma
3. 注意：此案例保持原结构，因为依赖是固有的

优化结果: ⚠️ 部分向量化（依赖无法完全消除）

【你的任务】:
分析上述代码的向量化障碍，应用适当的优化技术，输出优化后的代码。
如果存在递推变量、参数化步长或 dummy() 语义风险，优先使用可验证的保守重构，不要做未经证明的闭式化简或批量折叠。

请输出优化策略和完整代码：
- 先给 2-4 行策略说明，再给一个 ```c 代码块
- 代码块内只能包含纯 C 代码，禁止夹带解释文字
- 不要输出 `...`、`TODO`、伪代码或半截函数
- 如果不确定优化是否成立，返回完整保守版本函数，不要只给分析
```
