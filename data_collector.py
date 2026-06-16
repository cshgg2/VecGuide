#!/usr/bin/env python3
"""
VecGuide 数据收集器
从 Clang 编译器提取循环向量化失败的诊断信息
支持函数级别的诊断映射
"""

import subprocess
import os
import re
import sys
import json
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple
from config import config, check_clang_available, check_source_file_exists


def extract_functions_from_source(source_file: str) -> Dict[str, Dict]:
    """
    从源文件中提取所有函数及其行号范围
    返回: {func_name: {'start_line': int, 'end_line': int}}
    """
    functions = {}

    try:
        with open(source_file, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ 读取源文件失败: {e}")
        return functions

    # 匹配函数定义: real_t func_name(...)
    func_pattern = re.compile(r'^(real_t|void|int|float|double)\s+(s\d+)\s*\(')

    for i, line in enumerate(lines, 1):
        match = func_pattern.match(line.strip())
        if match:
            func_name = match.group(2)
            functions[func_name] = {
                'start_line': i,
                'end_line': i  # 暂时设为起始行，后面会更新
            }

    # 确定每个函数的结束行（下一个函数的开始行前一行，或文件末尾）
    sorted_funcs = sorted(functions.items(), key=lambda x: x[1]['start_line'])
    for i, (func_name, info) in enumerate(sorted_funcs):
        if i < len(sorted_funcs) - 1:
            functions[func_name]['end_line'] = sorted_funcs[i + 1][1]['start_line'] - 1
        else:
            functions[func_name]['end_line'] = len(lines)

    return functions


def find_function_by_line(line_num: int, functions: Dict) -> Optional[str]:
    """根据行号查找对应的函数名"""
    for func_name, info in functions.items():
        if info['start_line'] <= line_num <= info['end_line']:
            return func_name
    return None


def run_clang_analysis(source_file: str, clang_path: str) -> Tuple[bool, str]:
    """
    运行 Clang 分析，返回诊断输出
    """
    cmd = [
        clang_path,
        "-O3",
        "-Rpass-missed=loop-vectorize",
        "-Rpass-analysis=loop-vectorize",
        f"-I{config.TSVC_INCLUDE_PATH}",
        "-c", source_file,
        "-o", "/dev/null"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60
        )
        return True, result.stderr
    except subprocess.TimeoutExpired:
        return False, "❌ Clang 分析超时 (60秒)"
    except Exception as e:
        return False, f"❌ 执行 Clang 时出错: {e}"


def parse_diagnostics(diagnostics_output: str, functions: Dict) -> Dict:
    """
    解析 Clang 诊断输出，按函数归类
    返回: {
        'by_function': {func_name: [diagnostics]},
        'by_reason': {reason: count},
        'summary': {...}
    }
    """
    results = {
        'by_function': defaultdict(list),
        'by_reason': Counter(),
        'total_diagnostics': 0
    }

    # 匹配诊断行: file:line:col: remark: ...
    diagnostic_pattern = re.compile(
        r'^([^:]+):(\d+):(\d+):\s+remark:\s+(.+)$'
    )

    lines = diagnostics_output.split('\n')

    for line in lines:
        match = diagnostic_pattern.match(line.strip())
        if not match:
            continue

        file_path = match.group(1)
        line_num = int(match.group(2))
        col_num = int(match.group(3))
        message = match.group(4)

        # 找到对应的函数
        func_name = find_function_by_line(line_num, functions)

        # 提取诊断类型和原因
        diag_info = {
            'line': line_num,
            'column': col_num,
            'message': message,
            'type': 'unknown'
        }

        # 分类诊断
        if 'loop not vectorized:' in message.lower():
            diag_info['type'] = 'not_vectorized'
            # 提取具体原因
            reason_match = re.search(r'loop not vectorized:\s*(.+?)(?:\s*\[|$)', message, re.IGNORECASE)
            if reason_match:
                reason = reason_match.group(1).strip()
                results['by_reason'][reason] += 1
                diag_info['reason'] = reason
        elif 'loop vectorized' in message.lower() and 'not' not in message.lower():
            diag_info['type'] = 'vectorized'
        elif 'loop-vectorize' in message.lower():
            diag_info['type'] = 'analysis'

        results['total_diagnostics'] += 1

        if func_name:
            results['by_function'][func_name].append(diag_info)
        else:
            # 不属于任何函数（可能是全局代码）
            results['by_function']['__global__'].append(diag_info)

    return results


def build_problem_map(diagnostics: Dict, functions: Dict) -> Dict:
    """
    构建问题映射，用于指导优化
    返回: {
        func_name: {
            'severity': 'high'|'medium'|'low',
            'problems': [...],
            'line_range': [start, end]
        }
    }
    """
    problem_map = {}

    for func_name in functions.keys():
        func_diags = diagnostics['by_function'].get(func_name, [])

        if not func_diags:
            continue

        # 计算严重程度
        not_vectorized_count = sum(1 for d in func_diags if d['type'] == 'not_vectorized')

        if not_vectorized_count >= 3:
            severity = 'high'
        elif not_vectorized_count >= 1:
            severity = 'medium'
        else:
            severity = 'low'

        # 收集唯一的问题原因
        unique_reasons = []
        seen_reasons = set()
        for d in func_diags:
            if d['type'] == 'not_vectorized' and 'reason' in d:
                reason = d['reason']
                if reason not in seen_reasons:
                    seen_reasons.add(reason)
                    unique_reasons.append({
                        'reason': reason,
                        'line': d['line']
                    })

        problem_map[func_name] = {
            'severity': severity,
            'line_range': [
                functions[func_name]['start_line'],
                functions[func_name]['end_line']
            ],
            'total_diagnostics': len(func_diags),
            'not_vectorized_count': not_vectorized_count,
            'problems': unique_reasons[:5]  # 最多保留5个问题
        }

    return problem_map


def print_statistics(diagnostics: Dict, problem_map: Dict):
    """打印统计信息"""
    print("\n" + "=" * 70)
    print("🎯 编译器无法向量化的原因统计（按问题类型）")
    print("=" * 70)

    total = sum(diagnostics['by_reason'].values())
    if total == 0:
        print("\n✅ 没有找到循环向量化失败的诊断信息")
        return

    for idx, (reason, count) in enumerate(diagnostics['by_reason'].most_common(), 1):
        percentage = (count / total) * 100
        print(f"\n{idx}. [{count} 次({percentage:.1f}%)] {reason[:100]}")

    print("\n" + "=" * 70)
    print(f"总计: {total} 条诊断信息")
    print("=" * 70)

    # 按函数统计
    print("\n" + "=" * 70)
    print("📊 问题函数统计")
    print("=" * 70)

    # 按严重程度排序
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    sorted_funcs = sorted(
        problem_map.items(),
        key=lambda x: (severity_order.get(x[1]['severity'], 3), -x[1]['not_vectorized_count'])
    )

    print(f"\n{'函数名':<12} {'严重程度':<10} {'问题数':<8} {'状态':<15}")
    print("-" * 60)

    for func_name, info in sorted_funcs:
        severity_icon = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }.get(info['severity'], '⚪')

        status = "需要优化" if info['not_vectorized_count'] > 0 else "观察"

        print(f"{func_name:<12} {severity_icon} {info['severity']:<7} "
              f"{info['not_vectorized_count']:<8} {status:<15}")

    print("-" * 60)
    print(f"总计: {len(problem_map)} 个函数有问题")


