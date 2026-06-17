#!/usr/bin/env python3
"""
实验运行器
==========
为 baseline / full method / ablation 提供统一的运行入口和产物隔离。
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Dict, List

from benchmark_protocols import (
    list_benchmark_protocol_names,
    resolve_benchmark_protocol,
    validate_benchmark_protocol_config,
)
from config import config, get_clang_path, get_model_name
from correctness_verifier import full_correctness_verification, run_performance_benchmark
from data_collector import get_functions_to_optimize
from evaluate_optimization import analyze_single_function, extract_function_code
from experiment_config import DEFAULT_EXPERIMENT_STRATEGY_CSV, get_experiment_strategy, list_experiment_strategies
from state_manager import get_best_code, load_state


RUNS_ROOT = Path("experiments") / "runs"
COMPARISON_SPEEDUP_TOLERANCE = 0.02


def generate_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def emit_progress(message: str) -> None:
    print(message, flush=True)


def parse_strategy_names(raw: str) -> List[str]:
    names = [part.strip() for part in raw.split(",") if part.strip()]
    if not names:
        raise ValueError("至少需要一个实验策略")
    # 去重但保留顺序
    return list(dict.fromkeys(names))


def cleanup_run_dir(repo_root: Path, run_id: str) -> Path:
    run_dir = (repo_root / RUNS_ROOT / run_id).resolve()
    runs_root = (repo_root / RUNS_ROOT).resolve()
    if runs_root not in run_dir.parents:
        raise ValueError(f"run-id 非法，拒绝清理目录: {run_id}")
    if run_dir.exists():
        shutil.rmtree(run_dir)
    return run_dir


def load_problem_map(problem_map_file: Path) -> Dict:
    with open(problem_map_file, "r", encoding="utf-8") as f:
        return json.load(f)


def build_benchmark_config(
    warmup_runs: int | None,
    timing_runs: int | None,
    batches: int | None,
    protocol_name: str | None = "formal",
) -> Dict:
    benchmark_config = resolve_benchmark_protocol(
        protocol_name=protocol_name,
        warmup_runs=warmup_runs,
        timing_runs=timing_runs,
        batches=batches,
    )
    validate_benchmark_protocol_config(benchmark_config)
    return benchmark_config


def hash_file(path: Path | None) -> str | None:
    if path is None or not path.exists() or not path.is_file():
        return None

    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def capture_command_output(cmd: List[str], cwd: Path | None = None) -> str | None:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None
    return result.stdout.strip()


def resolve_functions(args, problem_map_file: Path | None) -> List[str]:
    if args.functions:
        return args.functions

    if problem_map_file is None or not problem_map_file.exists():
        raise ValueError("未指定函数列表，且没有可用的问题映射文件")

    problem_map = load_problem_map(problem_map_file)
    if args.severity:
        severity_filter = [part.strip().lower() for part in args.severity.split(",") if part.strip()]
    else:
        severity_filter = ["high", "medium"]

    functions = get_functions_to_optimize(problem_map, severity_filter)
    if not functions:
        raise ValueError("根据当前 problem_map 和严重程度筛选后，没有可用函数")
    return functions


def run_analysis(repo_root: Path, clang_path: str, output_file: Path) -> None:
    cmd = [
        sys.executable,
        "data_collector.py",
        "-c", clang_path,
        "-o", str(output_file),
    ]
    result = subprocess.run(cmd, cwd=repo_root)
    if result.returncode != 0:
        raise RuntimeError(f"分析失败，退出码: {result.returncode}")


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def write_csv(path: Path, rows: List[Dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def public_path(path: Path | str | None, base_dir: Path | None = None) -> str | None:
    """Return a stable artifact path without machine-specific absolute prefixes."""
    if path is None:
        return None

    item = Path(path)
    if base_dir is not None:
        try:
            return item.relative_to(base_dir).as_posix()
        except ValueError:
            pass

    try:
        return item.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return item.as_posix() if not item.is_absolute() else item.name


def path_payload(path: Path | str, base_dir: Path | None = None) -> Dict:
    item = Path(path)
    return {
        "path": public_path(item, base_dir=base_dir),
        "exists": item.exists(),
        "is_dir": item.is_dir(),
        "sha256": hash_file(item) if item.exists() and item.is_file() else None,
    }


def safe_mean(values: List[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def safe_median(values: List[float]) -> float | None:
    if not values:
        return None
    return median(values)


def benchmark_row_is_comparable(row: Dict | None) -> bool:
    return bool(
        row
        and row.get("status") != "skipped"
        and row.get("correctness_overall")
        and row.get("benchmark_success")
        and row.get("speedup") is not None
    )


def classify_observed_outcome(row: Dict) -> str:
    tolerance = COMPARISON_SPEEDUP_TOLERANCE
    speedup = row.get("speedup")

    if row.get("strategy") == "origin":
        if not row.get("benchmark_success"):
            return "origin_benchmark_failed"
        return (
            "origin_vectorized_baseline"
            if row.get("analysis_vectorized")
            else "origin_not_vectorized_baseline"
        )

    if row.get("status") == "skipped":
        return "already_vectorized_skipped"
    if row.get("performance_guard_rejected"):
        return "performance_guard_rejected"
    if not row.get("correctness_overall"):
        return "correctness_failed"
    if not row.get("benchmark_success"):
        return "benchmark_failed"
    if speedup is None:
        return "missing_speedup"

    if row.get("analysis_vectorized"):
        if speedup > 1.0 + tolerance:
            return "vectorized_speedup"
        if speedup < 1.0 - tolerance:
            return "vectorized_slowdown"
        return "vectorized_flat"

    if speedup > 1.0 + tolerance:
        return "non_vectorized_speedup"
    if speedup < 1.0 - tolerance:
        return "non_vectorized_slowdown"
    return "non_vectorized_flat"


def load_json_if_exists(path: str | Path | None) -> Dict:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_problem_info(problem_map: Dict, func_name: str) -> Dict:
    info = problem_map.get(func_name, {})
    return {
        "severity": info.get("severity"),
        "problem_count": info.get("not_vectorized_count"),
        "line_range": info.get("line_range"),
    }


def build_origin_row(
    run_id: str,
    func_name: str,
    clang_path: str,
    problem_map: Dict,
    benchmark_config: Dict,
) -> tuple[Dict, Dict]:
    original_code = extract_function_code(config.SOURCE_FILE, func_name)
    problem_info = get_problem_info(problem_map, func_name)

    row = {
        "run_id": run_id,
        "strategy": "origin",
        "function": func_name,
        "severity": problem_info["severity"],
        "problem_count": problem_info["problem_count"],
        "line_range": problem_info["line_range"],
        "status": "origin_baseline",
        "rounds": 0,
        "best_round": None,
        "stored_correctness_overall": True,
        "correctness_overall": True,
        "verification_error": None,
        "analysis_compilable": False,
        "analysis_vectorized": False,
        "analysis_vectorized_count": 0,
        "analysis_missed_count": 0,
        "benchmark_mode": "baseline_only",
        "benchmark_protocol": benchmark_config.get("protocol_name"),
        "benchmark_protocol_role": benchmark_config.get("protocol_role"),
        "benchmark_protocol_display": benchmark_config.get("display_name"),
        "paper_main_table_eligible": benchmark_config.get("paper_main_table_eligible"),
        "benchmark_protocol_warning": benchmark_config.get("warning"),
        "benchmark_success": False,
        "benchmark_warmup_runs": benchmark_config["warmup_runs"],
        "benchmark_timing_runs": benchmark_config["timing_runs"],
        "benchmark_batches": benchmark_config["batches"],
        "original_time_ms": None,
        "optimized_time_ms": None,
        "speedup": None,
        "improvement_pct": None,
        "speedup_median": None,
        "speedup_stddev": None,
        "observed_outcome": None,
        "error": None,
    }
    benchmark_result = {
        "func_name": func_name,
        "success": False,
        "error": "未执行 benchmark",
    }

    if not original_code:
        row["error"] = "未能从源文件提取原始函数代码"
        row["observed_outcome"] = classify_observed_outcome(row)
        return row, benchmark_result

    analysis_result = analyze_single_function(func_name, original_code, clang_path)
    row["analysis_compilable"] = analysis_result.get("compilable", False)
    row["analysis_vectorized"] = analysis_result.get("vectorized", False)
    row["analysis_vectorized_count"] = analysis_result.get("vectorized_count", 0)
    row["analysis_missed_count"] = analysis_result.get("missed_count", 0)

    emit_progress(
        f"[origin] 基线 benchmark {func_name}: "
        f"warmup={benchmark_config['warmup_runs']} timing={benchmark_config['timing_runs']} batches={benchmark_config['batches']}"
    )
    benchmark_result = run_performance_benchmark(
        original_code,
        original_code,
        func_name,
        clang_path,
        **benchmark_config,
    )
    emit_progress(f"[origin] 基线 benchmark 完成: {func_name}")
    if benchmark_result.get("success"):
        row["benchmark_success"] = True
        row["original_time_ms"] = benchmark_result.get("original_time_ms")
        row["optimized_time_ms"] = benchmark_result.get("optimized_time_ms")
        row["speedup"] = 1.0
        row["improvement_pct"] = 0.0
        row["speedup_median"] = 1.0
        row["speedup_stddev"] = 0.0
    else:
        row["error"] = benchmark_result.get("error")

    row["observed_outcome"] = classify_observed_outcome(row)
    return row, benchmark_result


def build_optimized_row(
    run_id: str,
    strategy_name: str,
    func_name: str,
    clang_path: str,
    state: Dict,
    problem_map: Dict,
    benchmark_config: Dict,
) -> tuple[Dict, Dict, Dict]:
    func_state = state.get(func_name, {}) if isinstance(state, dict) else {}
    original_code = func_state.get("original_code")
    best_code = get_best_code(func_name, state) if func_state else None
    if not best_code and func_state.get("status") == "skipped":
        best_code = original_code
    problem_info = get_problem_info(problem_map, func_name)
    row_status = func_state.get("status", "missing")
    row_rounds = 0 if row_status == "skipped" else len(func_state.get("rounds", []))
    row_best_round = 0 if row_status == "skipped" else func_state.get("best")
    performance_guard = (
        (func_state.get("performance_guard") or {})
        if isinstance(func_state, dict)
        else {}
    )

    row = {
        "run_id": run_id,
        "strategy": strategy_name,
        "function": func_name,
        "severity": problem_info["severity"],
        "problem_count": problem_info["problem_count"],
        "line_range": problem_info["line_range"],
        "status": row_status,
        "rounds": row_rounds,
        "best_round": row_best_round,
        "stored_correctness_overall": func_state.get("correctness_overall"),
        "correctness_overall": False,
        "verification_error": None,
        "analysis_compilable": False,
        "analysis_vectorized": False,
        "analysis_vectorized_count": 0,
        "analysis_missed_count": 0,
        "benchmark_mode": "optimized_vs_original",
        "benchmark_protocol": benchmark_config.get("protocol_name"),
        "benchmark_protocol_role": benchmark_config.get("protocol_role"),
        "benchmark_protocol_display": benchmark_config.get("display_name"),
        "paper_main_table_eligible": benchmark_config.get("paper_main_table_eligible"),
        "benchmark_protocol_warning": benchmark_config.get("warning"),
        "benchmark_success": False,
        "benchmark_warmup_runs": benchmark_config["warmup_runs"],
        "benchmark_timing_runs": benchmark_config["timing_runs"],
        "benchmark_batches": benchmark_config["batches"],
        "original_time_ms": None,
        "optimized_time_ms": None,
        "speedup": None,
        "improvement_pct": None,
        "speedup_median": None,
        "speedup_stddev": None,
        "observed_outcome": None,
        "performance_guard_rejected": bool(performance_guard.get("rejected")),
        "performance_guard_reason": performance_guard.get("reason"),
        "performance_guard_speedup": performance_guard.get("speedup"),
        "performance_guard_speedup_median": performance_guard.get("speedup_median"),
        "error": None,
    }

    verification_report = {
        "func_name": func_name,
        "overall": False,
        "error": "缺少原始代码或最佳优化代码",
    }
    benchmark_result = {
        "func_name": func_name,
        "success": False,
        "error": "未执行 benchmark",
    }

    if not original_code or not best_code:
        row["error"] = "缺少原始代码或最佳优化代码"
        row["verification_error"] = row["error"]
        row["observed_outcome"] = classify_observed_outcome(row)
        return row, verification_report, benchmark_result

    analysis_result = analyze_single_function(func_name, best_code, clang_path)
    row["analysis_compilable"] = analysis_result.get("compilable", False)
    row["analysis_vectorized"] = analysis_result.get("vectorized", False)
    row["analysis_vectorized_count"] = analysis_result.get("vectorized_count", 0)
    row["analysis_missed_count"] = analysis_result.get("missed_count", 0)

    verification_report = full_correctness_verification(
        original_code, best_code, func_name, clang_path
    )
    row["correctness_overall"] = verification_report.get("overall", False)
    row["verification_error"] = (
        verification_report.get("layer2_semantic", {}).get("error")
        or verification_report.get("layer1_compilation", {}).get("error")
        or verification_report.get("layer3_runtime", {}).get("error")
    )

    if verification_report.get("overall"):
        if row.get("performance_guard_rejected"):
            row["correctness_overall"] = True
            row["benchmark_mode"] = "performance_guard_rejected"
            row["error"] = row.get("performance_guard_reason") or "性能守护拒绝了最终候选"
            benchmark_result = {
                "func_name": func_name,
                "success": False,
                "error": row["error"],
            }
            row["observed_outcome"] = classify_observed_outcome(row)
            return row, verification_report, benchmark_result

        benchmark_compare_code = best_code
        if row_status == "skipped":
            row["benchmark_mode"] = "baseline_only"
            benchmark_compare_code = original_code

        emit_progress(
            f"[{strategy_name}] 结果 benchmark {func_name}: "
            f"warmup={benchmark_config['warmup_runs']} timing={benchmark_config['timing_runs']} batches={benchmark_config['batches']}"
        )
        benchmark_result = run_performance_benchmark(
            original_code,
            benchmark_compare_code,
            func_name,
            clang_path,
            **benchmark_config,
        )
        emit_progress(f"[{strategy_name}] 结果 benchmark 完成: {func_name}")
        row["benchmark_success"] = benchmark_result.get("success", False)
        row["original_time_ms"] = benchmark_result.get("original_time_ms")
        row["optimized_time_ms"] = benchmark_result.get("optimized_time_ms")
        row["speedup"] = benchmark_result.get("speedup")
        row["improvement_pct"] = benchmark_result.get("improvement_pct")
        row["speedup_median"] = benchmark_result.get("speedup_median")
        row["speedup_stddev"] = benchmark_result.get("speedup_stddev")
        if row_status == "skipped" and benchmark_result.get("success"):
            row["optimized_time_ms"] = row["original_time_ms"]
            row["speedup"] = 1.0
            row["improvement_pct"] = 0.0
            row["speedup_median"] = 1.0
            row["speedup_stddev"] = 0.0
        if not benchmark_result.get("success"):
            row["error"] = benchmark_result.get("error")
    else:
        row["error"] = row["verification_error"] or "正确性验证失败"
        benchmark_result = {
            "func_name": func_name,
            "success": False,
            "error": "正确性验证失败，未执行 benchmark",
        }

    row["observed_outcome"] = classify_observed_outcome(row)
    return row, verification_report, benchmark_result


def summarize_rows(strategy_name: str, rows: List[Dict], exit_code: int) -> Dict:
    benchmark_rows = [row for row in rows if row.get("benchmark_success")]
    speedups = [
        row["speedup"] for row in benchmark_rows
        if row.get("speedup") is not None and row.get("benchmark_mode") != "baseline_only"
    ]
    improvements = [
        row["improvement_pct"] for row in benchmark_rows
        if row.get("improvement_pct") is not None and row.get("benchmark_mode") != "baseline_only"
    ]

    status_counts = {}
    outcome_counts = {}
    for row in rows:
        status = row.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        outcome = row.get("observed_outcome") or classify_observed_outcome(row)
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

    return {
        "strategy": strategy_name,
        "exit_code": exit_code,
        "total_functions": len(rows),
        "status_counts": status_counts,
        "observed_outcome_counts": outcome_counts,
        "correctness_passed": sum(1 for row in rows if row.get("correctness_overall")),
        "fully_vectorized": sum(
            1 for row in rows
            if (
                row.get("status") != "skipped"
                and not row.get("performance_guard_rejected")
                and row.get("analysis_vectorized")
            )
        ),
        "benchmark_success_count": len(benchmark_rows),
        "avg_speedup": safe_mean(speedups),
        "median_speedup": safe_median(speedups),
        "avg_improvement_pct": safe_mean(improvements),
        "negative_optimization_count": sum(1 for row in benchmark_rows if (row.get("speedup") or 0) < 1.0),
    }


def build_row_snapshot(row: Dict | None) -> Dict:
    if row is None:
        return {"available": False}

    return {
        "available": True,
        "strategy": row.get("strategy"),
        "severity": row.get("severity"),
        "problem_count": row.get("problem_count"),
        "status": row.get("status"),
        "correctness_overall": row.get("correctness_overall"),
        "analysis_vectorized": row.get("analysis_vectorized"),
        "analysis_vectorized_count": row.get("analysis_vectorized_count"),
        "analysis_missed_count": row.get("analysis_missed_count"),
        "benchmark_success": row.get("benchmark_success"),
        "benchmark_protocol": row.get("benchmark_protocol"),
        "benchmark_protocol_role": row.get("benchmark_protocol_role"),
        "paper_main_table_eligible": row.get("paper_main_table_eligible"),
        "benchmark_warmup_runs": row.get("benchmark_warmup_runs"),
        "benchmark_timing_runs": row.get("benchmark_timing_runs"),
        "benchmark_batches": row.get("benchmark_batches"),
        "speedup": row.get("speedup"),
        "speedup_median": row.get("speedup_median"),
        "speedup_stddev": row.get("speedup_stddev"),
        "improvement_pct": row.get("improvement_pct"),
        "observed_outcome": row.get("observed_outcome"),
        "performance_guard_rejected": row.get("performance_guard_rejected"),
        "performance_guard_reason": row.get("performance_guard_reason"),
        "performance_guard_speedup": row.get("performance_guard_speedup"),
        "performance_guard_speedup_median": row.get("performance_guard_speedup_median"),
        "verification_error": row.get("verification_error"),
        "error": row.get("error"),
    }


def get_comparison_row_status(row: Dict | None) -> str:
    if row is None:
        return "missing"
    if row.get("status") == "skipped":
        return "skipped"
    if row.get("performance_guard_rejected"):
        return "performance_guard_rejected"
    if not row.get("correctness_overall"):
        return "correctness_failed"
    if not row.get("benchmark_success"):
        return "benchmark_failed"
    if row.get("speedup") is None:
        return "missing_speedup"
    return "ok"


def build_pairwise_function_result(
    left_strategy: str,
    right_strategy: str,
    function_name: str,
    row_by_strategy: Dict[str, Dict],
) -> Dict:
    left_row = row_by_strategy.get(left_strategy)
    right_row = row_by_strategy.get(right_strategy)
    left_status = get_comparison_row_status(left_row)
    right_status = get_comparison_row_status(right_row)

    result = {
        "function": function_name,
        "severity": (left_row or right_row or {}).get("severity"),
        "problem_count": (left_row or right_row or {}).get("problem_count"),
        "left_strategy": left_strategy,
        "right_strategy": right_strategy,
        "left_status": left_status,
        "right_status": right_status,
        "comparable": left_status == "ok" and right_status == "ok",
        "left_speedup": left_row.get("speedup") if left_row else None,
        "right_speedup": right_row.get("speedup") if right_row else None,
        "delta_speedup": None,
        "delta_improvement_pct": None,
        "verdict": None,
    }

    if result["comparable"]:
        result["delta_speedup"] = left_row["speedup"] - right_row["speedup"]
        result["delta_improvement_pct"] = (
            (left_row.get("improvement_pct") or 0.0)
            - (right_row.get("improvement_pct") or 0.0)
        )
        if abs(result["delta_speedup"]) <= COMPARISON_SPEEDUP_TOLERANCE:
            result["verdict"] = "tie"
        elif result["delta_speedup"] > 0:
            result["verdict"] = "better"
        else:
            result["verdict"] = "worse"

    return result


def build_pairwise_summary(
    left_strategy: str,
    right_strategy: str,
    rows_by_function: Dict[str, Dict[str, Dict]],
) -> Dict:
    function_results = []
    verdict_counts = {"better": 0, "tie": 0, "worse": 0}
    left_status_counts = {}
    right_status_counts = {}
    comparable_deltas = []
    comparable_improvement_deltas = []

    for function_name in sorted(rows_by_function):
        result = build_pairwise_function_result(
            left_strategy=left_strategy,
            right_strategy=right_strategy,
            function_name=function_name,
            row_by_strategy=rows_by_function[function_name],
        )
        function_results.append(result)

        left_status = result["left_status"]
        right_status = result["right_status"]
        left_status_counts[left_status] = left_status_counts.get(left_status, 0) + 1
        right_status_counts[right_status] = right_status_counts.get(right_status, 0) + 1

        if result["comparable"]:
            verdict_counts[result["verdict"]] += 1
            comparable_deltas.append(result["delta_speedup"])
            comparable_improvement_deltas.append(result["delta_improvement_pct"])

    comparable_only = [item for item in function_results if item["comparable"]]
    left_advantages = sorted(
        [item for item in comparable_only if item["verdict"] == "better"],
        key=lambda item: item["delta_speedup"],
        reverse=True,
    )[:5]
    right_advantages = sorted(
        [item for item in comparable_only if item["verdict"] == "worse"],
        key=lambda item: item["delta_speedup"],
    )[:5]

    return {
        "pair": f"{left_strategy}_vs_{right_strategy}",
        "left_strategy": left_strategy,
        "right_strategy": right_strategy,
        "comparison_tolerance_speedup": COMPARISON_SPEEDUP_TOLERANCE,
        "total_functions": len(function_results),
        "comparable_functions": len(comparable_only),
        "verdict_counts": verdict_counts,
        "left_status_counts": left_status_counts,
        "right_status_counts": right_status_counts,
        "avg_delta_speedup": safe_mean(comparable_deltas),
        "median_delta_speedup": safe_median(comparable_deltas),
        "avg_delta_improvement_pct": safe_mean(comparable_improvement_deltas),
        "top_left_advantages": left_advantages,
        "top_right_advantages": right_advantages,
        "function_results": function_results,
    }


def build_run_comparison(run_id: str, strategies: List[str], rows: List[Dict]) -> Dict:
    rows_by_function: Dict[str, Dict[str, Dict]] = {}
    outcome_counts_by_strategy: Dict[str, Dict[str, int]] = {}

    for row in rows:
        function_name = row["function"]
        strategy_name = row["strategy"]
        rows_by_function.setdefault(function_name, {})[strategy_name] = row

        outcome = row.get("observed_outcome") or classify_observed_outcome(row)
        strategy_counts = outcome_counts_by_strategy.setdefault(strategy_name, {})
        strategy_counts[outcome] = strategy_counts.get(outcome, 0) + 1

    pairwise_summaries = []
    for index, left_strategy in enumerate(strategies):
        for right_strategy in strategies[index + 1:]:
            pairwise_summaries.append(
                build_pairwise_summary(left_strategy, right_strategy, rows_by_function)
            )

    function_comparisons = []
    pairwise_lookup = {
        item["pair"]: {entry["function"]: entry for entry in item["function_results"]}
        for item in pairwise_summaries
    }

    for function_name in sorted(rows_by_function):
        row_by_strategy = rows_by_function[function_name]
        first_row = next(iter(row_by_strategy.values()))
        function_comparisons.append(
            {
                "function": function_name,
                "severity": first_row.get("severity"),
                "problem_count": first_row.get("problem_count"),
                "line_range": first_row.get("line_range"),
                "strategies": {
                    strategy_name: build_row_snapshot(row_by_strategy.get(strategy_name))
                    for strategy_name in strategies
                },
                "pairwise": {
                    pair_name: function_map[function_name]
                    for pair_name, function_map in pairwise_lookup.items()
                    if function_name in function_map
                },
            }
        )

    return {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "strategies": strategies,
        "total_functions": len(function_comparisons),
        "outcome_counts_by_strategy": outcome_counts_by_strategy,
        "pairwise_summaries": pairwise_summaries,
        "functions": function_comparisons,
    }


def invert_pairwise_result(result: Dict) -> Dict:
    if not result:
        return {}

    inverted = dict(result)
    inverted["left_strategy"] = result.get("right_strategy")
    inverted["right_strategy"] = result.get("left_strategy")
    inverted["left_status"] = result.get("right_status")
    inverted["right_status"] = result.get("left_status")
    inverted["left_speedup"] = result.get("right_speedup")
    inverted["right_speedup"] = result.get("left_speedup")

    if result.get("delta_speedup") is not None:
        inverted["delta_speedup"] = -result["delta_speedup"]
    if result.get("delta_improvement_pct") is not None:
        inverted["delta_improvement_pct"] = -result["delta_improvement_pct"]

    verdict = result.get("verdict")
    if verdict == "better":
        inverted["verdict"] = "worse"
    elif verdict == "worse":
        inverted["verdict"] = "better"
    else:
        inverted["verdict"] = verdict

    return inverted


def get_function_pairwise_result(function_item: Dict, left_strategy: str, right_strategy: str) -> Dict:
    pairwise = function_item.get("pairwise", {})
    direct_key = f"{left_strategy}_vs_{right_strategy}"
    if direct_key in pairwise:
        return pairwise[direct_key]

    reverse_key = f"{right_strategy}_vs_{left_strategy}"
    if reverse_key in pairwise:
        return invert_pairwise_result(pairwise[reverse_key])

    return {}


def format_markdown_number(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def format_strategy_cell(snapshot: Dict) -> str:
    if not snapshot.get("available"):
        return "-"

    speedup = snapshot.get("speedup")
    outcome = snapshot.get("observed_outcome") or "-"
    if speedup is None:
        return f"NA / {outcome}"
    return f"{speedup:.3f}x / {outcome}"


def render_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    if not rows:
        return ""
    header_row = "| " + " | ".join(headers) + " |"
    divider_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_rows = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_row, divider_row, *body_rows])


def render_run_markdown_report(run_summary: Dict, comparison: Dict) -> str:
    benchmark_config = run_summary.get("benchmark_config", {})
    lines = [
        f"# VecGuide 实验汇总（{run_summary['run_id']}）",
        "",
        f"- 生成时间：{run_summary['timestamp']}",
        f"- 函数数量：{comparison['total_functions']}",
        f"- 策略：{', '.join(comparison['strategies'])}",
        (
            f"- benchmark 协议：{benchmark_config.get('display_name', benchmark_config.get('protocol_name', '-'))}, "
            f"role={benchmark_config.get('protocol_role', '-')}, "
            f"main_table_eligible={benchmark_config.get('paper_main_table_eligible', False)}, "
            f"warmup={benchmark_config.get('warmup_runs', '-')}, "
            f"timing={benchmark_config.get('timing_runs', '-')}, "
            f"batches={benchmark_config.get('batches', '-')}, "
            "arg_info=per-function protocol "
            "(default uses (1,1); parameterized kernels use verifier-defined multi-case sets)"
        ),
        "",
        "## 策略级汇总",
        "",
    ]

    strategy_rows = []
    for strategy_item in run_summary.get("strategies", []):
        metrics = strategy_item.get("metrics", {})
        strategy_rows.append(
            [
                strategy_item.get("strategy", "-"),
                str(strategy_item.get("exit_code", "-")),
                str(metrics.get("correctness_passed", "-")),
                str(metrics.get("fully_vectorized", "-")),
                str(metrics.get("benchmark_success_count", "-")),
                format_markdown_number(metrics.get("avg_speedup")),
                format_markdown_number(metrics.get("median_speedup")),
                str(metrics.get("negative_optimization_count", "-")),
            ]
        )
    lines.append(
        render_markdown_table(
            [
                "strategy",
                "exit",
                "correctness_passed",
                "fully_vectorized",
                "benchmark_success",
                "avg_speedup",
                "median_speedup",
                "negative_opt",
            ],
            strategy_rows,
        )
    )

    lines.extend(["", "## 跨策略对比", ""])
    pairwise_rows = []
    for pair_item in comparison.get("pairwise_summaries", []):
        verdict_counts = pair_item.get("verdict_counts", {})
        pairwise_rows.append(
            [
                pair_item.get("pair", "-"),
                str(pair_item.get("comparable_functions", 0)),
                str(verdict_counts.get("better", 0)),
                str(verdict_counts.get("tie", 0)),
                str(verdict_counts.get("worse", 0)),
                format_markdown_number(pair_item.get("avg_delta_speedup")),
            ]
        )
    if pairwise_rows:
        lines.append(
            render_markdown_table(
                ["pair", "comparable", "better", "tie", "worse", "avg_delta_speedup"],
                pairwise_rows,
            )
        )
    else:
        lines.append("本次 run 只有单个策略，没有可计算的跨策略对比。")

    lines.extend(["", "## 函数级明细", ""])
    function_headers = ["function", "severity", *comparison["strategies"]]
    if "ours_full" in comparison["strategies"] and "llm_plain" in comparison["strategies"]:
        function_headers.append("ours_full_vs_llm_plain")

    function_rows = []
    for function_item in comparison.get("functions", []):
        row = [
            function_item.get("function", "-"),
            function_item.get("severity") or "-",
        ]
        for strategy_name in comparison["strategies"]:
            row.append(format_strategy_cell(function_item["strategies"][strategy_name]))

        if "ours_full" in comparison["strategies"] and "llm_plain" in comparison["strategies"]:
            pair = get_function_pairwise_result(function_item, "ours_full", "llm_plain")
            if pair.get("comparable"):
                row.append(
                    f"{pair.get('verdict')} ({format_markdown_number(pair.get('delta_speedup'))})"
                )
            else:
                row.append(f"NA ({pair.get('left_status', '-')}/{pair.get('right_status', '-')})")

        function_rows.append(row)

    lines.append(render_markdown_table(function_headers, function_rows))
    lines.append("")
    return "\n".join(lines)


def collect_strategy_artifacts(
    run_id: str,
    strategy: Dict,
    strategy_result: Dict,
    strategy_dir: Path,
    functions: List[str],
    clang_path: str,
    problem_map: Dict,
    benchmark_config: Dict,
) -> tuple[Dict, List[Dict]]:
    rows: List[Dict] = []
    verification_payload = {}
    benchmark_payload = {}

    if strategy["name"] == "origin":
        for func_name in functions:
            row, benchmark_result = build_origin_row(
                run_id, func_name, clang_path, problem_map, benchmark_config
            )
            verification_payload[func_name] = {
                "func_name": func_name,
                "overall": True,
                "mode": "origin_baseline",
            }
            benchmark_payload[func_name] = {
                "func_name": func_name,
                "success": row.get("benchmark_success", False),
                "original_time_ms": row.get("original_time_ms"),
                "optimized_time_ms": row.get("optimized_time_ms"),
                "speedup": row.get("speedup"),
                "improvement_pct": row.get("improvement_pct"),
                "speedup_median": row.get("speedup_median"),
                "speedup_stddev": row.get("speedup_stddev"),
                "benchmark_protocol": row.get("benchmark_protocol"),
                "benchmark_protocol_role": row.get("benchmark_protocol_role"),
                "benchmark_protocol_display": row.get("benchmark_protocol_display"),
                "paper_main_table_eligible": row.get("paper_main_table_eligible"),
                "benchmark_protocol_warning": row.get("benchmark_protocol_warning"),
                "warmup_runs": row.get("benchmark_warmup_runs"),
                "timing_runs": row.get("benchmark_timing_runs"),
                "batch_count": row.get("benchmark_batches"),
                "arg_case_count": benchmark_result.get("arg_case_count"),
                "sample_count": benchmark_result.get("sample_count"),
                "benchmark_scope": benchmark_result.get("benchmark_scope"),
                "arg_cases": benchmark_result.get("arg_cases", []),
                "arg_case_results": benchmark_result.get("arg_case_results", []),
                "batches": benchmark_result.get("batches", []),
                "benchmark_mode": row.get("benchmark_mode"),
                "error": row.get("error"),
            }
            rows.append(row)
    else:
        state = {}
        state_file = strategy_result.get("state_file")
        if state_file and Path(state_file).exists():
            state = load_state(state_file)

        for func_name in functions:
            row, verification_report, benchmark_result = build_optimized_row(
                run_id=run_id,
                strategy_name=strategy["name"],
                func_name=func_name,
                clang_path=clang_path,
                state=state,
                problem_map=problem_map,
                benchmark_config=benchmark_config,
            )
            verification_payload[func_name] = verification_report
            benchmark_result.update(
                {
                    "benchmark_protocol": row.get("benchmark_protocol"),
                    "benchmark_protocol_role": row.get("benchmark_protocol_role"),
                    "benchmark_protocol_display": row.get("benchmark_protocol_display"),
                    "paper_main_table_eligible": row.get("paper_main_table_eligible"),
                    "benchmark_protocol_warning": row.get("benchmark_protocol_warning"),
                }
            )
            benchmark_payload[func_name] = benchmark_result
            rows.append(row)

    strategy_summary = summarize_rows(strategy["name"], rows, strategy_result["exit_code"])
    verification_file = strategy_dir / "verification.json"
    benchmark_file = strategy_dir / "benchmark.json"
    rows_file = strategy_dir / "paper_rows.json"
    summary_file = strategy_dir / "paper_summary.json"

    write_json(verification_file, {"strategy": strategy["name"], "results": verification_payload})
    write_json(benchmark_file, {"strategy": strategy["name"], "results": benchmark_payload})
    write_json(rows_file, {"strategy": strategy["name"], "rows": rows})
    write_json(summary_file, strategy_summary)

    strategy_result.update(
        {
            "verification_file": str(verification_file),
            "benchmark_file": str(benchmark_file),
            "paper_rows_file": str(rows_file),
            "paper_summary_file": str(summary_file),
            "metrics": strategy_summary,
        }
    )
    return strategy_result, rows


def build_run_paper_summary(
    run_id: str,
    strategy_results: List[Dict],
    rows: List[Dict],
    benchmark_config: Dict,
) -> Dict:
    return {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "total_rows": len(rows),
        "benchmark_config": benchmark_config,
        "strategies": [
            {
                "strategy": item["strategy"],
                "exit_code": item["exit_code"],
                "metrics": item.get("metrics", {}),
                "summary_file": item.get("paper_summary_file"),
            }
            for item in strategy_results
        ],
    }


PAPER_ROW_FIELDS = [
    "run_id",
    "strategy",
    "function",
    "severity",
    "problem_count",
    "line_range",
    "status",
    "rounds",
    "best_round",
    "stored_correctness_overall",
    "correctness_overall",
    "verification_error",
    "analysis_compilable",
    "analysis_vectorized",
    "analysis_vectorized_count",
    "analysis_missed_count",
    "benchmark_mode",
    "benchmark_protocol",
    "benchmark_protocol_role",
    "benchmark_protocol_display",
    "paper_main_table_eligible",
    "benchmark_protocol_warning",
    "benchmark_success",
    "benchmark_warmup_runs",
    "benchmark_timing_runs",
    "benchmark_batches",
    "original_time_ms",
    "optimized_time_ms",
    "speedup",
    "speedup_median",
    "speedup_stddev",
    "improvement_pct",
    "observed_outcome",
    "performance_guard_rejected",
    "performance_guard_reason",
    "performance_guard_speedup",
    "performance_guard_speedup_median",
    "error",
]


def build_manifest(
    repo_root: Path,
    run_id: str,
    strategies: List[Dict],
    functions: List[str],
    clang_path: str,
    model_name: str,
    requested_rounds: int,
    shared_problem_map: Path | None,
    benchmark_config: Dict,
    dry_run: bool,
) -> Dict:
    git_commit = capture_command_output(["git", "rev-parse", "HEAD"], cwd=repo_root)
    git_status_short = capture_command_output(["git", "status", "--short"], cwd=repo_root)
    clang_version = capture_command_output([clang_path, "--version"])
    source_file = Path(config.SOURCE_FILE)
    if not source_file.is_absolute():
        source_file = repo_root / source_file

    return {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "repo_root": "<repo>",
        "git": {
            "commit": git_commit,
            "is_dirty": bool(git_status_short),
            "status_short": [],
            "status_sanitized": True,
            "status_sanitized_reason": "Local working-tree paths are omitted from public artifacts.",
        },
        "source": {
            "path": public_path(source_file, base_dir=repo_root),
            "sha256": hash_file(source_file),
        },
        "toolchain": {
            "clang_path": "${CLANG_PATH}" if clang_path else None,
            "clang_version": [
                line if not line.startswith("InstalledDir:") else "InstalledDir: <clang-install-dir>"
                for line in clang_version.splitlines()
            ] if clang_version else None,
        },
        "runtime": {
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "hostname": socket.gethostname(),
        },
        "model_name": model_name,
        "requested_rounds": requested_rounds,
        "benchmark_config": benchmark_config,
        "functions": functions,
        "shared_problem_map": {
            "path": public_path(shared_problem_map, base_dir=repo_root) if shared_problem_map else None,
            "sha256": hash_file(shared_problem_map),
        },
        "strategies": [
            {
                "name": strategy["name"],
                "publication_name": strategy.get("publication_name"),
                "implementation_status": strategy.get("implementation_status"),
                "paper_role": strategy.get("paper_role"),
                "prompt_version": strategy.get("prompt_version"),
                "legacy_name": strategy.get("legacy_name"),
                "description": strategy["description"],
                "single_round": strategy["single_round"],
                "max_rounds": strategy["max_rounds"],
                "prompt_options": strategy["prompt_options"],
                "performance_guard": strategy.get("performance_guard"),
            }
            for strategy in strategies
        ],
    }


def build_strategy_config_payload(run_id: str, strategies: List[Dict]) -> Dict:
    """Build the run-level frozen strategy configuration."""
    return {
        "schema_version": 1,
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "strategies": [
            {
                "name": strategy["name"],
                "publication_name": strategy.get("publication_name"),
                "implementation_status": strategy.get("implementation_status"),
                "paper_role": strategy.get("paper_role"),
                "prompt_version": strategy.get("prompt_version"),
                "legacy_name": strategy.get("legacy_name"),
                "description": strategy["description"],
                "optimizer_enabled": strategy["optimizer_enabled"],
                "single_round": strategy["single_round"],
                "max_rounds": strategy["max_rounds"],
                "prompt_options": strategy["prompt_options"],
                "performance_guard": strategy.get("performance_guard"),
            }
            for strategy in strategies
        ],
    }


def write_strategy_config(run_dir: Path, run_id: str, strategies: List[Dict]) -> Path:
    strategy_config_file = run_dir / "strategy_config.json"
    write_json(strategy_config_file, build_strategy_config_payload(run_id, strategies))
    return strategy_config_file


def initialize_run_directory_contract(run_dir: Path, strategy_root: Path, strategies: List[Dict]) -> None:
    """Create stable run directories before optimization starts."""
    (run_dir / "shared").mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt_snapshot").mkdir(parents=True, exist_ok=True)
    raw_logs_dir = run_dir / "raw_logs"
    raw_logs_dir.mkdir(parents=True, exist_ok=True)
    write_text(
        raw_logs_dir / "README.md",
        "\n".join(
            [
                "# Raw Logs",
                "",
                "This directory is reserved for terminal transcripts and external run logs.",
                "If the terminal transcript is stored outside this run directory, record its path in `external_log_path.txt`.",
                "",
            ]
        ),
    )
    write_text(
        raw_logs_dir / "external_log_path.txt",
        "未填写。若终端记录保存在 a local private transcript path，请在归档正式 run 时写入该路径。\n",
    )

    for strategy in strategies:
        strategy_dir = strategy_root / strategy["name"]
        strategy_dir.mkdir(parents=True, exist_ok=True)
        (strategy_dir / "reports").mkdir(parents=True, exist_ok=True)
        (strategy_dir / "prompt_snapshot").mkdir(parents=True, exist_ok=True)


def write_run_prompt_snapshot_index(
    run_dir: Path,
    run_id: str,
    strategy_results: List[Dict],
) -> Path:
    """Write a run-level index pointing to per-strategy prompt snapshots."""
    strategies = []
    for item in strategy_results:
        strategy_name = item.get("strategy")
        snapshot_dir = Path(
            item.get("prompt_snapshot_dir")
            or run_dir / "strategies" / str(strategy_name) / "prompt_snapshot"
        )
        strategy_index_file = snapshot_dir / "index.json"
        strategy_index = load_json_if_exists(strategy_index_file)
        snapshots = strategy_index.get("snapshots", []) if isinstance(strategy_index, dict) else []
        selected_card_ids = []
        for snapshot in snapshots:
            for card_id in snapshot.get("selected_case_card_ids", []) or []:
                if card_id not in selected_card_ids:
                    selected_card_ids.append(card_id)
        strategies.append(
            {
                "strategy": strategy_name,
                "prompt_snapshot_dir": public_path(snapshot_dir, base_dir=run_dir),
                "strategy_index_file": public_path(strategy_index_file, base_dir=run_dir),
                "strategy_index_exists": strategy_index_file.exists(),
                "snapshot_count": len(snapshots),
                "selected_case_card_ids": selected_card_ids,
            }
        )

    payload = {
        "schema_version": 1,
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "strategies": strategies,
    }
    index_file = run_dir / "prompt_snapshot" / "index.json"
    write_json(index_file, payload)
    return index_file


def build_artifact_index_payload(
    run_id: str,
    run_dir: Path,
    strategies: List[Dict],
    strategy_results: List[Dict],
    dry_run: bool,
) -> Dict:
    """Build a stable top-level index for all formal run artifacts."""
    paper_files = {
        "paper_results_csv": run_dir / "paper_results.csv",
        "paper_rows_json": run_dir / "paper_rows.json",
        "paper_summary_json": run_dir / "paper_summary.json",
        "paper_comparison_json": run_dir / "paper_comparison.json",
        "paper_report_md": run_dir / "paper_report.md",
    }
    fixed_files = {
        "manifest": run_dir / "manifest.json",
        "strategy_config": run_dir / "strategy_config.json",
        "summary": run_dir / "summary.json",
        "prompt_snapshot_index": run_dir / "prompt_snapshot" / "index.json",
    }

    strategy_result_by_name = {item.get("strategy"): item for item in strategy_results}
    strategy_items = []
    for strategy in strategies:
        strategy_name = strategy["name"]
        strategy_dir = run_dir / "strategies" / strategy_name
        result = strategy_result_by_name.get(strategy_name, {})
        strategy_items.append(
            {
                "strategy": strategy_name,
                "publication_name": strategy.get("publication_name"),
                "prompt_version": strategy.get("prompt_version"),
                "strategy_dir": path_payload(strategy_dir, base_dir=run_dir),
                "summary_file": path_payload(result.get("summary_file") or strategy_dir / "summary.json", base_dir=run_dir),
                "state_file": path_payload(result.get("state_file") or strategy_dir / "optimization_state.json", base_dir=run_dir),
                "prompt_snapshot_dir": path_payload(
                    result.get("prompt_snapshot_dir") or strategy_dir / "prompt_snapshot",
                    base_dir=run_dir,
                ),
                "reports_dir": path_payload(strategy_dir / "reports", base_dir=run_dir),
                "verification_file": path_payload(result.get("verification_file") or strategy_dir / "verification.json", base_dir=run_dir),
                "benchmark_file": path_payload(result.get("benchmark_file") or strategy_dir / "benchmark.json", base_dir=run_dir),
                "paper_rows_file": path_payload(result.get("paper_rows_file") or strategy_dir / "paper_rows.json", base_dir=run_dir),
                "paper_summary_file": path_payload(result.get("paper_summary_file") or strategy_dir / "paper_summary.json", base_dir=run_dir),
            }
        )

    return {
        "schema_version": 1,
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "run_dir": public_path(run_dir),
        "fixed_files": {name: path_payload(path, base_dir=run_dir) for name, path in fixed_files.items()},
        "paper_outputs": {name: path_payload(path, base_dir=run_dir) for name, path in paper_files.items()},
        "directories": {
            "shared": path_payload(run_dir / "shared", base_dir=run_dir),
            "strategies": path_payload(run_dir / "strategies", base_dir=run_dir),
            "prompt_snapshot": path_payload(run_dir / "prompt_snapshot", base_dir=run_dir),
            "raw_logs": path_payload(run_dir / "raw_logs", base_dir=run_dir),
        },
        "strategies": strategy_items,
    }


def write_artifact_index(
    run_dir: Path,
    run_id: str,
    strategies: List[Dict],
    strategy_results: List[Dict],
    dry_run: bool,
) -> Path:
    artifact_index_file = run_dir / "artifact_index.json"
    write_json(
        artifact_index_file,
        build_artifact_index_payload(
            run_id=run_id,
            run_dir=run_dir,
            strategies=strategies,
            strategy_results=strategy_results,
            dry_run=dry_run,
        ),
    )
    return artifact_index_file


def write_run_paper_outputs(
    run_dir: Path,
    run_id: str,
    functions: List[str],
    strategies: List[Dict],
    strategy_results: List[Dict],
    all_rows: List[Dict],
    benchmark_config: Dict,
    strategy_config_file: Path,
) -> Dict:
    """Write all run-level paper artifacts after strategy collection."""
    write_json(run_dir / "paper_rows.json", {"run_id": run_id, "rows": all_rows})
    write_csv(run_dir / "paper_results.csv", all_rows, PAPER_ROW_FIELDS)
    paper_summary = build_run_paper_summary(run_id, strategy_results, all_rows, benchmark_config)
    write_json(run_dir / "paper_summary.json", paper_summary)
    run_comparison = build_run_comparison(
        run_id=run_id,
        strategies=[item["strategy"] for item in strategy_results],
        rows=all_rows,
    )
    write_json(run_dir / "paper_comparison.json", run_comparison)
    write_text(run_dir / "paper_report.md", render_run_markdown_report(paper_summary, run_comparison))
    prompt_snapshot_index_file = write_run_prompt_snapshot_index(
        run_dir=run_dir,
        run_id=run_id,
        strategy_results=strategy_results,
    )

    overall = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "functions": functions,
        "benchmark_config": benchmark_config,
        "strategies": strategy_results,
        "paper_summary_file": public_path(run_dir / "paper_summary.json", base_dir=run_dir),
        "paper_rows_file": public_path(run_dir / "paper_rows.json", base_dir=run_dir),
        "paper_csv_file": public_path(run_dir / "paper_results.csv", base_dir=run_dir),
        "paper_comparison_file": public_path(run_dir / "paper_comparison.json", base_dir=run_dir),
        "paper_report_file": public_path(run_dir / "paper_report.md", base_dir=run_dir),
        "strategy_config_file": public_path(strategy_config_file, base_dir=run_dir),
        "prompt_snapshot_index_file": public_path(prompt_snapshot_index_file, base_dir=run_dir),
        "raw_logs_dir": public_path(run_dir / "raw_logs", base_dir=run_dir),
        "artifact_index_file": public_path(run_dir / "artifact_index.json", base_dir=run_dir),
        "all_succeeded": all(item["exit_code"] == 0 for item in strategy_results),
    }
    write_json(run_dir / "summary.json", overall)
    write_artifact_index(
        run_dir=run_dir,
        run_id=run_id,
        strategies=strategies,
        strategy_results=strategy_results,
        dry_run=False,
    )
    return overall


def collect_existing_run(
    repo_root: Path,
    run_id: str,
    clang_path: str,
    fallback_benchmark_config: Dict,
) -> int:
    """Recover run-level paper artifacts from already completed strategy outputs."""
    run_dir = repo_root / RUNS_ROOT / run_id
    if not run_dir.exists():
        raise FileNotFoundError(f"collect-only 需要已有 run 目录: {run_dir}")

    manifest = load_json_if_exists(run_dir / "manifest.json")
    if not manifest:
        raise FileNotFoundError(f"collect-only 需要已有 manifest.json: {run_dir / 'manifest.json'}")

    functions = manifest.get("functions") or []
    if not functions:
        raise ValueError("collect-only 无法从 manifest 恢复函数列表")

    benchmark_config = manifest.get("benchmark_config") or fallback_benchmark_config
    validate_benchmark_protocol_config(benchmark_config)

    strategy_items = manifest.get("strategies") or []
    if not strategy_items:
        strategy_config = load_json_if_exists(run_dir / "strategy_config.json")
        strategy_items = strategy_config.get("strategies") or []
    strategy_names = [item.get("name") for item in strategy_items if item.get("name")]
    if not strategy_names:
        raise ValueError("collect-only 无法从 manifest/strategy_config 恢复策略列表")

    strategies = [get_experiment_strategy(name) for name in strategy_names]
    strategy_config_file = run_dir / "strategy_config.json"
    if not strategy_config_file.exists():
        strategy_config_file = write_strategy_config(run_dir, run_id, strategies)

    shared_problem_map = None
    manifest_problem_map = manifest.get("shared_problem_map", {}).get("path")
    if manifest_problem_map and Path(manifest_problem_map).exists():
        shared_problem_map = Path(manifest_problem_map)
    problem_map = load_problem_map(shared_problem_map) if shared_problem_map else {}

    strategy_results = []
    all_rows: List[Dict] = []
    for strategy in strategies:
        strategy_dir = run_dir / "strategies" / strategy["name"]
        summary_file = strategy_dir / "summary.json"
        state_file = strategy_dir / "optimization_state.json"
        if strategy["name"] != "origin" and not summary_file.exists():
            raise FileNotFoundError(f"缺少策略摘要，无法 collect-only: {summary_file}")
        if strategy["name"] != "origin" and not state_file.exists():
            raise FileNotFoundError(f"缺少优化状态，无法 collect-only: {state_file}")

        result = {
            "strategy": strategy["name"],
            "exit_code": 0,
            "summary_file": str(summary_file),
            "state_file": str(state_file) if state_file.exists() else None,
            "optimized_prefix": str(strategy_dir / "optimized_"),
            "prompt_snapshot_dir": str(strategy_dir / "prompt_snapshot"),
        }
        result, rows = collect_strategy_artifacts(
            run_id=run_id,
            strategy=strategy,
            strategy_result=result,
            strategy_dir=strategy_dir,
            functions=functions,
            clang_path=clang_path,
            problem_map=problem_map,
            benchmark_config=benchmark_config,
        )
        strategy_results.append(result)
        all_rows.extend(rows)

    write_run_paper_outputs(
        run_dir=run_dir,
        run_id=run_id,
        functions=functions,
        strategies=strategies,
        strategy_results=strategy_results,
        all_rows=all_rows,
        benchmark_config=benchmark_config,
        strategy_config_file=strategy_config_file,
    )

    failed = [item for item in strategy_results if item["exit_code"] != 0]
    if failed:
        for item in failed:
            print(f"❌ 策略失败: {item['strategy']} (exit={item['exit_code']})")
        return 1

    print(f"collect-only 完成: {run_dir}")
    return 0


def run_strategy(
    repo_root: Path,
    strategy: Dict,
    strategy_dir: Path,
    shared_problem_map: Path | None,
    functions: List[str],
    clang_path: str,
    model_name: str,
    requested_rounds: int,
    benchmark_config: Dict,
) -> Dict:
    strategy_dir.mkdir(parents=True, exist_ok=True)
    summary_path = strategy_dir / "summary.json"

    if not strategy["optimizer_enabled"]:
        payload = {
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy["name"],
            "strategy_description": strategy["description"],
            "requested_rounds": requested_rounds,
            "benchmark_config": benchmark_config,
            "effective_rounds": 0,
            "single_round": True,
            "functions": functions,
            "results": [],
            "note": "origin 基线不执行 LLM 优化，仅作为原始代码对照。",
        }
        write_json(summary_path, payload)
        return {
            "strategy": strategy["name"],
            "exit_code": 0,
            "summary_file": str(summary_path),
            "state_file": None,
            "optimized_prefix": None,
            "prompt_snapshot_dir": str(strategy_dir / "prompt_snapshot"),
        }

    env = os.environ.copy()
    env["OPTIMIZATION_STATE_FILE"] = str(strategy_dir / "optimization_state.json")
    env["OPTIMIZED_FILE_PREFIX"] = str(strategy_dir / "optimized_")
    env["REPORTS_DIR"] = str(strategy_dir / "reports")
    env["PROMPT_SNAPSHOT_DIR"] = str(strategy_dir / "prompt_snapshot")
    if shared_problem_map is not None:
        env["PROBLEM_MAP_FILE"] = str(shared_problem_map)

    cmd = [
        sys.executable,
        "optimizer_pipeline.py",
        "--strategy", strategy["name"],
        "-c", clang_path,
        "-m", model_name,
        "-r", str(requested_rounds),
        "--json-summary", str(summary_path),
    ]

    # 实验入口已经提前解析并固定了函数集，这里始终透传显式函数列表，
    # 避免 optimizer_pipeline 再按默认 high,medium 重新筛选，导致
    # 策略执行层与 manifest / paper 汇总层的函数口径不一致。
    cmd.extend(functions)

    result = subprocess.run(cmd, cwd=repo_root, env=env)
    return {
        "strategy": strategy["name"],
        "exit_code": result.returncode,
        "summary_file": str(summary_path),
        "state_file": env["OPTIMIZATION_STATE_FILE"],
        "optimized_prefix": env["OPTIMIZED_FILE_PREFIX"],
        "prompt_snapshot_dir": env["PROMPT_SNAPSHOT_DIR"],
    }


def main():
    parser = argparse.ArgumentParser(description="VecGuide 实验运行器")
    parser.add_argument("functions", nargs="*", help="要纳入实验的函数名")
    parser.add_argument("-c", "--clang", default=get_clang_path(),
                        help=f"Clang 路径 (默认: {get_clang_path()})")
    parser.add_argument("-m", "--model", default=get_model_name(), help="模型名称")
    parser.add_argument("-r", "--rounds", type=int, default=config.DEFAULT_MAX_ROUNDS,
                        help=f"最大优化轮数 (默认: {config.DEFAULT_MAX_ROUNDS})")
    parser.add_argument("--strategies", default=DEFAULT_EXPERIMENT_STRATEGY_CSV,
                        help=f"逗号分隔的实验策略列表；默认 {DEFAULT_EXPERIMENT_STRATEGY_CSV}")
    parser.add_argument("--from-analysis", metavar="FILE",
                        help="使用现有问题映射文件")
    parser.add_argument("--severity", default=None,
                        help="按严重程度筛选函数 (high, medium, low, 或组合)")
    parser.add_argument("--run-id", default=None, help="自定义 run_id")
    parser.add_argument("--cleanup-run-id", default=None,
                        help="删除指定 run-id 的已有产物目录后退出")
    parser.add_argument("--force-clean-run-id", action="store_true",
                        help="若目标 run-id 已存在且非空，则先删除该目录再开始实验")
    parser.add_argument("--collect-only", action="store_true",
                        help="复用已有 run 的策略输出，只补生成论文汇总产物；不调用优化/API")
    parser.add_argument("--dry-run", action="store_true", help="只生成 manifest，不执行优化")
    parser.add_argument("--refresh-analysis", action="store_true",
                        help="先重新生成 shared problem_map")
    parser.add_argument("--list-strategies", action="store_true", help="列出可用实验策略")
    parser.add_argument("--benchmark-protocol", default="formal",
                        choices=[*list_benchmark_protocol_names(), "custom", "auto"],
                        help="benchmark 协议标签，默认 formal")
    parser.add_argument("--warmup-runs", type=int, default=None,
                        help="覆盖 benchmark 协议的 warmup 次数；覆盖后不再视为正式主表协议")
    parser.add_argument("--timing-runs", type=int, default=None,
                        help="覆盖 benchmark 协议的计时次数，至少为 3；覆盖后不再视为正式主表协议")
    parser.add_argument("--batches", type=int, default=None,
                        help="覆盖 benchmark 协议的重复批次数；覆盖后不再视为正式主表协议")

    args = parser.parse_args()

    if args.list_strategies:
        print(json.dumps(list_experiment_strategies(), indent=2, ensure_ascii=False))
        return 0

    repo_root = Path(__file__).resolve().parent
    if args.cleanup_run_id:
        cleaned_dir = cleanup_run_dir(repo_root, args.cleanup_run_id)
        print(f"已清理 run-id 目录: {cleaned_dir}")
        return 0
    benchmark_config = build_benchmark_config(
        args.warmup_runs,
        args.timing_runs,
        args.batches,
        args.benchmark_protocol,
    )

    run_id = args.run_id or generate_run_id()
    run_dir = repo_root / RUNS_ROOT / run_id
    shared_dir = run_dir / "shared"
    strategy_root = run_dir / "strategies"

    if args.collect_only:
        if not args.run_id:
            raise ValueError("collect-only 必须显式提供 --run-id")
        return collect_existing_run(
            repo_root=repo_root,
            run_id=run_id,
            clang_path=args.clang,
            fallback_benchmark_config=benchmark_config,
        )

    if run_dir.exists() and any(run_dir.iterdir()):
        if args.force_clean_run_id:
            cleanup_run_dir(repo_root, run_id)
            emit_progress(f"已清理旧的 run-id 目录并重新开始: {run_dir}")
        else:
            raise FileExistsError(
                f"run-id 已存在且目录非空: {run_dir}\n"
                "为避免旧的 optimization_state / summary 污染本次结果，请使用新的 --run-id，"
                "或先执行 --cleanup-run-id / 再配合 --force-clean-run-id。"
            )

    strategy_names = parse_strategy_names(args.strategies)
    strategies = [get_experiment_strategy(name) for name in strategy_names]

    run_dir.mkdir(parents=True, exist_ok=True)
    shared_dir.mkdir(parents=True, exist_ok=True)
    strategy_root.mkdir(parents=True, exist_ok=True)
    initialize_run_directory_contract(run_dir, strategy_root, strategies)
    strategy_config_file = write_strategy_config(run_dir, run_id, strategies)

    shared_problem_map = shared_dir / "problem_map.json"

    if args.refresh_analysis:
        run_analysis(repo_root, args.clang, shared_problem_map)
    elif args.from_analysis:
        source_map = Path(args.from_analysis)
        if not source_map.exists():
            raise FileNotFoundError(f"问题映射文件不存在: {source_map}")
        shutil.copy2(source_map, shared_problem_map)
    elif args.severity and not args.functions:
        default_map = repo_root / config.PROBLEM_MAP_FILE
        if not default_map.exists():
            raise FileNotFoundError(f"缺少 problem_map，无法按严重程度筛选: {default_map}")
        shutil.copy2(default_map, shared_problem_map)
    elif not args.functions:
        default_map = repo_root / config.PROBLEM_MAP_FILE
        if default_map.exists():
            shutil.copy2(default_map, shared_problem_map)

    effective_problem_map = shared_problem_map if shared_problem_map.exists() else None
    functions = resolve_functions(args, effective_problem_map)

    manifest = build_manifest(
        repo_root=repo_root,
        run_id=run_id,
        strategies=strategies,
        functions=functions,
        clang_path=args.clang,
        model_name=args.model,
        requested_rounds=args.rounds,
        shared_problem_map=effective_problem_map,
        benchmark_config=benchmark_config,
        dry_run=args.dry_run,
    )
    write_json(run_dir / "manifest.json", manifest)

    if args.dry_run:
        dry_strategy_results = [
            {
                "strategy": strategy["name"],
                "exit_code": None,
                "summary_file": str(strategy_root / strategy["name"] / "summary.json"),
                "state_file": str(strategy_root / strategy["name"] / "optimization_state.json"),
                "prompt_snapshot_dir": str(strategy_root / strategy["name"] / "prompt_snapshot"),
            }
            for strategy in strategies
        ]
        prompt_snapshot_index_file = write_run_prompt_snapshot_index(
            run_dir=run_dir,
            run_id=run_id,
            strategy_results=dry_strategy_results,
        )
        artifact_index_file = run_dir / "artifact_index.json"
        write_json(
            run_dir / "summary.json",
            {
                "run_id": run_id,
                "mode": "dry_run",
                "functions": functions,
                "strategies": strategy_names,
                "benchmark_config": benchmark_config,
                "strategy_config_file": public_path(strategy_config_file, base_dir=run_dir),
                "prompt_snapshot_index_file": public_path(prompt_snapshot_index_file, base_dir=run_dir),
                "artifact_index_file": public_path(artifact_index_file, base_dir=run_dir),
                "raw_logs_dir": public_path(run_dir / "raw_logs", base_dir=run_dir),
            },
        )
        write_artifact_index(
            run_dir=run_dir,
            run_id=run_id,
            strategies=strategies,
            strategy_results=dry_strategy_results,
            dry_run=True,
        )
        print(f"Dry run 完成，manifest 已写入: {run_dir / 'manifest.json'}")
        return 0

    problem_map = load_problem_map(effective_problem_map) if effective_problem_map else {}
    strategy_results = []
    all_rows: List[Dict] = []
    for strategy in strategies:
        strategy_dir = strategy_root / strategy["name"]
        result = run_strategy(
            repo_root=repo_root,
            strategy=strategy,
            strategy_dir=strategy_dir,
            shared_problem_map=effective_problem_map,
            functions=functions,
            clang_path=args.clang,
            model_name=args.model,
            requested_rounds=args.rounds,
            benchmark_config=benchmark_config,
        )
        result, rows = collect_strategy_artifacts(
            run_id=run_id,
            strategy=strategy,
            strategy_result=result,
            strategy_dir=strategy_dir,
            functions=functions,
            clang_path=args.clang,
            problem_map=problem_map,
            benchmark_config=benchmark_config,
        )
        strategy_results.append(result)
        all_rows.extend(rows)

    write_run_paper_outputs(
        run_dir=run_dir,
        run_id=run_id,
        functions=functions,
        strategies=strategies,
        strategy_results=strategy_results,
        all_rows=all_rows,
        benchmark_config=benchmark_config,
        strategy_config_file=strategy_config_file,
    )

    failed = [item for item in strategy_results if item["exit_code"] != 0]
    if failed:
        for item in failed:
            print(f"❌ 策略失败: {item['strategy']} (exit={item['exit_code']})")
        return 1

    print(f"实验运行完成: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
