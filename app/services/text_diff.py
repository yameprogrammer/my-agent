"""
H6: 두 본문 버전 간 줄 단위 side-by-side diff 유틸 (stdlib difflib).
"""
from __future__ import annotations

import difflib
from typing import Any, Dict, List


def build_line_diff(left: str, right: str) -> List[Dict[str, Any]]:
    """
    SequenceMatcher opcodes 기반 행 단위 diff.
    각 행: { "op": equal|delete|insert|replace, "left": str|null, "right": str|null }
    """
    left_lines = (left or "").splitlines()
    right_lines = (right or "").splitlines()
    sm = difflib.SequenceMatcher(None, left_lines, right_lines, autojunk=False)
    rows: List[Dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                rows.append({
                    "op": "equal",
                    "left": left_lines[i1 + k],
                    "right": right_lines[j1 + k],
                })
        elif tag == "delete":
            for k in range(i2 - i1):
                rows.append({
                    "op": "delete",
                    "left": left_lines[i1 + k],
                    "right": None,
                })
        elif tag == "insert":
            for k in range(j2 - j1):
                rows.append({
                    "op": "insert",
                    "left": None,
                    "right": right_lines[j1 + k],
                })
        elif tag == "replace":
            left_chunk = left_lines[i1:i2]
            right_chunk = right_lines[j1:j2]
            n = max(len(left_chunk), len(right_chunk))
            for k in range(n):
                rows.append({
                    "op": "replace",
                    "left": left_chunk[k] if k < len(left_chunk) else None,
                    "right": right_chunk[k] if k < len(right_chunk) else None,
                })
    return rows


def apply_span_replacement(full_text: str, selected: str, replacement: str) -> str:
    """
    full_text 내 selected 첫 등장 구간을 replacement 로 교체.
    selected 가 없으면 ValueError.
    """
    if not selected:
        raise ValueError("selected_text is empty")
    idx = full_text.find(selected)
    if idx < 0:
        raise ValueError("selected_text not found in full_text")
    return full_text[:idx] + replacement + full_text[idx + len(selected):]