def save_problem_map(problem_map: Dict, output_file: str, verbose: bool = True):
    """保存问题映射到 JSON 文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(problem_map, f, indent=2, ensure_ascii=False)
        if verbose:
            print(f"\n💾 问题映射已保存到: {output_file}")
        return True
    except Exception as e:
        print(f"❌ 保存问题映射失败: {e}")
        return False


def get_functions_to_optimize(problem_map: Dict, severity_filter: Optional[List[str]] = None) -> List[str]:
    """
    获取需要优化的函数列表
    severity_filter: 可选 ['high', 'medium', 'low'] 的子集
    """
    if severity_filter is None:
        severity_filter = ['high', 'medium']

    funcs = []
    for func_name, info in problem_map.items():
        if info['severity'] in severity_filter and info['not_vectorized_count'] > 0:
            funcs.append(func_name)

    return sorted(funcs)


def main():
    """主程序入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Clang 循环向量化诊断信息收集工具"
    )
    parser.add_argument(
        "-s", "--source",
        default=config.SOURCE_FILE,
        help=f"源文件路径 (默认: {config.SOURCE_FILE})"
    )
    parser.add_argument(
        "-c", "--clang",
        default=config.CLANG_PATH,
        help=f"Clang 编译器路径 (默认: {config.CLANG_PATH})"
    )
    parser.add_argument(
        "-o", "--output",
        default=config.PROBLEM_MAP_FILE,
        help=f"问题映射输出文件 (默认: {config.PROBLEM_MAP_FILE})"
    )
    parser.add_argument(
        "--export-functions",
        action="store_true",
        help="输出需要优化的函数名列表（用于管道传递）"
    )
    parser.add_argument(
        "--severity",
        default="high,medium",
        help="要包含的严重程度，逗号分隔 (默认: high,medium)"
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="只输出 JSON 结果，不打印统计"
    )

    args = parser.parse_args()

    if args.json_only and args.export_functions:
        parser.error("--json-only 与 --export-functions 不能同时使用")

    if not args.json_only:
        print("=" * 70)
        print("Clang 循环向量化诊断信息收集工具")
        print("=" * 70)
        print()

    # 检查文件
    ok, error = check_source_file_exists(args.source)
    if not ok:
        print(f"❌ {error}")
        sys.exit(1)

    ok, error = check_clang_available(args.clang)
    if not ok:
        print(f"❌ {error}")
        sys.exit(1)

    # 提取函数信息
    if not args.json_only:
        print(f"🔍 正在分析源文件: {args.source}")
    functions = extract_functions_from_source(args.source)
    if not args.json_only:
        print(f"✅ 发现 {len(functions)} 个函数")

    # 运行 Clang 分析
    if not args.json_only:
        print(f"🚀 正在调用 Clang 分析...")
    success, output = run_clang_analysis(args.source, args.clang)
    if not success:
        print(f"❌ {output}")
        sys.exit(1)

    # 解析诊断信息
    diagnostics = parse_diagnostics(output, functions)

    # 构建问题映射
    problem_map = build_problem_map(diagnostics, functions)

    # 保存问题映射
    save_problem_map(problem_map, args.output, verbose=not args.json_only)

    if args.json_only:
        print(json.dumps(problem_map, indent=2, ensure_ascii=False))
        return problem_map

    # 打印统计
    print_statistics(diagnostics, problem_map)

    # 输出建议
    severity_list = args.severity.split(',')
    funcs_to_optimize = get_functions_to_optimize(problem_map, severity_list)

    print("\n" + "=" * 70)
    print("💡 后续步骤建议")
    print("=" * 70)
    print(f"\n1. 查看问题详情: cat {args.output}")
    print(f"2. 优化所有问题函数:")
    print(f"   python main.py optimize {' '.join(funcs_to_optimize[:5])} --rounds 3")
    print(f"3. 或基于问题映射自动优化:")
    print(f"   python main.py optimize --from-analysis {args.output}")

    # 导出函数列表模式（用于管道）
    if args.export_functions:
        severity_list = args.severity.split(',')
        funcs = get_functions_to_optimize(problem_map, severity_list)
        print(' '.join(funcs))

    return problem_map


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
