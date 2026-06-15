#!/usr/bin/env python3
"""
ACPO-LLM 性能评估脚本
对比优化前后的执行时间，验证向量化带来的实际性能提升
"""

import os
import sys
import json
import csv
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Dict, List, Optional

from benchmark_protocols import (
    list_benchmark_protocol_names,
    resolve_benchmark_protocol,
    validate_benchmark_protocol_config,
)
from config import config, check_clang_available
from state_manager import load_state, get_best_code, get_function_state
from correctness_verifier import run_performance_benchmark


REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", "reports"))
BENCHMARK_RESULTS_FILE = REPORTS_DIR / "benchmark_results.json"
BENCHMARK_CSV_FILE = REPORTS_DIR / "benchmark_results.csv"

BENCHMARK_ELIGIBLE_STATUSES = {"success", "partial_success", "skipped"}


def ensure_reports_dir():
    """确保报告目录存在"""
    REPORTS_DIR.mkdir(exist_ok=True)


def safe_mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return mean(values)


def safe_median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return median(values)


def safe_stddev(values: List[float]) -> Optional[float]:
    if len(values) < 2:
        return None
    return stdev(values)


def get_original_code(func_name: str, state: Dict = None) -> Optional[str]:
    """获取函数的原始代码"""
    if state is None:
        state = load_state()
    func_state = get_function_state(func_name, state)
    return func_state.get("original_code")


def benchmark_single_function(
    func_name: str,
    state: Dict = None,
    clang_path: str = None,
    verbose: bool = True,
    force: bool = False,  # 新增：强制测试即使状态不是 success
    warmup_runs: int | None = None,
    timing_runs: int | None = None,
    batches: int | None = None,
    benchmark_protocol: str | None = "formal",
    protocol_config: Optional[Dict] = None,
) -> Dict:
    """
    对单个函数进行性能测试

    Returns:
        性能测试结果字典
    """
    if state is None:
        state = load_state()
    if clang_path is None:
        clang_path = config.CLANG_PATH
    if protocol_config is None:
        protocol_config = resolve_benchmark_protocol(
            protocol_name=benchmark_protocol,
            warmup_runs=warmup_runs,
            timing_runs=timing_runs,
            batches=batches,
        )
    validate_benchmark_protocol_config(protocol_config)

    result = {
        'func_name': func_name,
        'timestamp': datetime.now().isoformat(),
        'success': False,
        'benchmark_mode': 'optimized_vs_original',
        'original_time_ms': None,
        'optimized_time_ms': None,
        'speedup': None,
        'improvement_pct': None,
        'benchmark_protocol': protocol_config.get('protocol_name'),
        'benchmark_protocol_role': protocol_config.get('protocol_role'),
        'benchmark_protocol_display': protocol_config.get('display_name'),
        'paper_main_table_eligible': protocol_config.get('paper_main_table_eligible'),
        'benchmark_protocol_warning': protocol_config.get('warning'),
        'error': None
    }

    # 获取原始代码和优化代码
    original_code = get_original_code(func_name, state)
    optimized_code = get_best_code(func_name, state)
    func_state = get_function_state(func_name, state)
    if not optimized_code and func_state.get("status") == "skipped":
        optimized_code = original_code

    if not original_code:
        result['error'] = "未找到原始代码"
        return result

    if not optimized_code:
        result['error'] = "未找到优化代码"
        return result

    # 检查函数状态（仅在非 force 模式下）
    if not force and func_state.get('status') not in BENCHMARK_ELIGIBLE_STATUSES:
        result['error'] = f"函数状态为 {func_state.get('status')}，跳过性能测试"
        return result
    if not force and func_state.get('correctness_overall') is False:
        result['error'] = "函数正确性验证未通过，跳过性能测试"
        return result

    if verbose:
        print(f"\n🔍 测试函数: {func_name}")
        if func_state.get("status") == "skipped":
            print("   状态: 原始代码已完全向量化，跳过优化")
        else:
            print(f"   最佳轮次: 第 {func_state.get('best')} 轮")

    compare_code = optimized_code
    if func_state.get("status") == "skipped":
        compare_code = original_code
        result["benchmark_mode"] = "baseline_only"

    # 运行性能测试
    perf_result = run_performance_benchmark(
        original_code,
        compare_code,
        func_name,
        clang_path,
        warmup_runs=protocol_config["warmup_runs"],
        timing_runs=protocol_config["timing_runs"],
        batches=protocol_config["batches"],
    )

    result.update(perf_result)
    result.update(
        {
            'benchmark_protocol': protocol_config.get('protocol_name'),
            'benchmark_protocol_role': protocol_config.get('protocol_role'),
            'benchmark_protocol_display': protocol_config.get('display_name'),
            'paper_main_table_eligible': protocol_config.get('paper_main_table_eligible'),
            'benchmark_protocol_warning': protocol_config.get('warning'),
        }
    )
    if result.get("success") and func_state.get("status") == "skipped":
        result["optimized_time_ms"] = result.get("original_time_ms")
        result["optimized_time_median_ms"] = result.get("original_time_median_ms")
        result["optimized_batch_times_ms"] = list(result.get("original_batch_times_ms", []) or [])
        result["speedup"] = 1.0
        result["speedup_median"] = 1.0
        result["speedup_stddev"] = 0.0
        result["improvement_pct"] = 0.0

    if verbose and result['success']:
        arg_case_count = result.get('arg_case_count', 1)
        scope = result.get('benchmark_scope', 'batches_only')
        print(
            f"   协议: warmup={result['warmup_runs']} timing={result['timing_runs']} "
            f"batches={result['batch_count']} arg_cases={arg_case_count} scope={scope}"
        )
        print(
            f"   原始代码: {result['original_time_ms']:.3f} ms"
            f" (median={result['original_time_median_ms']:.3f})"
        )
        print(
            f"   优化代码: {result['optimized_time_ms']:.3f} ms"
            f" (median={result['optimized_time_median_ms']:.3f})"
        )
        speedup_stddev = result.get('speedup_stddev')
        speedup_stddev_text = f", std={speedup_stddev:.4f}" if speedup_stddev is not None else ""
        print(
            f"   加速比:   {result['speedup']:.2f}x ({result['improvement_pct']:+.1f}%)"
            f" [median={result['speedup_median']:.2f}x{speedup_stddev_text}]"
        )

    if verbose and not result['success']:
        print(f"   ❌ 失败: {result.get('error', '未知错误')[:100]}")

    return result


