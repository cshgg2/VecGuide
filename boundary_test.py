#!/usr/bin/env python3
"""
ACPO-LLM 边界条件测试脚本
测试 s122, s172, s4121 等函数的边界条件
"""

import os
import sys
from pathlib import Path

from config import config, check_clang_available
from state_manager import load_state, get_best_code, get_function_state
from correctness_verifier import verify_with_boundary_conditions


def get_original_code(func_name: str, state: dict = None) -> str:
    """获取函数的原始代码"""
    if state is None:
        state = load_state()
    func_state = get_function_state(func_name, state)
    return func_state.get("original_code")


def run_boundary_tests(func_names: list, clang_path: str = None) -> dict:
    """
    对指定函数运行边界条件测试
    """
    if clang_path is None:
        clang_path = config.CLANG_PATH

    state = load_state()
    results = {}

    print("=" * 70)
    print("🧪 边界条件测试")
    print("=" * 70)
    print(f"测试函数: {', '.join(func_names)}")
    print(f"编译器: {clang_path}")
    print("=" * 70)

    for func_name in func_names:
        print(f"\n📋 测试函数: {func_name}")
        print("-" * 70)

        original_code = get_original_code(func_name, state)
        optimized_code = get_best_code(func_name, state)

        if not original_code or not optimized_code:
            print(f"   ❌ 未找到代码，跳过")
            results[func_name] = {'pass': False, 'error': '代码未找到'}
            continue

        # 运行边界条件测试
        result = verify_with_boundary_conditions(
            original_code, optimized_code, func_name, clang_path
        )

        results[func_name] = result

        # 打印详细结果
        for detail in result.get('details', []):
            print(f"   {detail}")

        # 如果没有details，打印原始输出（用于调试）
        if not result.get('details'):
            print(f"   ⚠️ 无详细输出，可能测试未运行")

        status = "✅ 通过" if result['pass'] else "❌ 失败"
        print(f"\n   结果: {status} ({result['tests_passed']}/{result['total_tests']})")

    print("\n" + "=" * 70)
    print("📊 汇总报告")
    print("=" * 70)

    passed = sum(1 for r in results.values() if r.get('pass'))
    total = len(results)

    for func_name, result in results.items():
        status = "✅" if result.get('pass') else "❌"
        print(f"{status} {func_name}: {result.get('tests_passed', 0)}/{result.get('total_tests', 0)}")

    print(f"\n总计: {passed}/{total} 函数通过边界条件测试")
    print("=" * 70)

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="ACPO-LLM 边界条件测试工具"
    )
    parser.add_argument(
        "functions",
        nargs="*",
        help="要测试的函数名（默认: s122 s172 s4121）"
    )
    parser.add_argument(
        "-c", "--clang",
        default=config.CLANG_PATH,
        help=f"Clang 编译器路径 (默认: {config.CLANG_PATH})"
    )

    args = parser.parse_args()

    # 检查编译器
    ok, error = check_clang_available(args.clang)
    if not ok:
        print(f"❌ {error}")
        sys.exit(1)

    # 确定要测试的函数
    func_names = args.functions if args.functions else ["s122", "s172", "s4121"]

    # 运行测试
    results = run_boundary_tests(func_names, args.clang)

    # 返回退出码
    all_passed = all(r.get('pass') for r in results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
