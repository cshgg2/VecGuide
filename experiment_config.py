"""
Experiment strategy configuration.

This module owns strategy definitions only. It does not execute experiments,
write run artifacts, build prompts, or decide paper-table eligibility.

Naming policy:
- Paper-facing strategy names are: origin, strong_plain, diagnostic_only,
  case_card_only, and full_method.
- Legacy operational names such as ours_full and llm_plain remain available
  only for reading old artifacts or running compatibility checks.
- New public experiments should use the paper-facing names.
"""

from copy import deepcopy
from typing import Dict, List


DEFAULT_PROMPT_OPTIONS = {
    "system_prompt_profile": "method",
    "include_strong_baseline_guidance": False,
    "include_diagnostics": True,
    "include_structured_feedback": True,
    "include_semantic_hints": True,
    "include_knowledge": True,
    "include_examples": True,
    "include_history": True,
    "include_progress_analysis": True,
    "use_multi_round_system_prompt": True,
}

DEFAULT_PERFORMANCE_GUARD = {
    "enabled": False,
    "min_median_speedup": 0.80,
    "min_mean_speedup": 0.80,
}


EXPERIMENT_STRATEGIES = {
    "origin": {
        "description": "原始代码基线，不执行 LLM 优化。",
        "publication_name": "origin",
        "paper_role": "原始代码基线。",
        "implementation_status": "ready",
        "prompt_version": "origin_no_prompt_v1_20260601",
        "legacy_name": None,
        "optimizer_enabled": False,
        "single_round": True,
        "max_rounds": 0,
        "prompt_options": deepcopy(DEFAULT_PROMPT_OPTIONS),
        "performance_guard": deepcopy(DEFAULT_PERFORMANCE_GUARD),
    },
    "full_method": {
        "description": "投稿版完整方法：诊断路由 + 案例卡约束 + 多轮反馈 + 性能筛选。",
        "publication_name": "full_method",
        "paper_role": "论文主方法。",
        "implementation_status": "ready",
        "prompt_version": "full_method_v1_20260601",
        "legacy_name": "ours_full",
        "optimizer_enabled": True,
        "single_round": False,
        "max_rounds": None,
        "prompt_options": deepcopy(DEFAULT_PROMPT_OPTIONS),
        "performance_guard": {
            **deepcopy(DEFAULT_PERFORMANCE_GUARD),
            "enabled": True,
        },
    },
    "ours_full": {
        "description": "完整方法：诊断 + 知识库 + Few-shot + 多轮反馈。",
        "publication_name": "full_method",
        "paper_role": "历史完整方法名；投稿版统一称为 full_method。",
        "implementation_status": "legacy_alias",
        "prompt_version": "full_method_v1_20260601",
        "legacy_name": None,
        "optimizer_enabled": True,
        "single_round": False,
        "max_rounds": None,
        "prompt_options": deepcopy(DEFAULT_PROMPT_OPTIONS),
        "performance_guard": {
            **deepcopy(DEFAULT_PERFORMANCE_GUARD),
            "enabled": True,
        },
    },
    "strong_plain": {
        "description": (
            "投稿版强基础提示词 baseline：给出充分的通用自动向量化改写建议，"
            "但关闭诊断路由、结构化反馈、案例卡和多轮。"
        ),
        "publication_name": "strong_plain",
        "paper_role": "公平强基础大模型基线。",
        "implementation_status": "ready",
        "prompt_version": "strong_plain_v1_20260601",
        "legacy_name": None,
        "optimizer_enabled": True,
        "single_round": True,
        "max_rounds": 1,
        "prompt_options": {
            **deepcopy(DEFAULT_PROMPT_OPTIONS),
            "system_prompt_profile": "strong_plain",
            "include_strong_baseline_guidance": True,
            "include_diagnostics": False,
            "include_structured_feedback": False,
            "include_semantic_hints": False,
            "include_knowledge": False,
            "include_examples": False,
            "include_history": False,
            "include_progress_analysis": False,
            "use_multi_round_system_prompt": False,
        },
        "performance_guard": deepcopy(DEFAULT_PERFORMANCE_GUARD),
    },
    "diagnostic_only": {
        "description": "投稿版诊断基线：保留编译诊断和结构化反馈，去掉案例卡、Few-shot 和多轮反馈。",
        "publication_name": "diagnostic_only",
        "paper_role": "诊断反馈消融基线。",
        "implementation_status": "ready",
        "prompt_version": "diagnostic_only_v1_20260601",
        "legacy_name": "llm_plain",
        "optimizer_enabled": True,
        "single_round": True,
        "max_rounds": 1,
        "prompt_options": {
            **deepcopy(DEFAULT_PROMPT_OPTIONS),
            "include_knowledge": False,
            "include_examples": False,
            "include_history": False,
            "include_progress_analysis": False,
            "use_multi_round_system_prompt": False,
        },
        "performance_guard": deepcopy(DEFAULT_PERFORMANCE_GUARD),
    },
    "llm_plain": {
        "description": "纯 LLM baseline：仅保留代码与诊断，不使用知识库、Few-shot 和多轮反馈。",
        "publication_name": "diagnostic_only",
        "paper_role": "历史纯模型基线名；投稿版不再称为 strong_plain。",
        "implementation_status": "legacy_alias",
        "prompt_version": "diagnostic_only_v1_20260601",
        "legacy_name": None,
        "optimizer_enabled": True,
        "single_round": True,
        "max_rounds": 1,
        "prompt_options": {
            **deepcopy(DEFAULT_PROMPT_OPTIONS),
            "include_knowledge": False,
            "include_examples": False,
            "include_history": False,
            "include_progress_analysis": False,
            "use_multi_round_system_prompt": False,
        },
        "performance_guard": deepcopy(DEFAULT_PERFORMANCE_GUARD),
    },
    "case_card_only": {
        "description": "投稿版案例卡基线：保留诊断驱动的案例卡/知识库约束，但只做单轮，不使用历史反馈。",
        "publication_name": "case_card_only",
        "paper_role": "案例卡约束消融基线。",
        "implementation_status": "ready",
        "prompt_version": "case_card_only_v1_20260601",
        "legacy_name": None,
        "optimizer_enabled": True,
        "single_round": True,
        "max_rounds": 1,
        "prompt_options": {
            **deepcopy(DEFAULT_PROMPT_OPTIONS),
            "include_examples": False,
            "include_history": False,
            "include_progress_analysis": False,
            "use_multi_round_system_prompt": False,
        },
        "performance_guard": deepcopy(DEFAULT_PERFORMANCE_GUARD),
    },
    "ablate_kb": {
        "description": "消融：移除知识库，保留 Few-shot 和多轮反馈。",
        "publication_name": "ablate_without_knowledge",
        "paper_role": "历史消融：去掉知识库/案例卡。",
        "implementation_status": "legacy_ablation",
        "prompt_version": "ablate_without_knowledge_v1_20260601",
        "legacy_name": None,
        "optimizer_enabled": True,
        "single_round": False,
        "max_rounds": None,
        "prompt_options": {
            **deepcopy(DEFAULT_PROMPT_OPTIONS),
            "include_knowledge": False,
        },
        "performance_guard": {
            **deepcopy(DEFAULT_PERFORMANCE_GUARD),
            "enabled": True,
        },
    },
    "ablate_examples": {
        "description": "消融：移除 Few-shot 示例，保留知识库和多轮反馈。",
        "publication_name": "ablate_without_fewshot",
        "paper_role": "历史消融：去掉 Few-shot 示例。",
        "implementation_status": "legacy_ablation",
        "prompt_version": "ablate_without_fewshot_v1_20260601",
        "legacy_name": None,
        "optimizer_enabled": True,
        "single_round": False,
        "max_rounds": None,
        "prompt_options": {
            **deepcopy(DEFAULT_PROMPT_OPTIONS),
            "include_examples": False,
        },
        "performance_guard": {
            **deepcopy(DEFAULT_PERFORMANCE_GUARD),
            "enabled": True,
        },
    },
    "ablate_multiround": {
        "description": "消融：保留知识库和 Few-shot，但只做单轮优化。",
        "publication_name": "ablate_without_multiround",
        "paper_role": "历史消融：去掉多轮反馈。",
        "implementation_status": "legacy_ablation",
        "prompt_version": "ablate_without_multiround_v1_20260601",
        "legacy_name": None,
        "optimizer_enabled": True,
        "single_round": True,
        "max_rounds": 1,
        "prompt_options": {
            **deepcopy(DEFAULT_PROMPT_OPTIONS),
            "include_history": False,
            "include_progress_analysis": False,
            "use_multi_round_system_prompt": False,
        },
        "performance_guard": {
            **deepcopy(DEFAULT_PERFORMANCE_GUARD),
            "enabled": True,
        },
    },
}


