"""
向量化知识库
============
包含常见的向量化障碍模式、解决方案和适用场景。
"""

from typing import Dict, List, Optional, Tuple

from feedback_structuring import category_label, dedupe_preserve_order

EXPERIMENT_CASE_CARD_SET_VERSION = "experiment_case_cards_v1_20260601"
CASE_CARD_FORMAT_VERSION = "case_card_format_v1_20260601"

# 编译器指令和选项知识库
COMPILER_HINTS = {
    "vectorize_pragma": {
        "syntax": "#pragma clang loop vectorize(enable)",
        "use_case": "当编译器保守地决定不向量化，但你确定循环是安全的",
        "risk": "如果实际有数据依赖，可能导致错误结果",
        "effectiveness": "高 - 强制编译器尝试向量化"
    },
    "vectorize_width": {
        "syntax": "#pragma clang loop vectorize_width(4)",
        "use_case": "指定向量宽度（2/4/8/16），针对特定 SIMD 架构优化",
        "risk": "宽度不匹配可能导致性能下降",
        "effectiveness": "中 - 需要了解目标架构"
    },
    "interleave_pragma": {
        "syntax": "#pragma clang loop interleave(enable) interleave_count(4)",
        "use_case": "增加指令级并行度，隐藏内存延迟",
        "risk": "寄存器压力增加",
        "effectiveness": "中到高 - 配合向量化使用"
    },
    "unroll_pragma": {
        "syntax": "#pragma clang loop unroll(enable) unroll_count(4)",
        "use_case": "减少循环开销，增加优化机会",
        "risk": "代码膨胀",
        "effectiveness": "中 - 小循环效果好"
    },
    "restrict_keyword": {
        "syntax": "real_t * __restrict__ ptr",
        "use_case": "告诉编译器指针不会与其他指针重叠",
        "risk": "如果实际重叠，属于未定义行为",
        "effectiveness": "高 - 消除别名分析障碍"
    },
    "aligned_attribute": {
        "syntax": "__attribute__((aligned(64)))",
        "use_case": "确保数组按指定字节对齐，便于 SIMD 访问",
        "risk": "内存浪费",
        "effectiveness": "中 - 对向量化有帮助"
    }
}

# 编译选项对向量化的影响
COMPILER_OPTIONS = {
    "march_native": {
        "option": "-march=native",
        "use_case": "针对本机 CPU 架构优化，启用所有支持的 SIMD 指令集",
        "when_to_use": "当知道运行环境时使用",
        "effectiveness": "高"
    },
    "fno_tree_vectorize": {
        "option": "-fno-tree-vectorize",
        "use_case": "禁用 GCC 风格的向量化（如果干扰）",
        "when_to_use": "仅当 LLVM 向量化与 GCC 冲突",
        "effectiveness": "低"
    },
    "Rpass": {
        "option": "-Rpass=loop-vectorize -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize",
        "use_case": "获取详细的向量化诊断信息",
        "when_to_use": "调试时",
        "effectiveness": "信息收集"
    }
}

# 向量化障碍的解决策略分类
# 区分"必须改源码" vs "可用编译选项/pragma"
VECTORIZATION_SOLUTIONS = {
    "source_change_required": {
        "induction_variable": {
            "description": "归纳变量导致的跨迭代依赖",
            "solution_type": "必须改源码",
            "techniques": ["循环拆分", "索引预计算", "标量提升"],
            "example": "见 VECTORIZATION_PATTERNS['induction_variable']"
        },
        "loop_carried_dependency": {
            "description": "循环携带依赖（a[i] 依赖于 a[i-1]）",
            "solution_type": "必须改源码",
            "techniques": ["算法重构", "前缀和", "循环分发"],
            "note": "真依赖通常无法直接向量化"
        },
        "control_flow": {
            "description": "复杂控制流（if-else, break）",
            "solution_type": "优先改源码",
            "techniques": ["条件选择代替分支", "消除 break/continue"],
            "fallback": "有时可以用 #pragma clang loop vectorize(enable)"
        }
    },
    "compiler_hint_applicable": {
        "variable_bounds": {
            "description": "变量边界导致编译器无法确定循环次数",
            "solution_type": "优先用 pragma",
            "primary_solution": "#pragma clang loop vectorize(enable)",
            "secondary_solution": "将边界参数复制到局部变量",
            "effectiveness": "pragma 通常有效"
        },
        "alias_analysis": {
            "description": "指针别名分析障碍",
            "solution_type": "可用 __restrict__ 或 pragma",
            "primary_solution": "使用 __restrict__ 关键字",
            "secondary_solution": "#pragma clang loop vectorize(enable) (风险较高)",
            "effectiveness": "__restrict__ 最可靠"
        },
        "memory_access_pattern": {
            "description": "非连续内存访问",
            "solution_type": "视情况而定",
            "techniques": ["interleave_count pragma", "改变数据结构", "gather/scatter"],
            "note": "strided access 在现代 CPU 上可能可接受"
        }
    }
}

# 向量化障碍模式知识库
VECTORIZATION_PATTERNS = {
    "induction_variable": {
        "description": "归纳变量导致的跨迭代依赖",
        "patterns": [
            r"k\s*\+=\s*\w+",
            r"\w+\s*[=\+\-]\s*\w+\s*\*\s*i",
        ],
        "examples": [
            {
                "code": """for (int i = n1-1; i < LEN_1D; i += n3) {
    k += j;
    a[i] += b[LEN_1D - k];
}""",
                "problem": "归纳变量 k 的值在每次迭代中变化，导致反向索引访问模式",
                "solution": "预计算所有索引值到数组，将依赖计算与数据访问分离",
                "transformed": """// 预计算阶段
int k_values[LEN_1D];
int idx = 0;
for (int i = n1-1; i < LEN_1D; i += n3) {
    k += j;
    k_values[idx++] = k;
}

// 向量化数据访问阶段
for (int idx = 0; idx < loop_count; idx++) {
    int i = n1-1 + idx * n3;
    a[i] += b[LEN_1D - k_values[idx]];
}""",
                "key_points": [
                    "将循环拆分为两个阶段：索引计算和数据访问",
                    "使用数组存储中间结果，打破跨迭代依赖",
                    "数据访问阶段使用连续索引，便于向量化",
                ],
            }
        ],
    },
    "variable_bounds": {
        "description": "变量边界导致编译器无法确定循环次数",
        "patterns": [
            r"for\s*\([^;]+;\s*\w+\s*[<>=]+\s*\w+",
            r"stride\s*=\s*\w+",
        ],
        "examples": [
            {
                "code": """for (int i = n1-1; i < LEN_1D; i += n3) {
    a[i] += b[i];
}""",
                "problem": "循环边界 n1 和步长 n3 是变量，编译器无法展开循环",
                "solution": "将变量边界转为局部变量；如果循环属于简单同址访问模式且 pragma 仍无效，可使用多个常见小步长的等价专用分支，并保留通用 fallback",
                "transformed": """int start = n1 - 1;
int stride = n3;

if (stride == 1) {
    #pragma clang loop vectorize(enable)
    for (int i = start; i < LEN_1D; ++i) {
        a[i] += b[i];
    }
} else if (stride == 2) {
    #pragma clang loop vectorize(enable)
    for (int i = start; i < LEN_1D; i += 2) {
        a[i] += b[i];
    }
} else if (stride == 4) {
    #pragma clang loop vectorize(enable)
    for (int i = start; i < LEN_1D; i += 4) {
        a[i] += b[i];
    }
} else {
    for (int i = start; i < LEN_1D; i += stride) {
        a[i] += b[i];
    }
}""",
                "key_points": [
                    "将函数参数复制到局部变量",
                    "这类多版本化更适合简单同址访问模式",
                    "不要只为默认参数写快路径，要覆盖多个代表性步长并保留通用 fallback",
                    "每个分支必须与原循环访问完全相同的索引集合",
                ],
            }
        ],
    },
    "alias_analysis": {
        "description": "指针别名分析障碍",
        "patterns": [
            r"real_t\s*\*\s*\w+\s*=",
            r"a\[i\]\s*=.*b\[i\]",
        ],
        "examples": [
            {
                "code": """for (int i = 0; i < LEN_1D; i++) {
    a[i] = a[i] + b[i];
}""",
                "problem": "编译器担心 a 和 b 可能指向重叠内存",
                "solution": "使用 __restrict__ 关键字告诉编译器指针不会重叠",
                "transformed": """real_t * __restrict__ a_ = a;
real_t * __restrict__ b_ = b;

#pragma clang loop vectorize(enable)
for (int i = 0; i < LEN_1D; i++) {
    a_[i] = a_[i] + b_[i];
}""",
                "key_points": [
                    "使用 __restrict__ 关键字消除别名顾虑",
                    "在循环前将全局数组赋值给 restrict 指针",
                    "restrict 指针告诉编译器：此指针是唯一访问该内存的方式",
                ],
            }
        ],
    },
    "scalar_dependency": {
        "description": "标量变量的跨迭代依赖",
        "patterns": [
            r"(\w+)\s*=.*\1\s*",
            r"(\w+)\s*\+?=.*for",
        ],
        "examples": [
            {
                "code": """real_t sum = 0;
for (int i = 0; i < LEN_1D; i++) {
    sum += a[i];
}""",
                "problem": "标量 sum 每次迭代都更新，形成依赖链",
                "solution": "如果可能，使用数组存储中间结果；或者接受此循环无法向量化",
                "transformed": """// 对于归约操作，可以使用 OpenMP simd 指令
real_t sum = 0;
#pragma omp simd reduction(+:sum)
for (int i = 0; i < LEN_1D; i++) {
    sum += a[i];
}
// 或者使用 Clang 的 vectorize 指令（效果有限）
#pragma clang loop vectorize(enable) interleave(enable)
for (int i = 0; i < LEN_1D; i++) {
    sum += a[i];
}""",
                "key_points": [
                    "归约操作（reduction）难以完全向量化",
                    "可以尝试使用 reduction 指令",
                    "某些情况下应接受此循环无法向量化",
                ],
            }
        ],
    },
    "memory_access_pattern": {
        "description": "非连续内存访问模式",
        "patterns": [
            r"\w+\[\w+\s*\*\s*\d+\]",
            r"\w+\[LEN_\w+\s*-\s*\w+\]",
        ],
        "examples": [
            {
                "code": """for (int i = 0; i < LEN_1D/2; i++) {
    a[2*i] = b[i] + c[i];
}""",
                "problem": "访问模式 a[2*i] 是非连续的，每次跳过 2 个元素",
                "solution": "使用 gather/scatter 指令（如果硬件支持）或循环展开",
                "transformed": """// 方法1：循环展开，处理偶数和奇数索引
#pragma clang loop vectorize(enable) interleave_count(2)
for (int i = 0; i < LEN_1D/2; i++) {
    a[2*i] = b[i] + c[i];
}

// 方法2：如果 LEN_1D 是固定的，可以显式展开
for (int i = 0; i < LEN_1D; i += 2) {
    a[i] = b[i/2] + c[i/2];
}""",
                "key_points": [
                    "非连续访问可以使用 interleave_count 提示",
                    "考虑是否可以改变算法，使访问模式连续",
                    "某些 strided access 在现代 CPU 上性能可以接受",
                ],
            }
        ],
    },
    "loop_carried_dependency": {
        "description": "循环携带依赖（Loop-Carried Dependency）",
        "patterns": [
            r"a\[i\]\s*=.*a\[i\s*[+-]\s*\d+\]",
        ],
        "examples": [
            {
                "code": """for (int i = 1; i < LEN_1D; i++) {
    a[i] = a[i-1] + b[i];
}""",
                "problem": "每个 a[i] 依赖于前一个迭代的 a[i-1]",
                "solution": "分析依赖性质，如果是真依赖则难以向量化；如果是输出依赖可考虑复制",
                "transformed": """// 真依赖（True Dependency）：a[i] 依赖于 a[i-1] 的新值
// 这种情况通常无法直接向量化
// 但可以检查是否有等价的非递归形式

// 原始：a[i] = a[i-1] + b[i]
// 展开：a[1] = a[0] + b[1]
//       a[2] = a[1] + b[2] = a[0] + b[1] + b[2]
//       a[3] = a[2] + b[3] = a[0] + b[1] + b[2] + b[3]
// 可以发现：a[i] = a[0] + sum(b[1..i])
// 使用前缀和可以并行化

// 优化版本（前缀和）：
real_t prefix_sum = a[0];
for (int i = 1; i < LEN_1D; i++) {
    prefix_sum += b[i];
    a[i] = prefix_sum;
}""",
                "key_points": [
                    "识别依赖类型：真依赖、反依赖、输出依赖",
                    "真依赖通常需要算法重构",
                    "考虑数学等价变换（如前缀和）",
                ],
            }
        ],
    },
    "control_flow": {
        "description": "复杂控制流阻碍向量化",
        "patterns": [
            r"if\s*\([^)]+\)\s*\{[^}]*a\[i\]",
            r"break|continue",
        ],
        "examples": [
            {
                "code": """for (int i = 0; i < LEN_1D; i++) {
    if (b[i] > 0) {
        a[i] = b[i] * c[i];
    } else {
        a[i] = 0;
    }
}""",
                "problem": "if 语句导致控制流发散，SIMD 指令需要统一执行路径",
                "solution": "使用条件选择代替分支，或应用 if-conversion",
                "transformed": """// 方法：将分支转为条件选择（select）
#pragma clang loop vectorize(enable)
for (int i = 0; i < LEN_1D; i++) {
    a[i] = (b[i] > 0) ? (b[i] * c[i]) : 0;
}

// 或者使用显式的条件移动
#pragma clang loop vectorize(enable)
for (int i = 0; i < LEN_1D; i++) {
    real_t product = b[i] * c[i];
    a[i] = (b[i] > 0) * product;
}""",
                "key_points": [
                    "分支可以转为条件选择表达式 ?:",
                    "确保两个分支都执行，然后用 mask 选择",
                    "消除 break/continue 语句",
                ],
            }
        ],
    },
}


