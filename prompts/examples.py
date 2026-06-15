"""
Few-shot Examples
=================
提供成功优化案例作为 Few-shot 示例
"""

from collections import OrderedDict
from typing import List, Optional

from feedback_structuring import dedupe_preserve_order


# 成功的向量化优化案例库
SUCCESS_CASES = [
    {
        "func_name": "s1113",
        "issue_type": "scalar_dependency",
        "description": "标量依赖 - 循环内使用数组中间元素",
        "original": """real_t s1113(struct args_t * func_args)
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
}""",
        "optimized": """real_t s1113(struct args_t * func_args)
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
}""",
        "key_techniques": [
            "将 a[LEN_1D/2] 提取到循环外，消除循环内标量依赖",
            "使用 __restrict__ 消除别名分析障碍",
            "添加 #pragma clang loop vectorize(enable) 提示编译器"
        ],
        "result": "✅ 完全向量化"
    },

    {
        "func_name": "s111",
        "issue_type": "loop_carried_dependency",
        "description": "循环携带依赖 - 使用 a[i-1]",
        "original": """real_t s111(struct args_t * func_args)
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
}""",
        "optimized": """real_t s111(struct args_t * func_args)
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
}""",
        "key_techniques": [
            "使用 __restrict__ 关键字",
            "添加 vectorize pragma",
            "注意：此案例保持原结构，因为依赖是固有的"
        ],
        "result": "⚠️ 部分向量化（依赖无法完全消除）"
    },

    {
        "func_name": "runtime_stride_mv",
        "issue_type": "variable_bounds",
        "description": "运行时步长 - 多版本化 + 通用 fallback",
        "original": """real_t runtime_stride_mv(struct args_t * func_args)
{
    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = n1 - 1; i < LEN_1D; i += n3) {
            a[i] += b[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}""",
        "optimized": """real_t runtime_stride_mv(struct args_t * func_args)
{
    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ = a;
    real_t * __restrict__ b_ = b;

    for (int nl = 0; nl < iterations; nl++) {
        int start = n1 - 1;
        int stride = n3;

        if (stride == 1) {
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; ++i) {
                a_[i] += b_[i];
            }
        } else if (stride == 2) {
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; i += 2) {
                a_[i] += b_[i];
            }
        } else if (stride == 4) {
            #pragma clang loop vectorize(enable)
            for (int i = start; i < LEN_1D; i += 4) {
                a_[i] += b_[i];
            }
        } else {
            for (int i = start; i < LEN_1D; i += stride) {
                a_[i] += b_[i];
            }
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}""",
        "key_techniques": [
            "对运行时步长循环采用多版本化，而不是只堆 pragma",
            "覆盖多个代表性步长（1/2/4），避免只针对默认参数投机优化",
            "保留通用 fallback，确保所有 arg_info 都有正确路径"
        ],
        "result": "⚠️ 视编译器而定，但通常比 pragma-only 更稳"
    },

    {
        "func_name": "s122",
        "issue_type": "induction_variable",
        "description": "归纳变量 - 递增索引 k",
        "original": """real_t s122(struct args_t * func_args)
{
    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int j, k;
    for (int nl = 0; nl < iterations; nl++) {
        j = 1;
        k = 0;
        for (int i = n1-1; i < LEN_1D; i += n3) {
            k += j;  // 归纳变量
            a[i] += b[LEN_1D - k];  // 依赖 k 的值
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}""",
        "optimized": """real_t s122(struct args_t * func_args)
{
    struct{int a;int b;} * x = func_args->arg_info;
    int n1 = x->a;
    int n3 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t * __restrict__ a_ = a;
    real_t * __restrict__ b_ = b;

    for (int nl = 0; nl < iterations; nl++) {
        int j = 1;
        int k = 0;

        // 阶段1：预计算所有索引值
        int k_values[LEN_1D];
        int idx = 0;
        for (int i = n1-1; i < LEN_1D; i += n3) {
            k += j;
            k_values[idx++] = k;
        }

        // 阶段2：向量化数据访问
        int loop_count = idx;
        #pragma clang loop vectorize(enable)
        for (int idx = 0; idx < loop_count; idx++) {
            int i = n1-1 + idx * n3;
            a_[i] += b_[LEN_1D - k_values[idx]];
        }

        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}""",
        "key_techniques": [
            "循环拆分（Loop Distribution）：将原循环拆分为索引计算和数据访问两个阶段",
            "预计算：使用数组 k_values[] 存储所有 k 值，打破跨迭代依赖",
            "使用 __restrict__ 消除别名顾虑",
            "添加 pragma 提示编译器向量化第二阶段"
        ],
        "result": "⚠️ 部分向量化（预计算循环仍然有序）"
    },

    {
        "func_name": "s243",
        "issue_type": "control_flow",
        "description": "控制流 - 条件分支",
        "original": """for (int i = 0; i < LEN_1D; i++) {
    if (b[i] > (real_t)0.) {
        a[i] = b[i] * c[i];
    }
}""",
        "optimized": """#pragma clang loop vectorize(enable)
for (int i = 0; i < LEN_1D; i++) {
    a[i] = (b[i] > 0.0f) ? (b[i] * c[i]) : a[i];
}""",
        "key_techniques": [
            "将 if-else 分支转为条件选择表达式（?:）",
            "确保两个分支都执行，用 mask 选择结果",
            "使用 pragma 强制向量化"
        ],
        "result": "✅ 向量化成功"
    },

    {
        "func_name": "s317",
        "issue_type": "alias_analysis",
        "description": "别名分析 - 指针可能重叠",
        "original": """for (int i = 0; i < LEN_1D; i++) {
    a[i] = a[i] + b[i];
    b[i] = b[i] + c[i];
}""",
        "optimized": """real_t * __restrict__ a_ = a;
real_t * __restrict__ b_ = b;
real_t * __restrict__ c_ = c;

#pragma clang loop vectorize(enable)
for (int i = 0; i < LEN_1D; i++) {
    a_[i] = a_[i] + b_[i];
    b_[i] = b_[i] + c_[i];
}""",
        "key_techniques": [
            "使用 __restrict__ 关键字声明指针不重叠",
            "在循环前将全局数组赋值给 restrict 局部指针",
            "添加 pragma 提示编译器"
        ],
        "result": "✅ 向量化成功"
    }
]


