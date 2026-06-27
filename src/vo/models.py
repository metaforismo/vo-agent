"""Serializable workflow models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    """Return a stable ISO-8601 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def short_id() -> str:
    """Return a compact random identifier for local run objects."""

    return uuid4().hex[:12]


def jsonable(value: Any) -> Any:
    """Convert common Python values into JSON-safe primitives."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    return str(value)


@dataclass(slots=True)
class AgentSpec:
    """Declarative description of an agent participating in a workflow."""

    name: str
    goal: str
    model: str | None = None
    tools: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("agent name must not be empty")
        if not self.goal.strip():
            raise ValueError("agent goal must not be empty")
        self.tools = tuple(self.tools)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "goal": self.goal,
            "model": self.model,
            "tools": list(self.tools),
            "metadata": jsonable(self.metadata),
        }


@dataclass(slots=True)
class Evidence:
    """Evidence produced by a verifier."""

    name: str
    passed: bool
    summary: str
    kind: str = "generic"
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "passed": self.passed,
            "summary": self.summary,
            "data": jsonable(self.data),
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class Claim:
    """A statement that can only advance through attached evidence."""

    statement: str
    id: str = field(default_factory=short_id)
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("claim statement must not be empty")
        if self.status not in {"pending", "accepted", "rejected"}:
            raise ValueError("claim status must be pending, accepted, or rejected")

    def add_evidence(self, evidence: Evidence) -> None:
        self.evidence.append(evidence)

    def accept(self) -> None:
        self.status = "accepted"

    def reject(self) -> None:
        self.status = "rejected"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "status": self.status,
            "metadata": jsonable(self.metadata),
            "evidence": [item.to_dict() for item in self.evidence],
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class VerificationResult:
    """Result of running a verifier chain against a claim."""

    passed: bool
    evidence: list[Evidence]
    failed_evidence: Evidence | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "evidence": [item.to_dict() for item in self.evidence],
            "failed_evidence": (
                self.failed_evidence.to_dict() if self.failed_evidence else None
            ),
        }


@dataclass(slots=True)
class WorkflowEvent:
    """A timestamped workflow event for run replay and inspection."""

    type: str
    data: dict[str, Any] | None = None
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.type.strip():
            raise ValueError("event type must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "data": jsonable(self.data or {}),
            "created_at": self.created_at,
        }
