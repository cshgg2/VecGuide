"""
Prompt Templates
================
提供各种场景下的结构化 Prompt 模板
"""

from typing import Dict, List, Optional, Tuple
from experiment_config import normalize_prompt_options
from .knowledge_base import (
    format_knowledge_for_prompt, 
    get_optimization_strategy,
    format_enhanced_knowledge,
    format_case_cards_for_prompt,
    format_structured_feedback_for_prompt,
    get_quick_fix_suggestions,
    analyze_issue_depth,
    get_compiler_hints_guide,
    check_fundamental_limitation,
    analyze_optimization_progress,
    get_partial_vectorization_guidance
)
from .examples import get_relevant_examples


PROMPT_TEMPLATE_VERSIONS = {
    "method_system": "method_system_v1_20260601",
    "strong_plain_system": "strong_plain_system_v1_20260601",
    "multi_round_system": "multi_round_system_v1_20260601",
    "optimization_user": "optimization_user_v1_20260601",
    "retry_prompt": "retry_prompt_v1_20260601",
    "structured_feedback_format": "structured_feedback_v1_20260601",
}


def get_prompt_template_versions() -> Dict[str, str]:
    """Return prompt template versions used for run-level reproducibility."""
    return dict(PROMPT_TEMPLATE_VERSIONS)


def resolve_system_prompt_template_name(round_num: int, prompt_options: Optional[Dict] = None) -> str:
    """Resolve which system prompt template a strategy will use for an optimization round."""
    options = normalize_prompt_options(prompt_options)
    if options.get("system_prompt_profile") == "strong_plain":
        return "strong_plain_system"
    if round_num == 1 or not options["use_multi_round_system_prompt"]:
        return "method_system"
    return "multi_round_system"


# 系统级 Prompt（定义角色和能力）
SYSTEM_PROMPT_BASE = """你是 ACPO-LLM（AI-Enabled Compiler Program Optimization - Large Language Model），一个专门为 C/C++ 自动向量化优化设计的大模型。

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
"""


SYSTEM_PROMPT_STRONG_PLAIN = """你是一个擅长 C 程序性能优化和自动向量化友好改写的大模型。你的任务是在不依赖项目案例库、历史反馈或编译器诊断路由的情况下，根据给定函数源码生成一个更容易被 Clang 自动向量化的等价版本。

## 任务目标
1. 识别源码中可能阻碍自动向量化的结构，例如循环携带依赖、复杂索引、运行时步长、控制流、别名疑虑、不规范循环边界和混合语句。
2. 在保持语义完全一致的前提下，尝试常见且可证明安全的源码级改写。
3. 输出完整、可编译的 C 函数代码，而不是解释性建议。

## 允许尝试的通用优化
- 循环交换：当交换循环顺序能让内层循环连续访问且不破坏依赖顺序时使用。
- 循环分发/拆分：将生产语句和消费语句拆成多个有序循环，降低单个循环内的依赖复杂度。
- 循环剥离：单独处理少量边界迭代，使主循环更规则。
- 节点拆分：把混在一个循环中的多个语句拆成语义等价的阶段。
- 标量临时变量：缓存循环不变或固定源值，但必须确认该值不会在后续迭代中被本循环更新。
- 条件结构化：将 goto 或复杂分支改写为等价的 if/else 或条件选择。
- restrict 与局部指针：在能保证不改变语义的情况下帮助编译器消除别名疑虑。
- pragma：可以添加 Clang loop pragma，但不能只依赖 pragma；若存在真实依赖，应先做源码结构改写。

## 必须遵守的正确性约束
- 不改变函数签名、全局数组含义、dummy() 调用层级和调用次数。
- 不硬编码 LEN_1D、LEN_2D、iterations 等宏的具体数值。
- 不把跨迭代递推变量随意改成闭式公式，除非能严格保证每轮值序列一致。
- 不把同时被当前循环写入的固定数组位置当作整轮不变量。
- 对运行时参数控制的循环，不能只针对默认参数投机优化；若做特化，必须保留通用正确路径。
- 不引入与 TSVC 全局数组同名的局部变量或循环变量。
- 如果无法证明激进改写等价，返回保守但完整的函数版本。

## 输出格式
先用 2-4 行说明采用的优化策略，然后输出一个 ```c 代码块。代码块内只能包含完整 C 函数代码，不能包含省略号、TODO、伪代码或自然语言解释。
"""