def get_all_examples() -> List[dict]:
    """获取所有成功案例"""
    return SUCCESS_CASES


def get_examples_by_issue_type(issue_type: str) -> List[dict]:
    """根据问题类型获取相关案例"""
    return [case for case in SUCCESS_CASES if case["issue_type"] == issue_type]


def get_relevant_examples(missed_reasons: List[str], structured_feedback: Optional[dict] = None) -> str:
    """
    根据失败原因获取相关的 Few-shot 示例

    Args:
        missed_reasons: 向量化失败原因列表
        structured_feedback: 结构化反馈摘要

    Returns:
        格式化的示例文本
    """
    # 关键词到问题类型的映射
    keyword_map = {
        "induction": "induction_variable",
        "could not determine": "variable_bounds",
        "alias": "alias_analysis",
        "dependence": "loop_carried_dependency",
        "dependent": "loop_carried_dependency",
        "control": "control_flow",
        "branch": "control_flow",
    }

    matched_types = []

    if structured_feedback:
        pattern_family = structured_feedback.get("pattern_family")
        categories = structured_feedback.get("primary_categories", [])
        if pattern_family == "runtime_stride_simple":
            matched_types.append("variable_bounds")
        elif pattern_family == "runtime_stride_complex":
            matched_types.extend(["induction_variable", "variable_bounds"])
        elif pattern_family == "loop_distribution_dependence_isolation":
            matched_types.append("scalar_dependency")
        elif pattern_family == "branch_hoisting":
            matched_types.append("control_flow")
        elif pattern_family in {"recurrence_boundary", "reduction_or_recurrence"}:
            matched_types.append("loop_carried_dependency")

        category_map = {
            "dependency_unsafe": "scalar_dependency",
            "trip_count_bounds": "variable_bounds",
            "call_side_effect": "variable_bounds",
            "recurrence_reduction": "loop_carried_dependency",
            "control_flow": "control_flow",
            "alias_memory": "alias_analysis",
        }
        for category in categories:
            mapped = category_map.get(category)
            if mapped:
                matched_types.append(mapped)

    for reason in missed_reasons:
        reason_lower = reason.lower()
        for keyword, issue_type in keyword_map.items():
            if keyword in reason_lower:
                matched_types.append(issue_type)

    # 如果没有匹配，返回通用案例
    if not matched_types:
        matched_types = ["alias_analysis", "induction_variable"]
    else:
        matched_types = dedupe_preserve_order(matched_types)

    # 收集相关案例（每种类型最多1个）
    selected_cases = []
    for issue_type in matched_types:
        cases = get_examples_by_issue_type(issue_type)
        if cases:
            selected_cases.append(cases[0])
        if len(selected_cases) >= 2:  # 最多返回2个案例
            break

    # 格式化输出
    sections = []
    for i, case in enumerate(selected_cases, 1):
        section = f"""
=== 案例 {i}: {case['func_name']} - {case['description']} ===

问题类型: {case['issue_type']}
原始代码:
```c
{case['original']}
```

优化后代码:
```c
{case['optimized']}
```

关键技术:
"""
        for j, technique in enumerate(case['key_techniques'], 1):
            section += f"{j}. {technique}\n"

        section += f"\n优化结果: {case['result']}"
        sections.append(section)

    return "\n".join(sections)