EXPERIMENT_CASE_CARDS = [
    {
        "id": "runtime_stride_simple_multiversion",
        "title": "runtime-stride simple: multiversion with fallback",
        "categories": ["trip_count_bounds"],
        "pattern_families": ["runtime_stride_simple"],
        "summary": "When the hot loop is a simple same-index stride loop, prefer a few representative stride specializations plus a generic fallback.",
        "recommended_actions": [
            "Copy runtime bounds and stride into local variables.",
            "Specialize only a small set of common stride values such as 1/2/4.",
            "Keep one fully generic fallback path that preserves all arg_info cases.",
        ],
        "avoid_patterns": [
            "Do not optimize only the default stride case.",
            "Do not change the accessed index set across branches.",
        ],
        "mini_before": "for (int i = start; i < LEN_1D; i += stride) { a[i] += b[i]; }",
        "mini_after": "if (stride == 1) use a unit-stride loop; else if (stride == 2) use the stride-2 loop; else keep the original loop.",
        "semantic_safety": "Each specialized branch must update exactly the same index set as the original start/stride loop, and the generic fallback must cover all remaining runtime cases.",
        "vectorization_rationale": "Small constant-stride branches expose predictable loop bounds and memory access shape to Clang, especially for stride 1/2/4.",
        "performance_risk": "Too many specializations increase code size; accepting a branch that only covers the default input is a false positive.",
        "oracle_function": "s172",
        "oracle_before": "for (int i = n1-1; i < LEN_1D; i += n3) {\n    a[i] += b[i];\n}",
        "oracle_after": "int start = n1 - 1;\nint stride = n3;\nif (stride == 1) {\n    #pragma clang loop vectorize(enable)\n    for (int i = start; i < LEN_1D; ++i) { a_[i] += b_[i]; }\n} else if (stride == 2) {\n    #pragma clang loop vectorize(enable)\n    for (int i = start; i < LEN_1D; i += 2) { a_[i] += b_[i]; }\n} else if (stride == 4) {\n    #pragma clang loop vectorize(enable)\n    for (int i = start; i < LEN_1D; i += 4) { a_[i] += b_[i]; }\n} else if (stride > 0) {\n    int trip_count = (LEN_1D - start + stride - 1) / stride;\n    real_t *pa = a_ + start;\n    #pragma clang loop vectorize(enable)\n    for (int k = 0; k < trip_count; ++k) { pa[k*stride] += pb[k*stride]; }\n} else { /* negative stride: fallback */ }",
        "oracle_speedup": "2.07x (glm-4.7), 2.27x (deepseek-v4-pro)",
        "oracle_verified": "2026-05-15",
    },
    {
        "id": "runtime_stride_complex_two_phase",
        "title": "runtime-stride complex: two-phase index materialization only",
        "categories": ["trip_count_bounds", "instruction_shape"],
        "pattern_families": ["runtime_stride_complex"],
        "summary": "If runtime stride is mixed with indexed recurrence or reverse indexing, stay conservative: isolate the recurrence first, then vectorize only the clean data-access phase.",
        "recommended_actions": [
            "Keep the original outer iteration structure intact.",
            "Precompute index values or dependent scalars in a first phase.",
            "Vectorize only the second phase with simple loop indices.",
        ],
        "avoid_patterns": [
            "Do not mechanically clone stride 2/4 branches for complex indexed loops.",
            "Do not rewrite indexed recurrence into a closed form unless sequence equivalence is proven.",
        ],
        "mini_before": "k += j; a[i] += b[LEN_1D - k];",
        "mini_after": "phase 1 records k_values in original order; phase 2 updates a[i] from b[LEN_1D - k_values[idx]].",
        "semantic_safety": "The recurrence variable is still advanced in original iteration order; only the later data-access phase is separated.",
        "vectorization_rationale": "The second phase uses an explicit logical iteration index, which removes the loop-carried scalar update from the vectorized loop body.",
        "performance_risk": "The helper index array adds memory traffic, so this is partial evidence and must pass the performance guard.",
        "oracle_function": "s122",
        "oracle_before": "for (int i = n1-1; i < LEN_1D; i += n3) {\n    k += j;\n    a[i] += b[LEN_1D - k];\n}",
        "oracle_after": "int k_values[LEN_1D];\nint idx = 0;\nint start = n1 - 1;\nint stride = n3;\nfor (int i = start; i < LEN_1D; i += stride) {\n    k += j;\n    k_values[idx++] = k;\n}\nint loop_count = idx;\n#pragma clang loop vectorize(enable)\nfor (int idx = 0; idx < loop_count; idx++) {\n    int i = start + idx * stride;\n    a_[i] += b_[LEN_1D - k_values[idx]];\n}",
        "oracle_speedup": "formal_s122_glm_20260522: ours_full 1.147x vs llm_plain 0.889x; partial vectorization only",
        "oracle_verified": "2026-05-21",
        "oracle_critical_note": "This is a supplemental complex runtime-stride card, not a strong positive oracle. The safe route is to preserve the recurrence order in a precompute phase. Direct closed-form replacement of k was flagged as high-risk and should be avoided unless sequence equivalence is proven.",
    },
    {
        "id": "loop_distribution_dependency_isolation",
        "title": "unsafe dependence: isolate the offending statement",
        "categories": ["dependency_unsafe"],
        "pattern_families": ["loop_distribution_dependence_isolation"],
        "summary": "When clang reports unsafe dependent memory operations, first try to isolate the dependent statement rather than rewriting the whole loop.",
        "recommended_actions": [
            "Split the loop into vectorizable and non-vectorizable phases.",
            "Hoist invariant scalar reads outside the inner loop only when the source location is provably outside the loop's write domain.",
            "Use temporary scalars or arrays only for the dependent fragment.",
        ],
        "avoid_patterns": [
            "Do not flatten the whole loop into a large new data structure if only one statement is problematic.",
            "Do not hoist a fixed-index read from the same array if the loop may later overwrite that index in the same pass.",
            "Do not claim full vectorization if one dependent fragment must remain ordered.",
        ],
        "mini_before": "a[i] = a[mid] + b[i];",
        "mini_after": "split into i < mid / i == mid / i > mid segments, or keep ordered reads if no safe split is proven.",
        "semantic_safety": "The split uses the old value of a[mid] before i == mid and the new value after i == mid, matching the original sequential update.",
        "vectorization_rationale": "The i < mid and i > mid segments read a scalar invariant and write disjoint ranges, so each segment becomes a clean vectorizable loop.",
        "performance_risk": "Hoisting a[mid] once for the entire loop is incorrect; over-splitting would add overhead without changing the dependency.",
        "oracle_function": "s1113",
        "oracle_before": "for (int i = 0; i < LEN_1D; i++) {\n    a[i] = a[LEN_1D/2] + b[i];\n}",
        "oracle_after": "int mid = LEN_1D / 2;\nreal_t mid_val_old = a_[mid];\n#pragma clang loop vectorize(enable)\nfor (int i = 0; i < mid; i++) {\n    a_[i] = mid_val_old + b_[i];\n}\na_[mid] = a_[mid] + b_[mid];\nreal_t mid_val_new = a_[mid];\n#pragma clang loop vectorize(enable)\nfor (int i = mid + 1; i < LEN_1D; i++) {\n    a_[i] = mid_val_new + b_[i];\n}",
        "oracle_speedup": "2.95x (glm-4.7), 2.96x (deepseek-v4-pro)",
        "oracle_verified": "2026-05-15",
        "oracle_critical_note": "Must NOT hoist a[mid] once for the whole loop — must split at mid because a[mid] is overwritten when i==mid.",
    },
    {
        "id": "triangular_saxpy_inner_loop_scalarization",
        "title": "triangular saxpy: keep outer order, scalarize inner invariant",
        "categories": ["dependency_unsafe"],
        "pattern_families": ["triangular_saxpy_dependency_isolation"],
        "summary": "For triangular saxpy loops, keep the outer dependency order and expose the inner loop by scalarizing the fixed source element.",
        "recommended_actions": [
            "Keep the outer triangular loop order unchanged.",
            "For a fixed outer index, cache the source element such as a[j] into a scalar before the inner loop.",
            "Use restrict local pointers for the destination array and the current matrix row.",
            "Vectorize only the inner contiguous update loop.",
        ],
        "avoid_patterns": [
            "Do not interchange the triangular loops unless the sequential triangular dependence is proven equivalent.",
            "Do not treat a[j] as an original array value; it may include earlier outer-loop updates.",
            "Do not claim a general dependence solution if only the inner loop was exposed.",
        ],
        "mini_before": "for (int j = 0; j < N; j++) { for (int i = j + 1; i < N; i++) { a[i] -= aa[j][i] * a[j]; } }",
        "mini_after": "for each j in order, read real_t a_j = a[j]; then vectorize the i > j update using a_j and aa[j][i].",
        "semantic_safety": "The outer j order is preserved. For a fixed j, the inner loop writes only a[i] where i > j, so it does not modify a[j]; caching a[j] as a scalar preserves the value used by all inner iterations.",
        "vectorization_rationale": "After scalarizing a[j] and using restrict row pointers, the inner loop becomes a contiguous update with one invariant scalar and no loop-carried write to the scalar source.",
        "performance_risk": "The verifier reports NaN state metrics for s115, so this card needs runtime equality and repeated benchmark evidence before it is used as final paper-grade proof.",
        "oracle_function": "s115",
        "oracle_before": "for (int j = 0; j < LEN_2D; j++) {\n    for (int i = j+1; i < LEN_2D; i++) {\n        a[i] -= aa[j][i] * a[j];\n    }\n}",
        "oracle_after": "for (int j = 0; j < LEN_2D; j++) {\n    real_t * __restrict__ a_ptr = a;\n    real_t * __restrict__ aa_ptr = aa[j];\n    real_t a_j = a[j];\n    #pragma clang loop vectorize(enable)\n    for (int i = j + 1; i < LEN_2D; i++) {\n        a_ptr[i] -= aa_ptr[i] * a_j;\n    }\n}",
        "oracle_speedup": "oracle_batch1_core_20260522: ours_full 4.045x mean / 4.030x median, 1 vectorized / 0 missed; oracle_s115_plain_baseline_20260522: llm_plain 0 vectorized / 2 missed and benchmark timeout.",
        "oracle_verified": "2026-05-22",
        "oracle_critical_note": "The important transformation is not loop interchange. The plain baseline interchanged loops, preserved correctness, but remained non-vectorized and timed out in benchmark.",
    },
    {
        "id": "row_recurrence_loop_interchange",
        "title": "row recurrence: interchange to expose independent columns",
        "categories": ["recurrence_reduction"],
        "pattern_families": ["loop_interchange_row_recurrence"],
        "summary": "When an inner loop walks along the recurrence direction of a 2D array, interchange loops only if the new inner dimension is independent and contiguous.",
        "recommended_actions": [
            "Identify the true recurrence direction before changing loop order.",
            "Make the recurrence-carrying dimension the outer loop.",
            "Keep the independent contiguous dimension as the vectorized inner loop.",
            "Use row pointers or restrict aliases only after the loop order is proven equivalent.",
        ],
        "avoid_patterns": [
            "Do not call every recurrence-like diagnostic a loop-interchange candidate.",
            "Do not interchange triangular self-recurrences without proving the new iteration space preserves order.",
            "Do not claim this as a full-method-only advantage when a plain model also finds the same loop order.",
        ],
        "mini_before": "for (i) { for (j=1) { aa[j][i] = aa[j-1][i] + bb[j][i]; } }",
        "mini_after": "for (j=1) { #pragma clang loop vectorize(enable) for (i) { aa[j][i] = aa[j-1][i] + bb[j][i]; } }",
        "semantic_safety": "For each fixed j, all i columns read the already computed row j-1 and write row j, so the i iterations are independent after interchange.",
        "vectorization_rationale": "The transformed inner loop walks contiguous i elements in the same row and no longer carries the j-direction recurrence.",
        "performance_risk": "This is a loop-interchange evidence card, not evidence that the full method beats the plain baseline on this pattern.",
        "oracle_function": "s231",
        "oracle_before": "for (int i = 0; i < LEN_2D; ++i) {\n    for (int j = 1; j < LEN_2D; j++) {\n        aa[j][i] = aa[j - 1][i] + bb[j][i];\n    }\n}",
        "oracle_after": "for (int j = 1; j < LEN_2D; j++) {\n    real_t * __restrict__ aa_j = &aa[j][0];\n    real_t * __restrict__ aa_j_1 = &aa[j-1][0];\n    real_t * __restrict__ bb_j = &bb[j][0];\n    #pragma clang loop vectorize(enable)\n    for (int i = 0; i < LEN_2D; ++i) {\n        aa_j[i] = aa_j_1[i] + bb_j[i];\n    }\n}",
        "oracle_speedup": "oracle_batch3_loop_interchange_20260527: ours_full 23.520x mean / 25.672x median. oracle_batch3_loop_interchange_plain_20260527: llm_plain also succeeded at 28.021x mean / 27.379x median.",
        "oracle_verified": "2026-05-27",
        "oracle_critical_note": "Use s231 to show that loop interchange is a valid transform family, not to claim plain-baseline failure; llm_plain was also correct, vectorized and faster in this run.",
    },
    {
        "id": "imperfect_nested_distribution_interchange",
        "title": "imperfect nested loop: distribute producer before interchange",
        "categories": ["recurrence_reduction"],
        "pattern_families": ["loop_distribution_or_interchange", "loop_interchange_row_recurrence"],
        "summary": "For imperfectly nested loops where a per-column producer precedes a row recurrence, split the producer first, then interchange the recurrence nest.",
        "recommended_actions": [
            "Identify scalar or 1D producer statements that must run before the nested recurrence consumes them.",
            "Distribute those producer statements into a separate loop if different columns are independent.",
            "Move the recurrence-carrying dimension outside the vectorized loop.",
            "Keep the contiguous independent dimension as the inner loop and verify that every consumed producer value has already been computed.",
        ],
        "avoid_patterns": [
            "Do not leave the producer inside the recurrence nest if it prevents interchange.",
            "Do not interchange before proving the producer is available for all columns.",
            "Do not report this as a full formal-protocol result when the heavy original benchmark times out.",
        ],
        "mini_before": "for (i) { a[i] += b[i] * c[i]; for (j=1) { aa[j][i] = aa[j-1][i] + bb[j][i] * a[i]; } }",
        "mini_after": "first vectorize for (i) a[i] += b[i] * c[i]; then for (j=1) vectorize the inner i loop for aa[j][i].",
        "semantic_safety": "In s235, each a[i] update is independent and must be completed before every aa[j][i] for the same column reads a[i]. After all a[i] values are produced, the aa recurrence still runs in increasing j order.",
        "vectorization_rationale": "The transformed aa nest reads row j-1 and writes row j for each fixed j, so the inner i loop is contiguous and independent across columns.",
        "performance_risk": "This is a protocol-limited strong candidate: the heavy original s235 function can exceed the formal export or benchmark timeout. A mid protocol with warmup=2, timing=5, batches=3 also hit the 120-second per-process benchmark timeout, so evidence should name the reduced 3-batch repeat protocol unless timeout handling is changed.",
        "oracle_function": "s235",
        "oracle_before": "for (int i = 0; i < LEN_2D; i++) {\n    a[i] += b[i] * c[i];\n    for (int j = 1; j < LEN_2D; j++) {\n        aa[j][i] = aa[j-1][i] + bb[j][i] * a[i];\n    }\n}",
        "oracle_after": "for (int i = 0; i < LEN_2D; i++) {\n    a[i] += b[i] * c[i];\n}\nfor (int j = 1; j < LEN_2D; j++) {\n    #pragma clang loop vectorize(enable)\n    for (int i = 0; i < LEN_2D; i++) {\n        aa[j][i] = aa[j-1][i] + bb[j][i] * a[i];\n    }\n}",
        "oracle_speedup": "oracle_batch7_distribution_control_20260529: ours_full internal correctness passed, 2 vectorized / 0 missed; reduced 3-batch benchmark mean 21.752x / median 22.074x, repeat mean 21.210x / median 21.393x. oracle_s235_distribution_interchange_plain_20260529: llm_plain correctness passed but stayed non-vectorized at 0 vectorized / 2 missed and 1.000x.",
        "oracle_verified": "2026-05-29",
        "oracle_critical_note": "Use s235 as a method-advantage strong candidate under the reduced protocol, not as a completed formal main-table result. The full warmup=3 timing=10 batches=5 export path hit original-function timeout, and a mid warmup=2 timing=5 batches=3 benchmark hit the 120-second process timeout.",
    },
    {
        "id": "selective_interchange_two_inner_loops",
        "title": "selective interchange: split two inner loops before swapping one",
        "categories": ["recurrence_reduction"],
        "pattern_families": ["loop_interchange_selective"],
        "summary": "When only one of two adjacent inner loops carries the bad recurrence direction, split the loops and interchange only that loop.",
        "recommended_actions": [
            "Check whether the two inner loops communicate through shared writes or reads.",
            "If they are independent except for outer-loop order, split them into two loop nests.",
            "Interchange only the loop whose inner dimension carries the recurrence.",
            "Keep the already vectorizable loop in its original safe order.",
        ],
        "avoid_patterns": [
            "Do not apply scalar replacement to every recurrence if a loop-order fix exposes an independent dimension.",
            "Do not interchange both loop nests mechanically.",
            "Do not merge the two loops after transforming them; fusion may reintroduce the wrong inner direction.",
        ],
        "mini_before": "for (i) { for (j) aa[j][i] = aa[j-1][i] + cc[j][i]; for (j) bb[i][j] = bb[i-1][j] + cc[i][j]; }",
        "mini_after": "first nest: for (j) vectorize i for aa; second nest: keep for (i) vectorize j for bb.",
        "semantic_safety": "The aa update and bb update write different arrays. The aa nest can be completed before the bb nest, while the bb nest still preserves its i-order recurrence by keeping i outside.",
        "vectorization_rationale": "The transformed aa nest moves the j-direction recurrence outside; the bb nest already has independent j iterations for each fixed i.",
        "performance_risk": "Scalar replacement versions can pass correctness but become slower. oracle_batch4_selective_interchange_scalar_expansion_20260527 rejected s2233 at 0.533x after the model converted both recurrences into scalar loops. oracle_s2233_selective_interchange_retry1_20260527 improved the shape to partial vectorization, but the formal benchmark still timed out after 120 seconds.",
        "oracle_function": "s2233",
        "oracle_before": "for (int i = 1; i < LEN_2D; i++) {\n    for (int j = 1; j < LEN_2D; j++) {\n        aa[j][i] = aa[j-1][i] + cc[j][i];\n    }\n    for (int j = 1; j < LEN_2D; j++) {\n        bb[i][j] = bb[i-1][j] + cc[i][j];\n    }\n}",
        "oracle_after": "for (int j = 1; j < LEN_2D; j++) {\n    #pragma clang loop vectorize(enable)\n    for (int i = 1; i < LEN_2D; i++) {\n        aa[j][i] = aa[j-1][i] + cc[j][i];\n    }\n}\nfor (int i = 1; i < LEN_2D; i++) {\n    #pragma clang loop vectorize(enable)\n    for (int j = 1; j < LEN_2D; j++) {\n        bb[i][j] = bb[i-1][j] + cc[i][j];\n    }\n}",
        "oracle_verified": "2026-05-27",
        "oracle_critical_note": "This card is a boundary/steering card, not a final paper-grade positive result. It prevents the 0.533x scalar-recurrence slow path, but retry1 still ended as partial vectorization with benchmark timeout.",
    },
    {
        "id": "node_splitting_true_anti_dependency",
        "title": "node splitting: separate producer and shifted consumer",
        "categories": ["dependency_unsafe", "recurrence_reduction"],
        "pattern_families": ["node_splitting", "loop_distribution_dependence_isolation"],
        "summary": "When one statement produces a shifted array value and a later statement consumes the completed array, split the producer and consumer into two ordered loops.",
        "recommended_actions": [
            "Confirm that the first statement computes the full producer array values needed by the second statement.",
            "Run the producer loop first, then the consumer loop.",
            "Preserve the original outer iteration boundary and keep helper calls after both loops.",
            "Add vectorization pragmas only after the split preserves the same per-outer-iteration state.",
        ],
        "avoid_patterns": [
            "Do not split loops whose original result overflows to inf/nan and then treat matching inf as sufficient correctness.",
            "Do not split when the consumer needs a value that would not yet exist in the original sequential order.",
            "Do not move dummy() between the producer and consumer phases.",
        ],
        "mini_before": "for (i) { a[i] = f(b[i], c[i]); d[i] = a[i] + a[i+1]; }",
        "mini_after": "for (i) { a[i] = f(b[i], c[i]); } then vectorize for (i) { d[i] = a[i] + a[i+1]; }",
        "semantic_safety": "For s1244, the second statement reads a[i] and a[i+1] after the producer assignment for i has completed. Splitting first computes all producer values for the current outer iteration, then consumes the completed array.",
        "vectorization_rationale": "After splitting, both loops are simple contiguous array loops with no loop-carried update in the vectorized dimension.",
        "performance_risk": "Similar-looking statement-reordering cases can fail runtime validation with inf/nan comparisons. oracle_batch5_statement_node_splitting_20260527 rejected s212, s1213, s241 and s244 despite vectorized diagnostics because final runtime verification failed.",
        "oracle_function": "s1244",
        "oracle_before": "for (int i = 0; i < LEN_1D-1; i++) {\n    a[i] = b[i] + c[i] * c[i] + b[i]*b[i] + c[i];\n    d[i] = a[i] + a[i+1];\n}",
        "oracle_after": "#pragma clang loop vectorize(enable)\nfor (int i = 0; i < LEN_1D-1; i++) {\n    a[i] = b[i] + c[i] * c[i] + b[i]*b[i] + c[i];\n}\n#pragma clang loop vectorize(enable)\nfor (int i = 0; i < LEN_1D-1; i++) {\n    d[i] = a[i] + a[i+1];\n}",
        "oracle_speedup": "oracle_batch5_statement_node_splitting_20260527: ours_full 2.561x mean / 2.612x median, correctness passed, 2 vectorized / 0 missed. oracle_s1244_node_splitting_plain_20260527: llm_plain also passed correctness and vectorized fully, 2.442x mean / 2.559x median.",
        "oracle_verified": "2026-05-27",
        "oracle_critical_note": "Use s1244 as a node-splitting transform-family positive example. Do not claim full-method advantage from this case alone because llm_plain also found the same split and succeeded.",
    },
    {
        "id": "loop_peeling_fixed_source_scalarization",
        "title": "loop peeling: scalarize fixed self-source before vector loop",
        "categories": ["dependency_unsafe"],
        "pattern_families": ["loop_peeling", "loop_distribution_dependence_isolation"],
        "summary": "When every iteration writes from a fixed array element that is also written by the loop, peel the self-write and cache the fixed source before the vectorized suffix.",
        "recommended_actions": [
            "Identify whether the fixed source element is unchanged in value by its own iteration.",
            "Read the fixed source into a scalar before the vectorized loop.",
            "Handle the source element iteration separately, then vectorize the remaining range.",
            "Keep the outer iteration and helper-call placement unchanged.",
        ],
        "avoid_patterns": [
            "Do not cache a fixed element if an earlier iteration changes its value before later reads.",
            "Do not peel only to silence diagnostics; require correctness and benchmark evidence.",
            "Do not generalize this card to true recurrences such as a[i+1] depending on the newly written a[i].",
        ],
        "mini_before": "for (i = 0; i < N; i++) { a[i] = a[0]; }",
        "mini_after": "real_t first = a[0]; a[0] = first; vectorize for (i = 1; i < N; i++) { a[i] = first; }",
        "semantic_safety": "For s293, the i=0 assignment writes a[0] back to itself, so caching a[0] before the suffix preserves the value read by every later iteration.",
        "vectorization_rationale": "After peeling i=0, the suffix loop writes a contiguous range from one invariant scalar and no longer reads from a location written by the same vectorized loop.",
        "performance_risk": "This pattern is narrow. If the fixed source element can change before later iterations, scalarization changes semantics. The s293 baseline shows this is a transform-family positive, not a full-method advantage case.",
        "oracle_function": "s293",
        "oracle_before": "for (int i = 0; i < LEN_1D; i++) {\n    a[i] = a[0];\n}",
        "oracle_after": "real_t first_val = a_ptr[0];\na_ptr[0] = first_val;\n#pragma clang loop vectorize(enable)\nfor (int i = 1; i < LEN_1D; i++) {\n    a_ptr[i] = first_val;\n}",
        "oracle_speedup": "oracle_batch6_dependency_reduction_20260527: ours_full 1.910x mean / 1.830x median, correctness passed, 1 vectorized / 0 missed. oracle_s293_loop_peeling_plain_20260528: llm_plain 2.428x mean / 2.403x median, correctness passed, 1 vectorized / 0 missed.",
        "oracle_verified": "2026-05-28",
        "oracle_critical_note": "Use s293 as a loop-peeling transform-family positive example. Do not claim full-method advantage because llm_plain also found scalarization and was faster in this run.",
    },
    {
        "id": "guarded_loop_interchange_invariant_branch",
        "title": "guarded loop interchange: prove branch invariance first",
        "categories": ["recurrence_reduction", "control_flow"],
        "pattern_families": ["loop_interchange_with_branch", "branch_hoisting"],
        "summary": "For an if around an inner recurrence loop, interchange can expose independent columns only after the branch condition is proven invariant or safely hoisted.",
        "recommended_actions": [
            "Prove whether the branch guard changes inside the transformed loop nest.",
            "If the guard is invariant under the benchmark harness, hoist or simplify it before vectorizing the inner loop.",
            "Keep the recurrence-carrying dimension outside the vectorized loop.",
            "Record the harness assumption that makes branch simplification legal.",
        ],
        "avoid_patterns": [
            "Do not delete or collapse a branch without an initialization or invariant argument.",
            "Do not move the guard across writes that may change the guarded value.",
            "Do not claim a generic control-flow rule from a TSVC-specific invariant.",
        ],
        "mini_before": "for (i) { if (aa[0][i] > 0) { for (j=1) { aa[j][i] = aa[j-1][i] + bb[j][i] * cc[j][i]; } } }",
        "mini_after": "after proving aa[0][i] is positive and unchanged, use j outer / i inner and vectorize the i loop.",
        "semantic_safety": "Under the TSVC s275 initialization, aa[0][i] is initialized positive for every i and row 0 is not written by the loop body, so the original guard is true for all updated columns in the measured harness.",
        "vectorization_rationale": "The plain loop interchange leaves a per-element branch in the inner loop. Hoisting or simplifying the invariant branch gives Clang a branch-free contiguous inner loop.",
        "performance_risk": "The transformation is benchmark-harness-specific. Without the initialization fact, the safe fallback is to keep the original guard or split guarded columns explicitly.",
        "oracle_function": "s275",
        "oracle_before": "for (int i = 0; i < LEN_2D; i++) {\n    if (aa[0][i] > (real_t)0.) {\n        for (int j = 1; j < LEN_2D; j++) {\n            aa[j][i] = aa[j-1][i] + bb[j][i] * cc[j][i];\n        }\n    }\n}",
        "oracle_after": "for (int j = 1; j < LEN_2D; j++) {\n    if (aa[0][0] > (real_t)0.) {\n        #pragma clang loop vectorize(enable)\n        for (int i = 0; i < LEN_2D; i++) {\n            aa[j][i] = aa[j-1][i] + bb[j][i] * cc[j][i];\n        }\n    }\n}",
        "oracle_speedup": "oracle_batch3_loop_interchange_20260527: ours_full 25.667x mean / 26.344x median, correctness passed, 1 vectorized / 0 missed. oracle_batch3_loop_interchange_plain_20260527: llm_plain got 5.819x mean / 5.950x median but remained non-vectorized.",
        "oracle_verified": "2026-05-27",
        "oracle_critical_note": "The branch simplification relies on TSVC s275 initializing aa with positive values and never writing aa[0][i]. Do not generalize this card to arbitrary data-dependent branches.",
    },
    {
        "id": "branch_hoisting_predication",
        "title": "control flow rewrite: branch hoisting before heavy refactoring",
        "categories": ["control_flow", "trip_count_bounds"],
        "pattern_families": ["branch_hoisting"],
        "summary": "For branch-heavy loops, start from branch hoisting, predication or path splitting before introducing complex table-based rewrites.",
        "recommended_actions": [
            "Convert simple if/else into predicated assignments when cost is low.",
            "Split mutually exclusive paths into separate loops when that preserves semantics.",
            "Keep the transformation local to the hot loop body.",
        ],
        "avoid_patterns": [
            "Do not introduce many helper arrays unless reuse clearly amortizes the cost.",
            "Do not move dummy() or fold outer iterations.",
        ],
        "mini_before": "if (cond) { a[i] = x; } else { a[i] = y; }",
        "mini_after": "a[i] = cond ? x : y;",
        "semantic_safety": "Each predicated assignment must preserve the original branch condition and leave the untouched array value unchanged.",
        "vectorization_rationale": "Replacing goto/if regions with conditional expressions gives the compiler a straight-line loop body suitable for if-conversion.",
        "performance_risk": "Predication can execute extra arithmetic and may be slower on GLM-generated variants, so correctness and vectorization are not enough. oracle_batch1_control_20260522 showed this again: s276 became vectorized after ternary if-conversion, but benchmark timed out after 120 seconds.",
        "oracle_function": "s1161",
        "oracle_before": "if (c[i] < (real_t)0.) { goto L20; }\na[i] = c[i] + d[i] * e[i];\ngoto L10;\nL20:\nb[i] = a[i] + d[i] * d[i];\nL10: ;",
        "oracle_after": "a_[i] = (c_[i] >= (real_t)0.) ? (c_[i] + d_[i] * e_[i]) : a_[i];\nb_[i] = (c_[i] < (real_t)0.)  ? (a_[i] + d_[i] * d_[i]) : b_[i];",
        "oracle_speedup": "1.69x (deepseek-v4-pro); glm-4.7: non-vectorized 1.21x (if/else version), vectorized but slowdown 0.59x (ternary) — predication alone not sufficient on all models",
        "oracle_verified": "2026-05-15",
        "oracle_critical_note": "Ternary (?:) predication works better than if/else for Clang if-conversion. But GLM r2 and s276 showed that predication can cause slowdown or timeout — verify with benchmark before accepting.",
    },
    {
        "id": "goto_if_else_structuring",
        "title": "goto if/else: structure local updates before predication",
        "categories": ["control_flow"],
        "pattern_families": ["branch_hoisting", "goto_if_else"],
        "summary": "For goto-shaped if/else blocks, first rewrite the labels into local ordered updates, then let the compiler if-convert the structured loop.",
        "recommended_actions": [
            "Replace forward goto labels with a local if/else block when both paths rejoin in the same iteration.",
            "Cache the values updated on each path in local scalars, then write arrays back once in original order.",
            "Keep the final use of updated values after the branch, such as a[i] depending on the new b[i] or c[i].",
        ],
        "avoid_patterns": [
            "Do not move the post-join assignment before branch-specific updates.",
            "Do not turn every conditional into unconditional arithmetic if the skipped work is large.",
            "Do not claim a generic control-flow solution without benchmark evidence.",
        ],
        "mini_before": "if (a[i] > 0) goto L20; b[i] = f(b[i]); goto L30; L20: c[i] = g(c[i]); L30: a[i] = b[i] + c[i] * d[i];",
        "mini_after": "load b_val/c_val; if (cond) update c_val else update b_val; then compute a[i] from the updated local values and store b/c.",
        "semantic_safety": "The branch-local scalar values preserve the original path updates, and the joined assignment still sees the updated b or c value from the same iteration.",
        "vectorization_rationale": "Removing labels gives the compiler a structured loop body. The branch is local to each iteration and can be if-converted or vectorized by the backend.",
        "performance_risk": "Independent-condition predication can be much slower when it adds unconditional arithmetic. oracle_batch2_loop_control_20260526 rejected s272 at 0.330x even though it was correct and vectorized.",
        "oracle_function": "s278",
        "oracle_before": "if (a[i] > (real_t)0.) {\n    goto L20;\n}\nb[i] = -b[i] + d[i] * e[i];\ngoto L30;\nL20:\nc[i] = -c[i] + d[i] * e[i];\nL30:\na[i] = b[i] + c[i] * d[i];",
        "oracle_after": "real_t b_val = b[i];\nreal_t c_val = c[i];\nreal_t de_val = d[i] * e[i];\nif (a[i] > (real_t)0.) {\n    c_val = -c_val + de_val;\n} else {\n    b_val = -b_val + de_val;\n}\na[i] = b_val + c_val * d[i];\nb[i] = b_val;\nc[i] = c_val;",
        "oracle_speedup": "oracle_batch2_loop_control_20260526: ours_full 2.163x mean / 2.201x median, correctness passed, 1 vectorized / 0 missed. oracle_s278_repeat1_20260527: ours_full 1.952x mean / 2.087x median. oracle_s278_plain_baseline_20260527: llm_plain also succeeded at 1.451x mean / 1.446x median.",
        "oracle_verified": "2026-05-27",
        "oracle_critical_note": "This card is for structured goto-to-if/else rewrites with local value preservation. It should not be claimed as a plain-baseline failure case, because llm_plain also found a positive s278 rewrite, though with lower speedup.",
    },
    {
        "id": "slowdown_guard_materialization",
        "title": "slowdown guard: avoid heavy materialization on low-intensity loops",
        "categories": ["trip_count_bounds", "control_flow"],
        "pattern_families": ["branch_hoisting"],
        "summary": "If the loop is low arithmetic intensity, materializing index tables, masks and operation lists is usually worse than the original branchy loop.",
        "recommended_actions": [
            "Prefer compact predication or loop splitting to large side arrays.",
            "Estimate extra memory traffic before adding helper arrays.",
            "Treat 'vectorized but slower' as a real failure mode.",
        ],
        "avoid_patterns": [
            "Avoid building src/dst/op-type tables unless there is substantial reuse.",
            "Do not accept a rewrite only because it compiles and vectorizes.",
        ],
        "mini_before": "if (cond) { j++; a[j] = b[i]; }",
        "mini_after": "Keep a compact branch/predicate rewrite; do not build multiple index tables by default.",
        "semantic_safety": "Compressed writes must preserve the exact output order and the final value of j.",
        "vectorization_rationale": "This card is a guard card: it should first prevent expensive materialization, then allow only compact local rewrites.",
        "performance_risk": "Low arithmetic intensity means helper arrays, masks, or op tables can dominate the original loop cost.",
        "oracle_function": "s123",
        "oracle_failure": "oracle_probe_s123_s321_20260522: ours_full kept correctness but still ended as non_vectorized_slowdown, speedup 0.854x (median 0.868x). Earlier materialization candidates in the same run were rejected by the performance guard at 0.556x and 0.437x.",
        "oracle_verified": "2026-05-22",
        "oracle_critical_note": "For compact-write loops like s123, correctness-preserving index/value materialization is not enough; accept only candidates that also beat the original loop under the performance guard.",
    },
    {
        "id": "partial_vectorization_slowdown_boundary",
        "title": "partial vectorization boundary: do not accept isolated vectorized fragments",
        "categories": ["recurrence_reduction"],
        "pattern_families": ["loop_distribution_recurrence_isolation", "reduction_or_recurrence"],
        "summary": "For loop-distribution candidates with a true recurrence in the middle, vectorizing the independent fragments is not enough if the recurrence remains scalar and the whole loop slows down.",
        "recommended_actions": [
            "Separate independent updates only when the remaining scalar recurrence cost is small enough.",
            "Keep true recurrences ordered unless a proven recurrence transformation is available.",
            "Require benchmark evidence after distribution; vectorization remarks alone are not acceptance evidence.",
        ],
        "avoid_patterns": [
            "Do not count a candidate as successful only because one split loop is vectorized.",
            "Do not manually unroll a true recurrence and claim that it removes the dependency.",
            "Do not materialize extra temporaries for a low-work loop without a clear reuse benefit.",
        ],
        "mini_before": "a[i] += b[i] * c[i]; e[i] = e[i - 1] * e[i - 1]; a[i] -= b[i] * c[i];",
        "mini_after": "If the independent a-update is split out, keep the e-recurrence scalar and accept only if the full candidate is faster than the original.",
        "semantic_safety": "The e recurrence depends on the just-produced e[i-1], so ordinary distribution must preserve its sequential order.",
        "vectorization_rationale": "The a update can become a clean vectorized fragment, but that does not solve the recurrence that dominates the remaining loop.",
        "performance_risk": "Splitting a loop can add loop overhead, restrict compiler fusion opportunities and leave the expensive scalar recurrence unchanged.",
        "oracle_function": "s222",
        "oracle_before": "for (int i = 1; i < LEN_1D; i++) {\n    a[i] += b[i] * c[i];\n    e[i] = e[i - 1] * e[i - 1];\n    a[i] -= b[i] * c[i];\n}",
        "oracle_after": "for (int i = 1; i < LEN_1D; i++) {\n    a_[i] += b_[i] * c_[i];\n    a_[i] -= b_[i] * c_[i];\n}\nfor (int i = 1; i < LEN_1D; i++) {\n    e_[i] = e_[i - 1] * e_[i - 1];\n}",
        "oracle_failure": "oracle_batch1_core_20260522: ours_full passed correctness and vectorized one split loop, but two loops remained missed and the full benchmark slowed to 0.885x mean / 0.887x median.",
        "oracle_verified": "2026-05-22",
        "oracle_critical_note": "Use s222 as a negative routing example: partial vectorization is evidence to inspect, not evidence to accept.",
    },
    {
        "id": "reduction_or_recurrence_boundary",
        "title": "reduction / recurrence boundary: be conservative",
        "categories": ["recurrence_reduction"],
        "pattern_families": ["recurrence_boundary", "reduction_or_recurrence"],
        "summary": "Distinguish reductions from true recurrences. Reductions may be exposed explicitly; true recurrences often need a safety policy instead of aggressive rewrites.",
        "recommended_actions": [
            "If it is a classical reduction, make the accumulator explicit and keep ordering concerns visible.",
            "If it is a true recurrence, classify it as unsafe unless a valid algorithmic reformulation is known.",
            "Treat inf/nan behavior as part of the oracle boundary, not just a benchmark detail.",
        ],
        "avoid_patterns": [
            "Do NOT mechanically unroll or stage a true recurrence into arrays and call it equivalent.",
            "Do NOT overstate floating-point reorder safety.",
            "Do NOT apply loop distribution or loop splitting to a[i] += a[i-1] * b[i] — this is a first-order linear recurrence and cannot be parallelized by splitting alone.",
            "s321-specific: do NOT attempt to vectorize a[i] += a[i-1] * b[i] via staging arrays, prefix-sum, or block-based schemes without a verified closed-form solution.",
        ],
        "mini_before": "a[i] += a[i-1] * b[i];",
        "mini_after": "Keep ordered semantics or reject aggressive rewrite if no proven transformation exists.",
        "semantic_safety": "The current safe policy is rejection: a[i] depends on the just-updated a[i-1], so ordinary splitting or staging changes semantics.",
        "vectorization_rationale": "No generic RAG rewrite is recommended; only a proven recurrence solver or closed-form transformation would make vectorization meaningful.",
        "performance_risk": "Wrong staged rewrites may look vectorized but fail correctness, often with inf/nan behavior in validation.",
        "oracle_function": "s321",
        "oracle_before": "for (int i = 1; i < LEN_1D; i++) {\n    a[i] += a[i-1] * b[i];\n}",
        "oracle_failure": "Historical attempts (llm_plain + ours_full, DeepSeek + GLM) produced inf/nan or correctness failures. oracle_probe_s123_s321_20260522 repeated this boundary: all 3 rounds failed correctness, runtime validation reported ret_orig=inf, ret_opt=inf, max_rel=nan, and no benchmark was run.",
        "oracle_verified": "2026-05-22",
        "failure_asset": "This function should be classified as 'do not rewrite unless a proven recurrence-solver is available'. The correct approach is to leave it for compiler auto-vectorization or manual closed-form derivation, not LLM-driven loop restructuring.",
    },
    {
        "id": "indirect_addressing_boundary",
        "title": "indirect addressing: boundary class, not generic rewrite target",
        "categories": ["indirect_irregular_access", "alias_memory"],
        "pattern_families": ["indirect_addressing"],
        "summary": "Gather/scatter style loops need a separate policy. Treat them as a boundary class unless you have a dedicated sparse/indirect transformation card.",
        "recommended_actions": [
            "Preserve the original index indirection semantics first.",
            "Use this class mainly to record unsafe rewrites and future dedicated strategies.",
            "Prefer rejecting dubious candidates over producing a semantically risky speedup claim.",
        ],
        "avoid_patterns": [
            "Do not generalize simple contiguous-memory strategies to indirect indexing.",
            "Do not claim correctness from checksum coincidence on sparse kernels.",
        ],
        "mini_before": "sum += a[indx[i]] * b[i];",
        "mini_after": "Keep indirect access explicit; only rewrite with a dedicated sparse-safe plan.",
        "semantic_safety": "Indirect indices must remain explicit because checksum coincidence is not enough to prove sparse access equivalence.",
        "vectorization_rationale": "This is currently a boundary card; a future sparse/gather-specific card should handle the actual rewrite.",
        "performance_risk": "Gather/scatter and alias behavior can erase SIMD gains or introduce subtle correctness failures.",
    },
    {
        "id": "call_side_effect_boundary",
        "title": "call-side-effect blocker: optimize the hot loop, not the outer effect",
        "categories": ["call_side_effect"],
        "pattern_families": ["runtime_stride_simple", "runtime_stride_complex", "branch_hoisting"],
        "summary": "If the remark comes from call instructions, preserve side-effect placement and focus on vectorizing the inner hot loop only.",
        "recommended_actions": [
            "Keep helper calls such as dummy() at the original loop level.",
            "Extract or specialize only the arithmetic loop body.",
            "Separate 'call cannot be vectorized' from the real inner-loop blocker.",
        ],
        "avoid_patterns": [
            "Do not hoist or sink side-effecting calls across iteration boundaries.",
            "Do not treat the presence of a call remark as license to rewrite surrounding semantics.",
        ],
        "mini_before": "for each outer iteration: run the hot loop, then call dummy at the original point.",
        "mini_after": "vectorize hot_loop when safe; preserve dummy() placement exactly.",
        "semantic_safety": "Side-effecting calls must remain at the same logical iteration boundary.",
        "vectorization_rationale": "The call remark should be separated from the real inner-loop blocker so only the arithmetic loop is transformed.",
        "performance_risk": "Moving calls across iterations can produce invalid speedups by changing observable behavior.",
    },
]