# 多轮优化的增强系统 Prompt
SYSTEM_PROMPT_MULTI_ROUND = """你是 ACPO-LLM（AI-Enabled Compiler Program Optimization - Large Language Model），一个专门为 C/C++ 自动向量化优化设计的大模型。

## 你的核心使命
通过多轮迭代优化，逐步消除代码中的向量化障碍，最终生成能够被 Clang 自动向量化的代码。

## 当前优化轮次：第 {round_num} 轮 / 共 {max_rounds} 轮

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
"""


def build_optimization_prompt(
    code: str,
    func_name: str,
    diagnostics: Dict,
    round_num: int = 1,
    max_rounds: int = 3,
    previous_rounds: Optional[List[Dict]] = None,
    prompt_options: Optional[Dict] = None,
    semantic_hints: Optional[List[str]] = None,
    correctness_feedback: Optional[Dict] = None,
    semantic_risks: Optional[List[str]] = None,
) -> Tuple[str, str]:
    """
    构建优化 Prompt

    Args:
        code: 当前代码（原始代码或上一轮优化结果）
        func_name: 函数名
        diagnostics: 诊断信息（包含 missed、vectorized 等）
        round_num: 当前轮次
        max_rounds: 最大轮次
        previous_rounds: 之前的优化轮次信息（用于多轮优化）

    Returns:
        (system_prompt, user_prompt)
    """
    options = normalize_prompt_options(prompt_options)

    # 根据轮次和策略选择系统 Prompt
    if resolve_system_prompt_template_name(round_num, options) == "strong_plain_system":
        system_prompt = SYSTEM_PROMPT_STRONG_PLAIN
    elif resolve_system_prompt_template_name(round_num, options) == "method_system":
        system_prompt = SYSTEM_PROMPT_BASE
    else:
        system_prompt = SYSTEM_PROMPT_MULTI_ROUND.format(
            round_num=round_num,
            max_rounds=max_rounds
        )

    # 构建用户 Prompt
    sections = []

    # 1. 函数信息
    sections.append(f"【函数名】: {func_name}")
    sections.append(f"【当前轮次】: 第 {round_num} 轮 / 共 {max_rounds} 轮")

    # 2. 待优化代码
    sections.append(f"\n【待优化代码】:\n```c\n{code}\n```")

    if options["include_strong_baseline_guidance"]:
        sections.append("\n【通用自动向量化改写建议】:")
        sections.append("- 先检查循环是否存在真实跨迭代依赖；有真实依赖时不要强行加 pragma。")
        sections.append("- 可以尝试循环交换、循环分发、循环剥离、节点拆分、标量临时变量、条件结构化、restrict 和 Clang loop pragma。")
        sections.append("- 每个改写都必须保持原始迭代空间、数组写入集合、dummy() 调用层级和运行时参数语义。")
        sections.append("- 若使用运行时参数特化，必须保留覆盖所有参数的通用正确路径。")
        sections.append("- 不要使用项目案例卡、历史反馈或特定已知函数经验；只依据当前源码做通用优化判断。")

    # 3. 向量化诊断信息
    missed = diagnostics.get("missed", [])
    vectorized = diagnostics.get("vectorized", [])
    structured_feedback = diagnostics.get("structured_feedback")

    if options["include_diagnostics"] and missed:
        sections.append(f"\n【向量化失败原因】({len(missed)} 个问题):")
        for i, reason in enumerate(missed[:5], 1):  # 最多显示5个
            # 清理并简化原因描述
            clean_reason = reason.strip()
            if "loop not vectorized:" in clean_reason:
                clean_reason = clean_reason.split("loop not vectorized:", 1)[-1].strip()
            sections.append(f"{i}. {clean_reason}")

    if options["include_diagnostics"] and vectorized:
        sections.append(f"\n【已向量化的循环】({len(vectorized)} 个):")
        for reason in vectorized[:3]:  # 最多显示3个
            sections.append(f"- {reason.strip()}")

    if options["include_structured_feedback"] and structured_feedback:
        structured_text = format_structured_feedback_for_prompt(structured_feedback)
        if structured_text:
            sections.append(f"\n【结构化反馈摘要】:\n{structured_text}")
    elif not options["include_structured_feedback"]:
        structured_feedback = None

    # 3.5. 从源码结构中提炼的语义提示
    if options["include_semantic_hints"] and semantic_hints:
        sections.append("\n【语义安全提示】:")
        for hint in semantic_hints[:5]:
            sections.append(f"- {hint}")
        if (
            any("变步长循环" in hint for hint in semantic_hints)
            and (options["include_knowledge"] or options["include_examples"] or options["include_history"])
        ):
            if any("简单同址 runtime-stride 模式" in hint for hint in semantic_hints):
                sections.append("\n【参数化步长循环推荐策略】:")
                sections.append("- 如果循环是简单的 `a[i] += b[i]` 一类同址访问，不要只做 `restrict + pragma`。")
                sections.append("- 可以尝试少量代表性小步长（如 1/2/4）的等价专用分支，并保留一个覆盖全部参数的通用 fallback。")
                sections.append("- 特化分支不能只覆盖默认参数；每个分支都必须更新与原循环完全相同的索引集合。")
                sections.append("- 如果无法直接证明等价，就回退到通用路径，而不是提交激进但不稳的改写。")
            elif any("复杂 runtime-stride 模式" in hint for hint in semantic_hints):
                sections.append("\n【复杂参数化步长循环推荐策略】:")
                sections.append("- 这类循环同时伴随递推变量、反向索引或复杂地址表达式，不要机械套用 `1/2/4` 多版本化。")
                sections.append("- 优先考虑：只为 `stride == 1` 提供可直接证明等价的快路径。")
                sections.append("- 对 `stride > 1`，优先保留原始通用路径，或使用索引预计算 / 两阶段重构。")
                sections.append("- 如果需要恢复逻辑迭代号，优先维护独立的 `idx/t` 计数器；不要在热循环里写 `(i - start) / stride` 或 `% stride`。")
                sections.append("- 如果快路径无法证明覆盖相同索引集合与更新顺序，就不要提交该特化。")

    # 4. 知识库信息（第一轮或新问题时添加）
    if options["include_knowledge"] and (round_num == 1 or (round_num > 1 and not previous_rounds)):
        case_cards = format_case_cards_for_prompt(structured_feedback)
        if case_cards:
            sections.append(f"\n【类别化案例卡】:\n{case_cards}")

        # 使用增强版知识库（包含深度分析和编译器指令指导）
        enhanced_knowledge = format_enhanced_knowledge(missed)
        if enhanced_knowledge:
            sections.append(f"\n【向量化知识库参考】:\n{enhanced_knowledge}")
        
        # 添加快速修复建议
        quick_fixes = get_quick_fix_suggestions(missed)
        if quick_fixes:
            sections.append("\n【快速修复建议（按成功率排序）】:")
            for i, fix in enumerate(quick_fixes[:3], 1):
                sections.append(f"  {i}. {fix['method']} (成功率: {fix['probability']})")
                if 'code_example' in fix:
                    sections.append(f"     示例: {fix['code_example']}")

    # 5. 多轮优化上下文（第二轮及以后）
    if options["include_history"] and round_num > 1 and previous_rounds:
        sections.append(f"\n【前几轮优化历史】:")
        for i, prev in enumerate(previous_rounds[-2:], start=len(previous_rounds)-1):
            sections.append(f"\n--- 第 {i+1} 轮 ---")
            sections.append(f"策略: {prev.get('strategy', '无策略记录')}")
            sections.append(f"结果: {prev.get('vectorized_count', 0)} 成功 / {prev.get('missed_count', 0)} 失败")
            if "correctness_report" in prev and prev["correctness_report"] is not None:
                correctness_ok = prev["correctness_report"].get("overall", False)
                sections.append(f"正确性: {'通过' if correctness_ok else '失败'}")
                if not correctness_ok:
                    sem_error = (
                        prev["correctness_report"].get("layer2_semantic", {}).get("error")
                        or prev["correctness_report"].get("layer3_runtime", {}).get("error")
                    )
                    if sem_error:
                        sections.append(f"失败原因: {sem_error}")
            if prev.get("semantic_risks"):
                sections.append("高风险信号:")
                for risk in prev["semantic_risks"][:3]:
                    sections.append(f"- {risk}")

        if options["include_progress_analysis"]:
            # 检测优化进展
            progress_analysis = analyze_optimization_progress(previous_rounds)
            
            # 检测是否有本质限制
            fundamental = check_fundamental_limitation(missed)
            
            # 获取部分向量化指导
            current_v = previous_rounds[-1].get('vectorized_count', 0)
            current_m = previous_rounds[-1].get('missed_count', 0)
            partial_guidance = get_partial_vectorization_guidance(current_v, current_v + current_m, missed)
            
            # 根据进展状态给出不同指导
            if progress_analysis['status'] == 'fundamental_limit' or fundamental:
                # 检测到本质限制
                sections.append(f"\n【⚠️ 优化状态评估】:")
                sections.append(progress_analysis['message'])
                if 'explanation' in progress_analysis:
                    sections.append(f"说明: {progress_analysis['explanation']}")
                sections.append(f"\n建议: {progress_analysis['recommendation']}")
                sections.append(partial_guidance)
                sections.append("\n【本轮任务调整】:")
                sections.append("检测到可能存在无法完全向量化的循环。你的任务是：")
                sections.append("1. 验证哪些循环是可向量化的，最大化这部分的性能")
                sections.append("2. 对于可能无法向量化的循环，尝试最后的优化手段")
                sections.append("3. 如果确认无法完全向量化，接受部分向量化的结果")
                
            elif progress_analysis['status'] == 'stalled':
                # 优化停滞
                sections.append(f"\n【⚠️ 优化状态评估】:")
                sections.append(progress_analysis['message'])
                sections.append(f"建议: {progress_analysis['recommendation']}")
                sections.append("\n【本轮要求】:")
                sections.append("多轮优化后进展停滞。请尝试：")
                sections.append("1. 根本性改变策略（如从循环拆分改为算法重构）")
                sections.append("2. 检查是否遗漏了本质限制因素")
                sections.append("3. 如果仍无进展，考虑接受部分向量化")
                
            else:
                # 正常进展
                sections.append(f"\n【本轮要求】:")
                sections.append("上一轮优化后仍未完全向量化。你必须：")
                sections.append("1. 分析剩余失败原因")
                sections.append("2. 采用与之前不同的策略")
                sections.append("3. 做出实质性代码改变")
                sections.append("4. 禁止提交与之前完全相同的代码")
        else:
            sections.append(f"\n【本轮要求】:")
            sections.append("参考前几轮结果继续优化，但不要复述额外的进展分析。")
            sections.append("请直接尝试新的代码改写策略，并保持语义不变。")

    if correctness_feedback:
        sections.append("\n【上一候选的正确性反馈】:")
        sections.append(f"- 总体结果: {'通过' if correctness_feedback.get('overall') else '失败'}")
        failure_reason = correctness_feedback.get("failure_reason")
        if failure_reason:
            sections.append(f"- 关键失败原因: {failure_reason}")
        advice = correctness_feedback.get("advice")
        if advice:
            sections.append(f"- 修正建议: {advice}")

    if semantic_risks:
        sections.append("\n【上一候选的高风险模式】:")
        for risk in semantic_risks[:5]:
            sections.append(f"- {risk}")

    # 6. Few-shot 示例（仅第一轮）
    if options["include_examples"] and round_num == 1:
        examples = get_relevant_examples(missed, structured_feedback=structured_feedback)
        if examples:
            sections.append(f"\n【类似案例参考】:\n{examples}")

    # 7. 最终指令
    sections.append(f"\n【你的任务】:")
    if round_num == 1:
        sections.append("分析上述代码的向量化障碍，应用适当的优化技术，输出优化后的代码。")
    else:
        sections.append("基于前几轮的反馈，采用新策略继续优化。必须做出实质性改变！")
    sections.append("如果存在递推变量、参数化步长或 dummy() 语义风险，优先使用可验证的保守重构，不要做未经证明的闭式化简或批量折叠。")

    sections.append("\n请输出优化策略和完整代码：")
    sections.append("- 先给 2-4 行策略说明，再给一个 ```c 代码块")
    sections.append("- 代码块内只能包含纯 C 代码，禁止夹带解释文字")
    sections.append("- 不要输出 `...`、`TODO`、伪代码或半截函数")
    sections.append("- 如果不确定优化是否成立，返回完整保守版本函数，不要只给分析")

    user_prompt = "\n".join(sections)
    return system_prompt, user_prompt