def get_transformation_examples() -> str:
    """
    获取代码转换的通用示例（用于展示常见优化技术）

    Returns:
        格式化的转换示例
    """
    return """
=== 常见向量化优化技术示例 ===

【技术1: 别名消除 - 使用 restrict】
优化前:
    for (int i = 0; i < n; i++) {
        a[i] = b[i] + c[i];
    }

优化后:
    real_t * __restrict__ a_ = a;
    real_t * __restrict__ b_ = b;
    real_t * __restrict__ c_ = c;
    #pragma clang loop vectorize(enable)
    for (int i = 0; i < n; i++) {
        a_[i] = b_[i] + c_[i];
    }

【技术2: 循环拆分 - Loop Distribution】
优化前:
    for (int i = 0; i < n; i++) {
        a[i] = b[i] + c[i];  // 无依赖
        d[i] = d[i-1] * e[i]; // 有依赖
    }

优化后:
    // 拆分：第一部分可以向量化的
    #pragma clang loop vectorize(enable)
    for (int i = 0; i < n; i++) {
        a[i] = b[i] + c[i];
    }
    // 拆分：第二部分保持原样
    for (int i = 0; i < n; i++) {
        d[i] = d[i-1] * e[i];
    }

【技术3: 索引预计算】
优化前:
    int k = 0;
    for (int i = 0; i < n; i += 2) {
        k += i;
        a[i] = b[k];  // k 每次变化，无法向量化
    }

优化后:
    // 预计算阶段
    int k_values[LEN_1D];
    int k = 0, idx = 0;
    for (int i = 0; i < n; i += 2) {
        k += i;
        k_values[idx++] = k;
    }
    // 数据访问阶段（可向量化）
    #pragma clang loop vectorize(enable)
    for (int j = 0; j < idx; j++) {
        int i = j * 2;
        a[i] = b[k_values[j]];
    }

【技术4: 条件转换】
优化前:
    for (int i = 0; i < n; i++) {
        if (a[i] > 0) {
            b[i] = a[i] * 2;
        }
    }

优化后:
    #pragma clang loop vectorize(enable)
    for (int i = 0; i < n; i++) {
        b[i] = (a[i] > 0) ? (a[i] * 2) : b[i];
    }
"""


def format_case_for_prompt(case: dict) -> str:
    """将单个案例格式化为 Prompt 可用的格式"""
    techniques_str = "\n".join([f"- {t}" for t in case['key_techniques']])
    return f"""
【优化案例 - {case['func_name']}】
问题描述: {case['description']}

原始代码:
```c
{case['original']}
```

优化后:
```c
{case['optimized']}
```

优化要点:
{techniques_str}
"""