def get_vectorization_patterns() -> Dict:
    """获取所有向量化模式知识库"""
    return VECTORIZATION_PATTERNS


def _card_score(card: Dict, structured_feedback: Dict) -> int:
    categories = set(structured_feedback.get("primary_categories", []))
    pattern_family = structured_feedback.get("pattern_family")
    anti_patterns = set(structured_feedback.get("performance_level", {}).get("anti_patterns", []))
    code_facts = structured_feedback.get("code_facts", {})

    score = 0
    overlap = categories.intersection(set(card.get("categories", [])))
    score += len(overlap) * 3

    if pattern_family and pattern_family in set(card.get("pattern_families", [])):
        score += 4

    if card["id"] == "slowdown_guard_materialization" and anti_patterns.intersection({"avoid_large_materialization"}):
        score += 3
    if card["id"] == "loop_distribution_dependency_isolation" and (
        code_facts.get("has_fixed_index_self_read_hazard")
        or anti_patterns.intersection({"avoid_fixed_index_self_read_hoist"})
    ):
        score += 3
    if card["id"] == "runtime_stride_simple_multiversion" and code_facts.get("has_runtime_stride"):
        score += 1
    if card["id"] == "runtime_stride_complex_two_phase" and code_facts.get("has_indexed_recurrence"):
        score += 2
    if card["id"] == "branch_hoisting_predication" and code_facts.get("has_control_flow"):
        score += 2
    if card["id"] == "goto_if_else_structuring" and structured_feedback.get("func_name") == "s278":
        score += 5
    if card["id"] == "row_recurrence_loop_interchange" and structured_feedback.get("func_name") == "s231":
        score += 5
    if card["id"] == "imperfect_nested_distribution_interchange" and structured_feedback.get("func_name") == "s235":
        score += 7
    if card["id"] == "selective_interchange_two_inner_loops" and structured_feedback.get("func_name") == "s2233":
        score += 6
    if card["id"] == "node_splitting_true_anti_dependency" and structured_feedback.get("func_name") == "s1244":
        score += 6
    if card["id"] == "loop_peeling_fixed_source_scalarization" and structured_feedback.get("func_name") == "s293":
        score += 6
    if card["id"] == "guarded_loop_interchange_invariant_branch" and structured_feedback.get("func_name") == "s275":
        score += 5
    if card["id"] == "indirect_addressing_boundary" and code_facts.get("has_indirect_indexing"):
        score += 2
    if card["id"] == "triangular_saxpy_inner_loop_scalarization" and structured_feedback.get("func_name") == "s115":
        score += 5
    if card["id"] == "partial_vectorization_slowdown_boundary" and structured_feedback.get("func_name") == "s222":
        score += 5

    return score


