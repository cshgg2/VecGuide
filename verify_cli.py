#!/usr/bin/env python3
"""
ACPO-LLM 正确性验证 CLI
============================
对已优化的函数独立执行三层正确性验证：
  1. 编译检查
  2. 语义等价性（校验和比对）
  3. 多输入运行时测试

用法示例:
  python verify_cli.py s122
  python verify_cli.py s122 s111
  python verify_cli.py s122 --round 1
  python verify_cli.py s122 --all-rounds
  python verify_cli.py s122 -c /path/to/clang
"""

import os
import sys
import argparse
import glob
import json
import re

from config import config, get_clang_path
from correctness_verifier import full_correctness_verification, format_verification_report
from logger import section, subsection, info, success, failure, warning_icon


# ──────────────────────────────────────────────
# 文件路径辅助
# ──────────────────────────────────────────────

def _origin_path(func_name: str) -> str:
    return _first_existing(_artifact_candidates(func_name, "_origin"))


def _final_path(func_name: str) -> str:
    return _first_existing(_artifact_candidates(func_name, ""))


def _round_path(func_name: str, round_num: int) -> str:
    return _first_existing(_artifact_candidates(func_name, f"_round{round_num}"))


def _all_round_paths(func_name: str):
    """返回该函数所有 _roundN.c 文件路径（按轮次升序）"""
    prefix = config.OPTIMIZED_FILE_PREFIX
    prefix_name = _prefix_name()
    patterns = [
        os.path.join(f"{prefix}{func_name}", f"{prefix_name}{func_name}_round*.c"),
        f"{prefix}{func_name}_round*.c",
    ]
    files = sorted({path for pattern in patterns for path in glob.glob(pattern)})
    return files


def _prefix_name() -> str:
    """返回文件名层面的优化前缀，兼容 OPTIMIZED_FILE_PREFIX 为绝对路径的实验模式。"""
    return os.path.basename(config.OPTIMIZED_FILE_PREFIX.rstrip(os.sep)) or config.OPTIMIZED_FILE_PREFIX


def _artifact_candidates(func_name: str, suffix: str):
    prefix = config.OPTIMIZED_FILE_PREFIX
    prefix_name = _prefix_name()
    return [
        os.path.join(f"{prefix}{func_name}", f"{prefix_name}{func_name}{suffix}.c"),
        f"{prefix}{func_name}{suffix}.c",
    ]


def _first_existing(paths):
    for path in paths:
        if os.path.exists(path):
            return path
    return paths[0]


def _strip_optimized_prefix(stem: str) -> str:
    prefix = _prefix_name()
    if stem.startswith(prefix):
        return stem[len(prefix):]
    if stem.startswith("optimized_"):
        return stem[len("optimized_"):]
    return stem


def _round_number_from_path(file_path: str):
    match = re.search(r"_round(\d+)\.c$", os.path.basename(file_path))
    if not match:
        return None
    return int(match.group(1))


def _load_function_state(func_name: str):
    try:
        from state_manager import load_state
        state = load_state()
    except Exception as exc:
        return None, f"无法加载 optimization_state.json: {exc}"

    func_state = state.get(func_name)
    if not isinstance(func_state, dict):
        return None, "状态文件中没有该函数"
    return func_state, None


def _state_round_count(func_name: str) -> int:
    func_state, _ = _load_function_state(func_name)
    if not func_state:
        return 0
    return len(func_state.get("rounds") or [])


