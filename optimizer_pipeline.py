#!/usr/bin/env python3
"""
VecGuide 优化流水线
整合多轮优化流程，支持自动反馈迭代
支持单轮和多轮优化模式
"""

import os
import sys
import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple

from config import config, get_clang_path, get_source_file, get_api_key, get_model_name
from experiment_config import (
    get_experiment_strategy,
    list_experiment_strategies,
    normalize_prompt_options,
)
from feedback_structuring import categorize_reason, dedupe_preserve_order
from state_manager import (
    load_state, save_state, get_function_state, add_round,
    set_original_code, get_code_for_next_round, get_best_code,
    get_summary, reset_function, determine_final_status, set_function_final_status,
    get_ranked_round_numbers, set_best_round,
)
from evaluate_optimization import (
    extract_function_code, analyze_single_function
)
from correctness_verifier import (
    full_correctness_verification,
    format_verification_report,
    run_performance_benchmark,
)
from prompts import (
    build_optimization_prompt,
    build_retry_prompt,
    get_prompt_template_versions,
    resolve_system_prompt_template_name,
)
from prompts.knowledge_base import (
    CASE_CARD_FORMAT_VERSION,
    EXPERIMENT_CASE_CARD_SET_VERSION,
    build_case_card_audit_snapshot,
)
from logger import (
    setup_logger, info, debug, warning, error, success, failure,
    warning_icon, section, subsection, progress
)


# 全局缓存 problem_map
_problem_map_cache = None


FINAL_SELECTION_BENCHMARK_WARMUP_RUNS = 0
FINAL_SELECTION_BENCHMARK_TIMING_RUNS = 3
FINAL_SELECTION_BENCHMARK_BATCHES = 1
DEFAULT_PERFORMANCE_GUARD_MIN_MEDIAN_SPEEDUP = 0.80
DEFAULT_PERFORMANCE_GUARD_MIN_MEAN_SPEEDUP = 0.80


def load_problem_map():
    """加载问题映射文件"""
    global _problem_map_cache
    if _problem_map_cache is not None:
        return _problem_map_cache

    problem_map_file = config.PROBLEM_MAP_FILE
    if os.path.exists(problem_map_file):
        try:
            with open(problem_map_file, 'r', encoding='utf-8') as f:
                _problem_map_cache = json.load(f)
            return _problem_map_cache
        except Exception as e:
            warning_icon(f"加载问题映射文件失败: {e}")
    return {}


def get_function_diagnostics(func_name: str) -> Dict:
    """获取函数的向量化诊断信息"""
    problem_map = load_problem_map()
    return problem_map.get(func_name, {})


def format_diagnostics_for_comment(func_name: str) -> str:
    """格式化诊断信息为注释格式"""
    diag = get_function_diagnostics(func_name)
    if not diag or not diag.get('problems'):
        return f"// Vectorization Issues: None (or data not available)"

    lines = [f"// Vectorization Issues for {func_name}:"]
    lines.append(f"//   Severity: {diag.get('severity', 'unknown')}")
    lines.append(f"//   Total diagnostics: {diag.get('total_diagnostics', 0)}")
    lines.append(f"//   Not vectorized count: {diag.get('not_vectorized_count', 0)}")
    lines.append(f"//   Problems:")

    for i, problem in enumerate(diag.get('problems', []), 1):
        reason = problem.get('reason', 'unknown')
        line = problem.get('line', 0)
        # 截断过长的原因描述
        if len(reason) > 80:
            reason = reason[:77] + '...'
        lines.append(f"//     {i}. Line {line}: {reason}")

    return '\n'.join(lines)


def format_round_header(func_name: str, round_num: int, strategy: str, eval_result: Dict) -> str:
    """格式化每轮优化文件的注释头"""
    lines = [f"// Round {round_num} optimization for {func_name}"]
    lines.append(f"//")

    # 添加优化策略
    lines.append(f"// Optimization Strategy:")
    strategy_lines = strategy.split('\n')
    for sline in strategy_lines[:3]:  # 最多显示3行策略
        sline = sline.strip()
        if sline:
            lines.append(f"//   {sline}")
    lines.append(f"//")

    # 添加编译和向量化状态
    if eval_result:
        compilable = eval_result.get('compilable', False)
        vectorized = eval_result.get('vectorized', False)
        v_count = eval_result.get('vectorized_count', 0)
        m_count = eval_result.get('missed_count', 0)

        lines.append(f"// Compilation: {'✅ Success' if compilable else '❌ Failed'}")
        if compilable:
            lines.append(f"// Vectorization: {'✅ Fully Vectorized' if vectorized else '⚠️ Partial'}")
            lines.append(f"//   Vectorized loops: {v_count}")
            lines.append(f"//   Missed loops: {m_count}")

            # 添加剩余问题
            diagnostics = eval_result.get('diagnostics', {})
            missed = diagnostics.get('missed', [])
            if missed:
                lines.append(f"//")
                lines.append(f"// Remaining Issues:")
                for i, issue in enumerate(missed[:3], 1):  # 最多显示3个问题
                    # 清理和截断
                    issue = issue.strip()
                    if len(issue) > 80:
                        issue = issue[:77] + '...'
                    lines.append(f"//   {i}. {issue}")

    return '\n'.join(lines)


