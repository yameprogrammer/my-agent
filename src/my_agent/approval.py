from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .schemas import ApprovalPolicy


@dataclass(slots=True)
class ApprovalDecision:
    approved: bool
    requires_manual_review: bool
    reason: str


class ApprovalPolicyStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> ApprovalPolicy:
        if not self.path.exists():
            return ApprovalPolicy()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return ApprovalPolicy.model_validate(data)

    def save(self, policy: ApprovalPolicy) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(policy.model_dump_json(indent=2), encoding="utf-8")

    def decide(self, score: float, critical: bool = False) -> ApprovalDecision:
        policy = self.load()
        if critical and policy.critical_requires_manual_review:
            return ApprovalDecision(False, True, "critical_issue")
        if score >= policy.auto_approve_threshold or score >= policy.auto_approval_ratio:
            return ApprovalDecision(True, False, "auto_approved")
        if score >= policy.manual_review_threshold or score >= policy.manual_review_ratio:
            return ApprovalDecision(False, True, "manual_review")
        return ApprovalDecision(False, True, "rejected_for_review")