def benchmark_functions(
    func_names: List[str],
    state: Dict = None,
    clang_path: str = None,
    verbose: bool = True,
    warmup_runs: int | None = None,
    timing_runs: int | None = None,
    batches: int | None = None,
    benchmark_protocol: str | None = "formal",
    protocol_config: Optional[Dict] = None,
) -> List[Dict]:
    """
    批量测试多个函数的性能

    Returns:
        性能测试结果列表
    """
    if state is None:
        state = load_state()
    if clang_path is None:
        clang_path = config.CLANG_PATH
    if protocol_config is None:
        protocol_config = resolve_benchmark_protocol(
            protocol_name=benchmark_protocol,
            warmup_runs=warmup_runs,
            timing_runs=timing_runs,
            batches=batches,
        )
    validate_benchmark_protocol_config(protocol_config)

    results = []

    if verbose:
        print("=" * 70)
        print("🚀 性能评估开始")
        print("=" * 70)
        print(f"测试函数数量: {len(func_names)}")
        print(f"编译器: {clang_path}")
        print(
            f"协议: {protocol_config['display_name']} "
            f"role={protocol_config['protocol_role']} "
            f"main_table_eligible={protocol_config['paper_main_table_eligible']}"
        )

    for i, func_name in enumerate(func_names, 1):
        if verbose:
            print(f"\n[{i}/{len(func_names)}] ", end="")

        result = benchmark_single_function(
            func_name,
            state,
            clang_path,
            verbose,
            warmup_runs=protocol_config["warmup_runs"],
            timing_runs=protocol_config["timing_runs"],
            batches=protocol_config["batches"],
            benchmark_protocol=benchmark_protocol,
            protocol_config=protocol_config,
        )
        results.append(result)

    if verbose:
        print("\n" + "=" * 70)
        print("✅ 性能评估完成")
        print("=" * 70)

    return results