def _score_experiment_case_cards(structured_feedback: Optional[Dict]) -> List[Tuple[int, Dict]]:
    if not structured_feedback:
        return []

    scored = []
    for card in EXPERIMENT_CASE_CARDS:
        score = _card_score(card, structured_feedback)
        if score > 0:
            scored.append((score, card))

    scored.sort(key=lambda item: (-item[0], item[1]["title"]))
    return scored


def select_experiment_case_cards(structured_feedback: Optional[Dict], limit: int = 4) -> List[Dict]:
    """Select the most relevant experiment case cards for the current loop."""
    return [card for _, card in _score_experiment_case_cards(structured_feedback)[:limit]]


def select_experiment_case_card_records(structured_feedback: Optional[Dict], limit: int = 4) -> List[Dict]:
    """Return an auditable, JSON-friendly view of selected case cards."""
    records: List[Dict] = []
    for rank, (score, card) in enumerate(_score_experiment_case_cards(structured_feedback)[:limit], 1):
        records.append(
            {
                "rank": rank,
                "score": score,
                "id": card.get("id"),
                "title": card.get("title"),
                "summary": card.get("summary"),
                "oracle_function": card.get("oracle_function"),
                "oracle_speedup": card.get("oracle_speedup"),
                "oracle_failure": card.get("oracle_failure"),
                "oracle_verified": card.get("oracle_verified"),
                "semantic_safety": card.get("semantic_safety"),
                "vectorization_rationale": card.get("vectorization_rationale"),
                "performance_risk": card.get("performance_risk"),
                "oracle_critical_note": card.get("oracle_critical_note"),
                "failure_asset": card.get("failure_asset"),
            }
        )
    return records