PUBLICATION_STRATEGY_DEFINITIONS = {
    "origin": {
        "operational_names": ["origin"],
        "legacy_names": [],
        "paper_role": "原始代码基线。",
        "status": "ready",
    },
    "strong_plain": {
        "operational_names": ["strong_plain"],
        "legacy_names": [],
        "paper_role": "公平强基础大模型基线。",
        "status": "ready",
    },
    "diagnostic_only": {
        "operational_names": ["diagnostic_only", "llm_plain"],
        "legacy_names": ["llm_plain"],
        "paper_role": "保留诊断反馈、去掉案例卡和多轮反馈的基线。",
        "status": "ready",
    },
    "case_card_only": {
        "operational_names": ["case_card_only"],
        "legacy_names": [],
        "paper_role": "保留案例卡约束、去掉多轮反馈的消融基线。",
        "status": "ready",
    },
    "full_method": {
        "operational_names": ["full_method", "ours_full"],
        "legacy_names": ["ours_full"],
        "paper_role": "论文主方法。",
        "status": "ready",
    },
    "ablate_without_knowledge": {
        "operational_names": ["ablate_kb"],
        "legacy_names": ["ablate_kb"],
        "paper_role": "历史消融：移除知识库/案例卡。",
        "status": "legacy_ablation",
    },
    "ablate_without_fewshot": {
        "operational_names": ["ablate_examples"],
        "legacy_names": ["ablate_examples"],
        "paper_role": "历史消融：移除 Few-shot 示例。",
        "status": "legacy_ablation",
    },
    "ablate_without_multiround": {
        "operational_names": ["ablate_multiround"],
        "legacy_names": ["ablate_multiround"],
        "paper_role": "历史消融：移除多轮反馈。",
        "status": "legacy_ablation",
    },
}