def save_benchmark_results(results: List[Dict], output_file: str = None):
    """保存性能测试结果到 JSON 文件"""
    if output_file is None:
        output_file = BENCHMARK_RESULTS_FILE

    ensure_reports_dir()

    # 读取已有结果（如果存在）
    existing_data = {}
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                existing_data = json.load(f)
        except:
            existing_data = {}

    # 更新结果
    if 'results' not in existing_data:
        existing_data['results'] = {}

    existing_data['generated_at'] = datetime.now().isoformat()
    if results:
        first = results[0]
        existing_data['benchmark_config'] = {
            'benchmark_protocol': first.get('benchmark_protocol'),
            'benchmark_protocol_role': first.get('benchmark_protocol_role'),
            'benchmark_protocol_display': first.get('benchmark_protocol_display'),
            'paper_main_table_eligible': first.get('paper_main_table_eligible'),
            'benchmark_protocol_warning': first.get('benchmark_protocol_warning'),
            'warmup_runs': first.get('warmup_runs'),
            'timing_runs': first.get('timing_runs'),
            'batches': first.get('batch_count'),
        }

    for result in results:
        if result['success']:
            func_name = result['func_name']
            existing_data['results'][func_name] = {
                'timestamp': result['timestamp'],
                'benchmark_protocol': result.get('benchmark_protocol'),
                'benchmark_protocol_role': result.get('benchmark_protocol_role'),
                'benchmark_protocol_display': result.get('benchmark_protocol_display'),
                'paper_main_table_eligible': result.get('paper_main_table_eligible'),
                'benchmark_protocol_warning': result.get('benchmark_protocol_warning'),
                'warmup_runs': result.get('warmup_runs'),
                'timing_runs': result.get('timing_runs'),
                'batch_count': result.get('batch_count'),
                'arg_case_count': result.get('arg_case_count'),
                'sample_count': result.get('sample_count'),
                'benchmark_scope': result.get('benchmark_scope'),
                'arg_cases': result.get('arg_cases', []),
                'original_time_ms': result['original_time_ms'],
                'optimized_time_ms': result['optimized_time_ms'],
                'speedup': result['speedup'],
                'improvement_pct': result['improvement_pct'],
                'original_time_median_ms': result.get('original_time_median_ms'),
                'optimized_time_median_ms': result.get('optimized_time_median_ms'),
                'speedup_median': result.get('speedup_median'),
                'speedup_stddev': result.get('speedup_stddev'),
                'improvement_pct_stddev': result.get('improvement_pct_stddev'),
                'arg_case_results': result.get('arg_case_results', []),
                'batches': result.get('batches', []),
            }

    # 保存到文件
    with open(output_file, 'w') as f:
        json.dump(existing_data, f, indent=2)

    print(f"\n💾 结果已保存到: {output_file}")


def export_to_csv(results: List[Dict], output_file: str = None):
    """导出结果到 CSV 文件"""
    if output_file is None:
        output_file = BENCHMARK_CSV_FILE

    ensure_reports_dir()

    # 准备数据
    rows = []
    for r in results:
        if r['success']:
            rows.append({
                'func_name': r['func_name'],
                'benchmark_protocol': r.get('benchmark_protocol'),
                'benchmark_protocol_role': r.get('benchmark_protocol_role'),
                'paper_main_table_eligible': r.get('paper_main_table_eligible'),
                'warmup_runs': r.get('warmup_runs'),
                'timing_runs': r.get('timing_runs'),
                'batch_count': r.get('batch_count'),
                'arg_case_count': r.get('arg_case_count'),
                'original_time_ms': f"{r['original_time_ms']:.6f}",
                'optimized_time_ms': f"{r['optimized_time_ms']:.6f}",
                'speedup': f"{r['speedup']:.4f}",
                'improvement_pct': f"{r['improvement_pct']:.2f}",
                'speedup_median': f"{r['speedup_median']:.4f}",
                'speedup_stddev': "" if r.get('speedup_stddev') is None else f"{r['speedup_stddev']:.6f}",
            })

    # 写入 CSV
    with open(output_file, 'w', newline='') as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    print(f"💾 CSV 已导出到: {output_file}")


