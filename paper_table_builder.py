#!/usr/bin/env python3
"""
Build publication-oriented result tables from experiment run artifacts.

Inputs are one or more `experiments/runs/<run_id>/paper_results.csv` files plus
an optional `problem_map.json`. The script enriches raw rows with benchmark
protocol metadata and blocker categories, then emits both all-evidence and
main-table-only summaries.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from benchmark_protocols import infer_benchmark_protocol
from experiment_config import get_experiment_strategy
from feedback_structuring import category_label, categorize_reason


STANDARD_STRATEGIES = [
    "origin",
    "strong_plain",
    "diagnostic_only",
    "case_card_only",
    "full_method",
]


def read_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_csv_rows(path: Path) -> List[Dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_supplemental_rows(path: Path) -> List[Dict]:
    if path.suffix.lower() == ".json":
        payload = read_json(path)
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            return payload["rows"]
        raise ValueError(f"supplemental JSON must be a list or contain a rows list: {path}")
    return read_csv_rows(path)


def write_csv(path: Path, rows: List[Dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def parse_float(value) -> Optional[float]:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value) -> Optional[int]:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def format_number(value, digits: int = 3) -> str:
    parsed = parse_float(value)
    if parsed is None:
        return "-"
    return f"{parsed:.{digits}f}"


def normalize_strategy_name(strategy_name: str) -> str:
    try:
        return get_experiment_strategy(strategy_name)["publication_name"]
    except Exception:
        return strategy_name or "unknown"


def infer_protocol_from_row(row: Dict) -> Dict:
    protocol_name = (row.get("benchmark_protocol") or "").strip()
    warmup = parse_int(row.get("benchmark_warmup_runs"))
    timing = parse_int(row.get("benchmark_timing_runs"))
    batches = parse_int(row.get("benchmark_batches"))

    if protocol_name:
        return {
            "protocol_name": protocol_name,
            "protocol_role": row.get("benchmark_protocol_role") or "unknown",
            "display_name": row.get("benchmark_protocol_display") or protocol_name,
            "paper_main_table_eligible": parse_bool(row.get("paper_main_table_eligible")),
            "warning": row.get("benchmark_protocol_warning") or None,
            "warmup_runs": warmup,
            "timing_runs": timing,
            "batches": batches,
        }

    if warmup is None or timing is None or batches is None:
        return {
            "protocol_name": "unknown",
            "protocol_role": "unknown",
            "display_name": "unknown",
            "paper_main_table_eligible": False,
            "warning": "missing benchmark protocol parameters",
            "warmup_runs": warmup,
            "timing_runs": timing,
            "batches": batches,
        }

    protocol = infer_benchmark_protocol(warmup, timing, batches)
    protocol["warning"] = protocol.get("warning")
    return protocol


def blocker_categories_for_function(problem_map: Dict, function_name: str) -> Tuple[List[str], str]:
    info = problem_map.get(function_name, {}) if problem_map else {}
    categories: List[str] = []
    for problem in info.get("problems", []) or []:
        if not isinstance(problem, dict):
            continue
        categories.extend(categorize_reason(problem.get("reason", "")))

    ordered = []
    for category in categories:
        if category and category not in ordered:
            ordered.append(category)
    if not ordered:
        if info.get("not_vectorized_count", 0):
            ordered = ["other"]
        else:
            ordered = ["unknown_or_already_vectorized"]
    primary = ordered[0]
    return ordered, primary


def enrich_row(row: Dict, csv_file: Path, problem_map: Dict) -> Dict:
    protocol = infer_protocol_from_row(row)
    function_name = row.get("function", "")
    categories, primary = blocker_categories_for_function(problem_map, function_name)
    correctness = parse_bool(row.get("correctness_overall"))
    benchmark_success = parse_bool(row.get("benchmark_success"))
    protocol_eligible = bool(protocol.get("paper_main_table_eligible"))
    speedup = parse_float(row.get("speedup"))
    observed_outcome = row.get("observed_outcome") or ""

    if not correctness:
        conclusion = "correctness_failed"
    elif not protocol_eligible:
        conclusion = "protocol_limited_or_nonformal"
    elif not benchmark_success:
        conclusion = "benchmark_failed"
    elif speedup is None:
        conclusion = "missing_speedup"
    else:
        conclusion = observed_outcome or "benchmark_success"

    return {
        **row,
        "source_csv": str(csv_file),
        "source_run_dir": str(csv_file.parent),
        "canonical_strategy": normalize_strategy_name(row.get("strategy", "")),
        "blocking_categories": ",".join(categories),
        "primary_blocker": primary,
        "primary_blocker_label": (
            category_label(primary)
            if primary != "unknown_or_already_vectorized"
            else "unknown or already vectorized"
        ),
        "benchmark_protocol": protocol.get("protocol_name"),
        "benchmark_protocol_role": protocol.get("protocol_role"),
        "benchmark_protocol_display": protocol.get("display_name"),
        "paper_main_table_eligible": protocol_eligible,
        "benchmark_protocol_warning": protocol.get("warning"),
        "main_table_result_usable": protocol_eligible and correctness and benchmark_success and speedup is not None,
        "conclusion_type": conclusion,
    }


def collect_result_rows(
    run_dirs: Iterable[Path],
    problem_map: Dict,
    supplemental_row_files: Optional[Iterable[Path]] = None,
) -> List[Dict]:
    rows: List[Dict] = []
    for run_dir in run_dirs:
        csv_file = run_dir / "paper_results.csv"
        if not csv_file.exists():
            raise FileNotFoundError(f"missing paper_results.csv: {csv_file}")
        for row in read_csv_rows(csv_file):
            rows.append(enrich_row(row, csv_file, problem_map))
    for supplemental_file in supplemental_row_files or []:
        for row in read_supplemental_rows(supplemental_file):
            rows.append(enrich_row(row, supplemental_file, problem_map))
    return rows


def row_quality_key(row: Dict) -> Tuple:
    return (
        1 if parse_bool(row.get("main_table_result_usable")) else 0,
        1 if parse_bool(row.get("paper_main_table_eligible")) else 0,
        1 if parse_bool(row.get("correctness_overall")) else 0,
        1 if parse_bool(row.get("benchmark_success")) else 0,
        parse_float(row.get("speedup")) or -1.0,
        parse_int(row.get("analysis_vectorized_count")) or 0,
    )


def select_representative_rows(rows: List[Dict]) -> Dict[Tuple[str, str], Dict]:
    selected: Dict[Tuple[str, str], Dict] = {}
    source_runs: Dict[Tuple[str, str], List[str]] = {}
    for row in rows:
        key = (row.get("function", ""), row.get("canonical_strategy", ""))
        source_runs.setdefault(key, [])
        run_id = row.get("run_id") or Path(row.get("source_run_dir", "")).name
        if run_id and run_id not in source_runs[key]:
            source_runs[key].append(run_id)

        if key not in selected or row_quality_key(row) > row_quality_key(selected[key]):
            selected[key] = row

    for key, row in selected.items():
        row["all_source_runs_for_function_strategy"] = ",".join(source_runs.get(key, []))
    return selected


def strategy_cell(row: Optional[Dict]) -> str:
    if not row:
        return "-"
    speedup = row.get("speedup")
    speedup_text = f"{format_number(speedup)}x" if parse_float(speedup) is not None else "NA"
    vectorized = f"v{row.get('analysis_vectorized_count', '-')}/m{row.get('analysis_missed_count', '-')}"
    protocol = row.get("benchmark_protocol") or "unknown"
    conclusion = row.get("conclusion_type") or row.get("observed_outcome") or "-"
    return f"{speedup_text}; {vectorized}; {protocol}; {conclusion}"


def build_wide_rows(rows: List[Dict], strategies: List[str]) -> List[Dict]:
    selected = select_representative_rows(rows)
    functions = sorted({row.get("function", "") for row in rows})
    wide_rows: List[Dict] = []

    for function_name in functions:
        function_rows = [row for row in rows if row.get("function") == function_name]
        if not function_rows:
            continue
        anchor = function_rows[0]
        wide = {
            "function": function_name,
            "primary_blocker": anchor.get("primary_blocker"),
            "primary_blocker_label": anchor.get("primary_blocker_label"),
            "blocking_categories": anchor.get("blocking_categories"),
            "severity": anchor.get("severity"),
            "problem_count": anchor.get("problem_count"),
            "main_table_has_usable_result": any(parse_bool(row.get("main_table_result_usable")) for row in function_rows),
            "source_runs": ",".join(sorted({row.get("run_id", "") for row in function_rows if row.get("run_id")})),
        }
        for strategy in strategies:
            row = selected.get((function_name, strategy))
            prefix = strategy
            wide[f"{prefix}_result"] = strategy_cell(row)
            wide[f"{prefix}_correctness"] = row.get("correctness_overall") if row else ""
            wide[f"{prefix}_vectorized_count"] = row.get("analysis_vectorized_count") if row else ""
            wide[f"{prefix}_missed_count"] = row.get("analysis_missed_count") if row else ""
            wide[f"{prefix}_speedup"] = row.get("speedup") if row else ""
            wide[f"{prefix}_protocol"] = row.get("benchmark_protocol") if row else ""
            wide[f"{prefix}_main_table_usable"] = row.get("main_table_result_usable") if row else ""
            wide[f"{prefix}_conclusion"] = row.get("conclusion_type") if row else ""
        wide_rows.append(wide)

    return sorted(wide_rows, key=lambda item: (item.get("primary_blocker") or "", item["function"]))


def render_markdown_table(rows: List[Dict], strategies: List[str], title: str) -> str:
    lines = [f"# {title}", ""]
    if not rows:
        lines.append("No rows.")
        return "\n".join(lines) + "\n"

    headers = ["function", "primary_blocker", *strategies]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        values = [
            row.get("function", "-"),
            row.get("primary_blocker", "-"),
            *[row.get(f"{strategy}_result", "-") for strategy in strategies],
        ]
        lines.append("| " + " | ".join(str(value).replace("|", "/") for value in values) + " |")
    lines.append("")
    return "\n".join(lines)


def summarize_rows(rows: List[Dict], wide_rows: List[Dict], main_wide_rows: List[Dict]) -> Dict:
    by_blocker: Dict[str, int] = {}
    by_strategy: Dict[str, int] = {}
    conclusion_counts: Dict[str, int] = {}
    for row in rows:
        by_blocker[row.get("primary_blocker", "unknown")] = by_blocker.get(row.get("primary_blocker", "unknown"), 0) + 1
        by_strategy[row.get("canonical_strategy", "unknown")] = by_strategy.get(row.get("canonical_strategy", "unknown"), 0) + 1
        conclusion = row.get("conclusion_type", "unknown")
        conclusion_counts[conclusion] = conclusion_counts.get(conclusion, 0) + 1

    return {
        "total_long_rows": len(rows),
        "total_functions": len({row.get("function") for row in rows}),
        "total_wide_rows": len(wide_rows),
        "total_main_table_wide_rows": len(main_wide_rows),
        "counts_by_blocker": by_blocker,
        "counts_by_strategy": by_strategy,
        "counts_by_conclusion": conclusion_counts,
    }


LONG_FIELDNAMES = [
    "run_id",
    "source_csv",
    "function",
    "strategy",
    "canonical_strategy",
    "primary_blocker",
    "primary_blocker_label",
    "blocking_categories",
    "severity",
    "problem_count",
    "status",
    "correctness_overall",
    "analysis_vectorized",
    "analysis_vectorized_count",
    "analysis_missed_count",
    "benchmark_protocol",
    "benchmark_protocol_role",
    "paper_main_table_eligible",
    "main_table_result_usable",
    "benchmark_success",
    "speedup",
    "speedup_median",
    "observed_outcome",
    "conclusion_type",
    "error",
]


def wide_fieldnames(strategies: List[str]) -> List[str]:
    fields = [
        "function",
        "primary_blocker",
        "primary_blocker_label",
        "blocking_categories",
        "severity",
        "problem_count",
        "main_table_has_usable_result",
        "source_runs",
    ]
    for strategy in strategies:
        fields.extend(
            [
                f"{strategy}_result",
                f"{strategy}_correctness",
                f"{strategy}_vectorized_count",
                f"{strategy}_missed_count",
                f"{strategy}_speedup",
                f"{strategy}_protocol",
                f"{strategy}_main_table_usable",
                f"{strategy}_conclusion",
            ]
        )
    return fields


def build_and_write_tables(
    run_dirs: List[Path],
    problem_map_file: Path,
    output_dir: Path,
    strategies: Optional[List[str]] = None,
    supplemental_row_files: Optional[List[Path]] = None,
) -> Dict:
    problem_map = read_json(problem_map_file) if problem_map_file else {}
    all_rows = collect_result_rows(run_dirs, problem_map, supplemental_row_files)
    strategies = strategies or STANDARD_STRATEGIES
    wide_rows = build_wide_rows(all_rows, strategies)
    main_rows = [row for row in all_rows if parse_bool(row.get("main_table_result_usable"))]
    main_wide_rows = build_wide_rows(main_rows, strategies)
    summary = summarize_rows(all_rows, wide_rows, main_wide_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "result_table_long.csv", all_rows, LONG_FIELDNAMES)
    write_csv(output_dir / "result_table_wide.csv", wide_rows, wide_fieldnames(strategies))
    write_csv(output_dir / "result_table_main_long.csv", main_rows, LONG_FIELDNAMES)
    write_csv(output_dir / "result_table_main_wide.csv", main_wide_rows, wide_fieldnames(strategies))
    (output_dir / "result_table_wide.md").write_text(
        render_markdown_table(wide_rows, strategies, "All Evidence Result Table"),
        encoding="utf-8",
    )
    (output_dir / "result_table_main_wide.md").write_text(
        render_markdown_table(main_wide_rows, strategies, "Main-Table Eligible Result Table"),
        encoding="utf-8",
    )
    write_json(output_dir / "result_table_summary.json", summary)
    return {
        "output_dir": str(output_dir),
        "summary": summary,
        "files": {
            "long_csv": str(output_dir / "result_table_long.csv"),
            "wide_csv": str(output_dir / "result_table_wide.csv"),
            "main_long_csv": str(output_dir / "result_table_main_long.csv"),
            "main_wide_csv": str(output_dir / "result_table_main_wide.csv"),
            "wide_md": str(output_dir / "result_table_wide.md"),
            "main_wide_md": str(output_dir / "result_table_main_wide.md"),
            "summary_json": str(output_dir / "result_table_summary.json"),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build paper result tables from experiment runs.")
    parser.add_argument("--run-dir", action="append", required=True, help="Experiment run directory. Repeatable.")
    parser.add_argument("--problem-map", default="problem_map.json", help="problem_map.json path")
    parser.add_argument("--output-dir", required=True, help="Output directory for generated tables")
    parser.add_argument(
        "--supplemental-rows",
        action="append",
        default=[],
        help="Optional paper_results-like CSV/JSON rows for curated benchmark/manual records. Repeatable.",
    )
    parser.add_argument(
        "--strategies",
        default=",".join(STANDARD_STRATEGIES),
        help="Comma-separated publication strategy columns for wide tables",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dirs = [Path(item) for item in args.run_dir]
    strategies = [item.strip() for item in args.strategies.split(",") if item.strip()]
    result = build_and_write_tables(
        run_dirs=run_dirs,
        problem_map_file=Path(args.problem_map),
        output_dir=Path(args.output_dir),
        strategies=strategies,
        supplemental_row_files=[Path(item) for item in args.supplemental_rows],
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