PAPER_STRATEGY_NAMES = [
    "origin",
    "strong_plain",
    "diagnostic_only",
    "case_card_only",
    "full_method",
]

PAPER_STRATEGY_CSV = ",".join(PAPER_STRATEGY_NAMES)

DEFAULT_EXPERIMENT_STRATEGY_NAMES = [
    "diagnostic_only",
    "full_method",
]

DEFAULT_EXPERIMENT_STRATEGY_CSV = ",".join(DEFAULT_EXPERIMENT_STRATEGY_NAMES)


LEGACY_STRATEGY_NAME_MAP = {
    "ours_full": "full_method",
    "llm_plain": "diagnostic_only",
    "ablate_kb": "ablate_without_knowledge",
    "ablate_examples": "ablate_without_fewshot",
    "ablate_multiround": "ablate_without_multiround",
}


def normalize_prompt_options(prompt_options: Dict | None = None) -> Dict:
    """补齐 prompt 选项的默认值。"""
    normalized = deepcopy(DEFAULT_PROMPT_OPTIONS)
    if prompt_options:
        normalized.update(prompt_options)
    return normalized


def normalize_performance_guard(performance_guard: Dict | None = None) -> Dict:
    """补齐性能守护配置的默认值。"""
    normalized = deepcopy(DEFAULT_PERFORMANCE_GUARD)
    if performance_guard:
        normalized.update(performance_guard)
    return normalized


def get_experiment_strategy(name: str) -> Dict:
    """获取实验策略配置。"""
    if name not in EXPERIMENT_STRATEGIES:
        available = ", ".join(sorted(EXPERIMENT_STRATEGIES))
        raise ValueError(f"未知策略: {name}. 可用策略: {available}")

    strategy = deepcopy(EXPERIMENT_STRATEGIES[name])
    strategy["name"] = name
    strategy.setdefault("publication_name", LEGACY_STRATEGY_NAME_MAP.get(name, name))
    strategy.setdefault("paper_role", "")
    strategy.setdefault("implementation_status", "ready")
    strategy.setdefault("prompt_version", f"{strategy['publication_name']}_unversioned")
    strategy.setdefault("legacy_name", None)
    strategy["prompt_options"] = normalize_prompt_options(strategy.get("prompt_options"))
    strategy["performance_guard"] = normalize_performance_guard(strategy.get("performance_guard"))
    return strategy


def list_experiment_strategies() -> List[Dict]:
    """返回所有实验策略。"""
    return [get_experiment_strategy(name) for name in sorted(EXPERIMENT_STRATEGIES)]


def get_publication_strategy_definition(name: str) -> Dict:
    """获取投稿版策略定义。"""
    if name not in PUBLICATION_STRATEGY_DEFINITIONS:
        available = ", ".join(sorted(PUBLICATION_STRATEGY_DEFINITIONS))
        raise ValueError(f"未知投稿策略: {name}. 可用策略: {available}")
    definition = deepcopy(PUBLICATION_STRATEGY_DEFINITIONS[name])
    definition["name"] = name
    return definition


def _join_contract_parts(parts: List[str]) -> str:
    if not parts:
        return "none"
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def describe_publication_prompt_contract() -> List[Dict]:
    """Return paper-facing prompt switch rows for public docs and tests."""
    rows = []
    for name in PAPER_STRATEGY_NAMES:
        strategy = get_experiment_strategy(name)
        options = strategy["prompt_options"]

        if not strategy["optimizer_enabled"]:
            main_inputs = "original source only"
            iteration = "none"
        elif options["include_strong_baseline_guidance"]:
            main_inputs = "generic vectorization guidance"
            iteration = "single round"
        else:
            parts = []
            if options["include_diagnostics"]:
                parts.append("compiler diagnostics")
            if options["include_structured_feedback"]:
                parts.append("structured feedback")
            if options["include_knowledge"]:
                parts.append("retrieved case cards")
            if options["include_examples"]:
                parts.append("few-shot examples")
            if options["include_history"]:
                parts.append("history")
            if options["include_progress_analysis"]:
                parts.append("progress analysis")
            main_inputs = _join_contract_parts(parts)
            iteration = "multi-round" if options["use_multi_round_system_prompt"] else "single round"

        rows.append({
            "strategy": name,
            "main_prompt_inputs": main_inputs,
            "iteration": iteration,
            "performance_guard": "on" if strategy["performance_guard"]["enabled"] else "off",
        })
    return rows


def list_publication_strategy_definitions() -> List[Dict]:
    """返回投稿版策略定义，供文档和 manifest 使用。"""
    return [
        get_publication_strategy_definition(name)
        for name in PAPER_STRATEGY_NAMES
    ]
