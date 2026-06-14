from __future__ import annotations

import math
from typing import Iterable


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    limit = min(len(left), len(right))
    left_slice = left[:limit]
    right_slice = right[:limit]
    dot = sum(l_value * r_value for l_value, r_value in zip(left_slice, right_slice, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left_slice))
    right_norm = math.sqrt(sum(value * value for value in right_slice))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def join_fields(*values: str) -> str:
    return "\n".join(value.strip() for value in values if value and value.strip())


def extract_keywords(text: str) -> list[str]:
    normalized = text.lower().replace(",", " ").replace("/", " ")
    tokens = [token for token in normalized.split() if len(token) > 1]
    return tokens