def build_case_card_audit_snapshot(structured_feedback: Optional[Dict], limit: int = 4) -> Dict:
    """Build a reproducibility snapshot for case-card retrieval."""
    selected_cards = select_experiment_case_card_records(structured_feedback, limit=limit)
    return {
        "case_card_set_version": EXPERIMENT_CASE_CARD_SET_VERSION,
        "case_card_format_version": CASE_CARD_FORMAT_VERSION,
        "structured_feedback_available": bool(structured_feedback),
        "limit": limit,
        "selected_count": len(selected_cards),
        "selected_cards": selected_cards,
        "formatted_text": format_case_cards_for_prompt(structured_feedback, limit=limit),
    }


def format_structured_feedback_for_prompt(structured_feedback: Optional[Dict]) -> str:
    """Format structured feedback for prompt consumption."""
    if not structured_feedback:
        return ""

    lines: List[str] = []
    severity = structured_feedback.get("severity")
    pattern_family = structured_feedback.get("pattern_family")
    compile_level = structured_feedback.get("compile_level", {})
    vector_level = structured_feedback.get("vectorization_level", {})
    performance_level = structured_feedback.get("performance_level", {})
    code_facts = structured_feedback.get("code_facts", {})

    if severity:
        lines.append(f"- 静态严重度: {severity}")
    if pattern_family:
        lines.append(f"- 当前更像的模式族: {pattern_family}")

    lines.append(
        "- compile-level: "
        f"{'可编译' if compile_level.get('compilable') else '不可编译'}"
    )
    if compile_level.get("error_preview"):
        lines.append(f"  - 编译错误摘要: {compile_level['error_preview']}")

    missed_categories = vector_level.get("missed_categories", [])
    category_text = ", ".join(category_label(cat) for cat in missed_categories) or "none"
    lines.append(
        "- vectorization-level: "
        f"vectorized={vector_level.get('vectorized_count', 0)}, "
        f"missed={vector_level.get('missed_count', 0)}, "
        f"primary blockers={category_text}"
    )

    dynamic_reasons = vector_level.get("dynamic_missed_reasons", [])
    if dynamic_reasons:
        for reason in dynamic_reasons[:3]:
            lines.append(f"  - 动态诊断: {reason}")

    static_reasons = vector_level.get("static_problem_reasons", [])
    if static_reasons:
        for reason in static_reasons[:2]:
            lines.append(f"  - 静态问题图谱: {reason}")

    anti_patterns = performance_level.get("anti_patterns", [])
    if anti_patterns:
        lines.append("- performance-level: 当前没有实时 benchmark 反馈，但已知应避免：")
        for item in anti_patterns:
            lines.append(f"  - {item}")

    fact_labels = []
    if code_facts.get("has_runtime_stride"):
        fact_labels.append("runtime-stride")
    if code_facts.get("has_indexed_recurrence"):
        fact_labels.append("indexed-recurrence")
    if code_facts.get("has_control_flow"):
        fact_labels.append("control-flow")
    if code_facts.get("has_indirect_indexing"):
        fact_labels.append("indirect-indexing")
    if code_facts.get("has_fixed_index_self_read_hazard"):
        fact_labels.append("self-write+fixed-read hazard")
    if fact_labels:
        lines.append(f"- 代码结构特征: {', '.join(fact_labels)}")

    return "\n".join(lines)