def _state_codes_for_target(func_name: str, round_num: int | None = None):
    func_state, error = _load_function_state(func_name)
    if error:
        return None, None, "", error

    original_code = func_state.get("original_code")
    if not original_code:
        return None, None, "", "状态文件中缺少 original_code"

    rounds = func_state.get("rounds") or []
    if round_num is not None:
        if round_num < 1 or round_num > len(rounds):
            return None, None, "", f"状态文件中没有 round {round_num}"
        target_code = rounds[round_num - 1].get("code")
        if not target_code:
            return None, None, "", f"状态文件 round {round_num} 缺少 code"
        return original_code, target_code, f"optimization_state.json round {round_num}", None

    if func_state.get("status") == "skipped":
        return original_code, original_code, "optimization_state.json original_code (skipped)", None

    best_round = func_state.get("best")
    if isinstance(best_round, int) and 1 <= best_round <= len(rounds):
        target_code = rounds[best_round - 1].get("code")
        if target_code:
            return original_code, target_code, f"optimization_state.json best round {best_round}", None

    for round_record in reversed(rounds):
        target_code = round_record.get("code")
        if target_code:
            return (
                original_code,
                target_code,
                f"optimization_state.json round {round_record.get('round', '?')}",
                None,
            )

    return None, None, "", "状态文件中没有可验证代码"


def _state_discover_functions():
    try:
        from state_manager import load_state
        state = load_state()
    except Exception:
        return []

    functions = []
    for func_name, func_state in state.items():
        if not isinstance(func_state, dict):
            continue
        if not func_state.get("original_code"):
            continue
        if func_state.get("status") == "skipped":
            functions.append(func_name)
            continue
        best_round = func_state.get("best")
        rounds = func_state.get("rounds") or []
        if isinstance(best_round, int) and 1 <= best_round <= len(rounds):
            if rounds[best_round - 1].get("code"):
                functions.append(func_name)
    return sorted(set(functions))


# ──────────────────────────────────────────────
# 核心：验证单个目标文件
# ──────────────────────────────────────────────

def verify_codes(
    func_name: str,
    original_code: str,
    optimized_code: str,
    clang_path: str,
    label: str = "",
    source_label: str = "",
) -> bool:
    """对两段代码执行三层验证。"""
    tag = f" [{label}]" if label else ""
    if source_label:
        info(f"代码来源: {source_label}")

    report = full_correctness_verification(original_code, optimized_code, func_name, clang_path)

    report_text = format_verification_report(report)
    for line in report_text.split('\n'):
        if line.strip():
            info(line)

    passed = report['overall']
    if passed:
        success(f"{func_name}{tag}: 正确性验证通过 ✅")
    else:
        warning_icon(f"{func_name}{tag}: 正确性验证失败 ❌")

    return passed


def verify_from_state(func_name: str, clang_path: str, round_num: int | None = None, label: str = "") -> bool:
    """文件产物缺失时，从 optimization_state.json 回退验证。"""
    original_code, target_code, source_label, error = _state_codes_for_target(func_name, round_num=round_num)
    if error:
        failure(f"{func_name}: 无法从状态文件验证: {error}")
        return False
    return verify_codes(
        func_name,
        original_code,
        target_code,
        clang_path,
        label=label,
        source_label=source_label,
    )


def verify_file(func_name: str, origin_file: str, target_file: str, clang_path: str, label: str = "") -> bool:
    """
    读取原始文件和目标文件，执行三层验证，打印报告。
    返回 True 表示整体通过。
    """
    tag = f" [{label}]" if label else ""

    # 读取文件
    for path, desc in [(origin_file, "原始文件"), (target_file, "目标文件")]:
        if not os.path.exists(path):
            failure(f"{func_name}{tag}: {desc}不存在: {path}")
            return False

    with open(origin_file, 'r') as f:
        original_code = f.read()
    with open(target_file, 'r') as f:
        optimized_code = f.read()

    info(f"原始文件: {origin_file}")
    info(f"目标文件: {target_file}")
    return verify_codes(func_name, original_code, optimized_code, clang_path, label=label)


