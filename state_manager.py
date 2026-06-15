"""
优化状态管理模块
管理多轮优化历史记录
"""

import json
import os
from datetime import datetime
from pathlib import Path

# 从 config 导入配置，保持配置一致性
try:
    from config import config
    STATE_FILE = config.OPTIMIZATION_STATE_FILE
    MAX_ROUNDS = config.MAX_ROUNDS
except ImportError:
    # 备用默认值
    STATE_FILE = "optimization_state.json"
    MAX_ROUNDS = 3

STATE_SCHEMA_VERSION = 2
STATE_SCHEMA_KEY = "state_schema_version"
VALID_STATUSES = {"pending", "optimizing", "partial_success", "success", "failed", "skipped"}


def _resolve_state_file(state_file=None):
    """解析状态文件路径，允许调用方显式覆盖默认状态文件。"""
    return state_file or STATE_FILE


def _iter_function_items(state):
    """遍历状态中的函数条目，跳过元数据字段。"""
    for key, value in state.items():
        if key == STATE_SCHEMA_KEY:
            continue
        if isinstance(value, dict):
            yield key, value


def _normalize_status(status: str) -> str:
    if status in VALID_STATUSES:
        return status
    return "pending"


def _migrate_to_v2(state):
    """
    v2 迁移：
    - 引入 partial_success 状态
    - 将可判定的 legacy failed（有向量化增量）迁移为 partial_success
    """
    changed = False

    for _, func_state in _iter_function_items(state):
        status = _normalize_status(func_state.get("status", "pending"))
        if status != func_state.get("status"):
            func_state["status"] = status
            changed = True

        if status != "failed":
            continue

        best_round_idx = func_state.get("best")
        rounds = func_state.get("rounds", [])
        if not isinstance(best_round_idx, int) or best_round_idx < 1 or best_round_idx > len(rounds):
            continue

        best_round = rounds[best_round_idx - 1]
        if not isinstance(best_round, dict):
            continue

        if (
            best_round.get("compilable")
            and not best_round.get("vectorized", False)
            and best_round.get("vectorized_count", 0) > 0
        ):
            func_state["status"] = "partial_success"
            changed = True

    if state.get(STATE_SCHEMA_KEY) != STATE_SCHEMA_VERSION:
        state[STATE_SCHEMA_KEY] = STATE_SCHEMA_VERSION
        changed = True

    return changed


def load_state(state_file=None):
    """加载优化状态"""
    state_path = _resolve_state_file(state_file)

    if os.path.exists(state_path):
        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            if not isinstance(state, dict):
                return {}

            schema_version = state.get(STATE_SCHEMA_KEY, 1)
            changed = False
            if schema_version < 2:
                changed = _migrate_to_v2(state)
            elif schema_version != STATE_SCHEMA_VERSION:
                state[STATE_SCHEMA_KEY] = STATE_SCHEMA_VERSION
                changed = True

            if changed:
                save_state(state, state_path)
            return state
        except Exception as e:
            print(f"⚠️  加载状态文件失败 ({state_path}): {e}")
            return {}
    return {STATE_SCHEMA_KEY: STATE_SCHEMA_VERSION}


def save_state(state, state_file=None):
    """保存优化状态"""
    state_path = _resolve_state_file(state_file)
    try:
        state[STATE_SCHEMA_KEY] = STATE_SCHEMA_VERSION
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ 保存状态文件失败 ({state_path}): {e}")
        return False


def get_function_state(func_name, state=None):
    """获取特定函数的状态"""
    if state is None:
        state = load_state()

    if func_name not in state:
        state[func_name] = {
            "original_code": None,
            "rounds": [],
            "best": None,
            "status": "pending"  # pending, optimizing, partial_success, success, failed
        }
    return state[func_name]


def add_round(
    func_name,
    code,
    result,
    diagnostics=None,
    state=None,
    strategy="",
    correctness_report=None,
    semantic_risks=None,
    prompt_snapshot=None,
):
    """
    添加一轮优化记录

    result: dict with keys:
        - compilable: bool
        - vectorized: bool
        - vectorized_count: int
        - missed_count: int
        - error: str (optional)
    strategy: str, 优化策略描述
    """
    if state is None:
        state = load_state()

    func_state = get_function_state(func_name, state)

    round_num = len(func_state["rounds"]) + 1

    round_record = {
        "round": round_num,
        "timestamp": datetime.now().isoformat(),
        "code": code,
        "compilable": result.get("compilable", False),
        "vectorized": result.get("vectorized", False),
        "vectorized_count": result.get("vectorized_count", 0),
        "missed_count": result.get("missed_count", 0),
        "error": result.get("error", None),
        "diagnostics": diagnostics,
        "strategy": strategy,
        "correctness_report": correctness_report,
        "semantic_risks": list(semantic_risks or []),
        "prompt_snapshot": prompt_snapshot,
    }

    func_state["rounds"].append(round_record)

    # 更新最佳结果
    if result.get("compilable"):
        if func_state["best"] is None:
            func_state["best"] = round_num
        else:
            best_round = func_state["rounds"][func_state["best"] - 1]
            # 如果当前轮次更好（更多向量化，更少错过），更新最佳
            if (result.get("vectorized_count", 0) > best_round.get("vectorized_count", 0) or
                (result.get("vectorized_count", 0) == best_round.get("vectorized_count", 0) and
                 result.get("missed_count", 0) < best_round.get("missed_count", 0))):
                func_state["best"] = round_num

    # 中间态更新（最终态由优化流程统一回写）
    if result.get("vectorized"):
        func_state["status"] = "success"
    else:
        func_state["status"] = "optimizing"

    save_state(state)
    return round_num


