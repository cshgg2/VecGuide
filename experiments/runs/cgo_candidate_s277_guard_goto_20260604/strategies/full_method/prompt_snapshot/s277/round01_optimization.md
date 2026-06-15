# Prompt Snapshot: s277 round 1

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
【函数名】: s277
【当前轮次】: 第 1 轮 / 共 3 轮

【待优化代码】:
```c
real_t s277(struct args_t * func_args)
{

//    control flow
//    test for dependences arising from guard variable computation.

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D-1; i++) {
                if (a[i] >= (real_t)0.) {
                    goto L20;
                }
                if (b[i] >= (real_t)0.) {
                    goto L30;
                }
                a[i] += c[i] * d[i];
L30:
                b[i+1] = c[i] + d[i] * e[i];
L20:
;
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
3. /tmp/acpo_s277_m5roung9/minimal_s277.c:55:9: remark: loop not vectorized [-Rpass-missed=loop-vectorize]

【结构化反馈摘要】:
- 静态严重度: medium
- 当前更像的模式族: branch_hoisting
- compile-level: 可编译
- vectorization-level: vectorized=0, missed=3, primary blockers=reduction / recurrence boundary, trip count or bounds unknown
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

【类别化案例卡】:
案例卡 1: slowdown guard: avoid heavy materialization on low-intensity loops
- 触发原因: If the loop is low arithmetic intensity, materializing index tables, masks and operation lists is usually worse than the original branchy loop.
- 推荐动作:
  - Prefer compact predication or loop splitting to large side arrays.
  - Estimate extra memory traffic before adding helper arrays.
  - Treat 'vectorized but slower' as a real failure mode.
- 明确避免:
  - Avoid building src/dst/op-type tables unless there is substantial reuse.
  - Do not accept a rewrite only because it compiles and vectorizes.
- 代表函数: s123
- 失败证据: oracle_probe_s123_s321_20260522: ours_full kept correctness but still ended as non_vectorized_slowdown, speedup 0.854x (median 0.868x). Earlier materialization candidates in the same run were rejected by the performance guard at 0.556x and 0.437x.
- 验证日期: 2026-05-22
- 语义安全理由: Compressed writes must preserve the exact output order and the final value of j.
- 有利于向量化的原因: This card is a guard card: it should first prevent expensive materialization, then allow only compact local rewrites.
- 性能风险: Low arithmetic intensity means helper arrays, masks, or op tables can dominate the original loop cost.
- 关键风险约束: For compact-write loops like s123, correctness-preserving index/value materialization is not enough; accept only candidates that also beat the original loop under the performance guard.
- 最小示例 before: if (cond) { j++; a[j] = b[i]; }
- 最小示例 after: Keep a compact branch/predicate rewrite; do not build multiple index tables by default.

案例卡 2: control flow rewrite: branch hoisting before heavy refactoring
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

案例卡 3: guarded loop interchange: prove branch invariance first
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

案例卡 4: call-side-effect blocker: optimize the hot loop, not the outer effect
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

【向量化知识库参考】:
============================================================
【深度诊断分析】
============================================================

问题 1: /tmp/acpo_s277_m5roung9/minimal_s277.c:55:9: remark: loop not vectorized: value ...
  根因: 未知原因: /tmp/acpo_s277_m5roung9/minimal_s277.c:55:9: remark: loop not vectorized: value that could not be identified as reduction is used outside the loop [-Rpass-analysis=loop-vectorize]
  类别: unknown
  解决类型: source_change
  成功概率: unknown

  推荐方案:
    1. 尝试使用 pragma 强制向量化
       代码: #pragma clang loop vectorize(enable)
       成功率: unknown

【编译器指令】: 可尝试 #pragma clang loop vectorize(enable)


问题 2: /tmp/acpo_s277_m5roung9/minimal_s277.c:55:9: remark: loop not vectorized: could ...
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

【类似案例参考】:

=== 案例 1: s243 - 控制流 - 条件分支 ===

问题类型: control_flow
原始代码:
```c
for (int i = 0; i < LEN_1D; i++) {
    if (b[i] > (real_t)0.) {
        a[i] = b[i] * c[i];
    }
}
```

优化后代码:
```c
#pragma clang loop vectorize(enable)
for (int i = 0; i < LEN_1D; i++) {
    a[i] = (b[i] > 0.0f) ? (b[i] * c[i]) : a[i];
}
```

关键技术:
1. 将 if-else 分支转为条件选择表达式（?:）
2. 确保两个分支都执行，用 mask 选择结果
3. 使用 pragma 强制向量化

优化结果: ✅ 向量化成功

=== 案例 2: s111 - 循环携带依赖 - 使用 a[i-1] ===

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