def verify_file_with_state_origin(
    func_name: str,
    origin_file: str,
    target_file: str,
    clang_path: str,
    label: str = "",
) -> bool:
    """优先用文件验证；若目标文件存在但 origin 文件缺失，则从状态文件补原始代码。"""
    if os.path.exists(origin_file):
        return verify_file(func_name, origin_file, target_file, clang_path, label=label)

    if not os.path.exists(target_file):
        tag = f" [{label}]" if label else ""
        failure(f"{func_name}{tag}: 目标文件不存在: {target_file}")
        return False

    func_state, error = _load_function_state(func_name)
    if error:
        failure(f"{func_name}: 无法从状态文件补充原始代码: {error}")
        return False

    original_code = func_state.get("original_code")
    if not original_code:
        failure(f"{func_name}: 状态文件中缺少 original_code，无法验证文件目标")
        return False

    with open(target_file, 'r') as f:
        optimized_code = f.read()

    info(f"原始代码来源: optimization_state.json original_code")
    info(f"目标文件: {target_file}")
    return verify_codes(
        func_name,
        original_code,
        optimized_code,
        clang_path,
        label=label,
    )


# ──────────────────────────────────────────────
# 命令行入口
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ACPO-LLM 正确性验证工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 验证 s122 最终优化结果
  python verify_cli.py s122

  # 同时验证多个函数
  python verify_cli.py s122 s111 s113

  # 验证第 1 轮的结果
  python verify_cli.py s122 --round 1

  # 验证所有轮次
  python verify_cli.py s122 --all-rounds

  # 指定 clang 路径
  python verify_cli.py s122 -c /usr/bin/clang-17
        """
    )

    parser.add_argument('functions', nargs='*', help='要验证的函数名，支持多个。不指定时自动发现所有已优化函数')
    parser.add_argument('-c', '--clang', default=get_clang_path(),
                        help=f'Clang 路径 (默认: {get_clang_path()})')
    parser.add_argument('--round', type=int, default=None, metavar='N',
                        help='验证指定轮次的结果 (例如 --round 1)')
    parser.add_argument('--all-rounds', action='store_true',
                        help='验证所有保存的轮次结果')
    parser.add_argument('--severity', default=None,
                        help='按严重程度筛选函数进行验证 (例如: high, medium, low, 或组合 high,medium)')

    args = parser.parse_args()

    # 检查 clang
    if not os.path.isfile(args.clang):
        print(f"❌ Clang 不存在: {args.clang}", file=sys.stderr)
        sys.exit(1)

    # 确定要验证的函数列表
    functions_to_verify = []
    
    if args.functions:
        # 使用命令行指定的函数
        functions_to_verify = args.functions
    elif args.severity:
        # 按严重程度从 problem_map.json 筛选
        problem_map_file = config.PROBLEM_MAP_FILE
        if not os.path.exists(problem_map_file):
            failure(f"问题映射文件不存在: {problem_map_file}")
            sys.exit(1)
        
        try:
            with open(problem_map_file, 'r') as f:
                problem_map = json.load(f)
            
            # 解析严重程度参数
            severity_filter = [s.strip().lower() for s in args.severity.split(',')]
            section(f"按严重程度筛选函数: {', '.join(severity_filter)}")
            
            # 同时检查是否有优化结果文件
            for func_name, info_dict in problem_map.items():
                severity = info_dict.get('severity', 'low')
                if severity in severity_filter:
                    # 检查是否有优化结果
                    final_file = _final_path(func_name)
                    origin_file = _origin_path(func_name)
                    state_original, state_target, _, _ = _state_codes_for_target(func_name)
                    if (os.path.exists(final_file) and os.path.exists(origin_file)) or (
                        state_original and state_target
                    ):
                        functions_to_verify.append(func_name)
            
            # 按严重程度排序
            severity_order = {'high': 0, 'medium': 1, 'low': 2}
            functions_to_verify.sort(
                key=lambda x: (severity_order.get(problem_map.get(x, {}).get('severity', 'low'), 3), x)
            )
            
            if functions_to_verify:
                info(f"找到 {len(functions_to_verify)} 个已优化的函数需要验证")
            else:
                warning_icon(f"未找到匹配筛选条件的已优化函数")
                sys.exit(0)
                
        except Exception as e:
            failure(f"读取问题映射文件失败: {e}")
            sys.exit(1)
    else:
        # 自动发现所有已优化的函数
        import glob
        
        # 从目录结构中发现（新结构）
        for dir_path in glob.glob(f"{config.OPTIMIZED_FILE_PREFIX}*/"):
            func_name = _strip_optimized_prefix(os.path.basename(dir_path.rstrip('/')))
            if func_name:
                # 检查是否有最终结果和原始文件
                final_file = _final_path(func_name)
                origin_file = _origin_path(func_name)
                if os.path.exists(final_file) and os.path.exists(origin_file):
                    functions_to_verify.append(func_name)
        
        # 从旧结构文件中发现
        for file_path in glob.glob(f"{config.OPTIMIZED_FILE_PREFIX}*.c"):
            stem = os.path.basename(file_path).replace('.c', '')
            func_name = _strip_optimized_prefix(stem)
            if func_name and '_origin' not in func_name and '_round' not in func_name:
                if func_name not in functions_to_verify:
                    # 检查是否有对应的原始文件
                    origin_file = _origin_path(func_name)
                    if os.path.exists(file_path) and os.path.exists(origin_file):
                        functions_to_verify.append(func_name)

        # 文件产物可能被清理，但状态文件仍保留了 original_code 和 best round。
        functions_to_verify.extend(_state_discover_functions())
        
        functions_to_verify = sorted(set(functions_to_verify))
        
        if functions_to_verify:
            section("自动发现已优化函数")
            info(f"发现 {len(functions_to_verify)} 个已优化的函数:")
            for func_name in functions_to_verify:
                info(f"  • {func_name}")
        else:
            warning_icon("未发现任何已优化的函数")
            sys.exit(0)

    all_passed = True

    for func_name in functions_to_verify:
        section(f"验证函数: {func_name}")

        origin_file = _origin_path(func_name)

        if args.all_rounds:
            # 验证所有轮次
            round_files = _all_round_paths(func_name)
            state_round_count = _state_round_count(func_name)
            if not round_files and state_round_count == 0:
                warning_icon(f"{func_name}: 未找到任何轮次文件或状态轮次")
                all_passed = False
                continue

            info(f"找到 {len(round_files)} 个轮次文件，{state_round_count} 个状态轮次")
            round_file_map = {}
            for rpath in round_files:
                round_num = _round_number_from_path(rpath)
                if round_num is None:
                    warning_icon(f"{func_name}: 无法识别轮次文件名，跳过: {rpath}")
                    continue
                round_file_map[round_num] = rpath

            round_numbers = sorted(set(round_file_map) | set(range(1, state_round_count + 1)))
            for round_num in round_numbers:
                round_label = f"round{round_num}"
                rpath = round_file_map.get(round_num)
                if rpath:
                    ok = verify_file_with_state_origin(func_name, origin_file, rpath, args.clang, label=round_label)
                else:
                    ok = verify_from_state(
                        func_name,
                        args.clang,
                        round_num=round_num,
                        label=round_label,
                    )
                if not ok:
                    all_passed = False

        elif args.round is not None:
            # 验证指定轮次
            target_file = _round_path(func_name, args.round)
            if os.path.exists(target_file):
                ok = verify_file_with_state_origin(func_name, origin_file, target_file, args.clang, label=f"round{args.round}")
            else:
                ok = verify_from_state(
                    func_name,
                    args.clang,
                    round_num=args.round,
                    label=f"round{args.round}",
                )
            if not ok:
                all_passed = False

        else:
            # 验证最终结果
            target_file = _final_path(func_name)
            if os.path.exists(target_file):
                ok = verify_file_with_state_origin(func_name, origin_file, target_file, args.clang)
            else:
                ok = verify_from_state(func_name, args.clang)
            if not ok:
                all_passed = False

    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