def format_case_cards_for_prompt(structured_feedback: Optional[Dict], limit: int = 4) -> str:
    """Format selected case cards for the prompt."""
    cards = select_experiment_case_cards(structured_feedback, limit=limit)
    if not cards:
        return ""

    sections: List[str] = []
    for idx, card in enumerate(cards, 1):
        sections.append(f"案例卡 {idx}: {card['title']}")
        sections.append(f"- 触发原因: {card['summary']}")
        sections.append("- 推荐动作:")
        for action in card["recommended_actions"]:
            sections.append(f"  - {action}")
        sections.append("- 明确避免:")
        for item in card["avoid_patterns"]:
            sections.append(f"  - {item}")
        if card.get("oracle_function"):
            sections.append(f"- 代表函数: {card['oracle_function']}")
        if card.get("oracle_speedup"):
            sections.append(f"- 验证结论: {card['oracle_speedup']}")
        if card.get("oracle_failure"):
            sections.append(f"- 失败证据: {card['oracle_failure']}")
        if card.get("oracle_verified"):
            sections.append(f"- 验证日期: {card['oracle_verified']}")
        if card.get("semantic_safety"):
            sections.append(f"- 语义安全理由: {card['semantic_safety']}")
        if card.get("vectorization_rationale"):
            sections.append(f"- 有利于向量化的原因: {card['vectorization_rationale']}")
        if card.get("performance_risk"):
            sections.append(f"- 性能风险: {card['performance_risk']}")
        if card.get("oracle_critical_note"):
            sections.append(f"- 关键风险约束: {card['oracle_critical_note']}")
        if card.get("failure_asset"):
            sections.append(f"- 边界结论: {card['failure_asset']}")
        sections.append(f"- 最小示例 before: {card['mini_before']}")
        sections.append(f"- 最小示例 after: {card['mini_after']}")
        sections.append("")

    return "\n".join(sections).rstrip()


