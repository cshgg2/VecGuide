#!/usr/bin/env python3
"""
VecGuide 统一入口
提供分析、优化、评估一站式工作流
"""

import os
import sys
import json
import subprocess
from typing import List, Optional

from benchmark_protocols import list_benchmark_protocol_names
from config import config, get_clang_path, get_source_file, check_clang_available, check_source_file_exists
from experiment_config import DEFAULT_EXPERIMENT_STRATEGY_CSV, PAPER_STRATEGY_CSV


class Colors:
    """终端颜色"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_banner():
    """打印启动横幅"""
    print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗
║              VecGuide: Auto-Vectorization Optimizer           ║
║                    基于大模型的代码向量化优化工具               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.ENDC}
""")


def run_analyze(args):
    """运行分析步骤"""
    print(f"\n{Colors.BOLD}🔍 步骤 1: 分析代码向量化问题{Colors.ENDC}\n")

    cmd = [
        sys.executable,
        "data_collector.py",
        "-s", args.source,
        "-c", args.clang,
        "-o", args.output
    ]

    if args.json_only:
        cmd.append("--json-only")

    result = subprocess.run(cmd)
    return result.returncode == 0


def run_optimize(args, functions: Optional[List[str]] = None):
    """运行优化步骤"""
    print(f"\n{Colors.BOLD}🚀 步骤 2: 优化代码{Colors.ENDC}\n")

    cmd = [
        sys.executable,
        "optimizer_pipeline.py",
        "-c", args.clang,
        "-r", str(args.rounds)
    ]

    if args.model:
        cmd.extend(["-m", args.model])

    if args.verbose:
        cmd.append("-v")

    if args.single_round:
        cmd.append("--single-round")

    if args.from_analysis:
        cmd.extend(["--from-analysis", args.from_analysis])
    elif functions:
        cmd.extend(functions)

    result = subprocess.run(cmd)
    return result.returncode == 0


def run_evaluate(args):
    """运行评估步骤"""
    print(f"\n{Colors.BOLD}📊 步骤 3: 评估优化结果{Colors.ENDC}\n")

    cmd = [
        sys.executable,
        "evaluate_optimization.py",
        "-c", args.clang
    ]

    if args.debug:
        cmd.append("--debug")

    if args.json:
        cmd.append("--json")

    result = subprocess.run(cmd)
    return result.returncode == 0


def run_pipeline(args):
    """运行完整流水线"""
    print_banner()

    # 检查依赖
    ok, error = check_source_file_exists(args.source)
    if not ok:
        print(f"{Colors.FAIL}❌ {error}{Colors.ENDC}")
        sys.exit(1)

    ok, error = check_clang_available(args.clang)
    if not ok:
        print(f"{Colors.FAIL}❌ {error}{Colors.ENDC}")
        sys.exit(1)

    # 步骤 1: 分析
    if not run_analyze(args):
        print(f"{Colors.FAIL}❌ 分析步骤失败{Colors.ENDC}")
        sys.exit(1)

    # 步骤 2: 优化
    problem_map_file = args.output
    functions = getattr(args, "functions", None)
    args.from_analysis = None if functions else problem_map_file

    if not run_optimize(args, functions):
        print(f"{Colors.FAIL}❌ 优化步骤失败{Colors.ENDC}")
        sys.exit(1)

    # 步骤 3: 评估
    if not run_evaluate(args):
        print(f"{Colors.WARNING}⚠️ 部分优化未完全成功，请查看详细报告{Colors.ENDC}")

    print(f"\n{Colors.GREEN}✅ 流水线执行完成！{Colors.ENDC}")
    print(f"\n{Colors.CYAN}查看结果:{Colors.ENDC}")
    print(f"  - 问题映射: {problem_map_file}")
    print(f"  - 优化后代码: optimized_*.c")
    print(f"  - 优化状态: {config.OPTIMIZATION_STATE_FILE}")