def build_retry_prompt(
    code: str,
    compilation_error: str,
    previous_strategy: str = ""
) -> Tuple[str, str]:
    """
    构建编译失败重试的 Prompt

    Args:
        code: 编译失败的代码
        compilation_error: 编译错误信息
        previous_strategy: 之前的优化策略

    Returns:
        (system_prompt, user_prompt)
    """
    system_prompt = """你是 ACPO-LLM 代码修复专家。

你的任务是修复编译错误的 C 代码，同时尽可能保留向量化优化意图。

修复原则：
1. 优先修复语法错误（括号匹配、分号等）
2. 保留 restrict 和 pragma 等向量化提示
3. 不改变代码的基本结构和语义
4. 确保修复后的代码可以编译
5. 只输出一个完整函数，禁止输出解释性文字、`...` 或占位符
"""

    user_prompt = f"""【编译失败的代码】:
```c
{code}
```

【编译错误信息】:
```
{compilation_error}
```

{f'【原优化策略】: {previous_strategy}' if previous_strategy else ''}

请修复上述代码中的编译错误，输出修复后的完整代码。
要求：
1. 只修复语法错误，不改变优化逻辑
2. 保留所有向量化相关的修饰符和 pragma
3. 输出完整的可编译代码
4. 只输出一个 ```c 代码块，代码块内不要包含任何自然语言解释
5. 禁止输出 `...`、`TODO`、伪代码或省略内容

修复后的代码：
"""

    return system_prompt, user_prompt


def build_analysis_prompt(
    code: str,
    func_name: str,
    evaluation_result: Dict
) -> str:
    """
    构建代码分析的 Prompt（用于理解为什么优化失败）

    Args:
        code: 优化后的代码
        func_name: 函数名
        evaluation_result: 评估结果

    Returns:
        analysis_prompt
    """
    vectorized_count = evaluation_result.get("vectorized_count", 0)
    missed_count = evaluation_result.get("missed_count", 0)
    diagnostics = evaluation_result.get("diagnostics", {})
    missed = diagnostics.get("missed", [])

    prompt = f"""请分析以下代码的向量化情况：

【函数名】: {func_name}
【向量化统计】: {vectorized_count} 成功 / {missed_count} 失败

【代码】:
```c
{code}
```

【未向量化的原因】:
"""
    for i, reason in enumerate(missed[:5], 1):
        prompt += f"{i}. {reason}\n"

    prompt += """
请分析：
1. 为什么这些循环未能向量化？
2. 根因是什么（归纳变量、别名、依赖等）？
3. 下一步应该尝试什么优化策略？

请给出简洁的分析（3-5行）：
"""

    return prompt
