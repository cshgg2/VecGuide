# Prompt Snapshot: s172 round 1

- strategy: case_card_only
- publication_name: case_card_only
- prompt_version: case_card_only_v1_20260601
- prompt_kind: optimization
- system_template: method_system
- case_cards_included: True

## System Prompt

```text
你是 VecGuide（AI-Enabled Compiler Program Optimization - Large Language Model），一个专门为 C/C++ 自动向量化优化设计的大模型。

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
【函数名】: s172
【当前轮次】: 第 1 轮 / 共 1 轮

【待优化代码】:
```c
real_t s172(struct args_t * func_args)
{
//    symbolics
//    vectorizable if n3 .ne. 0

    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = n1-1; i < LEN_1D; i += n3) {
            a[i] += b[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}
```

【向量化失败原因】(5 个问题):
1. call instruction cannot be vectorized [-Rpass-analysis=loop-vectorize]
2. instruction cannot be vectorized [-Rpass-analysis=loop-vectorize]
3. /tmp/acpo_s172_yy8hzl8c/minimal_s172.c:57:5: remark: loop not vectorized [-Rpass-missed=loop-vectorize]
4. could not determine number of loop iterations [-Rpass-analysis=loop-vectorize]
5. /tmp/acpo_s172_yy8hzl8c/minimal_s172.c:58:9: remark: loop not vectorized [-Rpass-missed=loop-vectorize]

【结构化反馈摘要】:
- 静态严重度: high
- 当前更像的模式族: runtime_stride_simple
- compile-level: 可编译
- vectorization-level: vectorized=0, missed=5, primary blockers=call or side effect blocker, instruction shape blocker, trip count or bounds unknown
  - 动态诊断: call instruction cannot be vectorized [-Rpass-analysis=loop-vectorize]
  - 动态诊断: instruction cannot be vectorized [-Rpass-analysis=loop-vectorize]
  - 动态诊断: could not determine number of loop iterations [-Rpass-analysis=loop-vectorize]
  - 静态问题图谱: call instruction cannot be vectorized
  - 静态问题图谱: instruction cannot be vectorized
- 代码结构特征: runtime-stride

【语义安全提示】:
- 检测到运行时参数 `n3` 控制的变步长循环。不要只针对默认 arg_info 做特化；若使用参数分支，必须保留覆盖所有参数的通用正确路径。
- 对运行时步长循环做结构重构时，每个分支都必须覆盖与原循环完全相同的索引集合，不能重复更新、遗漏边界，也不能改变 dummy() 的循环层级。
- 检测到简单同址 runtime-stride 模式：主要是 `a[i]`、`b[i]` 这类同址访问。若 pragma 无效，可尝试少量代表性步长（如 1/2/4）的等价专用分支，并保留通用 fallback。
- 检测到 `dummy()` 位于外层 `nl/iterations` 循环内。禁止改变 dummy() 的调用次数、顺序或循环层级，也不要折叠外层迭代。
- 若需要重构跨多次 `iterations` 的逻辑，只能做等价的逐轮改写；不要用乘法放大、批量累加或一次性聚合替代多轮副作用。

【参数化步长循环推荐策略】:
- 如果循环是简单的 `a[i] += b[i]` 一类同址访问，不要只做 `restrict + pragma`。
- 可以尝试少量代表性小步长（如 1/2/4）的等价专用分支，并保留一个覆盖全部参数的通用 fallback。
- 特化分支不能只覆盖默认参数；每个分支都必须更新与原循环完全相同的索引集合。
- 如果无法直接证明等价，就回退到通用路径，而不是提交激进但不稳的改写。

【类别化案例卡】:
案例卡 1: runtime-stride simple: multiversion with fallback
- 触发原因: When the hot loop is a simple same-index stride loop, prefer a few representative stride specializations plus a generic fallback.
- 推荐动作:
  - Copy runtime bounds and stride into local variables.
  - Specialize only a small set of common stride values such as 1/2/4.
  - Keep one fully generic fallback path that preserves all arg_info cases.
- 明确避免:
  - Do not optimize only the default stride case.
  - Do not change the accessed index set across branches.
- 代表函数: s172
- 验证结论: 2.07x (glm-4.7), 2.27x (deepseek-v4-pro)
- 验证日期: 2026-05-15
- 语义安全理由: Each specialized branch must update exactly the same index set as the original start/stride loop, and the generic fallback must cover all remaining runtime cases.
- 有利于向量化的原因: Small constant-stride branches expose predictable loop bounds and memory access shape to Clang, especially for stride 1/2/4.
- 性能风险: Too many specializations increase code size; accepting a branch that only covers the default input is a false positive.
- 最小示例 before: for (int i = start; i < LEN_1D; i += stride) { a[i] += b[i]; }
- 最小示例 after: if (stride == 1) use a unit-stride loop; else if (stride == 2) use the stride-2 loop; else keep the original loop.

案例卡 2: call-side-effect blocker: optimize the hot loop, not the outer effect
- 触发原因: If the remark comes from call instructions, preserve side-effect placement and focus on vectorizing the inner hot loop only.
- 推荐动作:
  - Keep helper calls such as dummy() at the original loop level.
  - Extract or specialize only the arithmetic loop body.
  - Separate 'call cannot be vectorized' from the real inner-loop blocker.
- 明确避免:
  - Do not hoist or sink side-effecting calls across iteration boundaries.
  - Do not treat the presence of a call remark as license to rewrite surrounding semantics.
- 语义安全理由: Side-effecting calls must remain at the same logical iteration boundary.
- 有利于向量化的原因: The call remark should be separated from the real inner-loop blocker so only the arithmetic loop is transformed.
- 性能风险: Moving calls across iterations can produce invalid speedups by changing observable behavior.
- 最小示例 before: for each outer iteration: run the hot loop, then call dummy at the original point.
- 最小示例 after: vectorize hot_loop when safe; preserve dummy() placement exactly.

案例卡 3: runtime-stride complex: two-phase index materialization only
- 触发原因: If runtime stride is mixed with indexed recurrence or reverse indexing, stay conservative: isolate the recurrence first, then vectorize only the clean data-access phase.
- 推荐动作:
  - Keep the original outer iteration structure intact.
  - Precompute index values or dependent scalars in a first phase.
  - Vectorize only the second phase with simple loop indices.
- 明确避免:
  - Do not mechanically clone stride 2/4 branches for complex indexed loops.
  - Do not rewrite indexed recurrence into a closed form unless sequence equivalence is proven.
- 代表函数: s122
- 验证结论: formal_s122_glm_20260522: ours_full 1.147x vs llm_plain 0.889x; partial vectorization only
- 验证日期: 2026-05-21
- 语义安全理由: The recurrence variable is still advanced in original iteration order; only the later data-access phase is separated.
- 有利于向量化的原因: The second phase uses an explicit logical iteration index, which removes the loop-carried scalar update from the vectorized loop body.
- 性能风险: The helper index array adds memory traffic, so this is partial evidence and must pass the performance guard.
- 关键风险约束: This is a supplemental complex runtime-stride card, not a strong positive oracle. The safe route is to preserve the recurrence order in a precompute phase. Direct closed-form replacement of k was flagged as high-risk and should be avoided unless sequence equivalence is proven.
- 最小示例 before: k += j; a[i] += b[LEN_1D - k];
- 最小示例 after: phase 1 records k_values in original order; phase 2 updates a[i] from b[LEN_1D - k_values[idx]].

案例卡 4: control flow rewrite: branch hoisting before heavy refactoring
- 触发原因: For branch-heavy loops, start from branch hoisting, predication or path splitting before introducing complex table-based rewrites.
- 推荐动作:
  - Convert simple if/else into predicated assignments when cost is low.
  - Split mutually exclusive paths into separate loops when that preserves semantics.
  - Keep the transformation local to the hot loop body.
- 明确避免:
  - Do not introduce many helper arrays unless reuse clearly amortizes the cost.
  - Do not move dummy() or fold outer iterations.
- 代表函数: s1161
- 验证结论: 1.69x (deepseek-v4-pro); glm-4.7: non-vectorized 1.21x (if/else version), vectorized but slowdown 0.59x (ternary) — predication alone not sufficient on all models
- 验证日期: 2026-05-15
- 语义安全理由: Each predicated assignment must preserve the original branch condition and leave the untouched array value unchanged.
- 有利于向量化的原因: Replacing goto/if regions with conditional expressions gives the compiler a straight-line loop body suitable for if-conversion.
- 性能风险: Predication can execute extra arithmetic and may be slower on GLM-generated variants, so correctness and vectorization are not enough. oracle_batch1_control_20260522 showed this again: s276 became vectorized after ternary if-conversion, but benchmark timed out after 120 seconds.
- 关键风险约束: Ternary (?:) predication works better than if/else for Clang if-conversion. But GLM r2 and s276 showed that predication can cause slowdown or timeout — verify with benchmark before accepting.
- 最小示例 before: if (cond) { a[i] = x; } else { a[i] = y; }
- 最小示例 after: a[i] = cond ? x : y;

【向量化知识库参考】:
============================================================
【深度诊断分析】
============================================================

问题 1: /tmp/acpo_s172_yy8hzl8c/minimal_s172.c:61:9: remark: loop not vectorized: call i...
  根因: 未知原因: /tmp/acpo_s172_yy8hzl8c/minimal_s172.c:61:9: remark: loop not vectorized: call instruction cannot be vectorized [-Rpass-analysis=loop-vectorize]
  类别: unknown
  解决类型: source_change
  成功概率: unknown

  推荐方案:
    1. 尝试使用 pragma 强制向量化
       代码: #pragma clang loop vectorize(enable)
       成功率: unknown

【编译器指令】: 可尝试 #pragma clang loop vectorize(enable)


问题 2: /tmp/acpo_s172_yy8hzl8c/minimal_s172.c:57:5: remark: loop not vectorized: instru...
  根因: 未知原因: /tmp/acpo_s172_yy8hzl8c/minimal_s172.c:57:5: remark: loop not vectorized: instruction cannot be vectorized [-Rpass-analysis=loop-vectorize]
  类别: unknown
  解决类型: source_change
  成功概率: unknown

  推荐方案:
    1. 尝试使用 pragma 强制向量化
       代码: #pragma clang loop vectorize(enable)
       成功率: unknown

【编译器指令】: 可尝试 #pragma clang loop vectorize(enable)


问题 3: /tmp/acpo_s172_yy8hzl8c/minimal_s172.c:58:9: remark: loop not vectorized: could ...
  根因: 编译器无法在编译时确定循环边界或迭代次数
  类别: variable_bounds
  解决类型: compiler_hint_first
  成功概率: high

  推荐方案:
    1. 添加在循环前，强制编译器尝试向量化
       代码: #pragma clang loop vectorize(enable)
       成功率: high
    2. 帮助编译器分析边界
       代码: int local_n = n; // 将参数复制到局部变量
       成功率: medium
    3. 仅当循环属于简单同址访问模式时，才使用多个常见小步长的等价专用分支；复杂地址模式优先 stride==1 快路径 + 通用 fallback
       代码: if (stride == 1) { ... } else if (stride == 2) { ... } else { original loop }
       成功率: medium

【编译器指令推荐】:
针对变量边界问题，建议按以下顺序尝试:

1. **首选方案** - vectorize pragma:
   ```c
   #pragma clang loop vectorize(enable)
   for (int i = start; i < end; i++) { ... }
   ```
   适用：你确定循环是安全的（无隐藏依赖）

2. **增强方案** - 配合 interleave:
   ```c
   #pragma clang loop vectorize(enable) interleave(enable)
   for (int i = start; i < end; i++) { ... }
   ```
   适用：需要更高的指令级并行度

3. **备选方案** - 局部变量 + pragma:
   ```c
   int local_start = start;
   int local_end = end;
   #pragma clang loop vectorize(enable)
   for (int i = local_start; i < local_end; i++) { ... }
   ```
   适用：pragma 单独使用效果不佳时

4. **运行时步长专用方案**:
   ```c
   int start = n1 - 1;
   int stride = n3;
   if (stride == 1) {
       #pragma clang loop vectorize(enable)
       for (int i = start; i < LEN_1D; ++i) { ... }
   } else if (stride == 2) {
       #pragma clang loop vectorize(enable)
       for (int i = start; i < LEN_1D; i += 2) { ... }
   } else if (stride == 4) {
       #pragma clang loop vectorize(enable)
       for (int i = start; i < LEN_1D; i += 4) { ... }
   } else {
       for (int i = start; i < LEN_1D; i += stride) { ... }
   }
   ```
   适用：
   - 简单同址访问：可尝试 `1/2/4 + fallback`
   - 复杂地址模式：优先只保留 `stride == 1` 快路径，`stride > 1` 回到通用路径或两阶段预计算
   - 如果复杂模式需要恢复“逻辑迭代号”，优先使用独立 `idx/t` 计数器，不要在热循环中写 `(i - start) / stride` 或 `% stride`


【决策流程】:
1. 首先尝试编译器指令（pragma）- 改动最小
2. 如果 pragma 无效，分析是否需要源码修改
3. 对于归纳变量/真依赖问题，必须重构代码
4. 对于别名/边界问题，pragma + restrict 通常有效

【编译选项建议】:
确保使用 -O3 -march=native 编译以启用所有优化


【快速修复建议（按成功率排序）】:
  1. pragma_vectorize (成功率: high)
     示例: #pragma clang loop vectorize(enable)
  2. local_variable (成功率: medium)
     示例: int local_n = n; // 将参数复制到局部变量
  3. multiversion_stride (成功率: medium)
     示例: if (stride == 1) { ... } else if (stride == 2) { ... } else { original loop }

【你的任务】:
分析上述代码的向量化障碍，应用适当的优化技术，输出优化后的代码。
如果存在递推变量、参数化步长或 dummy() 语义风险，优先使用可验证的保守重构，不要做未经证明的闭式化简或批量折叠。

请输出优化策略和完整代码：
- 先给 2-4 行策略说明，再给一个 ```c 代码块
- 代码块内只能包含纯 C 代码，禁止夹带解释文字
- 不要输出 `...`、`TODO`、伪代码或半截函数
- 如果不确定优化是否成立，返回完整保守版本函数，不要只给分析
```
