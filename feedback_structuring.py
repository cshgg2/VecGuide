"""
Structured compiler feedback utilities.

These helpers normalize clang vectorization remarks into stable categories so
the optimizer can drive class-specific retrieval instead of relying on raw
diagnostic strings only.
"""

from __future__ import annotations

import re
from typing import Dict, List


CATEGORY_METADATA: Dict[str, Dict[str, object]] = {
    "dependency_unsafe": {
        "label": "unsafe dependence / isolate dependent ops",
        "patterns": (
            r"unsafe dependent memory operations",
            r"\btrue dependency\b",
            r"\bflow dependency\b",
            r"\bunsafe dependency\b",
            r"\bdependent memory\b",
        ),
    },
    "trip_count_bounds": {
        "label": "trip count or bounds unknown",
        "patterns": (
            r"could not determine number of loop iterations",
            r"could not determine the upper bound",
            r"cannot identify array bounds",
            r"\bloop iteration\b",
            r"\bbounds\b",
        ),
    },
    "call_side_effect": {
        "label": "call or side effect blocker",
        "patterns": (
            r"call instruction cannot be vectorized",
            r"\bfunction call\b",
            r"\bcall instruction\b",
        ),
    },
    "recurrence_reduction": {
        "label": "reduction / recurrence boundary",
        "patterns": (
            r"value that could not be identified as reduction",
            r"\breduction\b",
            r"cannot prove it is safe to reorder floating-point operations",
            r"floating-point operations",
            r"\brecurr",
        ),
    },
    "control_flow": {
        "label": "control flow / predication candidate",
        "patterns": (
            r"\bcontrol flow\b",
            r"\bbranch\b",
            r"\bswitch\b",
            r"\bgoto\b",
        ),
    },
    "indirect_irregular_access": {
        "label": "indirect or irregular memory access",
        "patterns": (
            r"\bindirect\b",
            r"\bgather\b",
            r"\bscatter\b",
            r"\birregular\b",
            r"non-consecutive memory access",
        ),
    },
    "alias_memory": {
        "label": "alias or memory ambiguity",
        "patterns": (
            r"\balias\b",
            r"\bmay alias\b",
            r"\bmemory dependency\b",
        ),
    },
    "instruction_shape": {
        "label": "instruction shape blocker",
        "patterns": (
            r"instruction cannot be vectorized",
            r"unsupported instruction",
            r"interleaved memory access",
        ),
    },
    "other": {
        "label": "other vectorization blocker",
        "patterns": (),
    },
}


def dedupe_preserve_order(items: List[str]) -> List[str]:
    """Return unique items while preserving first-seen order."""
    seen = set()
    ordered: List[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def category_label(category: str) -> str:
    """Human-readable label for a diagnostic category."""
    meta = CATEGORY_METADATA.get(category, CATEGORY_METADATA["other"])
    return str(meta["label"])


def categorize_reason(reason: str) -> List[str]:
    """Map a compiler diagnostic string to one or more stable categories."""
    if not reason:
        return ["other"]

    lowered = reason.lower()
    matched: List[str] = []
    for category, meta in CATEGORY_METADATA.items():
        for pattern in meta.get("patterns", ()):
            if re.search(pattern, lowered):
                matched.append(category)
                break

    return dedupe_preserve_order(matched or ["other"])


def parse_diagnostic_line(line: str) -> Dict[str, object]:
    """Parse a raw clang remark into structured fields."""
    stripped = (line or "").strip()
    parsed: Dict[str, object] = {
        "raw": stripped,
        "line": None,
        "column": None,
        "message": stripped,
        "reason": stripped,
        "categories": ["other"],
    }
    if not stripped:
        return parsed

    match = re.search(r":(?P<line>\d+):(?P<column>\d+):\s+remark:\s+(?P<message>.+)$", stripped)
    if match:
        parsed["line"] = int(match.group("line"))
        parsed["column"] = int(match.group("column"))
        parsed["message"] = match.group("message").strip()
    else:
        alt = re.search(r"remark:\s+(?P<message>.+)$", stripped)
        if alt:
            parsed["message"] = alt.group("message").strip()

    message = str(parsed["message"])
    if "loop not vectorized:" in message:
        reason = message.split("loop not vectorized:", 1)[1].strip()
    elif "loop vectorized" in message:
        reason = "loop vectorized"
    else:
        reason = message

    parsed["reason"] = reason
    parsed["categories"] = categorize_reason(reason)
    return parsed
