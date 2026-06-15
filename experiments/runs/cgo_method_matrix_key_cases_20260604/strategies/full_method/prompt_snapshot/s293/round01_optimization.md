# Prompt Snapshot: s293 round 1

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
【函数名】: s293
【当前轮次】: 第 1 轮 / 共 3 轮

【待优化代码】:
```c
real_t s293(struct args_t * func_args)
{

//    loop peeling
//    a(i)=a(0) with actual dependence cycle, loop is vectorizable

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 4*iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            a[i] = a[0];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}
```

【向量化失败原因】(2 个问题):
1. unsafe dependent memory operations in loop. Use #pragma loop distribute(enable) to allow loop distribution to attempt to isolate the offending operations into a separate loop
2. /tmp/acpo_s293_9xlf4xu3/minimal_s293.c:55:9: remark: loop not vectorized [-Rpass-missed=loop-vectorize]

【结构化反馈摘要】:
- 静态严重度: medium
- 当前更像的模式族: loop_distribution_dependence_isolation
- compile-level: 可编译
- vectorization-level: vectorized=0, missed=2, primary blockers=unsafe dependence / isolate dependent ops
  - 动态诊断: unsafe dependent memory operations in loop. Use #pragma loop distribute(enable) to allow loop distribution to attempt to isolate the offending operations into a separate loop
  - 静态问题图谱: unsafe dependent memory operations in loop. Use #pragma loop distribute(enable) to allow loop distribution to attempt to isolate the offending operations into a separate loop
- performance-level: 当前没有实时 benchmark 反馈，但已知应避免：
  - avoid_fixed_index_self_read_hoist
- 代码结构特征: self-write+fixed-read hazard

【语义安全提示】:
- 检测到 `dummy()` 位于外层 `nl/iterations` 循环内。禁止改变 dummy() 的调用次数、顺序或循环层级，也不要折叠外层迭代。
- 若需要重构跨多次 `iterations` 的逻辑，只能做等价的逐轮改写；不要用乘法放大、批量累加或一次性聚合替代多轮副作用。
- 检测到循环同时写 `a[i]` 并读固定位置 `a[0]`。若循环变量可能命中该固定索引，这个值在同一轮中不是不变量；禁止把它整轮外提为标量。若要优化，必须按命中前/命中点/命中后拆分，或保留逐迭代读取语义。

【类别化案例卡】:
案例卡 1: loop peeling: scalarize fixed self-source before vector loop
- 触发原因: When every iteration writes from a fixed array element that is also written by the loop, peel the self-write and cache the fixed source before the vectorized suffix.
- 推荐动作:
  - Identify whether the fixed source element is unchanged in value by its own iteration.
  - Read the fixed source into a scalar before the vectorized loop.
  - Handle the source element iteration separately, then vectorize the remaining range.
  - Keep the outer iteration and helper-call placement unchanged.
- 明确避免:
  - Do not cache a fixed element if an earlier iteration changes its value before later reads.
  - Do not peel only to silence diagnostics; require correctness and benchmark evidence.
  - Do not generalize this card to true recurrences such as a[i+1] depending on the newly written a[i].
- 代表函数: s293
- 验证结论: oracle_batch6_dependency_reduction_20260527: ours_full 1.910x mean / 1.830x median, correctness passed, 1 vectorized / 0 missed. oracle_s293_loop_peeling_plain_20260528: llm_plain 2.428x mean / 2.403x median, correctness passed, 1 vectorized / 0 missed.
- 验证日期: 2026-05-28
- 语义安全理由: For s293, the i=0 assignment writes a[0] back to itself, so caching a[0] before the suffix preserves the value read by every later iteration.
- 有利于向量化的原因: After peeling i=0, the suffix loop writes a contiguous range from one invariant scalar and no longer reads from a location written by the same vectorized loop.
- 性能风险: This pattern is narrow. If the fixed source element can change before later iterations, scalarization changes semantics. The s293 baseline shows this is a transform-family positive, not a full-method advantage case.
- 关键风险约束: Use s293 as a loop-peeling transform-family positive example. Do not claim full-method advantage because llm_plain also found scalarization and was faster in this run.
- 最小示例 before: for (i = 0; i < N; i++) { a[i] = a[0]; }
- 最小示例 after: real_t first = a[0]; a[0] = first; vectorize for (i = 1; i < N; i++) { a[i] = first; }

