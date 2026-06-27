"""Verification-driven iteration loops."""

from __future__ import annotations

from dataclasses import dataclass, field

from vo.agents import AgentRun
from vo.models import VerificationResult, jsonable, utc_now


@dataclass(slots=True)
class IterationPolicy:
    """Limits and accounting rules for an iteration loop."""

    max_attempts: int
    budget_per_attempt: float | None = None
    budget_label: str = "iteration attempt"

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.budget_per_attempt is not None and self.budget_per_attempt < 0:
            raise ValueError("budget_per_attempt must be non-negative")
        if not self.budget_label.strip():
            raise ValueError("budget_label must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "max_attempts": self.max_attempts,
            "budget_per_attempt": self.budget_per_attempt,
            "budget_label": self.budget_label,
        }


@dataclass(slots=True)
class IterationAttempt:
    """One execution and optional verification attempt."""

    index: int
    agent_run: AgentRun
    passed: bool
    reason: str
    claim_id: str | None = None
    verification: VerificationResult | None = None
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("attempt index must be at least 1")
        if not self.reason.strip():
            raise ValueError("attempt reason must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "agent_run": self.agent_run.to_dict(),
            "claim_id": self.claim_id,
            "verification": self.verification.to_dict() if self.verification else None,
            "passed": self.passed,
            "reason": self.reason,
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class IterationLoop:
    """A bounded loop that runs an agent until verification passes."""

    name: str
    agent_name: str
    task: str
    policy: IterationPolicy
    claim_statement: str | None = None
    status: str = "pending"
    stop_reason: str | None = None
    attempts: list[IterationAttempt] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("iteration loop name must not be empty")
        if not self.agent_name.strip():
            raise ValueError("iteration loop agent_name must not be empty")
        if not self.task.strip():
            raise ValueError("iteration loop task must not be empty")
        if self.status not in {"pending", "running", "passed", "failed"}:
            raise ValueError("iteration loop status is invalid")

    def claim_for_attempt(self, index: int) -> str:
        if self.claim_statement:
            return self.claim_statement.format(
                loop=self.name,
                attempt=index,
                agent=self.agent_name,
            )
        return f"{self.name} attempt {index} passes verification"

    def record_attempt(self, attempt: IterationAttempt) -> IterationAttempt:
        expected = len(self.attempts) + 1
        if attempt.index != expected:
            raise ValueError(f"attempt index must be {expected}")
        self.attempts.append(attempt)
        return attempt

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "agent_name": self.agent_name,
            "task": self.task,
            "policy": self.policy.to_dict(),
            "claim_statement": self.claim_statement,
            "status": self.status,
            "stop_reason": self.stop_reason,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "data": jsonable(
                {
                    "attempt_count": len(self.attempts),
                    "passed": self.status == "passed",
                }
            ),
        }