def call_deepseek_anthropic_api(api_key: str, model_name: str, system_prompt: str,
                                  user_prompt: str, max_tokens: int = 2048, temperature: float = 0.2,
                                  max_retries: int = 3, timeout: float = 300.0):
    """调用 DeepSeek 的 Anthropic 兼容 API
    
    Args:
        max_retries: 最大重试次数
        timeout: 请求超时时间（秒），默认 300 秒
    """
    import time
    quota_markers = ("余额不足", "无可用资源包", "insufficient", "quota")
    busy_markers = ("访问人数多", "稍后再试", "try again later", "system busy", "server busy", "too many requests")

    def _retry_wait_seconds(attempt_index: int) -> int:
        return min(60, 5 * (2 ** attempt_index))

    def _response_text_from_json(data) -> str:
        parts = []
        if isinstance(data, dict):
            content = data.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("text"):
                        parts.append(str(item["text"]))
            error = data.get("error")
            if isinstance(error, dict):
                for key in ("message", "code", "type"):
                    if error.get(key):
                        parts.append(str(error[key]))
            for key in ("message", "detail", "type"):
                if data.get(key):
                    parts.append(str(data[key]))
        return " ".join(parts)

    def _contains_any_marker(text: str, markers) -> bool:
        lowered = text.lower()
        return any(marker.lower() in lowered for marker in markers)

    try:
        import httpx  # type: ignore
        http_client = "httpx"
        timeout_errors = (httpx.TimeoutException,)
        status_errors = (httpx.HTTPStatusError,)
    except ModuleNotFoundError:
        import requests
        httpx = None
        http_client = "requests"
        timeout_errors = (requests.exceptions.Timeout,)
        status_errors = (requests.exceptions.HTTPError,)
    
    base_url = config.DEEPSEEK_BASE_URL
    connect_timeout = min(30.0, timeout)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    payload = {
        "model": model_name,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }

    for attempt in range(max_retries):
        try:
            warning_icon(f"API 请求中... (尝试 {attempt + 1}/{max_retries}, 超时: {timeout}秒)")
            if http_client == "httpx":
                response = httpx.post(
                    f"{base_url}/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
            else:
                response = requests.post(
                    f"{base_url}/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=(connect_timeout, timeout)
                )
            response.raise_for_status()
            response_data = response.json()
            response_text = _response_text_from_json(response_data)
            if _contains_any_marker(response_text, busy_markers):
                warning_icon(f"API 返回忙碌提示 (尝试 {attempt + 1}/{max_retries}): {response_text[:120]}")
                if attempt < max_retries - 1:
                    wait_time = _retry_wait_seconds(attempt)
                    warning(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                failure("API 连续返回忙碌提示，已达到最大重试次数。")
                return None
            return response_data
            
        except timeout_errors as e:
            warning_icon(f"API 请求超时 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = _retry_wait_seconds(attempt)
                warning(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                failure(f"API 调用失败：连续 {max_retries} 次超时")
                return None
                
        except status_errors as e:
            status_code = getattr(getattr(e, "response", None), "status_code", "unknown")
            response_text = getattr(getattr(e, "response", None), "text", str(e))
            warning_icon(f"API HTTP 错误 (尝试 {attempt + 1}/{max_retries}): {status_code}")
            failure(f"响应内容: {response_text[:500]}")
            if status_code == 429 and _contains_any_marker(response_text, quota_markers):
                failure("检测到 API 配额或余额不足，停止重试。")
                return None
            if status_code in (429, 503, 529) or _contains_any_marker(response_text, busy_markers):
                if attempt < max_retries - 1:
                    wait_time = _retry_wait_seconds(attempt)
                    warning(f"检测到拥塞/限速，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                failure("API 连续返回拥塞/限速响应，已达到最大重试次数。")
                return None
            if status_code in (400, 401, 403, 404):
                failure("检测到不可恢复的 API 请求错误，停止重试。")
                return None
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None
                
        except Exception as e:
            warning_icon(f"API 调用异常 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                failure(f"API 调用失败: {e}")
                return None
    
    return None


def extract_text_from_api_response(response: Dict) -> Optional[str]:
    """从不同格式的 LLM API 响应中提取可解析文本。"""
    if not isinstance(response, dict):
        return None

    def _collect_text_from_content(content) -> List[str]:
        texts: List[str] = []
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    texts.append(item)
                    continue
                if not isinstance(item, dict):
                    continue
                if item.get("text"):
                    texts.append(str(item["text"]))
                    continue
                for key in ("thinking", "reasoning_content", "output_text", "completion", "response"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        texts.append(value)
                nested_content = item.get("content")
                if isinstance(nested_content, str):
                    texts.append(nested_content)
                elif isinstance(nested_content, list):
                    texts.extend(_collect_text_from_content(nested_content))
        return texts

    def _collect_text_recursively(node) -> List[str]:
        texts: List[str] = []
        if isinstance(node, str):
            if node.strip():
                texts.append(node)
            return texts
        if isinstance(node, list):
            for item in node:
                texts.extend(_collect_text_recursively(item))
            return texts
        if isinstance(node, dict):
            priority_keys = (
                "text",
                "content",
                "message",
                "output_text",
                "completion",
                "response",
                "reasoning_content",
                "thinking",
            )
            for key in priority_keys:
                if key in node:
                    texts.extend(_collect_text_recursively(node.get(key)))
            return texts
        return texts

    candidates: List[str] = []

    candidates.extend(_collect_text_from_content(response.get("content")))

    message = response.get("message")
    if isinstance(message, dict):
        candidates.extend(_collect_text_from_content(message.get("content")))

    choices = response.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            if choice.get("text"):
                candidates.append(str(choice["text"]))
            choice_message = choice.get("message")
            if isinstance(choice_message, dict):
                candidates.extend(_collect_text_from_content(choice_message.get("content")))
            delta = choice.get("delta")
            if isinstance(delta, dict):
                candidates.extend(_collect_text_from_content(delta.get("content")))

    for key in ("output_text", "completion", "response", "text"):
        value = response.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value)

    if not candidates:
        candidates.extend(_collect_text_recursively(response))

    merged = "\n".join(part.strip() for part in candidates if isinstance(part, str) and part.strip()).strip()
    return merged or None


def summarize_api_response_schema(response: Dict) -> str:
    """返回紧凑的响应 schema 摘要，便于定位响应格式差异。"""
    if not isinstance(response, dict):
        return f"non-dict response: {type(response).__name__}"

    parts = [f"top_keys={sorted(response.keys())}"]
    content = response.get("content")
    if isinstance(content, list):
        item_summaries = []
        for item in content[:5]:
            if isinstance(item, dict):
                item_summaries.append(sorted(item.keys()))
            else:
                item_summaries.append(type(item).__name__)
        parts.append(f"content_items={item_summaries}")

    choices = response.get("choices")
    if isinstance(choices, list):
        choice_summaries = []
        for choice in choices[:3]:
            if isinstance(choice, dict):
                choice_summaries.append(sorted(choice.keys()))
            else:
                choice_summaries.append(type(choice).__name__)
        parts.append(f"choices={choice_summaries}")

    return " | ".join(parts)


def find_all_functions_in_file(file_path: str) -> List[str]:
    """查找文件中的所有函数名"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        # 匹配 real_t sXXXX(...) 格式的函数
        pattern = r'real_t\s+(s[0-9]+)\s*\('
        matches = re.findall(pattern, content)
        return sorted(set(matches))
    except Exception as e:
        failure(f"读取文件失败: {e}")
        return []


def _extract_markdown_code_blocks(response_text: str) -> List[Tuple[str, int]]:
    """提取 markdown 代码块及其在原始响应中的起始位置。"""
    blocks: List[Tuple[str, int]] = []
    pattern = re.compile(r"```(?:[A-Za-z0-9_+-]+)?\s*\n(.*?)```", re.DOTALL)
    for match in pattern.finditer(response_text or ""):
        blocks.append((match.group(1).strip(), match.start()))
    return blocks


def _extract_balanced_c_function(code_text: str, func_name: Optional[str] = None) -> Tuple[Optional[str], Optional[int]]:
    """
    从混合文本中提取一个完整的 `real_t sXXXX(...) { ... }` 函数。

    这一步用于过滤模型返回中的解释性文字，只保留真正的函数体。
    """
    if not code_text:
        return None, None

    if func_name:
        pattern = re.compile(rf"\breal_t\s+{re.escape(func_name)}\s*\(")
    else:
        pattern = re.compile(r"\breal_t\s+(s[0-9]+)\s*\(")

    for match in pattern.finditer(code_text):
        start = match.start()
        brace_start = code_text.find("{", match.end())
        if brace_start == -1:
            continue

        depth = 0
        i = brace_start
        in_line_comment = False
        in_block_comment = False
        in_string = False
        in_char = False
        escape = False

        while i < len(code_text):
            ch = code_text[i]
            nxt = code_text[i + 1] if i + 1 < len(code_text) else ""

            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
                i += 1
                continue

            if in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                i += 1
                continue

            if in_char:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == "'":
                    in_char = False
                i += 1
                continue

            if ch == "/" and nxt == "/":
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue
            if ch == '"':
                in_string = True
                i += 1
                continue
            if ch == "'":
                in_char = True
                i += 1
                continue

            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return code_text[start:i + 1].strip(), start
            i += 1

    return None, None


def _contains_placeholder_tokens(code: str) -> bool:
    """检测 `...` / `TODO` / 省略提示等明显的非最终代码占位符。"""
    if not code:
        return True

    stripped = _strip_c_comments(code)
    placeholder_patterns = (
        r"(?m)^\s*\.\.\.\s*$",
        r"\bTODO\b",
        r"\bto be filled\b",
        r"\bplaceholder\b",
        r"省略",
        r"待补充",
    )
    return any(re.search(pattern, stripped, flags=re.IGNORECASE) for pattern in placeholder_patterns)


def _is_valid_function_candidate(code: str, func_name: Optional[str] = None) -> bool:
    """判断候选文本是否像一个可编译的完整 TSVC 函数。"""
    if not code:
        return False

    candidate = code.strip()
    if func_name and not re.search(rf"\breal_t\s+{re.escape(func_name)}\s*\(", candidate):
        return False
    if not re.search(r"\breal_t\s+s[0-9]+\s*\(", candidate):
        return False
    if _contains_placeholder_tokens(candidate):
        return False

    stripped = _strip_c_comments(candidate)
    if re.search(r"[^\x00-\x7F]", stripped):
        return False
    if "return" not in stripped:
        return False

    return True


def _clean_strategy_text(text: str) -> str:
    """清洗策略说明，避免把大段模板或空白误记为策略。"""
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"^(策略|优化策略)\s*[:：]?\s*", "", text, flags=re.IGNORECASE)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[:4]).strip()


def _extract_function_candidate(response_text: str, func_name: Optional[str] = None) -> Tuple[Optional[str], str]:
    """
    从响应中尽量提取一个完整函数。

    优先级：
    1. markdown 代码块中的目标函数
    2. 整个响应中的目标函数
    3. markdown 代码块中的任意 TSVC 函数
    4. 整个响应中的任意 TSVC 函数
    """
    blocks = _extract_markdown_code_blocks(response_text)

    def _iter_sources(prefer_exact_name: bool):
        for block, block_start in blocks:
            candidate, start = _extract_balanced_c_function(
                block,
                func_name=func_name if prefer_exact_name else None,
            )
            if candidate:
                yield candidate, response_text[:block_start]

        candidate, start = _extract_balanced_c_function(
            response_text,
            func_name=func_name if prefer_exact_name else None,
        )
        if candidate:
            yield candidate, response_text[:start] if start is not None else response_text

    for prefer_exact_name in (True, False):
        for candidate, strategy_prefix in _iter_sources(prefer_exact_name):
            if _is_valid_function_candidate(candidate, func_name=func_name if prefer_exact_name else None):
                return candidate, _clean_strategy_text(strategy_prefix)

    return None, ""


def summarize_code_extraction_issue(response_text: str, func_name: Optional[str] = None) -> str:
    """给出代码提取失败的紧凑原因，便于区分模型输出问题与接口问题。"""
    text = (response_text or "").strip()
    if not text:
        return "响应文本为空"
    if _contains_placeholder_tokens(text):
        return "响应包含 `...` / TODO / 省略占位符"
    if func_name and not re.search(rf"\breal_t\s+{re.escape(func_name)}\s*\(", text):
        if re.search(r"\breal_t\s+s[0-9]+\s*\(", text):
            return f"响应里有函数，但不是目标函数 `{func_name}`"
        return f"响应中未找到目标函数 `{func_name}` 的完整签名"
    if not re.search(r"\breal_t\s+s[0-9]+\s*\(", text):
        return "响应中未找到完整 TSVC 函数签名"
    if re.search(r"[^\x00-\x7F]", _strip_c_comments(text)):
        return "响应中的代码区域混入了未注释的非 ASCII 文本"
    return "响应含有函数痕迹，但未提取到完整可编译函数体"


def extract_code_from_response(response_text: str, func_name: Optional[str] = None) -> str:
    """从 API 响应中提取完整函数代码。"""
    code, _ = _extract_function_candidate(response_text, func_name=func_name)
    return code or ""


def extract_code_and_strategy(response_text: str, func_name: Optional[str] = None) -> tuple:
    """从 API 响应中提取代码和优化策略。"""
    code, strategy = _extract_function_candidate(response_text, func_name=func_name)

    if not strategy and response_text:
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and '策略' in line.lower():
                strategy = re.sub(r'^.*策略[:：]?\s*', '', line).strip()
                break

    if not strategy:
        strategy = "代码重构以消除向量化障碍"

    return code or "", strategy


def _has_indexed_recurrence(code: str) -> bool:
    """Detect recurrence variables that participate in array indexing."""
    if not code:
        return False
    code = _strip_c_comments(code)
    for recurrence_var in _extract_recurrence_vars(code):
        if re.search(rf'\[[^\]]*\b{re.escape(recurrence_var)}\b[^\]]*\]', code):
            return True
    return False


def _has_control_flow(code: str) -> bool:
    """Detect branch-heavy control flow in the loop body."""
    if not code:
        return False
    code = _strip_c_comments(code)
    return bool(re.search(r'\bif\s*\(|\bgoto\b|\bswitch\s*\(', code))


def _has_indirect_indexing(code: str) -> bool:
    """Detect nested or indirect indexing patterns such as a[indx[i]]."""
    if not code:
        return False
    code = _strip_c_comments(code)
    return bool(
        re.search(r'\[[^\]]+\[[^\]]+\][^\]]*\]', code)
        or re.search(r'\b(?:indx|index|idx)\s*\[', code)
    )


def _iter_for_loop_bodies(code: str) -> List[Tuple[str, str]]:
    """Extract loop variables and braced loop bodies for lightweight semantic checks."""
    if not code:
        return []

    code = _strip_c_comments(code)
    header_pattern = re.compile(
        r'for\s*\(\s*(?:int\s+)?([A-Za-z_]\w*)\s*=\s*[^;]*;'
        r'\s*[^;]*;'
        r'\s*[^)]*\)'
    )
    loops: List[Tuple[str, str]] = []
    search_pos = 0

    while True:
        match = header_pattern.search(code, search_pos)
        if not match:
            break

        loop_var = match.group(1)
        brace_start = code.find("{", match.end())
        if brace_start == -1:
            search_pos = match.end()
            continue

        depth = 0
        body_end = None
        for idx in range(brace_start, len(code)):
            if code[idx] == "{":
                depth += 1
            elif code[idx] == "}":
                depth -= 1
                if depth == 0:
                    body_end = idx
                    break

        if body_end is None:
            search_pos = match.end()
            continue

        loops.append((loop_var, code[brace_start + 1:body_end]))
        # Continue searching after the current loop header so nested loops are still visible.
        search_pos = match.end()

    return loops


def _extract_fixed_index_self_read_hazards(code: str) -> List[Dict[str, str]]:
    """
    Detect loops that both write `arr[i]` and read `arr[k]` with a fixed index expr.

    This is the classic "looks hoistable but is not necessarily invariant" pattern.
    """
    if not code:
        return []

    hazards: List[Dict[str, str]] = []
    seen = set()

    for loop_var, body in _iter_for_loop_bodies(code):
        write_arrays = set(
            re.findall(
                rf'\b([A-Za-z_]\w*)\s*\[\s*{re.escape(loop_var)}\s*\]\s*=',
                body,
            )
        )
        if not write_arrays:
            continue

        for array_name in sorted(write_arrays):
            for index_expr in re.findall(rf'\b{re.escape(array_name)}\s*\[([^\]]+)\]', body):
                if re.search(rf'\b{re.escape(loop_var)}\b', index_expr):
                    continue
                normalized_expr = re.sub(r'\s+', '', index_expr)
                if not normalized_expr:
                    continue
                key = (array_name, loop_var, normalized_expr)
                if key in seen:
                    continue
                seen.add(key)
                hazards.append(
                    {
                        "array": array_name,
                        "loop_var": loop_var,
                        "index_expr": index_expr.strip(),
                    }
                )

    return hazards


def _build_relaxed_expr_pattern(expr: str) -> str:
    """Build a whitespace-tolerant regex for a short index expression."""
    normalized = re.sub(r'\s+', '', expr or "")
    if not normalized:
        return ""
    return r'\s*'.join(re.escape(ch) for ch in normalized)


def _infer_pattern_family(code: str, categories: List[str]) -> Optional[str]:
    """Infer the current transformation family from code facts and diagnostics."""
    runtime_stride_pattern = _classify_runtime_stride_pattern(code)
    if runtime_stride_pattern == "simple_same_index":
        return "runtime_stride_simple"
    if runtime_stride_pattern == "complex_indexed":
        return "runtime_stride_complex"
    if _has_indirect_indexing(code):
        return "indirect_addressing"
    if _has_indexed_recurrence(code):
        return "recurrence_boundary"
    if _has_control_flow(code) and any(cat in categories for cat in ("trip_count_bounds", "control_flow")):
        return "branch_hoisting"
    if "dependency_unsafe" in categories:
        return "loop_distribution_dependence_isolation"
    if "recurrence_reduction" in categories:
        return "reduction_or_recurrence"
    return None


def build_structured_feedback(func_name: str, eval_result: Dict, code: str) -> Dict:
    """Build a structured feedback object for prompt-time retrieval and guidance."""
    diagnostics = dict(eval_result.get("diagnostics", {}) or {})
    static_diag = get_function_diagnostics(func_name)
    static_problems = static_diag.get("problems", []) or []
    static_problem_reasons = [
        problem.get("reason")
        for problem in static_problems
        if isinstance(problem, dict) and problem.get("reason")
    ]
    static_categories = [
        category
        for reason in static_problem_reasons
        for category in categorize_reason(reason)
    ]
    dynamic_categories = diagnostics.get("missed_categories", []) or []
    primary_categories = dedupe_preserve_order(dynamic_categories + static_categories)
    if len(primary_categories) > 1 and "other" in primary_categories:
        primary_categories = [category for category in primary_categories if category != "other"]

    code_facts = {
        "has_runtime_stride": bool(_extract_runtime_stride_args(code)),
        "has_indexed_recurrence": _has_indexed_recurrence(code),
        "has_control_flow": _has_control_flow(code),
        "has_indirect_indexing": _has_indirect_indexing(code),
        "has_fixed_index_self_read_hazard": bool(_extract_fixed_index_self_read_hazards(code)),
        "has_outer_iterations_loop": bool(re.search(r'for\s*\(\s*int\s+nl\s*=.*iterations', _strip_c_comments(code or ""))),
    }

    anti_patterns: List[str] = []
    if code_facts["has_indexed_recurrence"]:
        anti_patterns.append("avoid_closed_form_recurrence_rewrite")
    if code_facts["has_control_flow"] and "trip_count_bounds" in primary_categories:
        anti_patterns.append("avoid_large_materialization")
    if code_facts["has_indirect_indexing"]:
        anti_patterns.append("avoid_generic_gather_scatter_rewrite")
    if code_facts["has_fixed_index_self_read_hazard"]:
        anti_patterns.append("avoid_fixed_index_self_read_hoist")

    pattern_family = _infer_pattern_family(code, primary_categories)
    dynamic_reasons = []
    for entry in diagnostics.get("missed_entries", []):
        reason = entry.get("reason") or entry.get("message")
        lowered = str(reason or "").strip().lower()
        if lowered in {
            "loop not vectorized [-rpass-missed=loop-vectorize]",
            "loop not vectorized",
            "loop vectorized",
        }:
            continue
        dynamic_reasons.append(reason)
        if len(dynamic_reasons) >= 3:
            break

    return {
        "func_name": func_name,
        "severity": static_diag.get("severity"),
        "pattern_family": pattern_family,
        "primary_categories": primary_categories,
        "compile_level": {
            "compilable": bool(eval_result.get("compilable", False)),
            "error_preview": (eval_result.get("error") or "").splitlines()[0][:160] if eval_result.get("error") else None,
        },
        "vectorization_level": {
            "vectorized_count": int(eval_result.get("vectorized_count", 0) or 0),
            "missed_count": int(eval_result.get("missed_count", 0) or 0),
            "missed_categories": primary_categories,
            "dynamic_missed_reasons": [reason for reason in dynamic_reasons if reason],
            "static_problem_reasons": static_problem_reasons[:3],
        },
        "performance_level": {
            "available": False,
            "anti_patterns": anti_patterns,
        },
        "code_facts": code_facts,
    }


def get_diagnostic_for_prompt(eval_result: Dict, func_name: str, code: str) -> Dict:
    """从评估结果中提取用于 prompt 的诊断信息，并补齐结构化反馈。"""
    diagnostics = dict(eval_result.get("diagnostics", {}) or {})
    diagnostics["structured_feedback"] = build_structured_feedback(func_name, eval_result, code)
    return diagnostics


TSVC_RESERVED_LOCAL_NAMES = {
    "a", "b", "c", "d", "e",
    "aa", "bb", "cc", "tt",
    "x", "xx", "yy", "indx",
}


def _strip_c_comments(code: str) -> str:
    """移除 C/C++ 注释，避免注释文本干扰启发式检测。"""
    if not code:
        return ""
    no_block = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    no_line = re.sub(r'//.*', '', no_block)
    return no_line


def _extract_recurrence_vars(code: str) -> List[str]:
    """提取形如 `k += ...;` 的递推变量名。"""
    if not code:
        return []
    code = _strip_c_comments(code)
    matches = re.findall(r'(?m)^\s*([A-Za-z_]\w*)\s*\+=\s*[^;]+;', code)
    return sorted(set(matches))


def _extract_arg_info_var_names(code: str) -> List[str]:
    """提取由 arg_info 赋值而来的局部参数名。"""
    if not code:
        return []
    code = _strip_c_comments(code)
    matches = re.findall(r'\bint\s+([A-Za-z_]\w*)\s*=\s*x->\w+\s*;', code)
    return sorted(set(matches))


def _extract_runtime_stride_args(code: str) -> List[str]:
    """提取被用作循环步长的运行时参数名。"""
    if not code:
        return []
    code = _strip_c_comments(code)
    runtime_args = []
    for arg_name in _extract_arg_info_var_names(code):
        if re.search(
            rf'for\s*\([^;]*;\s*[^;]*;\s*[^;]*\+=\s*{re.escape(arg_name)}\s*\)',
            code,
        ):
            runtime_args.append(arg_name)
    return sorted(set(runtime_args))


def _extract_runtime_stride_loops(code: str) -> List[Tuple[str, str]]:
    """提取运行时步长循环中的循环变量与步长变量。"""
    if not code:
        return []
    code = _strip_c_comments(code)
    pattern = re.compile(
        r'for\s*\(\s*(?:int\s+)?([A-Za-z_]\w*)\s*=\s*[^;]*;'
        r'\s*[^;]*;'
        r'\s*[^;]*\+=\s*([A-Za-z_]\w*)\s*\)'
    )
    loops: List[Tuple[str, str]] = []
    for loop_var, stride_var in pattern.findall(code):
        loops.append((loop_var, stride_var))
    return list(dict.fromkeys(loops))


def _expand_alias_names(code: str, base_name: str) -> List[str]:
    """提取由某个运行时参数派生出的局部别名，如 `int stride = n3;`。"""
    if not code:
        return [base_name]

    code = _strip_c_comments(code)
    aliases = {base_name}
    changed = True
    while changed:
        changed = False
        for lhs, rhs in re.findall(r'\bint\s+([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*;', code):
            if rhs in aliases and lhs not in aliases:
                aliases.add(lhs)
                changed = True
    return sorted(aliases)


def _classify_runtime_stride_pattern(code: str) -> Optional[str]:
    """
    将运行时步长循环粗分为两类：
    - simple_same_index: 主要是 a[i] / b[i] 这类同址访问
    - complex_indexed: 含递推变量、反向索引或更复杂地址表达式
    """
    if not code:
        return None

    code = _strip_c_comments(code)
    loops = _extract_runtime_stride_loops(code)
    if not loops:
        return None

    recurrence_vars = set(_extract_recurrence_vars(code))
    subscript_exprs = re.findall(r'\b[A-Za-z_]\w*\s*\[([^\[\]]+)\]', code)

    for loop_var, _ in loops:
        relevant_exprs = [
            expr for expr in subscript_exprs
            if re.search(rf'\b{re.escape(loop_var)}\b', expr)
            or any(re.search(rf'\b{re.escape(var)}\b', expr) for var in recurrence_vars)
        ]

        if not relevant_exprs:
            continue

        for expr in relevant_exprs:
            normalized = re.sub(r'\s+', '', expr)
            if any(re.search(rf'\b{re.escape(var)}\b', expr) for var in recurrence_vars):
                return "complex_indexed"
            if re.search(r'LEN_\w+\s*-', expr):
                return "complex_indexed"
            if normalized != loop_var:
                return "complex_indexed"

    return "simple_same_index"


def _extract_specialized_arg_values(code: str, arg_name: str) -> List[str]:
    """提取代码中对某个运行时参数做等值特化的常量集合。"""
    if not code:
        return []
    code = _strip_c_comments(code)
    values: List[str] = []
    for alias_name in _expand_alias_names(code, arg_name):
        values.extend(re.findall(rf'\b{re.escape(alias_name)}\s*==\s*(\d+)\b', code))
    return sorted(set(values))


def _has_hot_loop_runtime_stride_division(candidate_code: str, stride_aliases: List[str]) -> bool:
    """
    检测运行时步长循环体内是否出现 `/ stride` 或 `% stride` 这类索引恢复。
    这类写法在复杂地址模式下常常 correctness 虽然通过，但会在 stride>1 的热路径里引入高额标量开销。
    """
    if not candidate_code or not stride_aliases:
        return False

    code = _strip_c_comments(candidate_code)
    alias_pattern = "|".join(re.escape(alias) for alias in stride_aliases)
    loop_pattern = re.compile(
        rf'for\s*\([^;]*;[^;]*;[^;]*\+=\s*(?:{alias_pattern})\s*\)'
    )
    arithmetic_pattern = re.compile(
        rf'(?<!/)/(?!/)\s*(?:{alias_pattern})\b|%\s*(?:{alias_pattern})\b'
    )

    pending_runtime_loop = False
    runtime_loop_depth: Optional[int] = None
    brace_depth = 0

    for raw_line in code.splitlines():
        line = raw_line.strip()
        if not line:
            brace_depth += raw_line.count("{") - raw_line.count("}")
            continue

        if loop_pattern.search(line):
            if "{" in line:
                runtime_loop_depth = brace_depth + line.count("{")
            else:
                pending_runtime_loop = True

        if runtime_loop_depth is not None and arithmetic_pattern.search(line):
            return True

        brace_depth += raw_line.count("{") - raw_line.count("}")

        if pending_runtime_loop and "{" in line:
            runtime_loop_depth = brace_depth
            pending_runtime_loop = False

        if runtime_loop_depth is not None and brace_depth < runtime_loop_depth:
            runtime_loop_depth = None

    return False


def _lightweight_candidate_benchmark(
    original_code: str,
    candidate_code: str,
    func_name: str,
    clang_path: str,
) -> Optional[Dict]:
    """对 correctness 通过的候选做一次低成本真实性能比较，用于最终候选选择。"""
    if not original_code or not candidate_code:
        return None

    benchmark_result = run_performance_benchmark(
        original_code,
        candidate_code,
        func_name,
        clang_path,
        warmup_runs=FINAL_SELECTION_BENCHMARK_WARMUP_RUNS,
        timing_runs=FINAL_SELECTION_BENCHMARK_TIMING_RUNS,
        batches=FINAL_SELECTION_BENCHMARK_BATCHES,
    )
    if not benchmark_result.get("success"):
        return None
    return benchmark_result


def _get_performance_guard_config(strategy_config: Optional[Dict]) -> Dict:
    """读取并补齐策略的性能守护配置。"""
    guard_config = dict((strategy_config or {}).get("performance_guard") or {})
    return {
        "enabled": bool(guard_config.get("enabled", False)),
        "min_median_speedup": float(
            guard_config.get("min_median_speedup", DEFAULT_PERFORMANCE_GUARD_MIN_MEDIAN_SPEEDUP)
        ),
        "min_mean_speedup": float(
            guard_config.get("min_mean_speedup", DEFAULT_PERFORMANCE_GUARD_MIN_MEAN_SPEEDUP)
        ),
    }


def _evaluate_performance_guard(benchmark_result: Optional[Dict], strategy_config: Optional[Dict]) -> Dict:
    """根据轻量 benchmark 判断候选是否应被性能守护拒绝。"""
    guard_config = _get_performance_guard_config(strategy_config)
    decision = {
        "enabled": guard_config["enabled"],
        "rejected": False,
        "reason": None,
        "speedup": None,
        "speedup_median": None,
        "thresholds": {
            "min_mean_speedup": guard_config["min_mean_speedup"],
            "min_median_speedup": guard_config["min_median_speedup"],
        },
    }
    if not guard_config["enabled"] or not benchmark_result or not benchmark_result.get("success"):
        return decision

    mean_speedup = float(benchmark_result.get("speedup") or 0.0)
    median_speedup = float(benchmark_result.get("speedup_median") or 0.0)
    decision["speedup"] = mean_speedup
    decision["speedup_median"] = median_speedup

    if (
        mean_speedup < guard_config["min_mean_speedup"]
        and median_speedup < guard_config["min_median_speedup"]
    ):
        decision["rejected"] = True
        decision["reason"] = (
            "轻量 benchmark 显示明显负优化："
            f" median={median_speedup:.3f}x, mean={mean_speedup:.3f}x，"
            f" 低于守护阈值 median<{guard_config['min_median_speedup']:.2f}x"
            f" 且 mean<{guard_config['min_mean_speedup']:.2f}x"
        )

    return decision


def _candidate_selection_key(candidate: Dict) -> Tuple:
    """为 correctness 通过的候选生成最终排序键。"""
    benchmark_result = candidate.get("benchmark_result") or {}
    benchmark_ok = bool(benchmark_result.get("success"))
    if benchmark_ok:
        median_speedup = float(benchmark_result.get("speedup_median") or float("-inf"))
        mean_speedup = float(benchmark_result.get("speedup") or float("-inf"))
        stddev_speedup = float(benchmark_result.get("speedup_stddev") or float("inf"))
    else:
        median_speedup = float("-inf")
        mean_speedup = float("-inf")
        stddev_speedup = float("inf")

    analysis_result = candidate.get("analysis_result") or {}
    return (
        -int(benchmark_ok),
        -median_speedup,
        -mean_speedup,
        stddev_speedup,
        -(analysis_result.get("vectorized_count", 0) or 0),
        analysis_result.get("missed_count", 0) or 0,
        candidate.get("round_num", 0) or 0,
    )


def _record_performance_guard_decision(
    func_state: Dict,
    func_name: str,
    chosen_candidate: Dict,
    strategy_config: Optional[Dict],
) -> Dict:
    """将性能守护的拒绝决定写入函数状态，供实验汇总阶段读取。"""
    guard_decision = dict(chosen_candidate.get("performance_guard") or {})
    if not guard_decision.get("rejected"):
        func_state.pop("performance_guard", None)
        return {}

    stored = {
        "enabled": True,
        "rejected": True,
        "selected_round": chosen_candidate.get("round_num"),
        "reason": guard_decision.get("reason"),
        "speedup": guard_decision.get("speedup"),
        "speedup_median": guard_decision.get("speedup_median"),
        "thresholds": guard_decision.get("thresholds")
        or _get_performance_guard_config(strategy_config),
    }
    func_state["performance_guard"] = stored
    return stored


def _has_generic_runtime_fallback(code: str, arg_name: str) -> bool:
    """检测候选代码是否仍保留按运行时步长执行的通用路径。"""
    if not code:
        return False
    code = _strip_c_comments(code)
    return any(
        re.search(
            rf'for\s*\([^;]*;\s*[^;]*;\s*[^;]*\+=\s*{re.escape(alias_name)}\s*\)',
            code,
        )
        for alias_name in _expand_alias_names(code, arg_name)
    )


def collect_semantic_hints(code: str) -> List[str]:
    """从当前代码结构中提炼通用语义提示，供 prompt 使用。"""
    if not code:
        return []
    code = _strip_c_comments(code)

    hints: List[str] = []
    recurrence_vars = _extract_recurrence_vars(code)
    indexed_recurrences = [
        var for var in recurrence_vars
        if re.search(rf'\[[^\]]*\b{re.escape(var)}\b[^\]]*\]', code)
    ]
    if indexed_recurrences:
        joined = ", ".join(indexed_recurrences)
        hints.append(
            f"检测到递推变量 `{joined}` 参与索引或地址计算。不要直接把它改写为闭式 `x = f(i)`；优先使用索引预计算或两阶段循环，并保持首项与更新顺序一致。"
        )

    runtime_stride_args = _extract_runtime_stride_args(code)
    if runtime_stride_args:
        joined = ", ".join(runtime_stride_args)
        hints.append(
            f"检测到运行时参数 `{joined}` 控制的变步长循环。不要只针对默认 arg_info 做特化；若使用参数分支，必须保留覆盖所有参数的通用正确路径。"
        )
        hints.append(
            "对运行时步长循环做结构重构时，每个分支都必须覆盖与原循环完全相同的索引集合，不能重复更新、遗漏边界，也不能改变 dummy() 的循环层级。"
        )
        runtime_stride_pattern = _classify_runtime_stride_pattern(code)
        if runtime_stride_pattern == "simple_same_index":
            hints.append(
                "检测到简单同址 runtime-stride 模式：主要是 `a[i]`、`b[i]` 这类同址访问。若 pragma 无效，可尝试少量代表性步长（如 1/2/4）的等价专用分支，并保留通用 fallback。"
            )
        elif runtime_stride_pattern == "complex_indexed":
            hints.append(
                "检测到复杂 runtime-stride 模式：步长循环同时伴随递推变量、反向索引或非同址访问。优先只为 `stride == 1` 提供保守快路径；`stride > 1` 应保留通用原始路径或两阶段预计算，不要机械复制 `2/4` 分支。"
            )
    elif re.search(r'\+=\s*n\d+\b', code):
        hints.append(
            "检测到运行时参数控制的变步长循环。不要只针对默认 arg_info 做优化；任何参数特化都必须保留对所有参数的通用正确路径。"
        )

    if "dummy(" in code and re.search(r'for\s*\(\s*int\s+nl\s*=', code):
        hints.append(
            "检测到 `dummy()` 位于外层 `nl/iterations` 循环内。禁止改变 dummy() 的调用次数、顺序或循环层级，也不要折叠外层迭代。"
        )

    if re.search(r'for\s*\(\s*int\s+nl\s*=', code) and "iterations" in code:
        hints.append(
            "若需要重构跨多次 `iterations` 的逻辑，只能做等价的逐轮改写；不要用乘法放大、批量累加或一次性聚合替代多轮副作用。"
        )

    fixed_index_hazards = _extract_fixed_index_self_read_hazards(code)
    if fixed_index_hazards:
        sample = fixed_index_hazards[0]
        hints.append(
            "检测到循环同时写 "
            f"`{sample['array']}[{sample['loop_var']}]` 并读固定位置 "
            f"`{sample['array']}[{sample['index_expr']}]`。若循环变量可能命中该固定索引，"
            "这个值在同一轮中不是不变量；禁止把它整轮外提为标量。若要优化，必须按命中前/命中点/命中后拆分，或保留逐迭代读取语义。"
        )

    return hints


def summarize_correctness_feedback(correctness_report: Optional[Dict]) -> Optional[Dict]:
    """提炼 correctness 失败的核心原因，供下一轮 prompt 使用。"""
    if not correctness_report:
        return None

    overall = bool(correctness_report.get("overall", False))
    failure_reason = (
        correctness_report.get("layer2_semantic", {}).get("error")
        or correctness_report.get("layer3_runtime", {}).get("error")
        or correctness_report.get("layer1_compilation", {}).get("error")
    )

    advice = None
    if failure_reason:
        lowered = failure_reason.lower()
        if "state_" in lowered or "checksum" in lowered:
            advice = (
                "最近一轮改变了状态更新顺序或索引映射。请回退到可验证的保守重构，优先使用预计算索引/两阶段循环，不要把递推直接闭式化，也不要折叠外层 iterations。"
            )
        elif "test" in lowered or "ret_orig" in lowered or "ret_opt" in lowered:
            advice = (
                "最近一轮只在部分输入或边界条件下正确。不要只针对默认参数取值优化，必须保留所有 arg_info 的通用语义。"
            )
        else:
            advice = "优先修复 correctness，再追求向量化；保持循环层级、索引序列和副作用顺序不变。"

    return {
        "overall": overall,
        "failure_reason": failure_reason,
        "advice": advice,
    }


def detect_candidate_semantic_risks(original_code: str, candidate_code: str) -> List[str]:
    """检测候选代码中的高风险改写模式。仅给出通用警告，不做函数特判。"""
    if not candidate_code:
        return []
    original_code = _strip_c_comments(original_code or "")
    candidate_code = _strip_c_comments(candidate_code)

    risks: List[str] = []

    declared_names = set(re.findall(r'for\s*\(\s*int\s+([A-Za-z_]\w*)\b', candidate_code))
    declared_names.update(
        re.findall(
            r'(?m)^\s*(?:int|long|size_t|float|double|real_t)\s+([A-Za-z_]\w*)\s*(?:=|;|,|\[)',
            candidate_code,
        )
    )
    shadowed = sorted(name for name in declared_names if name in TSVC_RESERVED_LOCAL_NAMES)
    if shadowed:
        risks.append(
            f"检测到与 TSVC 全局数组同名的局部变量/循环变量: {', '.join(shadowed)}。这类遮蔽很容易造成编译错误或错误地把标量传给 dummy()/数组访问。"
        )

    original_fixed_index_hazards = _extract_fixed_index_self_read_hazards(original_code)
    for hazard in original_fixed_index_hazards:
        array_name = hazard["array"]
        index_expr = hazard["index_expr"]
        index_pattern = _build_relaxed_expr_pattern(index_expr)
        scalar_hoist_pattern = re.compile(
            rf'\b[A-Za-z_]\w*\s*=\s*{re.escape(array_name)}_*\s*\[\s*{index_pattern}\s*\]\s*;'
        )
        writes_same_array_pattern = re.compile(
            rf'\b{re.escape(array_name)}_*\s*\[\s*[A-Za-z_]\w*\s*\]\s*='
        )
        if scalar_hoist_pattern.search(candidate_code) and writes_same_array_pattern.search(candidate_code):
            risks.append(
                f"检测到把 `{array_name}[{index_expr}]` 先读入标量，再批量写 `{array_name}[i]` 的改写。"
                "原始循环里该固定位置可能在同一轮后续迭代中被更新，因此它不是整轮不变量；"
                "若要优化，必须按命中点拆分循环或保持逐迭代读取语义。"
            )
            break

    for recurrence_var in _extract_recurrence_vars(original_code):
        if not re.search(rf'\[[^\]]*\b{re.escape(recurrence_var)}\b[^\]]*\]', original_code):
            continue
        direct_assignment_used_in_index = False
        assignment_pattern = re.compile(
            rf'(?m)^\s*(?:int|long|size_t|float|double|real_t)?\s*'
            rf'({re.escape(recurrence_var)}[A-Za-z0-9_]*)\s*=\s*([^;]*);'
        )
        for assignment in assignment_pattern.finditer(candidate_code):
            assigned_name = assignment.group(1)
            if re.search(rf'\b{re.escape(assigned_name)}\s*\+=', candidate_code):
                continue
            if re.search(rf'\[[^\]]*\b{re.escape(assigned_name)}\b[^\]]*\]', candidate_code):
                direct_assignment_used_in_index = True
                break

        if direct_assignment_used_in_index:
            risks.append(
                f"检测到递推变量 `{recurrence_var}` 被改写为直接赋值。若该变量参与索引，这通常会破坏首项或更新顺序；请优先使用索引预计算而不是闭式替换。"
            )
            break

    if re.search(r'for\s*\(\s*int\s+nl\s*=', original_code):
        if re.search(r'\biterations\s*-\s*1\b', candidate_code) or re.search(
            r'for\s*\(\s*int\s+\w+\s*=\s*1\s*;\s*\w+\s*<\s*iterations',
            candidate_code,
        ):
            risks.append(
                "检测到可能折叠外层 iterations/nl 循环的写法。请确认没有改变每轮数组更新次数，也没有改变 dummy() 的调用次数与层级。"
            )

    arg_names = re.findall(r'int\s+([A-Za-z_]\w*)\s*=\s*x->\w+\s*;', original_code or "")
    runtime_stride_args = set(_extract_runtime_stride_args(original_code))
    runtime_stride_pattern = _classify_runtime_stride_pattern(original_code)
    for arg_name in sorted(set(arg_names)):
        alias_names = _expand_alias_names(candidate_code, arg_name)
        has_specialized_condition = any(
            re.search(rf'\bif\s*\(\s*{re.escape(alias_name)}\s*(==|!=|<=|>=|<|>)\s*\d+\s*\)', candidate_code)
            for alias_name in alias_names
        )
        if (
            arg_name in runtime_stride_args
            and runtime_stride_pattern == "complex_indexed"
            and _has_hot_loop_runtime_stride_division(candidate_code, alias_names)
        ):
            risks.append(
                f"检测到复杂 runtime-stride 热循环里使用 `/ {arg_name}` 或 `% {arg_name}` 恢复索引/迭代号。请改用独立的 `idx/t` 计数器，或在循环外预计算映射，避免把整数除法/取模放进 stride>1 的热路径。"
            )
            break
        if has_specialized_condition:
            specialized_values = _extract_specialized_arg_values(candidate_code, arg_name)
            has_fallback = _has_generic_runtime_fallback(candidate_code, arg_name)
            if arg_name in runtime_stride_args:
                if (
                    runtime_stride_pattern == "simple_same_index"
                    and has_fallback
                    and len(specialized_values) >= 2
                ):
                    continue
                if (
                    runtime_stride_pattern == "complex_indexed"
                    and has_fallback
                    and set(specialized_values) == {"1"}
                ):
                    continue
                if runtime_stride_pattern == "complex_indexed":
                    risks.append(
                        f"检测到复杂 runtime-stride 模式下对运行时参数 `{arg_name}` 的多分支特化。对这类模式，优先只保留 `stride == 1` 快路径，其他参数走通用原始路径或两阶段预计算，不要机械复制 `2/4` 分支。"
                    )
                    break
            risks.append(
                f"检测到基于运行时参数 `{arg_name}` 的特化分支。请确认这不是只针对默认 benchmark 参数的投机优化，并且保留了所有参数的通用正确路径。"
            )
            break

    return risks


def get_function_output_dir(func_name: str) -> str:
    """获取函数的输出目录路径"""
    return f"{config.OPTIMIZED_FILE_PREFIX}{func_name}"


def ensure_function_dir(func_name: str) -> str:
    """确保函数的输出目录存在，返回目录路径"""
    output_dir = get_function_output_dir(func_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def save_code_to_file(file_path: str, code: str, header_comment: str = ""):
    """保存代码到文件"""
    with open(file_path, 'w') as f:
        if header_comment:
            f.write(f"{header_comment}\n")
        f.write(code)


PROMPT_SNAPSHOT_SCHEMA_VERSION = 1


def _prompt_snapshot_root() -> Optional[Path]:
    """Return the active prompt snapshot directory, if the experiment runner configured one."""
    snapshot_dir = os.environ.get("PROMPT_SNAPSHOT_DIR")
    if not snapshot_dir:
        return None
    return Path(snapshot_dir)


def _safe_snapshot_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "unknown")).strip("_")
    return safe or "unknown"


def _build_case_card_snapshot_for_prompt(
    diagnostics: Optional[Dict],
    prompt_options: Dict,
    round_num: int,
    previous_rounds: Optional[List[Dict]],
    prompt_kind: str,
) -> Dict:
    structured_feedback = (diagnostics or {}).get("structured_feedback")
    base = {
        "included": False,
        "case_card_set_version": EXPERIMENT_CASE_CARD_SET_VERSION,
        "case_card_format_version": CASE_CARD_FORMAT_VERSION,
        "structured_feedback_available": bool(structured_feedback),
        "selected_count": 0,
        "selected_cards": [],
        "formatted_text": "",
    }

    if prompt_kind != "optimization":
        base["reason"] = "retry_prompt_has_no_case_cards"
        return base
    if not prompt_options.get("include_knowledge"):
        base["reason"] = "include_knowledge_disabled"
        return base
    if not prompt_options.get("include_structured_feedback"):
        base["reason"] = "include_structured_feedback_disabled"
        return base
    if not (round_num == 1 or (round_num > 1 and not previous_rounds)):
        base["reason"] = "case_cards_only_added_without_round_history"
        return base
    if not structured_feedback:
        base["reason"] = "no_structured_feedback"
        return base

    snapshot = build_case_card_audit_snapshot(structured_feedback)
    snapshot["included"] = bool(snapshot.get("selected_cards"))
    if not snapshot["included"]:
        snapshot["reason"] = "no_matching_case_cards"
    return snapshot


def write_prompt_snapshot(
    func_name: str,
    strategy_config: Dict,
    round_num: int,
    max_rounds: int,
    prompt_kind: str,
    system_prompt: str,
    user_prompt: str,
    diagnostics: Optional[Dict] = None,
    previous_rounds: Optional[List[Dict]] = None,
    prompt_options: Optional[Dict] = None,
) -> Optional[Dict]:
    """Persist the exact prompt text and retrieval metadata used for one LLM request."""
    snapshot_root = _prompt_snapshot_root()
    if snapshot_root is None:
        return None

    options = normalize_prompt_options(prompt_options)
    timestamp = datetime.now().isoformat()
    function_dir = snapshot_root / _safe_snapshot_name(func_name)
    function_dir.mkdir(parents=True, exist_ok=True)

    safe_kind = _safe_snapshot_name(prompt_kind)
    base_name = f"round{round_num:02d}_{safe_kind}"
    json_path = function_dir / f"{base_name}.json"
    markdown_path = function_dir / f"{base_name}.md"
    case_card_path = function_dir / f"{base_name}_case_cards.json"
    template_versions = get_prompt_template_versions()
    if prompt_kind == "optimization":
        system_template_name = resolve_system_prompt_template_name(round_num, options)
        user_template_name = "optimization_user"
    else:
        system_template_name = "retry_prompt"
        user_template_name = "retry_prompt"

    case_card_snapshot = _build_case_card_snapshot_for_prompt(
        diagnostics=diagnostics,
        prompt_options=options,
        round_num=round_num,
        previous_rounds=previous_rounds,
        prompt_kind=prompt_kind,
    )

    payload = {
        "snapshot_schema_version": PROMPT_SNAPSHOT_SCHEMA_VERSION,
        "timestamp": timestamp,
        "function": func_name,
        "strategy": strategy_config.get("name"),
        "publication_name": strategy_config.get("publication_name"),
        "paper_role": strategy_config.get("paper_role"),
        "prompt_version": strategy_config.get("prompt_version"),
        "round": round_num,
        "max_rounds": max_rounds,
        "prompt_kind": prompt_kind,
        "prompt_options": options,
        "template_versions": template_versions,
        "system_prompt_template": {
            "name": system_template_name,
            "version": template_versions.get(system_template_name),
        },
        "user_prompt_template": {
            "name": user_template_name,
            "version": template_versions.get(user_template_name),
        },
        "diagnostics": diagnostics or {},
        "case_cards": case_card_snapshot,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(case_card_path, "w", encoding="utf-8") as f:
        json.dump(case_card_snapshot, f, indent=2, ensure_ascii=False)
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(f"# Prompt Snapshot: {func_name} round {round_num}\n\n")
        f.write(f"- strategy: {strategy_config.get('name')}\n")
        f.write(f"- publication_name: {strategy_config.get('publication_name')}\n")
        f.write(f"- prompt_version: {strategy_config.get('prompt_version')}\n")
        f.write(f"- prompt_kind: {prompt_kind}\n")
        f.write(f"- system_template: {system_template_name}\n")
        f.write(f"- case_cards_included: {case_card_snapshot.get('included')}\n\n")
        f.write("## System Prompt\n\n")
        f.write("```text\n")
        f.write(system_prompt)
        f.write("\n```\n\n")
        f.write("## User Prompt\n\n")
        f.write("```text\n")
        f.write(user_prompt)
        f.write("\n```\n")

    index_path = snapshot_root / "index.json"
    index_payload = {"snapshot_schema_version": PROMPT_SNAPSHOT_SCHEMA_VERSION, "snapshots": []}
    if index_path.exists():
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict) and isinstance(existing.get("snapshots"), list):
                index_payload = existing
        except Exception:
            index_payload = {"snapshot_schema_version": PROMPT_SNAPSHOT_SCHEMA_VERSION, "snapshots": []}

    index_entry = {
        "timestamp": timestamp,
        "function": func_name,
        "strategy": strategy_config.get("name"),
        "publication_name": strategy_config.get("publication_name"),
        "prompt_version": strategy_config.get("prompt_version"),
        "round": round_num,
        "prompt_kind": prompt_kind,
        "json_file": str(json_path),
        "markdown_file": str(markdown_path),
        "case_card_file": str(case_card_path),
        "case_cards_included": case_card_snapshot.get("included"),
        "selected_case_card_ids": [
            card.get("id")
            for card in case_card_snapshot.get("selected_cards", [])
            if card.get("id")
        ],
    }
    index_payload.setdefault("snapshots", []).append(index_entry)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_payload, f, indent=2, ensure_ascii=False)

    return {
        "json_file": str(json_path),
        "markdown_file": str(markdown_path),
        "case_card_file": str(case_card_path),
        "case_cards_included": case_card_snapshot.get("included"),
        "selected_case_card_ids": index_entry["selected_case_card_ids"],
    }


def backfill_round_correctness_reports(func_name: str, state: Dict, clang_path: str) -> bool:
    """为旧状态补齐逐轮 correctness，避免继续优化时信任过期的函数级状态。"""
    func_state = get_function_state(func_name, state)
    original_code = func_state.get("original_code")
    if not original_code:
        return False

    changed = False
    for round_record in func_state.get("rounds", []):
        if round_record.get("correctness_report") is not None:
            continue
        if not round_record.get("compilable"):
            continue
        candidate_code = round_record.get("code")
        if not candidate_code:
            continue

        round_num = round_record.get("round", "?")
        info(f"{func_name} round {round_num}: 补齐历史 correctness 验证")
        round_record["correctness_report"] = full_correctness_verification(
            original_code,
            candidate_code,
            func_name,
            clang_path,
        )
        changed = True

    if changed:
        reconcile_function_status_from_round_reports(func_name, state)
        save_state(state)
    return changed


def reconcile_function_status_from_round_reports(func_name: str, state: Dict) -> bool:
    """根据已保存的逐轮 correctness 报告修正 best/status。"""
    func_state = get_function_state(func_name, state)
    rounds = func_state.get("rounds", [])
    passing_rounds = []

    for round_record in rounds:
        correctness_report = round_record.get("correctness_report")
        if not correctness_report or not correctness_report.get("overall", False):
            continue
        if not round_record.get("compilable"):
            continue
        passing_rounds.append(round_record)

    previous_best = func_state.get("best")
    previous_status = func_state.get("status")
    previous_correctness = func_state.get("correctness_overall")

    if passing_rounds:
        passing_rounds.sort(
            key=lambda record: (
                -(record.get("vectorized_count", 0) or 0),
                record.get("missed_count", 0) or 0,
                record.get("round", 0) or 0,
            )
        )
        selected = passing_rounds[0]
        final_result = {
            "compilable": selected.get("compilable", False),
            "vectorized": selected.get("vectorized", False),
            "vectorized_count": selected.get("vectorized_count", 0),
            "missed_count": selected.get("missed_count", 0),
            "error": selected.get("error"),
            "diagnostics": selected.get("diagnostics") or {},
        }
        func_state["best"] = selected.get("round")
        func_state["correctness_overall"] = True
        func_state["status"] = determine_final_status(
            final_result,
            selected.get("correctness_report"),
            terminated=True,
        )
    elif rounds:
        func_state["correctness_overall"] = False
        func_state["status"] = "failed"

    return (
        previous_best != func_state.get("best")
        or previous_status != func_state.get("status")
        or previous_correctness != func_state.get("correctness_overall")
    )


def finalize_function_optimization(
    func_name: str,
    output_dir: str,
    state: Dict,
    clang_path: str,
    strategy_config: Optional[Dict] = None,
) -> Dict:
    """统一收尾单轮/多轮优化结果，执行正确性验证并回写最终状态。"""
    func_state = get_function_state(func_name, state)
    func_state.pop("performance_guard", None)
    best_code = get_best_code(func_name, state)
    final_result = None
    correctness_report = None
    selected_round = func_state.get("best")
    performance_guard_blocked = False
    performance_guard_config = _get_performance_guard_config(strategy_config)

    # 优先使用状态中的原始代码，避免从带注释文件中整段读取
    original_code = func_state.get("original_code")
    if not original_code:
        original_code_file = os.path.join(
            output_dir,
            f"{config.OPTIMIZED_FILE_PREFIX}{func_name}_origin.c"
        )
        if os.path.exists(original_code_file):
            original_code = extract_function_code(original_code_file, func_name)

    ranked_rounds = get_ranked_round_numbers(func_name, state)
    fallback_round = None
    passing_candidates = []

    if ranked_rounds:
        info("进行正确性验证...")
    for round_num in ranked_rounds:
        round_record = func_state["rounds"][round_num - 1]
        candidate_code = round_record.get("code")
        if not candidate_code:
            continue

        candidate_result = {
            "compilable": round_record.get("compilable", False),
            "vectorized": round_record.get("vectorized", False),
            "vectorized_count": round_record.get("vectorized_count", 0),
            "missed_count": round_record.get("missed_count", 0),
            "error": round_record.get("error"),
            "diagnostics": round_record.get("diagnostics") or {},
        }
        if not candidate_result.get("diagnostics"):
            candidate_result = analyze_single_function(func_name, candidate_code, clang_path)

        candidate_report = round_record.get("correctness_report")
        if candidate_report is None and original_code:
            candidate_report = full_correctness_verification(
                original_code, candidate_code, func_name, clang_path
            )
            round_record["correctness_report"] = candidate_report

        if fallback_round is None:
            fallback_round = (round_num, candidate_code, candidate_result, candidate_report)

        if candidate_report is None or not candidate_report.get("overall", False):
            if candidate_report:
                warning_icon(f"{func_name} round {round_num} correctness 未通过，尝试下一候选")
            continue

        passing_candidates.append({
            "round_num": round_num,
            "code": candidate_code,
            "analysis_result": candidate_result,
            "correctness_report": candidate_report,
            "benchmark_result": None,
            "performance_guard": {
                "enabled": performance_guard_config["enabled"],
                "rejected": False,
                "reason": None,
            },
        })

    if passing_candidates:
        should_run_preview_benchmark = len(passing_candidates) > 1 or performance_guard_config["enabled"]
        if should_run_preview_benchmark:
            for candidate in passing_candidates:
                preview_benchmark = _lightweight_candidate_benchmark(
                    original_code,
                    candidate["code"],
                    func_name,
                    clang_path,
                )
                candidate["benchmark_result"] = preview_benchmark
                round_num = candidate["round_num"]
                candidate["performance_guard"] = _evaluate_performance_guard(
                    preview_benchmark,
                    strategy_config,
                )
                if preview_benchmark:
                    info(
                        f"{func_name} round {round_num} 轻量 benchmark:"
                        f" median={preview_benchmark.get('speedup_median', 0.0):.3f}x"
                        f" mean={preview_benchmark.get('speedup', 0.0):.3f}x"
                    )
                    if candidate["performance_guard"].get("rejected"):
                        warning_icon(
                            f"{func_name} round {round_num} 被 performance guard 拒绝: "
                            f"{candidate['performance_guard']['reason']}"
                        )
                else:
                    info(f"{func_name} round {round_num} 轻量 benchmark 失败，回退到静态诊断排序")
        selection_candidates = passing_candidates
        if performance_guard_config["enabled"]:
            selection_candidates = [
                candidate for candidate in passing_candidates
                if not candidate.get("performance_guard", {}).get("rejected")
            ]

        if selection_candidates:
            selection_candidates.sort(key=_candidate_selection_key)
            chosen = selection_candidates[0]
        else:
            passing_candidates.sort(key=_candidate_selection_key)
            chosen = passing_candidates[0]
            performance_guard_info = _record_performance_guard_decision(
                func_state,
                func_name,
                chosen,
                strategy_config,
            )
            if performance_guard_info:
                performance_guard_blocked = True
                warning_icon(
                    f"{func_name} 所有 correctness 通过候选都被 performance guard 拒绝，"
                    f" round {chosen['round_num']} 不接受为最终结果"
                )

        selected_round = chosen["round_num"]
        best_code = chosen["code"]
        final_result = chosen["analysis_result"]
        correctness_report = chosen["correctness_report"]
        if func_state.get("best") != selected_round:
            info(f"{func_name} 最终选择 round {selected_round} 作为结果（基于 correctness + 轻量 benchmark）")
            set_best_round(func_name, selected_round, state)

    if final_result is None and fallback_round is not None:
        selected_round, best_code, final_result, correctness_report = fallback_round

    if correctness_report:
        report_text = format_verification_report(correctness_report)
        for line in report_text.split('\n'):
            if line.strip():
                info(line)

        if not correctness_report.get('overall', False):
            warning_icon("正确性验证失败！")

    v_count = final_result.get("vectorized_count", 0) if final_result else 0
    m_count = final_result.get("missed_count", 0) if final_result else 0

    if performance_guard_blocked:
        final_status = "failed"
    else:
        final_status = determine_final_status(final_result, correctness_report, terminated=True)
    correctness_overall = correctness_report.get("overall") if correctness_report else None
    set_function_final_status(func_name, final_status, correctness_overall=correctness_overall, state=state)

    is_success = final_status == "success"
    is_partial_success = final_status == "partial_success"

    if performance_guard_blocked:
        failure(
            f"{func_name} 优化未接受: "
            f"{func_state.get('performance_guard', {}).get('reason', '性能守护拒绝了最终候选')}"
        )
    elif final_status == "success":
        success(f"{func_name} 优化完成: 完全向量化且通过正确性验证")
    elif final_status == "partial_success":
        warning(f"{func_name} 优化完成: 部分向量化且通过正确性验证 ({v_count}/{v_count + m_count})")
    elif final_result and final_result.get("vectorized") and correctness_report and not correctness_report.get("overall", False):
        failure(f"{func_name} 优化失败: 向量化成功但正确性验证失败")
    elif v_count > 0:
        failure(f"{func_name} 优化失败: 部分向量化但未通过最终判定 ({v_count}/{v_count + m_count})")
    else:
        failure(f"{func_name} 优化失败: 未向量化")

    return {
        "status": final_status,
        "success": is_success,
        "partial": is_partial_success,
        "vectorized_count": v_count,
        "missed_count": m_count,
        "rounds": len(get_function_state(func_name, state).get("rounds", [])),
        "best_round": selected_round,
        "final_code": best_code,
        "final_result": final_result,
        "correctness_report": correctness_report
    }


def optimize_single_function(func_name: str, api_key: str, model_name: str,
                             clang_path: str, max_rounds: int = 3,
                             verbose: bool = False, single_round: bool = False,
                             strategy_config: Optional[Dict] = None) -> Dict:
    """
    对单个函数进行优化

    Args:
        single_round: 如果为 True，只进行一轮优化（不迭代）

    Returns: {
        "success": bool,
        "rounds": int,
        "final_code": str or None,
        "final_result": dict or None
    }
    """
    if strategy_config is None:
        strategy_config = get_experiment_strategy("ours_full")

    section(f"优化函数: {func_name}")
    info(f"实验策略: {strategy_config['name']}")
    if single_round:
        info(f"模式: 单轮优化")
    else:
        info(f"最大轮数: {max_rounds}")

    # 创建函数的输出目录
    output_dir = ensure_function_dir(func_name)
    info(f"输出目录: {output_dir}")

    state = load_state()

    # 获取或初始化函数状态
    func_state = get_function_state(func_name, state)

    # 如果已经标记为成功，跳过优化
    if func_state.get("status") == "success":
        info(f"函数 {func_name} 已优化成功，跳过")
        best_code = get_best_code(func_name, state)
        final_result = None
        if best_code:
            final_result = analyze_single_function(func_name, best_code, clang_path)
        return {
            "status": "success",
            "success": True,
            "partial": False,
            "vectorized_count": final_result.get("vectorized_count", 0) if final_result else 0,
            "missed_count": final_result.get("missed_count", 0) if final_result else 0,
            "rounds": len(func_state.get("rounds", [])),
            "final_code": best_code,
            "final_result": final_result,
            "correctness_report": None
        }

    # 首先确保保存原始代码（如果还没有保存过）
    origin_file = os.path.join(output_dir, f"{config.OPTIMIZED_FILE_PREFIX}{func_name}_origin.c")
    if not os.path.exists(origin_file):
        # 从源文件加载原始代码并保存
        original_file = get_source_file()
        if os.path.exists(original_file):
            original_code = extract_function_code(original_file, func_name)
            if original_code:
                # 构建包含诊断信息的注释头
                diag_comment = format_diagnostics_for_comment(func_name)
                header = f"// Original {func_name} from TSVC\n//\n{diag_comment}"
                save_code_to_file(origin_file, original_code, header)
                set_original_code(func_name, original_code, state)
                info(f"原始代码已保存到: {origin_file}")
    elif not func_state.get("original_code"):
        original_code = extract_function_code(origin_file, func_name)
        if original_code:
            set_original_code(func_name, original_code, state)
            info(f"已从现有原始文件恢复 original_code: {origin_file}")

    # 检查是否已有现有的优化文件
    existing_optimized_file = os.path.join(output_dir, f"{config.OPTIMIZED_FILE_PREFIX}{func_name}.c")
    if os.path.exists(existing_optimized_file) and not func_state.get("rounds"):
        # 从现有的优化文件开始
        info(f"发现现有优化文件: {existing_optimized_file}")
        code = extract_function_code(existing_optimized_file, func_name)
        if code:
            info(f"将从此文件开始多轮优化")
            # 评估现有代码作为第0轮（基准）
            eval_result = analyze_single_function(func_name, code, clang_path)
            add_round(func_name, code, eval_result, eval_result.get("diagnostics"), state, "")
        else:
            warning_icon(f"无法从 {existing_optimized_file} 提取代码，将从源文件开始")
            code = None

    backfill_round_correctness_reports(func_name, state, clang_path)

    # 获取下一轮应该使用的代码
    code, _, is_first = get_code_for_next_round(func_name, state)

    if not code:
        # 从源文件加载原始代码
        original_file = get_source_file()
        if os.path.exists(original_file):
            code = extract_function_code(original_file, func_name)
            if code:
                set_original_code(func_name, code, state)
            else:
                failure(f"无法从 {original_file} 提取函数 {func_name}")
                return {"success": False, "rounds": 0, "final_code": None, "final_result": None}
        else:
            failure(f"找不到原始代码文件")
            return {"success": False, "rounds": 0, "final_code": None, "final_result": None}

    # 第一轮分析
    if is_first or single_round:
        info("分析原始代码...")
        eval_result = analyze_single_function(func_name, code, clang_path)
        set_original_code(func_name, code, state)

        if eval_result.get("vectorized"):
            success("原始代码已完全向量化，跳过优化。")
            output_file = os.path.join(output_dir, f"{config.OPTIMIZED_FILE_PREFIX}{func_name}.c")
            save_code_to_file(
                output_file,
                code,
                f"// Skipped optimization for {func_name}: original code is already fully vectorized"
            )
            set_function_final_status(func_name, "skipped", correctness_overall=True, state=state)
            return {
                "status": "skipped",
                "success": False,
                "partial": False,
                "skipped": True,
                "rounds": 0,
                "best_round": None,
                "final_code": code,
                "final_result": eval_result,
                "correctness_report": {
                    "func_name": func_name,
                    "overall": True,
                },
            }

        # 第一轮优化
        diagnostics = get_diagnostic_for_prompt(eval_result, func_name, code)
        system_prompt, user_prompt = build_optimization_prompt(
            code=code,
            func_name=func_name,
            diagnostics=diagnostics,
            round_num=1,
            max_rounds=max_rounds,
            prompt_options=strategy_config.get("prompt_options"),
            semantic_hints=collect_semantic_hints(code),
        )

    # 单轮优化模式
    if single_round:
        subsection("单轮优化")
        prompt_snapshot = write_prompt_snapshot(
            func_name=func_name,
            strategy_config=strategy_config,
            round_num=1,
            max_rounds=max_rounds,
            prompt_kind="optimization",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            diagnostics=diagnostics,
            previous_rounds=None,
            prompt_options=strategy_config.get("prompt_options"),
        )

        # 调用 LLM 优化
        info("请求 LLM 优化...")
        response = call_deepseek_anthropic_api(api_key, model_name, system_prompt, user_prompt)

        if not response:
            failure("LLM API 调用失败")
            return {"success": False, "rounds": 0, "final_code": None, "final_result": None}

        response_text = extract_text_from_api_response(response)
        if not response_text:
            warning_icon("API 响应中未找到可解析文本内容")
            warning(f"响应摘要: {summarize_api_response_schema(response)}")
            return {"success": False, "rounds": 0, "final_code": None, "final_result": None}

        new_code, strategy = extract_code_and_strategy(response_text, func_name=func_name)

        if not new_code:
            warning_icon("无法从响应中提取代码")
            warning(f"提取失败原因: {summarize_code_extraction_issue(response_text, func_name=func_name)}")
            # DEBUG: save raw response for extraction failure diagnosis
            _debug_path = os.path.join(output_dir, f"debug_response_{func_name}.txt")
            with open(_debug_path, "w", encoding="utf-8") as _df:
                _df.write(response_text)
            info(f"原始响应已保存至: {_debug_path}")
            return {"success": False, "rounds": 0, "final_code": None, "final_result": None}

        info(f"优化策略: {strategy[:60]}...")

        # 评估最终代码
        final_result = analyze_single_function(func_name, new_code, clang_path)

        # 保存优化后的代码到文件（最终结果）
        output_file = os.path.join(output_dir, f"{config.OPTIMIZED_FILE_PREFIX}{func_name}.c")
        header = format_round_header(func_name, 1, strategy, final_result)
        save_code_to_file(output_file, new_code, header)

        info(f"代码已保存到: {output_file}")
        add_round(
            func_name,
            new_code,
            final_result,
            final_result.get("diagnostics"),
            state,
            strategy,
            prompt_snapshot=prompt_snapshot,
        )

        return finalize_function_optimization(
            func_name,
            output_dir,
            state,
            clang_path,
            strategy_config=strategy_config,
        )

    # 多轮优化循环 - 每轮生成新的优化版本
    for _ in range(max_rounds):
        # 获取当前已保存的轮次数（用于判断是否是真正的第一轮）
        func_state = get_function_state(func_name, state)
        existing_rounds = len(func_state.get("rounds", []))
        current_round = existing_rounds + 1

        if existing_rounds >= max_rounds:
            warning(f"停止优化: 已达到最大轮数 {max_rounds}")
            break

        subsection(f"第 {current_round}/{max_rounds} 轮优化")
        prompt_kind = "optimization"
        prompt_diagnostics = None
        prompt_previous_rounds = None

        # 如果已有优化历史，评估当前代码（这是上一轮优化的结果）
        if existing_rounds > 0:
            eval_result = analyze_single_function(func_name, code, clang_path)

            if verbose:
                compile_status = '成功' if eval_result['compilable'] else '失败'
                v_count = eval_result.get('vectorized_count', 0)
                m_count = eval_result.get('missed_count', 0)
                debug(f"编译: {compile_status}")
                debug(f"向量化: {v_count}/{m_count}")

            # 检查是否已经完全成功
            if eval_result.get("vectorized"):
                success(f"检测到函数 {func_name} 在第 {existing_rounds} 轮已完全向量化，进入最终正确性验证")
                break

            # 准备下一轮优化的 prompt
            is_retry = not eval_result.get("compilable")
            previous_error = eval_result.get("error") if is_retry else None

            if is_retry:
                # 编译失败，使用重试 prompt
                rounds = func_state.get("rounds", [])
                previous_strategy = rounds[-1].get("strategy", "") if rounds else ""
                system_prompt, user_prompt = build_retry_prompt(code, previous_error, previous_strategy)
                prompt_kind = "retry"
                prompt_diagnostics = {
                    "compile_error": previous_error,
                    "previous_strategy": previous_strategy,
                }
            else:
                # 编译成功但未完全向量化，使用增强版多轮 prompt
                previous_rounds = func_state.get("rounds", [])
                diagnostics = get_diagnostic_for_prompt(eval_result, func_name, code)
                prompt_diagnostics = diagnostics
                prompt_previous_rounds = previous_rounds
                latest_round = previous_rounds[-1] if previous_rounds else None
                correctness_feedback = summarize_correctness_feedback(
                    latest_round.get("correctness_report") if latest_round else None
                )
                latest_semantic_risks = None
                if latest_round:
                    latest_report = latest_round.get("correctness_report") or {}
                    if not latest_report.get("overall", False):
                        latest_semantic_risks = latest_round.get("semantic_risks")
                system_prompt, user_prompt = build_optimization_prompt(
                    code=code,
                    func_name=func_name,
                    diagnostics=diagnostics,
                    round_num=current_round,
                    max_rounds=max_rounds,
                    previous_rounds=previous_rounds,
                    prompt_options=strategy_config.get("prompt_options"),
                    semantic_hints=collect_semantic_hints(func_state.get("original_code") or code),
                    correctness_feedback=correctness_feedback,
                    semantic_risks=latest_semantic_risks,
                )
        else:
            # 真正的第一轮（没有历史记录）
            # 使用之前已经构建好的 prompt（从原始代码开始）
            if current_round == 1 and 'system_prompt' in locals():
                # 使用之前构建的 prompt（基于原始代码的诊断）
                prompt_diagnostics = diagnostics
                pass  # system_prompt 和 user_prompt 已存在
            else:
                # 重新构建 prompt
                diagnostics = get_diagnostic_for_prompt(eval_result, func_name, code)
                prompt_diagnostics = diagnostics
                system_prompt, user_prompt = build_optimization_prompt(
                    code=code,
                    func_name=func_name,
                    diagnostics=diagnostics,
                    round_num=current_round,
                    max_rounds=max_rounds,
                    prompt_options=strategy_config.get("prompt_options"),
                    semantic_hints=collect_semantic_hints(code),
                )

        prompt_snapshot = write_prompt_snapshot(
            func_name=func_name,
            strategy_config=strategy_config,
            round_num=current_round,
            max_rounds=max_rounds,
            prompt_kind=prompt_kind,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            diagnostics=prompt_diagnostics,
            previous_rounds=prompt_previous_rounds,
            prompt_options=strategy_config.get("prompt_options"),
        )

        # 调用 LLM 优化
        info("请求 LLM 优化...")
        response = call_deepseek_anthropic_api(api_key, model_name, system_prompt, user_prompt)

        if not response:
            failure("LLM API 调用失败")
            break

        response_text = extract_text_from_api_response(response)
        if not response_text:
            warning_icon("API 响应中未找到可解析文本内容")
            warning(f"响应摘要: {summarize_api_response_schema(response)}")
            break

        new_code, strategy = extract_code_and_strategy(response_text, func_name=func_name)

        if not new_code:
            warning_icon("无法从响应中提取代码")
            warning(f"提取失败原因: {summarize_code_extraction_issue(response_text, func_name=func_name)}")
            # DEBUG: save raw response for extraction failure diagnosis
            _debug_path = os.path.join(output_dir, f"debug_response_{func_name}_round{current_round}.txt")
            with open(_debug_path, "w", encoding="utf-8") as _df:
                _df.write(response_text)
            info(f"原始响应已保存至: {_debug_path}")
            break

        info(f"优化策略: {strategy[:60]}...")

        # 评估本轮代码
        round_eval_result = analyze_single_function(func_name, new_code, clang_path)
        original_code = get_function_state(func_name, state).get("original_code") or code
        semantic_risks = detect_candidate_semantic_risks(original_code, new_code)
        if semantic_risks:
            warning_icon("检测到候选代码中的高风险改写模式：")
            for risk in semantic_risks:
                warning(f"  - {risk}")

        round_correctness_report = None
        if round_eval_result.get("compilable") and original_code:
            info("进行本轮 correctness 检查...")
            round_correctness_report = full_correctness_verification(
                original_code, new_code, func_name, clang_path
            )
            if not round_correctness_report.get("overall", False):
                summary = summarize_correctness_feedback(round_correctness_report)
                warning_icon(f"{func_name} 第 {current_round} 轮 correctness 未通过")
                if summary and summary.get("failure_reason"):
                    warning(f"  失败原因: {summary['failure_reason']}")

        # 保存本轮优化后的代码到文件（包含策略和评估结果）
        output_file = os.path.join(output_dir, f"{config.OPTIMIZED_FILE_PREFIX}{func_name}_round{current_round}.c")
        header = format_round_header(func_name, current_round, strategy, round_eval_result)
        save_code_to_file(output_file, new_code, header)

        # 保存到状态
        add_round(
            func_name,
            new_code,
            round_eval_result,
            round_eval_result.get("diagnostics"),
            state,
            strategy,
            correctness_report=round_correctness_report,
            semantic_risks=semantic_risks,
            prompt_snapshot=prompt_snapshot,
        )

        info(f"代码已保存到: {output_file}")

        # 下一轮默认建立在最近一个 correctness 通过的候选上，避免持续放大语义错误。
        next_code, _, _ = get_code_for_next_round(func_name, state)
        if next_code != new_code:
            info(f"{func_name} 下一轮将回退到最近一个 correctness 通过的候选继续优化")
        code = next_code

    return finalize_function_optimization(
        func_name,
        output_dir,
        state,
        clang_path,
        strategy_config=strategy_config,
    )


def run_batch_optimization(functions: List[str], api_key: Optional[str] = None,
                           model_name: Optional[str] = None, clang_path: Optional[str] = None,
                           max_rounds: int = 3, verbose: bool = False,
                           single_round: bool = False,
                           strategy_name: str = "ours_full") -> List[Dict]:
    """
    批量优化多个函数

    Args:
        functions: 函数名列表
        single_round: 单轮优化模式
    """
    if model_name is None:
        model_name = get_model_name()
    if api_key is None:
        api_key = get_api_key()
    if clang_path is None:
        clang_path = get_clang_path()
    strategy_config = get_experiment_strategy(strategy_name)

    mode_str = "单轮优化" if single_round else f"多轮优化(最多{max_rounds}轮)"
    section("批量优化流水线")
    info(f"函数数量: {len(functions)}")
    info(f"模式: {mode_str}")
    info(f"模型: {model_name}")
    info(f"策略: {strategy_name} - {strategy_config['description']}")

    results = []

    for i, func_name in enumerate(functions, 1):
        progress(i, len(functions), f"处理函数: {func_name}")

        result = optimize_single_function(
            func_name,
            api_key,
            model_name,
            clang_path,
            max_rounds,
            verbose,
            single_round,
            strategy_config
        )

        results.append({
            "function": func_name,
            "strategy": strategy_name,
            **result
        })

    # 打印汇总
    section("批量优化汇总")

    success_count = sum(1 for r in results if r.get("status") == "success")
    partial_count = sum(1 for r in results if r.get("status") == "partial_success")
    skipped_count = sum(1 for r in results if r.get("status") == "skipped")
    total_rounds = sum(r["rounds"] for r in results)

    info(f"统计:")
    info(f"  • 总函数数: {len(results)}")
    info(f"  • 完全向量化: {success_count}/{len(results)}")
    if partial_count > 0:
        info(f"  • 部分向量化: {partial_count}/{len(results)}")
    if skipped_count > 0:
        info(f"  • 已跳过(原始已向量化): {skipped_count}/{len(results)}")
    info(f"  • 总轮次数: {total_rounds}")

    subsection("详细结果")
    info(f"{'函数名':<15} {'状态':<15} {'轮数':<8}")
    info("-" * 40)

    for r in results:
        result_status = r.get("status")
        if result_status == "success":
            status = "✅ 完全向量化"
        elif result_status == "partial_success":
            v = r.get("vectorized_count", 0)
            m = r.get("missed_count", 0)
            status = f"⚠️  部分({v}/{v+m})"
        elif result_status == "skipped":
            status = "⏭️ 已跳过"
        else:
            status = "❌ 优化失败"
        info(f"{r['function']:<15} {status:<15} {r['rounds']:<8}")

    # 保存最佳代码到最终文件（已在各函数目录中保存，这里仅显示信息）
    info("最终结果已保存到各函数目录：")
    for func_name in functions:
        output_dir = get_function_output_dir(func_name)
        best_code = get_best_code(func_name)
        if best_code:
            final_file = os.path.join(output_dir, f"{config.OPTIMIZED_FILE_PREFIX}{func_name}.c")
            # 确保最终文件存在（如果不存在则保存）
            if not os.path.exists(final_file):
                save_code_to_file(final_file, best_code, f"// Best optimization for {func_name}")
            info(f"  {func_name} -> {final_file}")

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="VecGuide 优化流水线")
    parser.add_argument("functions", nargs="*", help="要优化的函数名 (例如: s111 s112)")
    parser.add_argument("-r", "--rounds", type=int, default=config.DEFAULT_MAX_ROUNDS,
                        help=f"最大优化轮数 (默认: {config.DEFAULT_MAX_ROUNDS})")
    parser.add_argument("-c", "--clang", default=get_clang_path(), help="clang 路径")
    parser.add_argument("-m", "--model", default=None, help="模型名称")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--single-round", action="store_true",
                        help="单轮优化模式（不进行多轮迭代）")
    parser.add_argument("--from-analysis", metavar="FILE",
                        help="从问题映射文件读取要优化的函数")
    parser.add_argument("--reset", action="store_true", help="重置指定函数的优化状态")
    parser.add_argument("--clean", action="store_true", help="重置时同时删除函数目录和文件")
    parser.add_argument("--status", action="store_true", help="显示当前优化状态")
    parser.add_argument("--severity", default=None,
                        help="按严重程度筛选函数进行优化 (例如: high, medium, low, 或组合 high,medium)")
    parser.add_argument("--strategy", default="ours_full",
                        help="实验策略 (例如: ours_full, llm_plain, ablate_kb)")
    parser.add_argument("--list-strategies", action="store_true",
                        help="列出可用实验策略")
    parser.add_argument("--json-summary", metavar="FILE",
                        help="将本次运行的结构化摘要写入 JSON 文件")

    args = parser.parse_args()

    if args.list_strategies:
        info(json.dumps(list_experiment_strategies(), indent=2, ensure_ascii=False))
        return

    try:
        strategy_config = get_experiment_strategy(args.strategy)
    except ValueError as e:
        failure(str(e))
        sys.exit(1)

    if args.status:
        # 显示状态
        summary = get_summary()
        info(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    if args.reset:
        # 重置状态
        if not args.functions:
            # 不指定函数名时，自动发现所有已优化的函数
            import glob
            
            # 从优化状态文件中发现
            state = load_state()
            funcs_from_state = [
                name for name, info in state.items()
                if name != "state_schema_version" and isinstance(info, dict)
            ]
            
            # 从目录结构中发现（新结构）
            funcs_from_dirs = []
            for dir_path in glob.glob(f"{config.OPTIMIZED_FILE_PREFIX}*/"):
                func_name = os.path.basename(dir_path.rstrip('/')).replace(config.OPTIMIZED_FILE_PREFIX, '')
                if func_name:
                    funcs_from_dirs.append(func_name)
            
            # 从旧结构文件中发现
            funcs_from_files = []
            for file_path in glob.glob(f"{config.OPTIMIZED_FILE_PREFIX}*.c"):
                stem = Path(file_path).stem
                func_name = stem.replace(config.OPTIMIZED_FILE_PREFIX, '')
                if func_name and '_origin' not in func_name and '_round' not in func_name:
                    funcs_from_files.append(func_name)
            
            # 合并去重
            all_functions = sorted(set(funcs_from_state + funcs_from_dirs + funcs_from_files))
            
            if not all_functions:
                warning_icon("未发现任何已优化的函数")
                return
            
            section(f"准备重置所有优化状态")
            info(f"发现 {len(all_functions)} 个已优化的函数:")
            for func_name in all_functions:
                info(f"  • {func_name}")
            
            # 用户确认
            clean_msg = "并删除所有相关文件和目录" if args.clean else ""
            try:
                confirm = input(f"\n⚠️  确认要重置所有 {len(all_functions)} 个函数的优化状态{clean_msg}吗? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                info("操作已取消")
                return
            
            if confirm not in ('y', 'yes'):
                info("操作已取消")
                return
            
            functions_to_reset = all_functions
        else:
            functions_to_reset = args.functions
        
        section("重置优化状态")
        reset_count = 0
        for func_name in functions_to_reset:
            # 重置状态
            reset_function(func_name)
            info(f"已重置 {func_name} 的优化状态")
            reset_count += 1

            # 如果指定了 --clean，同时删除文件和目录
            if args.clean:
                output_dir = get_function_output_dir(func_name)
                if os.path.exists(output_dir):
                    import shutil
                    shutil.rmtree(output_dir)
                    info(f"  已删除目录: {output_dir}")
                # 同时检查并删除旧结构的文件
                old_file = f"{config.OPTIMIZED_FILE_PREFIX}{func_name}.c"
                if os.path.exists(old_file):
                    os.remove(old_file)
                    info(f"  已删除文件: {old_file}")
        
        success(f"共重置 {reset_count} 个函数的优化状态")
        return

    # 确定要优化的函数列表
    functions_to_optimize = []

    if args.from_analysis or args.severity:
        # 从问题映射文件读取
        problem_map_file = args.from_analysis if args.from_analysis else config.PROBLEM_MAP_FILE
        
        if not os.path.exists(problem_map_file):
            failure(f"问题映射文件不存在: {problem_map_file}")
            sys.exit(1)
        try:
            with open(problem_map_file, 'r') as f:
                problem_map = json.load(f)
            
            # 确定要筛选的严重程度
            if args.severity:
                # 解析严重程度参数（支持逗号分隔）
                severity_filter = [s.strip().lower() for s in args.severity.split(',')]
                section(f"按严重程度筛选函数: {', '.join(severity_filter)}")
            else:
                # 默认只选择高和中等严重程度
                severity_filter = ['high', 'medium']
            
            # 筛选函数
            for func_name, info_dict in problem_map.items():
                severity = info_dict.get('severity', 'low')
                not_vectorized = info_dict.get('not_vectorized_count', 0)
                
                # 检查严重程度是否匹配且有未向量化的循环
                if severity in severity_filter and not_vectorized > 0:
                    functions_to_optimize.append(func_name)
            
            # 按严重程度排序（high > medium > low）
            severity_order = {'high': 0, 'medium': 1, 'low': 2}
            functions_to_optimize.sort(
                key=lambda x: (severity_order.get(problem_map.get(x, {}).get('severity', 'low'), 3), x)
            )
            
            info(f"从 {problem_map_file} 加载了 {len(functions_to_optimize)} 个需要优化的函数")
            
            # 显示筛选结果详情
            if functions_to_optimize:
                info("筛选结果:")
                for func_name in functions_to_optimize[:20]:  # 最多显示20个
                    severity = problem_map.get(func_name, {}).get('severity', 'unknown')
                    count = problem_map.get(func_name, {}).get('not_vectorized_count', 0)
                    info(f"  • {func_name} [{severity}] ({count} 个问题)")
                if len(functions_to_optimize) > 20:
                    info(f"  ... 还有 {len(functions_to_optimize) - 20} 个函数")
            else:
                warning_icon("未找到匹配筛选条件的函数")
                
        except Exception as e:
            failure(f"读取问题映射文件失败: {e}")
            sys.exit(1)
    elif args.functions:
        # 使用命令行指定的函数
        functions_to_optimize = args.functions
    else:
        # 自动发现所有函数
        info("自动发现文件中的函数...")
        all_functions = find_all_functions_in_file(get_source_file())
        if not all_functions:
            failure("未在文件中检测到任何函数")
            sys.exit(1)

        info(f"发现 {len(all_functions)} 个函数")
        info(f"前 10 个函数: {', '.join(all_functions[:10])}")

        # 询问用户要处理多少个函数
        try:
            num_to_process = int(input(f"\n请输入要处理的函数数量 (1-{len(all_functions)}): ").strip())
            if num_to_process < 1 or num_to_process > len(all_functions):
                warning("输入数量无效，使用默认值: 5")
                num_to_process = 5
        except:
            warning("输入无效，使用默认值: 5")
            num_to_process = 5

        functions_to_optimize = all_functions[:num_to_process]

    if not functions_to_optimize:
        failure("没有要优化的函数")
        sys.exit(1)

    # 运行优化
    model_name = args.model or get_model_name()
    api_key = get_api_key()
    effective_single_round = args.single_round or strategy_config.get("single_round", False)
    effective_rounds = strategy_config.get("max_rounds")
    if effective_rounds is None:
        effective_rounds = args.rounds
    if effective_single_round:
        effective_rounds = 1

    results = run_batch_optimization(
        functions_to_optimize,
        api_key=api_key,
        model_name=model_name,
        clang_path=args.clang,
        max_rounds=effective_rounds,
        verbose=args.verbose,
        single_round=effective_single_round,
        strategy_name=args.strategy,
    )

    if args.json_summary:
        summary_payload = {
            "timestamp": datetime.now().isoformat(),
            "strategy": args.strategy,
            "strategy_description": strategy_config["description"],
            "requested_rounds": args.rounds,
            "effective_rounds": effective_rounds,
            "single_round": effective_single_round,
            "functions": functions_to_optimize,
            "results": results,
        }
        with open(args.json_summary, "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2, ensure_ascii=False)
        success(f"JSON 摘要已保存到: {args.json_summary}")


if __name__ == "__main__":
    main()