def run_and_exit(cmd):
    """执行子命令并透传退出码。"""
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="VecGuide: 基于大模型的代码向量化优化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 运行完整流水线（分析 → 优化 → 评估）
  python main.py pipeline

  # 只分析代码，生成问题映射
  python main.py analyze

  # 优化指定函数（单轮）
  python main.py optimize s111 s112 --single-round

  # 基于问题映射自动优化（多轮）
  python main.py optimize --from-analysis problem_map.json --rounds 3

  # 评估已优化的代码
  python main.py evaluate

  # 评估指定函数
  python main.py evaluate s122

  # 评估多个指定函数
  python main.py evaluate s122 s1113 s111

  # 验证 s122 最终优化结果的正确性
  python main.py verify s122

  # 验证多个函数
  python main.py verify s122 s111

  # 验证指定轮次
  python main.py verify s122 --round 1

  # 验证所有轮次
  python main.py verify s122 --all-rounds

  # 查看优化状态
  python main.py status
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # pipeline 命令
    pipeline_parser = subparsers.add_parser('pipeline', help='运行完整流水线')
    pipeline_parser.add_argument('functions', nargs='*',
                                 help='要优化的函数名。不指定时使用分析结果中的函数')
    pipeline_parser.add_argument('-s', '--source', default=get_source_file(),
                                  help=f'源文件路径 (默认: {get_source_file()})')
    pipeline_parser.add_argument('-c', '--clang', default=get_clang_path(),
                                  help=f'Clang 路径 (默认: {get_clang_path()})')
    pipeline_parser.add_argument('-o', '--output', default=config.PROBLEM_MAP_FILE,
                                  help=f'问题映射输出文件 (默认: {config.PROBLEM_MAP_FILE})')
    pipeline_parser.add_argument('-r', '--rounds', type=int, default=config.DEFAULT_MAX_ROUNDS,
                                  help=f'最大优化轮数 (默认: {config.DEFAULT_MAX_ROUNDS})')
    pipeline_parser.add_argument('-m', '--model', default=None, help='模型名称')
    pipeline_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    pipeline_parser.add_argument('--single-round', action='store_true', help='单轮优化模式')
    pipeline_parser.add_argument('--debug', action='store_true', help='调试模式')
    pipeline_parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    pipeline_parser.add_argument('--json-only', action='store_true', help='只输出 JSON')

    # analyze 命令
    analyze_parser = subparsers.add_parser('analyze', help='分析代码向量化问题')
    analyze_parser.add_argument('-s', '--source', default=get_source_file(),
                                 help=f'源文件路径 (默认: {get_source_file()})')
    analyze_parser.add_argument('-c', '--clang', default=get_clang_path(),
                                 help=f'Clang 路径 (默认: {get_clang_path()})')
    analyze_parser.add_argument('-o', '--output', default=config.PROBLEM_MAP_FILE,
                                 help=f'问题映射输出文件 (默认: {config.PROBLEM_MAP_FILE})')
    analyze_parser.add_argument('--export-functions', action='store_true',
                                 help='输出需要优化的函数名列表')
    analyze_parser.add_argument('--severity', default='high,medium',
                                 help='要包含的严重程度 (默认: high,medium)')
    analyze_parser.add_argument('--json-only', action='store_true', help='只输出 JSON')

    # optimize 命令
    optimize_parser = subparsers.add_parser('optimize', help='优化指定函数')
    optimize_parser.add_argument('functions', nargs='*', help='要优化的函数名')
    optimize_parser.add_argument('-c', '--clang', default=get_clang_path(),
                                  help=f'Clang 路径 (默认: {get_clang_path()})')
    optimize_parser.add_argument('-r', '--rounds', type=int, default=config.DEFAULT_MAX_ROUNDS,
                                  help=f'最大优化轮数 (默认: {config.DEFAULT_MAX_ROUNDS})')
    optimize_parser.add_argument('-m', '--model', default=None, help='模型名称')
    optimize_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    optimize_parser.add_argument('--single-round', action='store_true', help='单轮优化模式')
    optimize_parser.add_argument('--from-analysis', metavar='FILE',
                                  help='从问题映射文件读取要优化的函数')
    optimize_parser.add_argument('--reset', action='store_true', help='重置指定函数的优化状态')
    optimize_parser.add_argument('--clean', action='store_true', help='重置时同时删除函数目录和文件')
    optimize_parser.add_argument('--severity', default=None,
                                 help='按严重程度筛选函数 (high, medium, low, 或组合 high,medium)')
    optimize_parser.add_argument('--strategy', default='full_method',
                                 help='实验策略 (默认: full_method；旧名 ours_full 仍兼容)')
    optimize_parser.add_argument('--list-strategies', action='store_true',
                                 help='列出可用实验策略')
    optimize_parser.add_argument('--json-summary', metavar='FILE',
                                 help='将本次优化的结构化摘要写入 JSON 文件')

    # evaluate 命令
    evaluate_parser = subparsers.add_parser('evaluate', help='评估优化结果')
    evaluate_parser.add_argument('functions', nargs='*', help='要评估的函数名 (例如: s122 s1113)，可同时指定多个')
    evaluate_parser.add_argument('-c', '--clang', default=get_clang_path(),
                                  help=f'Clang 路径 (默认: {get_clang_path()})')
    evaluate_parser.add_argument('-d', '--directory', default='.',
                                  help='搜索优化后文件的目录 (默认: 当前目录)')
    evaluate_parser.add_argument('-f', '--function', help='只分析指定函数 (与位置参数等效)')
    evaluate_parser.add_argument('--debug', action='store_true', help='调试模式')
    evaluate_parser.add_argument('--json', action='store_true', help='输出 JSON 格式')

    # verify 命令
    verify_parser = subparsers.add_parser('verify', help='对优化结果进行正确性验证')
    verify_parser.add_argument('functions', nargs='*', help='要验证的函数名，支持多个。不指定时自动发现所有已优化函数')
    verify_parser.add_argument('-c', '--clang', default=get_clang_path(),
                               help=f'Clang 路径 (默认: {get_clang_path()})')
    verify_parser.add_argument('--round', type=int, default=None, metavar='N',
                               help='验证指定轮次 (例如 --round 1)')
    verify_parser.add_argument('--all-rounds', action='store_true',
                               help='验证所有保存的轮次结果')
    verify_parser.add_argument('--severity', default=None,
                               help='按严重程度筛选函数进行验证 (high, medium, low)')

    # status 命令
    status_parser = subparsers.add_parser('status', help='查看优化状态')

    # benchmark 命令
    benchmark_parser = subparsers.add_parser('benchmark', help='性能基准测试')
    benchmark_parser.add_argument('functions', nargs='*', help='要测试的函数名')
    benchmark_parser.add_argument('-c', '--clang', default=get_clang_path(),
                                  help=f'Clang 编译器路径 (默认: {get_clang_path()})')
    benchmark_parser.add_argument('--state-file', default=config.OPTIMIZATION_STATE_FILE,
                                  help=f'优化状态文件 (默认: {config.OPTIMIZATION_STATE_FILE})')
    benchmark_parser.add_argument('-o', '--output', help='JSON 结果输出文件')
    benchmark_parser.add_argument('--csv', action='store_true', help='同时导出 CSV 格式')
    benchmark_parser.add_argument('--md', '--markdown', action='store_true', help='同时生成 Markdown 报告')
    benchmark_parser.add_argument('-q', '--quiet', action='store_true', help='静默模式')
    benchmark_parser.add_argument('--benchmark-protocol', default='formal',
                                  choices=[*list_benchmark_protocol_names(), 'custom', 'auto'],
                                  help='benchmark 协议标签，默认 formal')
    benchmark_parser.add_argument('--warmup-runs', type=int, default=None,
                                  help='覆盖 benchmark 协议的 warmup 次数；覆盖后不再视为正式主表协议')
    benchmark_parser.add_argument('--timing-runs', type=int, default=None,
                                  help='覆盖 benchmark 协议的计时次数，至少为 3；覆盖后不再视为正式主表协议')
    benchmark_parser.add_argument('--batches', type=int, default=None,
                                  help='覆盖 benchmark 协议的重复批次数；覆盖后不再视为正式主表协议')

    # boundary 命令
    boundary_parser = subparsers.add_parser('boundary', help='边界条件测试')
    boundary_parser.add_argument('functions', nargs='*', help='要测试的函数名 (默认: s122 s172 s4121)')
    boundary_parser.add_argument('-c', '--clang', default=get_clang_path(),
                                 help=f'Clang 编译器路径 (默认: {get_clang_path()})')

    # experiment 命令
    experiment_parser = subparsers.add_parser('experiment', help='运行对照实验批次')
    experiment_parser.add_argument('functions', nargs='*', help='要纳入实验的函数名')
    experiment_parser.add_argument('-c', '--clang', default=get_clang_path(),
                                   help=f'Clang 路径 (默认: {get_clang_path()})')
    experiment_parser.add_argument('-m', '--model', default=None, help='模型名称')
    experiment_parser.add_argument('-r', '--rounds', type=int, default=config.DEFAULT_MAX_ROUNDS,
                                   help=f'最大优化轮数 (默认: {config.DEFAULT_MAX_ROUNDS})')
    experiment_parser.add_argument('--strategies', default=DEFAULT_EXPERIMENT_STRATEGY_CSV,
                                   help=f'逗号分隔的实验策略列表；默认 {DEFAULT_EXPERIMENT_STRATEGY_CSV}。完整投稿矩阵请显式使用 {PAPER_STRATEGY_CSV}')
    experiment_parser.add_argument('--from-analysis', metavar='FILE',
                                   help='从问题映射文件读取要优化的函数')
    experiment_parser.add_argument('--severity', default=None,
                                   help='按严重程度筛选函数')
    experiment_parser.add_argument('--run-id', default=None, help='自定义实验运行 ID')
    experiment_parser.add_argument('--cleanup-run-id', default=None,
                                   help='删除指定 run-id 的已有产物目录后退出')
    experiment_parser.add_argument('--force-clean-run-id', action='store_true',
                                   help='若目标 run-id 已存在且非空，则先删除该目录再开始实验')
    experiment_parser.add_argument('--collect-only', action='store_true',
                                   help='复用已有 run 的策略输出，只补生成论文汇总产物；不调用优化/API')
    experiment_parser.add_argument('--dry-run', action='store_true', help='只生成 manifest，不执行优化')
    experiment_parser.add_argument('--refresh-analysis', action='store_true',
                                   help='先重新生成 problem_map 再开始实验')
    experiment_parser.add_argument('--benchmark-protocol', default='formal',
                                   choices=[*list_benchmark_protocol_names(), 'custom', 'auto'],
                                   help='benchmark 协议标签，默认 formal')
    experiment_parser.add_argument('--warmup-runs', type=int, default=None,
                                   help='覆盖 benchmark 协议的 warmup 次数；覆盖后不再视为正式主表协议')
    experiment_parser.add_argument('--timing-runs', type=int, default=None,
                                   help='覆盖 benchmark 协议的计时次数，至少为 3；覆盖后不再视为正式主表协议')
    experiment_parser.add_argument('--batches', type=int, default=None,
                                   help='覆盖 benchmark 协议的重复批次数；覆盖后不再视为正式主表协议')

    # results-table 命令
    table_parser = subparsers.add_parser('results-table', help='从实验 run 生成论文结果总表')
    table_parser.add_argument('--run-dir', action='append', required=True,
                              help='实验 run 目录，可重复指定')
    table_parser.add_argument('--problem-map', default=config.PROBLEM_MAP_FILE,
                              help=f'问题映射文件 (默认: {config.PROBLEM_MAP_FILE})')
    table_parser.add_argument('--output-dir', required=True,
                              help='结果总表输出目录')
    table_parser.add_argument('--supplemental-rows', action='append', default=[],
                              help='可选 paper_results-like CSV/JSON 补充行，可重复指定')
    table_parser.add_argument('--strategies',
                              default=PAPER_STRATEGY_CSV,
                              help=f'wide 表中的投稿版策略列，逗号分隔；默认 {PAPER_STRATEGY_CSV}')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == 'pipeline':
        run_pipeline(args)
    elif args.command == 'analyze':
        # 直接调用 data_collector
        cmd = [
            sys.executable, 'data_collector.py',
            '-s', args.source,
            '-c', args.clang,
            '-o', args.output,
            '--severity', args.severity
        ]
        if args.export_functions:
            cmd.append('--export-functions')
        if args.json_only:
            cmd.append('--json-only')
        run_and_exit(cmd)
    elif args.command == 'optimize':
        # 直接调用 optimizer_pipeline
        cmd = [sys.executable, 'optimizer_pipeline.py', '-c', args.clang, '-r', str(args.rounds)]
        if args.model:
            cmd.extend(['-m', args.model])
        if args.verbose:
            cmd.append('-v')
        if args.single_round:
            cmd.append('--single-round')
        if args.from_analysis:
            cmd.extend(['--from-analysis', args.from_analysis])
        if args.reset:
            cmd.append('--reset')
        if args.clean:
            cmd.append('--clean')
        if args.severity:
            cmd.extend(['--severity', args.severity])
        if args.strategy:
            cmd.extend(['--strategy', args.strategy])
        if args.list_strategies:
            cmd.append('--list-strategies')
        if args.json_summary:
            cmd.extend(['--json-summary', args.json_summary])
        if args.functions:
            cmd.extend(args.functions)
        run_and_exit(cmd)
    elif args.command == 'evaluate':
        # 直接调用 evaluate_optimization
        cmd = [sys.executable, 'evaluate_optimization.py', '-c', args.clang, '-d', args.directory]
        if args.debug:
            cmd.append('--debug')
        if args.json:
            cmd.append('--json')
        # 优先使用 -f 参数，如果没有则使用位置参数
        if args.function:
            cmd.extend(['-f', args.function])
        elif args.functions:
            # 支持多个函数名作为位置参数
            cmd.extend(['-f', ','.join(args.functions)])
        run_and_exit(cmd)
    elif args.command == 'verify':
        cmd = [sys.executable, 'verify_cli.py', '-c', args.clang]
        if args.round is not None:
            cmd.extend(['--round', str(args.round)])
        if args.all_rounds:
            cmd.append('--all-rounds')
        if args.severity:
            cmd.extend(['--severity', args.severity])
        if args.functions:
            cmd.extend(args.functions)
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    elif args.command == 'status':
        # 显示状态
        cmd = [sys.executable, 'optimizer_pipeline.py', '--status']
        run_and_exit(cmd)
    elif args.command == 'benchmark':
        # 性能测试
        cmd = [sys.executable, 'benchmark.py', '-c', args.clang, '--state-file', args.state_file]
        if args.output:
            cmd.extend(['-o', args.output])
        if args.csv:
            cmd.append('--csv')
        if args.md:
            cmd.append('--md')
        if args.quiet:
            cmd.append('-q')
        if args.benchmark_protocol:
            cmd.extend(['--benchmark-protocol', args.benchmark_protocol])
        if args.warmup_runs is not None:
            cmd.extend(['--warmup-runs', str(args.warmup_runs)])
        if args.timing_runs is not None:
            cmd.extend(['--timing-runs', str(args.timing_runs)])
        if args.batches is not None:
            cmd.extend(['--batches', str(args.batches)])
        if args.functions:
            cmd.extend(args.functions)
        run_and_exit(cmd)
    elif args.command == 'boundary':
        # 边界条件测试
        cmd = [sys.executable, 'boundary_test.py', '-c', args.clang]
        if args.functions:
            cmd.extend(args.functions)
        run_and_exit(cmd)
    elif args.command == 'experiment':
        cmd = [sys.executable, 'experiment_runner.py', '-c', args.clang, '-r', str(args.rounds)]
        if args.model:
            cmd.extend(['-m', args.model])
        if args.strategies:
            cmd.extend(['--strategies', args.strategies])
        if args.from_analysis:
            cmd.extend(['--from-analysis', args.from_analysis])
        if args.severity:
            cmd.extend(['--severity', args.severity])
        if args.run_id:
            cmd.extend(['--run-id', args.run_id])
        if args.cleanup_run_id:
            cmd.extend(['--cleanup-run-id', args.cleanup_run_id])
        if args.force_clean_run_id:
            cmd.append('--force-clean-run-id')
        if args.collect_only:
            cmd.append('--collect-only')
        if args.dry_run:
            cmd.append('--dry-run')
        if args.refresh_analysis:
            cmd.append('--refresh-analysis')
        if args.benchmark_protocol:
            cmd.extend(['--benchmark-protocol', args.benchmark_protocol])
        if args.warmup_runs is not None:
            cmd.extend(['--warmup-runs', str(args.warmup_runs)])
        if args.timing_runs is not None:
            cmd.extend(['--timing-runs', str(args.timing_runs)])
        if args.batches is not None:
            cmd.extend(['--batches', str(args.batches)])
        if args.functions:
            cmd.extend(args.functions)
        run_and_exit(cmd)
    elif args.command == 'results-table':
        cmd = [sys.executable, 'paper_table_builder.py']
        for run_dir in args.run_dir:
            cmd.extend(['--run-dir', run_dir])
        cmd.extend(['--problem-map', args.problem_map])
        cmd.extend(['--output-dir', args.output_dir])
        for supplemental_rows in args.supplemental_rows:
            cmd.extend(['--supplemental-rows', supplemental_rows])
        cmd.extend(['--strategies', args.strategies])
        run_and_exit(cmd)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⏹️  用户中断执行{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ 程序执行出错: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
