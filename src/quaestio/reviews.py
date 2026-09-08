"""Multi-agent review panels for claim verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from quaestio.agents import AgentRun
from quaestio.exceptions import ReviewParseError
from quaestio.models import Evidence, jsonable, utc_now

ReviewDecision = Literal["approve", "reject", "revise", "invalid", "failed"]

VALID_REVIEW_DECISIONS = {"approve", "reject", "revise"}


@dataclass(slots=True)
class ReviewPolicy:
    """Quorum policy for a review panel."""

    min_approvals: int = 1
    reject_on_any_reject: bool = True

    def __post_init__(self) -> None:
        if self.min_approvals < 1:
            raise ValueError("min_approvals must be at least 1")

    def to_dict(self) -> dict[str, object]:
        return {
            "min_approvals": self.min_approvals,
            "reject_on_any_reject": self.reject_on_any_reject,
        }


@dataclass(slots=True)
class ReviewResult:
    """One reviewer agent's parsed decision."""

    reviewer_name: str
    agent_run: AgentRun
    decision: ReviewDecision
    comment: str = ""
    error: dict[str, str] | None = None
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.reviewer_name.strip():
            raise ValueError("reviewer_name must not be empty")
        if self.decision not in {
            "approve",
            "reject",
            "revise",
            "invalid",
            "failed",
        }:
            raise ValueError("review decision is invalid")

    @property
    def passed(self) -> bool:
        return self.decision == "approve"

    def to_evidence(self, panel_name: str) -> Evidence:
        return Evidence(
            name=f"review:{panel_name}:{self.reviewer_name}",
            kind="review",
            passed=self.decision == "approve",
            summary=f"{self.reviewer_name} decided {self.decision}",
            data=self.to_dict(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "reviewer_name": self.reviewer_name,
            "decision": self.decision,
            "comment": self.comment,
            "error": jsonable(self.error),
            "agent_run": self.agent_run.to_dict(),
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class ReviewPanel:
    """A group of reviewer agents that resolves a claim."""

    name: str
    reviewer_names: tuple[str, ...]
    policy: ReviewPolicy = field(default_factory=ReviewPolicy)
    prompt_template: str = (
        "Review this claim and respond with 'decision: approve', "
        "'decision: reject', or 'decision: revise'.\n\nClaim: {claim}"
    )
    status: str = "pending"
    stop_reason: str | None = None
    claim_id: str | None = None
    results: list[ReviewResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("review panel name must not be empty")
        self.reviewer_names = tuple(self.reviewer_names)
        if not self.reviewer_names:
            raise ValueError("reviewer_names must not be empty")
        if any(not reviewer.strip() for reviewer in self.reviewer_names):
            raise ValueError("reviewer_names must not contain empty names")
        if len(set(self.reviewer_names)) != len(self.reviewer_names):
            raise ValueError("reviewer_names must be unique")
        if self.policy.min_approvals > len(self.reviewer_names):
            raise ValueError("min_approvals cannot exceed reviewers")
        if self.status not in {"pending", "running", "approved", "rejected", "failed"}:
            raise ValueError("review panel status is invalid")
        if not self.prompt_template.strip():
            raise ValueError("prompt_template must not be empty")

    @property
    def approval_count(self) -> int:
        return sum(1 for result in self.results if result.decision == "approve")

    @property
    def reject_count(self) -> int:
        return sum(1 for result in self.results if result.decision == "reject")

    def task_for_claim(self, claim_statement: str) -> str:
        return self.prompt_template.format(claim=claim_statement, panel=self.name)

    def record_result(self, result: ReviewResult) -> ReviewResult:
        if result.reviewer_name not in self.reviewer_names:
            raise ValueError(f"reviewer {result.reviewer_name!r} is not in this panel")
        if any(existing.reviewer_name == result.reviewer_name for existing in self.results):
            raise ValueError(f"reviewer {result.reviewer_name!r} already submitted")
        self.results.append(result)
        return result

    def resolve(self) -> str:
        if any(result.decision == "failed" for result in self.results):
            self.status = "failed"
            self.stop_reason = "reviewer_failed"
        elif any(result.decision == "invalid" for result in self.results):
            self.status = "failed"
            self.stop_reason = "invalid_review"
        elif self.policy.reject_on_any_reject and self.reject_count > 0:
            self.status = "rejected"
            self.stop_reason = "reviewer_rejected"
        elif self.approval_count >= self.policy.min_approvals:
            self.status = "approved"
            self.stop_reason = "quorum_approved"
        else:
            self.status = "rejected"
            self.stop_reason = "insufficient_approvals"
        return self.status

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "reviewer_names": list(self.reviewer_names),
            "policy": self.policy.to_dict(),
            "prompt_template": self.prompt_template,
            "status": self.status,
            "stop_reason": self.stop_reason,
            "claim_id": self.claim_id,
            "approval_count": self.approval_count,
            "reject_count": self.reject_count,
            "results": [result.to_dict() for result in self.results],
        }


def parse_review_decision(stdout: str) -> dict[str, str]:
    """Parse the simple line-oriented reviewer protocol."""

    decision: str | None = None
    comments: list[str] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        key, sep, value = line.partition(":")
        if sep and key.strip().lower() == "decision":
            decision = value.strip().lower()
        elif sep and key.strip().lower() == "comment":
            comments.append(value.strip())
        else:
            comments.append(line)

    if decision is None:
        raise ReviewParseError("missing decision")
    if decision not in VALID_REVIEW_DECISIONS:
        raise ReviewParseError(f"unknown decision: {decision}")
    return {"decision": decision, "comment": "\n".join(comments).strip()}