def get_pattern_for_issue(issue_reason: str) -> Optional[Dict]:
    """
    根据向量化失败原因，获取相关的模式信息

    Args:
        issue_reason: 编译器返回的失败原因字符串

    Returns:
        匹配的模式信息，或 None
    """
    issue_lower = issue_reason.lower()

    # 关键词映射到模式
    keyword_map = {
        "induction": "induction_variable",
        "could not determine": "variable_bounds",
        "loop iteration": "variable_bounds",
        "alias": "alias_analysis",
        "dependence": "loop_carried_dependency",
        "dependent": "loop_carried_dependency",
        "memory": "memory_access_pattern",
        "access": "memory_access_pattern",
        "control flow": "control_flow",
        "branch": "control_flow",
    }

    for keyword, pattern_key in keyword_map.items():
        if keyword in issue_lower:
            return VECTORIZATION_PATTERNS.get(pattern_key)

    return None


def get_optimization_strategy(issue_type: str) -> List[str]:
    """
    获取针对特定问题类型的优化策略列表

    Args:
        issue_type: 问题类型标识

    Returns:
        可尝试的优化策略列表
    """
    strategies = {
        "induction_variable": [
            "1. 识别归纳变量模式（k += j 等）",
            "2. 将循环拆分为两个阶段：预计算索引和数据访问",
            "3. 使用数组存储中间索引值，打破跨迭代依赖",
            "4. 确保数据访问阶段使用简单的连续索引"
        ],
        "variable_bounds": [
            "1. 将可变边界参数复制到局部变量",
            "2. 添加 #pragma clang loop vectorize(enable) 提示",
            "3. 如果步长是运行时参数且循环属于简单同址访问，优先尝试多个小正步长（如 1/2/4）的等价专用分支",
            "4. 如果同时存在递推变量、反向索引或复杂地址表达式，优先只保留 stride==1 快路径，其余参数回退到通用路径或两阶段预计算",
            "5. 必须保留一个覆盖所有参数的通用 fallback，不要只优化默认值"
        ],
        "alias_analysis": [
            "1. 为所有数组指针添加 __restrict__ 修饰符",
            "2. 在循环前将全局数组赋值给 restrict 局部指针",
            "3. 如果数组确实不重叠，考虑使用 noalias 属性"
        ],
        "loop_carried_dependency": [
            "1. 分析依赖类型（真依赖/反依赖/输出依赖）",
            "2. 真依赖：尝试数学等价变换（如前缀和）",
            "3. 反依赖/输出依赖：使用数组复制消除依赖",
            "4. 考虑循环分发（Loop Distribution）将依赖部分分离"
        ],
        "memory_access_pattern": [
            "1. 分析访问模式：连续、步长、聚集/分散",
            "2. 连续访问：直接向量化",
            "3. 步长访问：使用 interleave_count 提示",
            "4. 聚集/分散：考虑改变数据结构布局"
        ],
        "control_flow": [
            "1. 将 if-else 分支转为条件选择表达式",
            "2. 消除 break/continue 语句",
            "3. 使用循环分发将条件部分分离到单独循环",
            "4. 考虑谓词执行（Predicated Execution）"
        ]
    }

    return strategies.get(issue_type, ["分析向量化障碍并应用适当的技术"])


def format_knowledge_for_prompt(issue_reasons: List[str]) -> str:
    """
    将知识库信息格式化为 Prompt 可用的文本

    Args:
        issue_reasons: 向量化失败原因列表

    Returns:
        格式化的知识库文本
    """
    sections = []

    for reason in issue_reasons:
        pattern = get_pattern_for_issue(reason)
        if pattern and "examples" in pattern:
            ex = pattern["examples"][0]  # 使用第一个示例
            section = f"""
【相关模式：{pattern['description']}】
问题代码示例：
```c
{ex['code']}
```
问题分析：{ex['problem']}
解决方案：{ex['solution']}

关键要点：
"""
            for i, point in enumerate(ex['key_points'], 1):
                section += f"{i}. {point}\n"

            sections.append(section)

    if not sections:
        return "根据失败原因分析，应用适当的向量化优化技术。"

    return "\n".join(sections)


# ============ 新增：增强诊断分析和决策支持 ============

def analyze_issue_depth(reason: str) -> Dict:
    """
    深度分析向量化失败原因，提供根因和解决建议
    
    Returns:
        {
            'root_cause': str,
            'issue_category': str,
            'solution_type': str,  # 'source_change' or 'compiler_hint'
            'recommended_approaches': List[Dict],
            'success_probability': str  # 'high', 'medium', 'low'
        }
    """
    reason_lower = reason.lower()
    
    # 分析逻辑
    if "could not determine" in reason_lower or "loop iteration" in reason_lower:
        return {
            'root_cause': "编译器无法在编译时确定循环边界或迭代次数",
            'issue_category': "variable_bounds",
            'solution_type': "compiler_hint_first",
            'recommended_approaches': [
                {
                    'method': 'pragma_vectorize',
                    'code': '#pragma clang loop vectorize(enable)',
                    'description': '添加在循环前，强制编译器尝试向量化',
                    'success_probability': 'high'
                },
                {
                    'method': 'local_variable',
                    'code': 'int local_n = n; // 将参数复制到局部变量',
                    'description': '帮助编译器分析边界',
                    'success_probability': 'medium'
                },
                {
                    'method': 'multiversion_stride',
                    'code': 'if (stride == 1) { ... } else if (stride == 2) { ... } else { original loop }',
                    'description': '仅当循环属于简单同址访问模式时，才使用多个常见小步长的等价专用分支；复杂地址模式优先 stride==1 快路径 + 通用 fallback',
                    'success_probability': 'medium'
                }
            ],
            'success_probability': 'high'
        }
    
    elif "induction" in reason_lower or "could not determine the upper bound" in reason_lower:
        return {
            'root_cause': "归纳变量导致跨迭代依赖，编译器无法分析依赖关系",
            'issue_category': "induction_variable",
            'solution_type': "source_change_required",
            'recommended_approaches': [
                {
                    'method': 'loop_distribution',
                    'description': '将循环拆分为索引计算和数据访问两个阶段',
                    'key_steps': [
                        '阶段1：预计算所有索引值到数组',
                        '阶段2：使用预计算的值进行可向量化访问'
                    ],
                    'success_probability': 'high'
                }
            ],
            'success_probability': 'medium'
        }
    
    elif "dependence" in reason_lower or "dependent" in reason_lower:
        return {
            'root_cause': "循环携带依赖（Loop-Carried Dependency）",
            'issue_category': "loop_carried_dependency",
            'solution_type': "source_change_required",
            'recommended_approaches': [
                {
                    'method': 'dependency_analysis',
                    'description': '首先分析依赖类型',
                    'steps': [
                        '真依赖（True Dependency）：尝试算法重构（如前缀和）',
                        '反依赖/输出依赖：使用数组复制消除依赖'
                    ],
                    'success_probability': 'low_to_medium'
                }
            ],
            'success_probability': 'low'
        }

    elif "alias" in reason_lower or "memory" in reason_lower:
        return {
            'root_cause': "编译器担心指针可能指向重叠的内存区域",
            'issue_category': "alias_analysis",
            'solution_type': "compiler_hint_or_source_change",
            'recommended_approaches': [
                {
                    'method': 'restrict_keyword',
                    'code': 'real_t * __restrict__ a_ = a;',
                    'description': '使用 __restrict__ 关键字告诉编译器指针不重叠',
                    'success_probability': 'high'
                },
                {
                    'method': 'pragma_vectorize',
                    'code': '#pragma clang loop vectorize(enable)',
                    'description': '如果确定无别名，可用 pragma 强制向量化（风险较高）',
                    'success_probability': 'medium'
                }
            ],
            'success_probability': 'high'
        }
    
    elif "control flow" in reason_lower or "branch" in reason_lower:
        return {
            'root_cause': "复杂控制流（if-else、break、continue）阻碍向量化",
            'issue_category': "control_flow",
            'solution_type': "source_change_preferred",
            'recommended_approaches': [
                {
                    'method': 'if_conversion',
                    'code': 'a[i] = (condition) ? value1 : value2;',
                    'description': '将分支转为条件选择表达式',
                    'success_probability': 'high'
                },
                {
                    'method': 'loop_distribution',
                    'description': '将条件部分分离到单独循环',
                    'success_probability': 'medium'
                }
            ],
            'success_probability': 'medium'
        }
    
    else:
        return {
            'root_cause': f"未知原因: {reason}",
            'issue_category': "unknown",
            'solution_type': "source_change",
            'recommended_approaches': [
                {
                    'method': 'general_pragma',
                    'code': '#pragma clang loop vectorize(enable)',
                    'description': '尝试使用 pragma 强制向量化',
                    'success_probability': 'unknown'
                }
            ],
            'success_probability': 'unknown'
        }


def get_compiler_hints_guide(issue_category: str) -> str:
    """
    根据问题类别获取编译器指令使用指南
    """
    guides = {
        "variable_bounds": """
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
""",
        "alias_analysis": """
【编译器指令推荐】:
针对别名分析问题，建议:

1. **最佳方案** - restrict 关键字:
   ```c
   real_t * __restrict__ a_ = a;
   real_t * __restrict__ b_ = b;
   #pragma clang loop vectorize(enable)
   for (int i = 0; i < n; i++) {
       a_[i] = b_[i] + c_[i];
   }
   ```
   注意：确保数组确实不重叠，否则是未定义行为！

2. **备选方案** - 纯 pragma（高风险）:
   ```c
   #pragma clang loop vectorize(enable)
   for (int i = 0; i < n; i++) {
       a[i] = b[i] + c[i];
   }
   ```
   仅在你完全确定无别名时使用

3. **编译选项**（对整个文件生效）:
   添加编译选项: -fstrict-aliasing
""",
        "memory_access_pattern": """
【编译器指令推荐】:
针对非连续内存访问，建议:

1. **interleave 优化**:
   ```c
   #pragma clang loop vectorize(enable) interleave_count(4)
   for (int i = 0; i < n; i += 2) {  // 步长为2
       a[i] = b[i] + c[i];
   }
   ```

2. **指定向量宽度**:
   ```c
   #pragma clang loop vectorize(enable) vectorize_width(4)
   for (int i = 0; i < n; i += 2) { ... }
   ```

3. **如果以上无效**: 考虑重构代码使访问连续
"""
    }
    
    return guides.get(issue_category, "\n【编译器指令】: 可尝试 #pragma clang loop vectorize(enable)\n")