def print_summary(results: List[Dict]):
    """打印性能测试汇总报告"""
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print("\n" + "=" * 70)
    print("📊 性能评估汇总报告")
    print("=" * 70)

    if not successful:
        print("\n❌ 没有成功的测试结果")
        return

    # 排序：按加速比降序
    successful.sort(key=lambda x: x['speedup'], reverse=True)

    print(f"\n{'函数名':<12} {'原始(ms)':<12} {'优化(ms)':<12} {'加速比':<10} {'提升':<10}")
    print("-" * 70)

    for r in successful:
        status = "✅" if r['speedup'] > 1.0 else "⚠️"
        print(f"{r['func_name']:<12} {r['original_time_ms']:<12.3f} "
              f"{r['optimized_time_ms']:<12.3f} {r['speedup']:<10.2f} "
              f"{r['improvement_pct']:<+9.1f}% {status}")

    print("-" * 70)

    # 统计信息
    speedups = [r['speedup'] for r in successful]
    improvements = [r['improvement_pct'] for r in successful]
    speedup_stddevs = [r['speedup_stddev'] for r in successful if r.get('speedup_stddev') is not None]

    print(f"\n📈 统计信息:")
    print(f"   测试函数数: {len(results)}")
    print(f"   成功: {len(successful)}, 失败: {len(failed)}")
    print(f"   平均加速比: {safe_mean(speedups):.2f}x")
    print(f"   中位加速比: {safe_median(speedups):.2f}x")
    print(f"   最大加速比: {max(speedups):.2f}x ({max(successful, key=lambda x: x['speedup'])['func_name']})")
    print(f"   最小加速比: {min(speedups):.2f}x ({min(successful, key=lambda x: x['speedup'])['func_name']})")
    print(f"   平均性能提升: {safe_mean(improvements):+.1f}%")
    if speedup_stddevs:
        print(f"   函数内 speedup std 平均值: {safe_mean(speedup_stddevs):.4f}")

    # 负优化统计
    negative = [r for r in successful if r['speedup'] < 1.0]
    if negative:
        print(f"\n⚠️  负优化函数 ({len(negative)} 个):")
        for r in negative:
            print(f"   - {r['func_name']}: {r['speedup']:.2f}x ({r['improvement_pct']:+.1f}%)")

    print("\n" + "=" * 70)


def generate_markdown_report(results: List[Dict], output_file: str = None):
    """生成 Markdown 格式的性能报告"""
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = REPORTS_DIR / f"performance_report_{timestamp}.md"

    ensure_reports_dir()

    successful = [r for r in results if r['success']]
    successful.sort(key=lambda x: x['speedup'], reverse=True)

    lines = []
    lines.append("# 性能评估报告")
    lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"\n## 测试摘要")
    lines.append(f"\n- 测试函数数: {len(results)}")
    lines.append(f"- 成功: {len(successful)}")
    lines.append(f"- 失败: {len(results) - len(successful)}")
    if results:
        first = results[0]
        lines.append(
            f"- benchmark 协议: {first.get('benchmark_protocol_display') or first.get('benchmark_protocol')}, "
            f"role={first.get('benchmark_protocol_role', '-')}, "
            f"main_table_eligible={first.get('paper_main_table_eligible', False)}, "
            f"warmup={first.get('warmup_runs', '-')}, "
            f"timing={first.get('timing_runs', '-')}, batches={first.get('batch_count', '-')}, "
            f"arg_cases={first.get('arg_case_count', 1)}"
        )

    if successful:
        speedups = [r['speedup'] for r in successful]
        lines.append(f"\n## 统计结果")
        lines.append(f"\n| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 平均加速比 | {safe_mean(speedups):.2f}x |")
        lines.append(f"| 中位加速比 | {safe_median(speedups):.2f}x |")
        lines.append(f"| 最大加速比 | {max(speedups):.2f}x ({max(successful, key=lambda x: x['speedup'])['func_name']}) |")
        lines.append(f"| 最小加速比 | {min(speedups):.2f}x ({min(successful, key=lambda x: x['speedup'])['func_name']}) |")

        lines.append(f"\n## 详细结果")
        lines.append(f"\n| 函数名 | 协议 | 原始时间(ms) | 优化时间(ms) | 加速比 | 说明 |")
        lines.append(f"|--------|------|-------------|-------------|--------|------|")

        for r in successful:
            status_icon = "✅" if r['speedup'] > 1.0 else "⚠️"
            protocol = (
                f"{r.get('benchmark_protocol', 'unknown')} "
                f"w{r.get('warmup_runs')}/t{r.get('timing_runs')}/"
                f"b{r.get('batch_count')}/c{r.get('arg_case_count', 1)}"
            )
            std_text = ""
            if r.get('speedup_stddev') is not None:
                std_text = f", std={r['speedup_stddev']:.4f}"
            lines.append(
                f"| {r['func_name']} | {protocol} | {r['original_time_ms']:.3f} | "
                f"{r['optimized_time_ms']:.3f} | {r['speedup']:.2f}x | "
                f"{r['improvement_pct']:+.1f}% {status_icon}, median={r['speedup_median']:.2f}x{std_text} |"
            )

        # 负优化列表
        negative = [r for r in successful if r['speedup'] < 1.0]
        if negative:
            lines.append(f"\n## ⚠️ 负优化函数")
            for r in negative:
                lines.append(f"\n- **{r['func_name']}**: {r['speedup']:.2f}x ({r['improvement_pct']:+.1f}%)")

    lines.append("\n---\n*Generated by ACPO-LLM Benchmark Tool*\n")

    with open(output_file, 'w') as f:
        f.write('\n'.join(lines))

    print(f"📝 Markdown 报告已生成: {output_file}")


