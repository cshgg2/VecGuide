"""
Benchmark protocol definitions for publication-oriented experiments.

The goal is to prevent screening measurements from being mixed with formal
paper-table results.
"""

from copy import deepcopy
from typing import Dict, List


BENCHMARK_PROTOCOLS: Dict[str, Dict] = {
    "formal": {
        "protocol_name": "formal",
        "protocol_role": "formal_main_table",
        "display_name": "formal(warmup=3,timing=10,batches=5)",
        "warmup_runs": 3,
        "timing_runs": 10,
        "batches": 5,
        "paper_main_table_eligible": True,
        "description": "Formal CGO-oriented benchmark protocol for main paper tables.",
    },
    "screening": {
        "protocol_name": "screening",
        "protocol_role": "candidate_screening",
        "display_name": "screening(warmup=1,timing=3,batches=3)",
        "warmup_runs": 1,
        "timing_runs": 3,
        "batches": 3,
        "paper_main_table_eligible": False,
        "description": "Light protocol for candidate screening and quick repeats only.",
    },
    "pipeline_selection": {
        "protocol_name": "pipeline_selection",
        "protocol_role": "internal_selection",
        "display_name": "pipeline_selection(warmup=0,timing=3,batches=1)",
        "warmup_runs": 0,
        "timing_runs": 3,
        "batches": 1,
        "paper_main_table_eligible": False,
        "description": "Internal lightweight benchmark used by the optimizer to rank candidates.",
    },
    "timeout_limited": {
        "protocol_name": "timeout_limited",
        "protocol_role": "timeout_limited_evidence",
        "display_name": "timeout_limited(warmup=1,timing=3,batches=3)",
        "warmup_runs": 1,
        "timing_runs": 3,
        "batches": 3,
        "paper_main_table_eligible": False,
        "description": (
            "Protocol label for heavyweight kernels where formal or mid-size "
            "benchmark attempts timed out; report only as protocol-limited evidence."
        ),
    },
}


def list_benchmark_protocol_names() -> List[str]:
    return sorted(BENCHMARK_PROTOCOLS)


def get_benchmark_protocol(name: str) -> Dict:
    if name not in BENCHMARK_PROTOCOLS:
        available = ", ".join(list_benchmark_protocol_names())
        raise ValueError(f"Unknown benchmark protocol: {name}. Available: {available}, custom, auto")
    return deepcopy(BENCHMARK_PROTOCOLS[name])


def _matches_protocol(config: Dict, protocol: Dict) -> bool:
    return (
        config["warmup_runs"] == protocol["warmup_runs"]
        and config["timing_runs"] == protocol["timing_runs"]
        and config["batches"] == protocol["batches"]
    )


def infer_benchmark_protocol(warmup_runs: int, timing_runs: int, batches: int) -> Dict:
    config = {
        "warmup_runs": warmup_runs,
        "timing_runs": timing_runs,
        "batches": batches,
    }
    for name in ("formal", "screening", "pipeline_selection"):
        protocol = get_benchmark_protocol(name)
        if _matches_protocol(config, protocol):
            return protocol

    protocol = {
        "protocol_name": "custom",
        "protocol_role": "custom_or_ad_hoc",
        "display_name": f"custom(warmup={warmup_runs},timing={timing_runs},batches={batches})",
        "warmup_runs": warmup_runs,
        "timing_runs": timing_runs,
        "batches": batches,
        "paper_main_table_eligible": False,
        "description": "Custom/ad-hoc benchmark protocol; do not use as a main paper-table result.",
    }
    return protocol


def resolve_benchmark_protocol(
    protocol_name: str | None = "formal",
    warmup_runs: int | None = None,
    timing_runs: int | None = None,
    batches: int | None = None,
) -> Dict:
    """
    Resolve protocol metadata and effective benchmark parameters.

    If a named protocol is selected and no numeric overrides are provided, the
    protocol defaults are used. If numeric overrides change a named protocol,
    the result is marked as a modified/custom protocol and is not main-table
    eligible.
    """
    if protocol_name in (None, "auto"):
        if warmup_runs is None or timing_runs is None or batches is None:
            protocol = get_benchmark_protocol("formal")
            protocol["inferred_from_parameters"] = False
            return protocol
        protocol = infer_benchmark_protocol(warmup_runs, timing_runs, batches)
        protocol["inferred_from_parameters"] = True
        return protocol

    if protocol_name == "custom":
        if warmup_runs is None or timing_runs is None or batches is None:
            raise ValueError("custom benchmark protocol requires --warmup-runs, --timing-runs, and --batches")
        protocol = infer_benchmark_protocol(warmup_runs, timing_runs, batches)
        protocol["protocol_name"] = "custom"
        protocol["protocol_role"] = "custom_or_ad_hoc"
        protocol["paper_main_table_eligible"] = False
        protocol["inferred_from_parameters"] = False
        return protocol

    protocol = get_benchmark_protocol(protocol_name)
    base = deepcopy(protocol)
    if warmup_runs is not None:
        protocol["warmup_runs"] = warmup_runs
    if timing_runs is not None:
        protocol["timing_runs"] = timing_runs
    if batches is not None:
        protocol["batches"] = batches

    protocol["inferred_from_parameters"] = False
    if not _matches_protocol(protocol, base):
        protocol["base_protocol_name"] = base["protocol_name"]
        protocol["protocol_name"] = f"{base['protocol_name']}_modified"
        protocol["protocol_role"] = "custom_or_ad_hoc"
        protocol["display_name"] = (
            f"{protocol['protocol_name']}(warmup={protocol['warmup_runs']},"
            f"timing={protocol['timing_runs']},batches={protocol['batches']})"
        )
        protocol["paper_main_table_eligible"] = False
        protocol["warning"] = (
            "Numeric overrides changed a named protocol; treat this result as custom/ad-hoc."
        )

    return protocol


def validate_benchmark_protocol_config(config: Dict) -> None:
    if config["warmup_runs"] < 0:
        raise ValueError("warmup-runs cannot be negative")
    if config["timing_runs"] < 3:
        raise ValueError("timing-runs must be at least 3")
    if config["batches"] < 1:
        raise ValueError("batches must be at least 1")