def _is_generic_missed_remark(reason: str) -> bool:
    """Return True for remarks that do not expose a concrete blocker."""
    lowered = (reason or "").strip().lower()
    return (
        "loop not vectorized [-rpass-missed=loop-vectorize]" in lowered
        or lowered == "loop not vectorized"
        or lowered == "loop vectorized"
    )


def format_enhanced_knowledge(issue_reasons: List[str]) -> str:
    """
    增强版知识库格式化 - 包含深度分析和决策指导
    
    Args:
        issue_reasons: 向量化失败原因列表
        
    Returns:
        格式化的增强知识库文本
    """
    if not issue_reasons:
        return "没有检测到向量化问题。"
    
    sections = []
    sections.append("=" * 60)
    sections.append("【深度诊断分析】")
    sections.append("=" * 60)
    
    filtered_reasons = [reason for reason in issue_reasons if not _is_generic_missed_remark(reason)]
    if not filtered_reasons:
        return "没有检测到可归因的具体向量化障碍。"

    for i, reason in enumerate(filtered_reasons[:3], 1):  # 最多分析3个问题
        analysis = analyze_issue_depth(reason)
        
        sections.append(f"\n问题 {i}: {reason[:80]}...")
        sections.append(f"  根因: {analysis['root_cause']}")
        sections.append(f"  类别: {analysis['issue_category']}")
        sections.append(f"  解决类型: {analysis['solution_type']}")
        sections.append(f"  成功概率: {analysis['success_probability']}")
        
        sections.append("\n  推荐方案:")
        for j, approach in enumerate(analysis['recommended_approaches'], 1):
            sections.append(f"    {j}. {approach['description']}")
            if 'code' in approach:
                sections.append(f"       代码: {approach['code']}")
            if 'success_probability' in approach:
                sections.append(f"       成功率: {approach['success_probability']}")
        
        # 添加编译器指令指南
        compiler_guide = get_compiler_hints_guide(analysis['issue_category'])
        if compiler_guide:
            sections.append(compiler_guide)
    
    # 添加决策流程图
    sections.append("""
【决策流程】:
1. 首先尝试编译器指令（pragma）- 改动最小
2. 如果 pragma 无效，分析是否需要源码修改
3. 对于归纳变量/真依赖问题，必须重构代码
4. 对于别名/边界问题，pragma + restrict 通常有效

【编译选项建议】:
确保使用 -O3 -march=native 编译以启用所有优化
""")
    
    return "\n".join(sections)


def get_quick_fix_suggestions(issue_reasons: List[str]) -> List[Dict]:
    """
    获取快速修复建议列表（用于自动尝试）
    
    Returns:
        按优先级排序的快速修复方案列表
    """
    suggestions = []
    
    for reason in issue_reasons:
        if _is_generic_missed_remark(reason):
            continue
        analysis = analyze_issue_depth(reason)
        
        for approach in analysis['recommended_approaches']:
            suggestion = {
                'issue': reason,
                'method': approach['method'],
                'probability': approach.get('success_probability', 'unknown'),
                'category': analysis['issue_category']
            }
            if 'code' in approach:
                suggestion['code_example'] = approach['code']
            suggestions.append(suggestion)
    
    # 按成功率排序
    prob_order = {'high': 0, 'medium': 1, 'low': 2, 'unknown': 3}
    suggestions.sort(key=lambda x: prob_order.get(x['probability'], 3))
    
    return suggestions


# ============ 新增：本质限制检测与部分向量化支持 ============

# 定义哪些向量化障碍是"本质限制"（难以/无法通过代码重构完全解决）
FUNDAMENTAL_LIMITATIONS = {
    "true_dependency": {
        "patterns": [
            r"dependent.*memory",  # unsafe dependent memory operations
            r"true.*depend",  # true dependency
            r"flow.*depend",  # flow dependency
        ],
        "description": "真依赖（True Dependency / Flow Dependency）",
        "explanation": "当前迭代计算依赖于前一迭代的结果，这是固有的数据流依赖，无法通过简单的代码重构消除",
        "solutions": [
            "算法级重构（如前缀和、扫描算法）",
            "接受部分向量化",
        ],
        "vectorizable": False,  # 通常无法完全向量化
        "accept_partial": True,  # 应接受部分向量化
    },
    "dynamic_memory": {
        "patterns": [
            r"malloc|alloca|new",  # 动态内存分配
            r"gather|scatter",  # 聚集/分散访问模式
            r"indirect.*access",  # 间接访问
        ],
        "description": "动态内存或间接访问",
        "explanation": "动态分配的内存或间接索引（如 a[idx[i]]）导致编译器无法分析内存别名和数据依赖",
        "solutions": [
            "使用静态数组代替动态分配（如果可能）",
            "使用 __builtin_assume_aligned 提供对齐信息",
            "接受部分向量化",
        ],
        "vectorizable": False,
        "accept_partial": True,
    },
    "force_vectorize_failed": {
        "patterns": [
            r"force.*true",  # Force=true 但仍然失败
            r"unable to perform the requested transformation",
            r"might be disabled",
        ],
        "description": "即使强制向量化也失败",
        "explanation": "编译器报告即使使用 #pragma clang loop vectorize(enable) 也无法向量化，这通常意味着存在本质性障碍",
        "solutions": [
            "检查是否有真依赖或动态内存问题",
            "接受该循环无法向量化",
        ],
        "vectorizable": False,
        "accept_partial": True,
    },
    "function_call": {
        "patterns": [
            r"call instruction",
            r"function call",
        ],
        "description": "函数调用阻止向量化",
        "explanation": "循环体内的函数调用无法内联或向量化",
        "solutions": [
            "将函数调用移出循环（如果可能）",
            "使用内联函数",
            "接受该循环无法向量化",
        ],
        "vectorizable": False,
        "accept_partial": True,
    },
}


def check_fundamental_limitation(diagnostics: List[str]) -> Optional[Dict]:
    """
    检查诊断信息中是否包含本质限制
    
    Args:
        diagnostics: 编译器诊断信息列表
        
    Returns:
        如果检测到本质限制，返回对应的限制信息；否则返回 None
    """
    import re
    
    for diag in diagnostics:
        diag_lower = diag.lower()
        for limitation_name, limitation_info in FUNDAMENTAL_LIMITATIONS.items():
            for pattern in limitation_info["patterns"]:
                if re.search(pattern, diag_lower):
                    return {
                        "name": limitation_name,
                        **limitation_info
                    }
    return None


def analyze_optimization_progress(rounds_history: List[Dict]) -> Dict:
    """
    分析多轮优化的进展，检测是否陷入停滞
    
    Args:
        rounds_history: 各轮优化结果历史
        
    Returns:
        {
            'status': 'progressing' | 'stalled' | 'partial_success' | 'fundamental_limit',
            'message': str,
            'recommendation': str
        }
    """
    if len(rounds_history) < 2:
        return {
            'status': 'progressing',
            'message': '优化进行中，轮次不足',
            'recommendation': '继续优化'
        }
    
    # 获取最近几轮的向量化数量
    recent_rounds = rounds_history[-3:]  # 最近3轮
    vectorized_counts = [r.get('vectorized_count', 0) for r in recent_rounds]
    
    # 检查是否有进展
    if len(set(vectorized_counts)) == 1 and vectorized_counts[0] > 0:
        # 向量化数量保持不变且大于0
        # 检查是否有本质限制
        last_diagnostics = recent_rounds[-1].get('diagnostics', {}).get('missed', [])
        fundamental = check_fundamental_limitation(last_diagnostics)
        
        if fundamental:
            return {
                'status': 'fundamental_limit',
                'message': f"检测到本质限制: {fundamental['description']}",
                'explanation': fundamental['explanation'],
                'recommendation': '接受部分向量化结果，该循环可能无法完全向量化',
                'limitation': fundamental
            }
        else:
            return {
                'status': 'stalled',
                'message': '多轮优化后向量化数量没有增加',
                'recommendation': '尝试不同的优化策略，或考虑接受当前结果'
            }
    
    # 检查是否有部分成功
    last_vectorized = vectorized_counts[-1] if vectorized_counts else 0
    total_loops = last_vectorized + recent_rounds[-1].get('missed_count', 0)
    
    if last_vectorized > 0 and last_vectorized < total_loops:
        return {
            'status': 'partial_success',
            'message': f'部分向量化成功 ({last_vectorized}/{total_loops})',
            'recommendation': '已部分向量化，继续尝试或接受结果'
        }
    
    # 有进展
    return {
        'status': 'progressing',
        'message': '优化正在取得进展',
        'recommendation': '继续优化'
    }


def get_partial_vectorization_guidance(current_vectorized: int, total_loops: int, 
                                        diagnostics: List[str]) -> str:
    """
    生成关于部分向量化的通用指导（不针对特定函数）
    
    Args:
        current_vectorized: 当前已向量化的循环数
        total_loops: 总循环数
        diagnostics: 未向量化的诊断信息
        
    Returns:
        格式化的指导文本
    """
    if current_vectorized == 0:
        return ""
    
    # 检查是否有本质限制
    fundamental = check_fundamental_limitation(diagnostics)
    
    sections = []
    sections.append("\n" + "=" * 60)
    sections.append("【部分向量化状态评估】")
    sections.append("=" * 60)
    sections.append(f"当前进展: {current_vectorized}/{total_loops} 循环已向量化 ({100*current_vectorized//total_loops}%)")
    
    if fundamental:
        sections.append(f"\n⚠️  检测到潜在的本质限制: {fundamental['description']}")
        sections.append(f"说明: {fundamental['explanation']}")
        sections.append("\n可能的解决方案:")
        for i, sol in enumerate(fundamental['solutions'], 1):
            sections.append(f"  {i}. {sol}")
        sections.append("\n💡 建议: 如果上述方案无效，接受部分向量化也是合理的结果。")
    else:
        sections.append("\n✅ 当前已取得部分进展，剩余循环可能存在可解决的障碍。")
        sections.append("建议: 继续尝试不同策略，或检查诊断信息寻找突破口。")
    
    sections.append("\n【通用指导原则】")
    sections.append("1. 部分向量化是正常结果，不是失败")
    sections.append("2. 并非所有循环都适合向量化（如带有真依赖的循环）")
    sections.append("3. 优先保证代码正确性，其次才是完全向量化")
    sections.append("4. 如果连续多轮没有进展，考虑接受当前结果")
    
    return "\n".join(sections)