案例卡 2: unsafe dependence: isolate the offending statement
- 触发原因: When clang reports unsafe dependent memory operations, first try to isolate the dependent statement rather than rewriting the whole loop.
- 推荐动作:
  - Split the loop into vectorizable and non-vectorizable phases.
  - Hoist invariant scalar reads outside the inner loop only when the source location is provably outside the loop's write domain.
  - Use temporary scalars or arrays only for the dependent fragment.
- 明确避免:
  - Do not flatten the whole loop into a large new data structure if only one statement is problematic.
  - Do not hoist a fixed-index read from the same array if the loop may later overwrite that index in the same pass.
  - Do not claim full vectorization if one dependent fragment must remain ordered.
- 代表函数: s1113
- 验证结论: 2.95x (glm-4.7), 2.96x (deepseek-v4-pro)
- 验证日期: 2026-05-15
- 语义安全理由: The split uses the old value of a[mid] before i == mid and the new value after i == mid, matching the original sequential update.
- 有利于向量化的原因: The i < mid and i > mid segments read a scalar invariant and write disjoint ranges, so each segment becomes a clean vectorizable loop.
- 性能风险: Hoisting a[mid] once for the entire loop is incorrect; over-splitting would add overhead without changing the dependency.
- 关键风险约束: Must NOT hoist a[mid] once for the whole loop — must split at mid because a[mid] is overwritten when i==mid.
- 最小示例 before: a[i] = a[mid] + b[i];
- 最小示例 after: split into i < mid / i == mid / i > mid segments, or keep ordered reads if no safe split is proven.

案例卡 3: node splitting: separate producer and shifted consumer
- 触发原因: When one statement produces a shifted array value and a later statement consumes the completed array, split the producer and consumer into two ordered loops.
- 推荐动作:
  - Confirm that the first statement computes the full producer array values needed by the second statement.
  - Run the producer loop first, then the consumer loop.
  - Preserve the original outer iteration boundary and keep helper calls after both loops.
  - Add vectorization pragmas only after the split preserves the same per-outer-iteration state.
- 明确避免:
  - Do not split loops whose original result overflows to inf/nan and then treat matching inf as sufficient correctness.
  - Do not split when the consumer needs a value that would not yet exist in the original sequential order.
  - Do not move dummy() between the producer and consumer phases.
- 代表函数: s1244
- 验证结论: oracle_batch5_statement_node_splitting_20260527: ours_full 2.561x mean / 2.612x median, correctness passed, 2 vectorized / 0 missed. oracle_s1244_node_splitting_plain_20260527: llm_plain also passed correctness and vectorized fully, 2.442x mean / 2.559x median.
- 验证日期: 2026-05-27
- 语义安全理由: For s1244, the second statement reads a[i] and a[i+1] after the producer assignment for i has completed. Splitting first computes all producer values for the current outer iteration, then consumes the completed array.
- 有利于向量化的原因: After splitting, both loops are simple contiguous array loops with no loop-carried update in the vectorized dimension.
- 性能风险: Similar-looking statement-reordering cases can fail runtime validation with inf/nan comparisons. oracle_batch5_statement_node_splitting_20260527 rejected s212, s1213, s241 and s244 despite vectorized diagnostics because final runtime verification failed.
- 关键风险约束: Use s1244 as a node-splitting transform-family positive example. Do not claim full-method advantage from this case alone because llm_plain also found the same split and succeeded.
- 最小示例 before: for (i) { a[i] = f(b[i], c[i]); d[i] = a[i] + a[i+1]; }
- 最小示例 after: for (i) { a[i] = f(b[i], c[i]); } then vectorize for (i) { d[i] = a[i] + a[i+1]; }