def determine_final_status(final_result=None, correctness_report=None, terminated=True):
    """
    统一的终态判定：
    - success: 完全向量化 + 正确性通过
    - partial_success: 部分向量化 + 正确性通过
    - failed: 其余终态
    - optimizing: 非终态兜底
    """
    if not final_result:
        return "failed" if terminated else "optimizing"

    correctness_ok = True
    if correctness_report is not None:
        correctness_ok = bool(correctness_report.get("overall", False))

    vectorized = bool(final_result.get("vectorized", False))
    vectorized_count = int(final_result.get("vectorized_count", 0) or 0)
    compilable = bool(final_result.get("compilable", False))

    if compilable and vectorized and correctness_ok:
        return "success"
    if compilable and (not vectorized) and vectorized_count > 0 and correctness_ok:
        return "partial_success"
    return "failed" if terminated else "optimizing"


def set_function_final_status(func_name, status, correctness_overall=None, state=None):
    """回写函数最终状态。"""
    if state is None:
        state = load_state()

    func_state = get_function_state(func_name, state)
    func_state["status"] = _normalize_status(status)
    if correctness_overall is not None:
        func_state["correctness_overall"] = bool(correctness_overall)
    save_state(state)


def set_original_code(func_name, code, state=None):
    """设置原始代码"""
    if state is None:
        state = load_state()

    func_state = get_function_state(func_name, state)
    func_state["original_code"] = code
    save_state(state)


def get_code_for_next_round(func_name, state=None):
    """
    获取下一轮优化应该使用的代码
    返回: (code, round_num, is_first_round)
    """
    if state is None:
        state = load_state()

    func_state = get_function_state(func_name, state)

    if not func_state["rounds"]:
        # 第一轮，使用原始代码
        return func_state.get("original_code"), 1, True

    # 优先使用最近一个 correctness 通过的候选，避免后续轮次继续建立在语义错误的代码上。
    for round_record in reversed(func_state["rounds"]):
        correctness_report = round_record.get("correctness_report")
        if correctness_report and correctness_report.get("overall", False):
            return round_record["code"], len(func_state["rounds"]) + 1, False

    # 如果还没有 correctness 通过的轮次，则退回原始代码，避免后续轮次继续建立在语义错误候选上。
    original_code = func_state.get("original_code")
    if original_code:
        return original_code, len(func_state["rounds"]) + 1, False

    # 兜底：原始代码缺失时才使用上一轮代码
    last_round = func_state["rounds"][-1]
    return last_round["code"], len(func_state["rounds"]) + 1, False


def get_best_code(func_name, state=None):
    """获取函数的最佳代码"""
    if state is None:
        state = load_state()

    func_state = get_function_state(func_name, state)

    best_round = func_state.get("best")
    rounds = func_state.get("rounds", [])
    if not isinstance(best_round, int):
        return None

    if best_round < 1 or best_round > len(rounds):
        return None

    best_record = rounds[best_round - 1]
    if not isinstance(best_record, dict):
        return None
    return best_record.get("code")


def get_ranked_round_numbers(func_name, state=None):
    """按当前 best 规则对可编译轮次排序，返回 1-based round 编号列表。"""
    if state is None:
        state = load_state()

    func_state = get_function_state(func_name, state)
    ranked_rounds = []

    for round_record in func_state.get("rounds", []):
        if not round_record.get("compilable"):
            continue
        ranked_rounds.append(round_record)

    ranked_rounds.sort(
        key=lambda record: (
            -(record.get("vectorized_count", 0) or 0),
            record.get("missed_count", 0) or 0,
            record.get("round", 0) or 0,
        )
    )
    return [record["round"] for record in ranked_rounds]


def set_best_round(func_name, round_num, state=None):
    """显式更新最佳轮次。"""
    if state is None:
        state = load_state()

    func_state = get_function_state(func_name, state)
    rounds = func_state.get("rounds", [])
    if not isinstance(round_num, int) or round_num < 1 or round_num > len(rounds):
        return False

    func_state["best"] = round_num
    save_state(state)
    return True


def get_summary(state=None):
    """获取所有函数的优化摘要"""
    if state is None:
        state = load_state()

    summary = {
        "total": 0,
        "success": 0,
        "partial_success": 0,
        "failed": 0,
        "skipped": 0,
        "optimizing": 0,
        "pending": 0,
        "functions": {}
    }

    for func_name, func_state in _iter_function_items(state):
        status = _normalize_status(func_state.get("status", "pending"))
        summary["total"] += 1
        summary[status] += 1

        summary["functions"][func_name] = {
            "status": status,
            "rounds": len(func_state.get("rounds", [])),
            "best_round": func_state.get("best")
        }

    return summary


def should_continue_optimization(func_name, max_rounds=None, state=None):
    """检查是否应该继续优化该函数"""
    if max_rounds is None:
        max_rounds = MAX_ROUNDS
    """检查是否应该继续优化该函数"""
    if state is None:
        state = load_state()

    func_state = get_function_state(func_name, state)

    # 已经成功
    if func_state.get("status") == "success":
        return False

    # 超过最大轮数
    if len(func_state.get("rounds", [])) >= max_rounds:
        return False

    return True


def reset_function(func_name, state=None):
    """重置特定函数的优化状态"""
    if state is None:
        state = load_state()

    if func_name in state:
        del state[func_name]
        save_state(state)
        return True
    return False


def reset_all():
    """重置所有优化状态"""
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        return True
    return False