def main():
    """主程序入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="ACPO-LLM 性能评估工具 - 对比优化前后执行时间"
    )
    parser.add_argument(
        "functions",
        nargs="*",
        help="要测试的函数名（不指定则测试所有已优化成功的函数）"
    )
    parser.add_argument(
        "-c", "--clang",
        default=config.CLANG_PATH,
        help=f"Clang 编译器路径 (默认: {config.CLANG_PATH})"
    )
    parser.add_argument(
        "--state-file",
        default=config.OPTIMIZATION_STATE_FILE,
        help=f"优化状态文件 (默认: {config.OPTIMIZATION_STATE_FILE})"
    )
    parser.add_argument(
        "-o", "--output",
        help="JSON 结果输出文件"
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="同时导出 CSV 格式"
    )
    parser.add_argument(
        "--md", "--markdown",
        action="store_true",
        help="同时生成 Markdown 报告"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="静默模式，只输出汇总"
    )
    parser.add_argument(
        "--benchmark-protocol",
        default="formal",
        choices=[*list_benchmark_protocol_names(), "custom", "auto"],
        help="benchmark 协议标签，默认 formal"
    )
    parser.add_argument(
        "--warmup-runs",
        type=int,
        default=None,
        help="覆盖 benchmark 协议的 warmup 次数；覆盖后不再视为正式主表协议"
    )
    parser.add_argument(
        "--timing-runs",
        type=int,
        default=None,
        help="覆盖 benchmark 协议的计时次数，至少为 3；覆盖后不再视为正式主表协议"
    )
    parser.add_argument(
        "--batches",
        type=int,
        default=None,
        help="覆盖 benchmark 协议的重复批次数；覆盖后不再视为正式主表协议"
    )

    args = parser.parse_args()

    # 检查编译器
    ok, error = check_clang_available(args.clang)
    if not ok:
        print(f"❌ {error}")
        sys.exit(1)

    # 加载状态
    if not os.path.exists(args.state_file):
        print(f"❌ 优化状态文件不存在: {args.state_file}")
        sys.exit(1)
    state = load_state(args.state_file)
    if not state:
        print(f"❌ 无法加载优化状态文件: {args.state_file}")
        sys.exit(1)

    # 确定要测试的函数
    if args.functions:
        func_names = args.functions
    else:
        # 测试所有成功/部分成功的函数
        func_names = [
            name for name, info in state.items()
            if isinstance(info, dict)
            and info.get('status') in BENCHMARK_ELIGIBLE_STATUSES
            and info.get('correctness_overall') is not False
        ]
        if not args.quiet:
            print(f"自动选择 {len(func_names)} 个可评测函数（success + partial_success）")

    if not func_names:
        print("❌ 没有可测试的函数")
        sys.exit(1)
    try:
        protocol_config = resolve_benchmark_protocol(
            protocol_name=args.benchmark_protocol,
            warmup_runs=args.warmup_runs,
            timing_runs=args.timing_runs,
            batches=args.batches,
        )
        validate_benchmark_protocol_config(protocol_config)
    except ValueError as exc:
        print(f"❌ {exc}")
        sys.exit(1)

    # 运行性能测试
    results = benchmark_functions(
        func_names,
        state=state,
        clang_path=args.clang,
        verbose=not args.quiet,
        warmup_runs=protocol_config["warmup_runs"],
        timing_runs=protocol_config["timing_runs"],
        batches=protocol_config["batches"],
        benchmark_protocol=args.benchmark_protocol,
        protocol_config=protocol_config,
    )

    # 打印汇总
    if not args.quiet:
        print_summary(results)

    # 保存结果
    save_benchmark_results(results, args.output)

    # 导出 CSV
    if args.csv:
        export_to_csv(results)

    # 生成 Markdown 报告
    if args.md:
        generate_markdown_report(results)

    # 静默模式下输出简要信息
    if args.quiet:
        successful = [r for r in results if r['success']]
        if successful:
            speedups = [r['speedup'] for r in successful]
            avg_speedup = safe_mean(speedups)
            median_speedup = safe_median(speedups)
            print(
                f"平均加速比: {avg_speedup:.2f}x, 中位加速比: {median_speedup:.2f}x "
                f"({len(successful)}/{len(results)} 成功)"
            )


if __name__ == "__main__":
    main()
