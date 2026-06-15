#!/usr/bin/env python3
"""
Clang 优化结果评估脚本
自动检查所有 optimized_*.c 文件的向量化情况
生成最小可编译单元进行精确评估
"""

import os
import re
import subprocess
import glob
import sys
import json
import tempfile
from pathlib import Path

from config import config, get_clang_path
from feedback_structuring import dedupe_preserve_order, parse_diagnostic_line
from logger import (
    setup_logger, info, success, failure, warning_icon,
    section, subsection, progress
)

# 初始化日志
setup_logger()


def _prefix_name():
    """返回文件名层面的优化前缀，兼容 OPTIMIZED_FILE_PREFIX 为路径的实验模式。"""
    return os.path.basename(config.OPTIMIZED_FILE_PREFIX.rstrip(os.sep)) or config.OPTIMIZED_FILE_PREFIX


def _strip_optimized_prefix(stem):
    prefix = _prefix_name()
    if stem.startswith(prefix):
        return stem[len(prefix):]
    if stem.startswith("optimized_"):
        return stem[len("optimized_"):]
    return stem


def _candidate_optimized_paths(func_name):
    prefix = config.OPTIMIZED_FILE_PREFIX
    prefix_name = _prefix_name()
    return [
        os.path.join(f"{prefix}{func_name}", f"{prefix_name}{func_name}.c"),
        f"{prefix}{func_name}.c",
    ]


# 最小可编译单元模板
MINIMAL_UNIT_TEMPLATE = '''/* Auto-generated minimal compile unit for {func_name} */
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <sys/time.h>

#define iterations 100000
#define LEN_1D 32000
#define LEN_2D 256
#define ARRAY_ALIGNMENT 64

struct args_t {{
    struct timeval t1;
    struct timeval t2;
    void * __restrict__ arg_info;
}};

#if 0
typedef double real_t;
#define ABS fabs
#else
typedef float real_t;
#define ABS fabsf
#endif

/* External array declarations */
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t flat_2d_array[LEN_2D*LEN_2D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t x[LEN_1D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t a[LEN_1D],b[LEN_1D],c[LEN_1D],d[LEN_1D],e[LEN_1D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t aa[LEN_2D][LEN_2D],bb[LEN_2D][LEN_2D],cc[LEN_2D][LEN_2D],tt[LEN_2D][LEN_2D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) int indx[LEN_1D];
extern real_t* __restrict__ xx;
extern real_t* yy;

/* Function declarations */
int dummy(real_t[LEN_1D], real_t[LEN_1D], real_t[LEN_1D], real_t[LEN_1D], real_t[LEN_1D], real_t[LEN_2D][LEN_2D], real_t[LEN_2D][LEN_2D], real_t[LEN_2D][LEN_2D], real_t);
int initialise_arrays(const char* name);
real_t calc_checksum(const char * name);

/* Optional TSVC helper definitions */
{support_code}

/* Target function */
{func_code}

/* Main function for standalone compilation test */
int main() {{
    struct args_t args;
    real_t result = {func_name}(&args);
    return 0;
}}
'''


TSVC_SUPPORT_SNIPPETS = {
    "f": '''/* Helper function f used by some TSVC kernels (e.g., s4121) */
real_t f(real_t a, real_t b) {
    return a * b;
}
'''
}