案例卡 4: triangular saxpy: keep outer order, scalarize inner invariant
- 触发原因: For triangular saxpy loops, keep the outer dependency order and expose the inner loop by scalarizing the fixed source element.
- 推荐动作:
  - Keep the outer triangular loop order unchanged.
  - For a fixed outer index, cache the source element such as a[j] into a scalar before the inner loop.
  - Use restrict local pointers for the destination array and the current matrix row.
  - Vectorize only the inner contiguous update loop.
- 明确避免:
  - Do not interchange the triangular loops unless the sequential triangular dependence is proven equivalent.
  - Do not treat a[j] as an original array value; it may include earlier outer-loop updates.
  - Do not claim a general dependence solution if only the inner loop was exposed.
- 代表函数: s115
- 验证结论: oracle_batch1_core_20260522: ours_full 4.045x mean / 4.030x median, 1 vectorized / 0 missed; oracle_s115_plain_baseline_20260522: llm_plain 0 vectorized / 2 missed and benchmark timeout.
- 验证日期: 2026-05-22
- 语义安全理由: The outer j order is preserved. For a fixed j, the inner loop writes only a[i] where i > j, so it does not modify a[j]; caching a[j] as a scalar preserves the value used by all inner iterations.
- 有利于向量化的原因: After scalarizing a[j] and using restrict row pointers, the inner loop becomes a contiguous update with one invariant scalar and no loop-carried write to the scalar source.
- 性能风险: The verifier reports NaN state metrics for s115, so this card needs runtime equality and repeated benchmark evidence before it is used as final paper-grade proof.
- 关键风险约束: The important transformation is not loop interchange. The plain baseline interchanged loops, preserved correctness, but remained non-vectorized and timed out in benchmark.
- 最小示例 before: for (int j = 0; j < N; j++) { for (int i = j + 1; i < N; i++) { a[i] -= aa[j][i] * a[j]; } }
- 最小示例 after: for each j in order, read real_t a_j = a[j]; then vectorize the i > j update using a_j and aa[j][i].

【向量化知识库参考】:
============================================================
【深度诊断分析】
============================================================

问题 1: /tmp/acpo_s293_9xlf4xu3/minimal_s293.c:56:18: remark: loop not vectorized: unsaf...
  根因: 循环携带依赖（Loop-Carried Dependency）
  类别: loop_carried_dependency
  解决类型: source_change_required
  成功概率: low

  推荐方案:
    1. 首先分析依赖类型
       成功率: low_to_medium

【编译器指令】: 可尝试 #pragma clang loop vectorize(enable)


【决策流程】:
1. 首先尝试编译器指令（pragma）- 改动最小
2. 如果 pragma 无效，分析是否需要源码修改
3. 对于归纳变量/真依赖问题，必须重构代码
4. 对于别名/边界问题，pragma + restrict 通常有效

【编译选项建议】:
确保使用 -O3 -march=native 编译以启用所有优化


【快速修复建议（按成功率排序）】:
  1. dependency_analysis (成功率: low_to_medium)

【类似案例参考】:

=== 案例 1: s1113 - 标量依赖 - 循环内使用数组中间元素 ===

问题类型: scalar_dependency
原始代码:
```c
real_t s1113(struct args_t * func_args)
{
    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < 2*iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            a[i] = a[LEN_1D/2] + b[i];  // a[LEN_1D/2] 是标量依赖
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}
```

优化后代码:
```c
real_t s1113(struct args_t * func_args)
{
    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ = a;
    real_t * __restrict__ b_ = b;
    real_t mid_val;

    for (int nl = 0; nl < 2*iterations; nl++) {
        mid_val = a_[LEN_1D/2];  // 循环外提取标量值
        #pragma clang loop vectorize(enable)
        for (int i = 0; i < LEN_1D; i++) {
            a_[i] = mid_val + b_[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}
```

关键技术:
1. 将 a[LEN_1D/2] 提取到循环外，消除循环内标量依赖
2. 使用 __restrict__ 消除别名分析障碍
3. 添加 #pragma clang loop vectorize(enable) 提示编译器

优化结果: ✅ 完全向量化

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