def extract_function_code(file_path, func_name):
    """从文件中提取函数代码"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        # 移除 markdown 代码块
        content = re.sub(r'^```c?\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)

        func_code_lines = []
        in_function = False
        brace_count = 0

        for line in content.split('\n'):
            if not in_function:
                # 匹配函数开始 - 支持多种返回类型
                func_pattern = rf'^(real_t|void|int|float|double)\s+{re.escape(func_name)}\s*\('
                if re.search(func_pattern, line.strip()):
                    in_function = True
                    brace_count = 0

            if in_function:
                func_code_lines.append(line)
                brace_count += line.count('{')
                brace_count -= line.count('}')

                if brace_count == 0 and '{' in ''.join(func_code_lines):
                    break

        return '\n'.join(func_code_lines) if func_code_lines else None

    except Exception as e:
        failure(f"提取函数代码时出错: {e}")
        return None


def build_support_code(func_code):
    """为最小编译单元补齐函数依赖的 TSVC helper 定义。"""
    support_blocks = []

    helper_checks = {
        "f": (
            r'\bf\s*\(',
            r'\b(?:real_t|void|int|float|double)\s+f\s*\(',
        ),
    }

    for helper_name, (call_pattern, def_pattern) in helper_checks.items():
        if re.search(call_pattern, func_code) and not re.search(def_pattern, func_code):
            support_blocks.append(TSVC_SUPPORT_SNIPPETS[helper_name])

    return '\n'.join(support_blocks).strip()


def create_minimal_compile_unit(func_name, func_code, output_path):
    """创建最小可编译单元"""
    support_code = build_support_code(func_code)
    full_code = MINIMAL_UNIT_TEMPLATE.format(
        func_name=func_name,
        func_code=func_code,
        support_code=support_code,
    )

    with open(output_path, 'w') as f:
        f.write(full_code)

    return output_path


def run_clang_analysis(c_file_path, clang_path):
    """运行 clang 分析并返回所有诊断信息"""
    cmd = [
        clang_path,
        "-O3",
        "-fvectorize",
        "-Rpass=loop-vectorize",
        "-Rpass-missed=loop-vectorize",
        "-Rpass-analysis=loop-vectorize",
        "-c", c_file_path,
        "-o", "/dev/null"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30
        )
        return result.stderr
    except subprocess.TimeoutExpired:
        return "❌ 编译器分析超时 (30秒)"
    except Exception as e:
        return f"❌ 执行编译器时发生错误: {e}"


def parse_diagnostics(diagnostic_output):
    """解析 clang 诊断输出"""
    results = {
        "vectorized": [],
        "missed": [],
        "analysis": [],
        "errors": [],
        "vectorized_entries": [],
        "missed_entries": [],
        "analysis_entries": [],
        "missed_categories": [],
        "analysis_categories": [],
        "all_categories": [],
    }

    lines = diagnostic_output.split('\n')

    for line in lines:
        line_lower = line.lower()
        stripped = line.strip()

        if not stripped or stripped.startswith('warning:'):
            continue

        parsed_entry = parse_diagnostic_line(stripped)

        # 匹配成功向量化的信息
        if "loop vectorized" in line_lower and "not" not in line_lower:
            results["vectorized"].append(stripped)
            results["vectorized_entries"].append(parsed_entry)
        elif "vectorized" in line_lower and "loop" in line_lower and "not" not in line_lower:
            if not any(v == stripped for v in results["vectorized"]):
                results["vectorized"].append(stripped)
                results["vectorized_entries"].append(parsed_entry)

        # 匹配错过的向量化信息
        if "loop not vectorized" in line_lower or ("not vectorized" in line_lower and "loop" in line_lower):
            if stripped not in results["missed"]:
                results["missed"].append(stripped)
                results["missed_entries"].append(parsed_entry)

        # 匹配分析信息
        if "loop-vectorize" in line_lower:
            if "analysis" in line_lower or "remark:" in line_lower:
                if stripped not in results["analysis"]:
                    results["analysis"].append(stripped)
                    results["analysis_entries"].append(parsed_entry)

        # 匹配编译错误
        if "error:" in line_lower and "vectorize" not in line_lower:
            results["errors"].append(stripped)

    results["missed_categories"] = dedupe_preserve_order(
        [
            category
            for entry in results["missed_entries"]
            for category in entry.get("categories", [])
        ]
    )
    results["analysis_categories"] = dedupe_preserve_order(
        [
            category
            for entry in results["analysis_entries"]
            for category in entry.get("categories", [])
        ]
    )
    results["all_categories"] = dedupe_preserve_order(
        results["missed_categories"] + results["analysis_categories"]
    )

    return results


def check_compilation_success(c_file_path, clang_path):
    """检查代码是否能成功编译"""
    cmd = [
        clang_path,
        "-O3",
        "-fvectorize",
        "-c", c_file_path,
        "-o", "/dev/null"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30
        )
        return result.returncode == 0, result.stderr
    except subprocess.TimeoutExpired:
        return False, "编译超时 (30秒)"
    except Exception as e:
        return False, f"执行编译器时出错: {e}"


def analyze_single_function(func_name, func_code, clang_path, temp_dir="/tmp"):
    """分析单个函数的优化效果（使用最小可编译单元）"""
    with tempfile.TemporaryDirectory(prefix=f"acpo_{func_name}_", dir=temp_dir) as work_dir:
        temp_file = os.path.join(work_dir, f"minimal_{func_name}.c")
        # 创建最小可编译单元
        create_minimal_compile_unit(func_name, func_code, temp_file)

        # 检查编译
        can_compile, compile_error = check_compilation_success(temp_file, clang_path)

        if not can_compile:
            return {
                "compilable": False,
                "vectorized": False,
                "vectorized_count": 0,
                "missed_count": 0,
                "error": compile_error
            }

        # 运行向量化分析
        diagnostic_output = run_clang_analysis(temp_file, clang_path)
        results = parse_diagnostics(diagnostic_output)

        # 判断是否完全向量化（有成功向量化的循环且没有错过的）
        is_fully_vectorized = len(results["vectorized"]) > 0 and len(results["missed"]) == 0

        return {
            "compilable": True,
            "vectorized": is_fully_vectorized,
            "vectorized_count": len(results["vectorized"]),
            "missed_count": len(results["missed"]),
            "diagnostics": results
        }


def analyze_function_code(func_name, func_code, clang_path, debug=False, source_label=None):
    """分析一段函数代码，可来自文件或 optimization_state。"""
    if source_label:
        subsection(f"分析来源: {source_label}")
    info(f"函数名: {func_name}")

    result = analyze_single_function(func_name, func_code, clang_path)
    result["function"] = func_name

    compile_status = "✅ 成功" if result['compilable'] else "❌ 失败"
    info(f"编译状态: {compile_status}")

    if not result['compilable']:
        error_msg = result.get('error', '')
        if "passing" in error_msg and "incompatible type" in error_msg:
            warning_icon("优化后的代码存在语义错误 (参数类型不匹配)")
        elif "undefined" in error_msg.lower():
            warning_icon("存在未定义的符号")
        elif debug:
            failure(f"编译错误:\n{error_msg}")
        else:
            lines = error_msg.split('\n')[:5]
            for line in lines:
                info(f"  {line}")
    else:
        info("")
        info("向量化分析结果:")
        diagnostics = result.get('diagnostics', {})

        if diagnostics.get("vectorized"):
            info(f"  ✅ 成功向量化的循环 ({len(diagnostics['vectorized'])} 个)")
        else:
            info(f"  ⚪ 没有成功向量化的循环")

        if diagnostics.get("missed"):
            info(f"  ❌ 错过的向量化机会 ({len(diagnostics['missed'])} 个)")
            for m in diagnostics['missed'][:3]:
                info(f"     • {m[:80]}...")
        else:
            info(f"  ✅ 没有错过的向量化机会")

        if result['vectorized']:
            success("最终判定: 完全向量化!")
        else:
            warning_icon("最终判定: 仍有改进空间")

    return result


def get_state_optimized_code(func_name):
    """从 optimization_state.json 读取最终/最佳候选代码。"""
    try:
        from state_manager import load_state
        state = load_state()
    except Exception as exc:
        return None, f"无法加载 optimization_state.json: {exc}"

    func_state = state.get(func_name)
    if not isinstance(func_state, dict):
        return None, "状态文件中没有该函数"

    if func_state.get("status") == "skipped" and func_state.get("original_code"):
        return func_state["original_code"], "optimization_state.json: original_code (skipped)"

    best_round = func_state.get("best")
    rounds = func_state.get("rounds") or []
    if isinstance(best_round, int) and 1 <= best_round <= len(rounds):
        code = rounds[best_round - 1].get("code")
        if code:
            return code, f"optimization_state.json: round {best_round}"

    for round_record in reversed(rounds):
        code = round_record.get("code")
        if code:
            return code, f"optimization_state.json: round {round_record.get('round', '?')}"

    return None, "状态文件中没有可评估代码"


def find_state_optimized_functions():
    """当文件产物不存在时，从状态文件发现可评估函数。"""
    try:
        from state_manager import load_state
        state = load_state()
    except Exception:
        return []

    functions = []
    for func_name, func_state in state.items():
        if not isinstance(func_state, dict):
            continue
        if func_state.get("status") == "skipped" and func_state.get("original_code"):
            functions.append(func_name)
            continue
        best_round = func_state.get("best")
        rounds = func_state.get("rounds") or []
        if isinstance(best_round, int) and 1 <= best_round <= len(rounds):
            if rounds[best_round - 1].get("code"):
                functions.append(func_name)
    return sorted(set(functions))


def analyze_optimized_file(file_path, clang_path, debug=False):
    """分析优化后的文件"""
    # 从文件名提取函数名，去掉 optimized_ 前缀和 _roundX 后缀
    stem = re.sub(r'_round\d+$', '', Path(file_path).stem)
    func_name = _strip_optimized_prefix(stem)

    # 提取函数代码
    func_code = extract_function_code(file_path, func_name)
    if not func_code:
        warning_icon(f"无法从文件中提取函数代码")
        return {
            "file": file_path,
            "function": func_name,
            "compilable": False,
            "vectorized": False,
            "error": "无法提取函数代码"
        }

    result = analyze_function_code(
        func_name,
        func_code,
        clang_path,
        debug=debug,
        source_label=f"文件: {file_path}",
    )
    result["file"] = file_path
    return result


def print_summary(all_results):
    """打印汇总报告"""
    section("优化结果汇总报告")

    total = len(all_results)
    compilable = sum(1 for r in all_results if r["compilable"])
    vectorized = sum(1 for r in all_results if r["vectorized"])

    info(f"统计:")
    info(f"  • 总文件数: {total}")
    info(f"  • 成功编译: {compilable}/{total} ({100*compilable//total if total > 0 else 0}%)")
    info(f"  • 完全向量化: {vectorized}/{compilable} ({100*vectorized//compilable if compilable > 0 else 0}%)")

    subsection("详细结果")
    info(f"{'函数名':<15} {'编译':<8} {'向量化':<10} {'成功/错过':<12} {'状态':<15}")
    info("-" * 60)

    for r in all_results:
        compile_status = "✅" if r["compilable"] else "❌"
        vector_status = "✅" if r["vectorized"] else "❌"
        loop_info = f"{r.get('vectorized_count', 0)}/{r.get('missed_count', 0)}"

        if not r["compilable"]:
            status = "编译失败"
        elif r["vectorized"]:
            status = "✅ 优化成功"
        elif r.get('vectorized_count', 0) > 0:
            status = "⚠️ 部分优化"
        else:
            status = "❌ 需要改进"

        info(f"{r['function']:<15} {compile_status:<8} {vector_status:<10} {loop_info:<12} {status:<15}")

    info("-" * 60)

    # 列出需要进一步优化的文件
    not_vectorized = [r for r in all_results if r["compilable"] and not r["vectorized"]]
    if not_vectorized:
        info(f"")
        warning_icon(f"需要进一步优化的函数 ({len(not_vectorized)} 个):")
        for r in not_vectorized:
            info(f"  • {r['function']}")

    # 列出编译失败的文件
    not_compilable = [r for r in all_results if not r["compilable"]]
    if not_compilable:
        info(f"")
        failure(f"编译失败的函数 ({len(not_compilable)} 个):")
        for r in not_compilable:
            info(f"  • {r['function']}")


def find_optimized_files(directory="."):
    """查找所有优化后的 C 文件（支持子目录结构）"""
    prefix = config.OPTIMIZED_FILE_PREFIX
    prefix_name = _prefix_name()

    # 先搜索当前目录下的 optimized_*.c（旧结构兼容）
    if os.path.isabs(prefix) or os.sep in prefix:
        pattern = f"{prefix}*.c"
        subdir_pattern = os.path.join(f"{prefix}*", f"{prefix_name}*.c")
    else:
        pattern = os.path.join(directory, f"{prefix}*.c")
        subdir_pattern = os.path.join(directory, f"{prefix}*", f"{prefix_name}*.c")

    files = glob.glob(pattern)

    # 再搜索子目录中的 optimized_<func>/optimized_<func>.c（新结构）
    # 查找所有 optimized_*/ 目录下的 optimized_*.c 文件（最终结果）
    subdir_files = glob.glob(subdir_pattern)

    # 合并结果，只保留最终结果文件（不包括 _origin 和 _roundX）
    files = files + subdir_files
    # 排除 test 文件、_origin 文件和 _roundX 文件
    files = [f for f in files if not f.endswith("_test.c") and "_origin" not in f and "_round" not in os.path.basename(f)]
    return sorted(files)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="评估 Clang 优化结果（最小可编译单元版）")
    parser.add_argument("-d", "--directory", default=".", help="搜索优化后文件的目录 (默认: 当前目录)")
    parser.add_argument("-c", "--clang", default=get_clang_path(), help=f"clang 路径 (默认: {get_clang_path()})")
    parser.add_argument("-f", "--function", help="只分析指定函数，支持逗号分隔多个函数 (例如: s111 或 s111,s112)")
    parser.add_argument("--debug", action="store_true", help="调试模式: 显示完整错误信息")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式结果")

    args = parser.parse_args()

    # 确定要分析的文件
    if args.function:
        # 支持逗号分隔的多个函数名
        func_names = [f.strip() for f in args.function.split(',') if f.strip()]
        files_to_analyze = []
        state_targets = []
        for func_name in func_names:
            file_path = next(
                (candidate for candidate in _candidate_optimized_paths(func_name) if os.path.exists(candidate)),
                None,
            )
            if not file_path:
                state_code, state_label = get_state_optimized_code(func_name)
                if state_code:
                    state_targets.append((func_name, state_code, state_label))
                    continue
                candidates = " 或 ".join(_candidate_optimized_paths(func_name))
                print(
                    f"❌ 文件不存在: {candidates}；状态回退也失败: {state_label}"
                )
                sys.exit(1)
            files_to_analyze.append(file_path)
    else:
        files_to_analyze = find_optimized_files(args.directory)
        state_targets = []

    if not files_to_analyze and not state_targets:
        for func_name in find_state_optimized_functions():
            state_code, state_label = get_state_optimized_code(func_name)
            if state_code:
                state_targets.append((func_name, state_code, state_label))

    if not files_to_analyze and not state_targets:
        failure("未找到任何 optimized_*.c 文件，也未在 optimization_state.json 中找到可评估代码")
        sys.exit(1)

    section("评估优化结果")
    info(f"找到 {len(files_to_analyze)} 个待分析文件，{len(state_targets)} 个状态回退目标")
    info(f"使用 clang: {args.clang}")

    # 分析每个文件
    all_results = []
    for i, file_path in enumerate(files_to_analyze, 1):
        progress(i, len(files_to_analyze), f"分析文件: {file_path}")
        result = analyze_optimized_file(file_path, args.clang, debug=args.debug)
        all_results.append(result)

    for i, (func_name, func_code, state_label) in enumerate(state_targets, 1):
        progress(i, len(state_targets), f"分析状态: {func_name}")
        result = analyze_function_code(
            func_name,
            func_code,
            args.clang,
            debug=args.debug,
            source_label=state_label,
        )
        result["source"] = state_label
        all_results.append(result)

    # 输出 JSON 或汇总
    if args.json:
        info(json.dumps(all_results, indent=2, ensure_ascii=False))
    else:
        print_summary(all_results)

    # 返回适当的退出码
    vectorized_count = sum(1 for r in all_results if r["vectorized"])
    if vectorized_count == len(all_results):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
