"""Budget accounting for workflow runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vo.exceptions import BudgetExceeded
from vo.models import jsonable, utc_now


@dataclass(slots=True)
class BudgetEntry:
    """One budget spend recorded during a workflow run."""

    amount: float
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("amount must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "label": self.label,
            "metadata": jsonable(self.metadata),
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class Budget:
    """A simple hard-limit budget ledger."""

    limit: float | None = None
    used: float = 0.0
    unit: str = "units"
    entries: list[BudgetEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.limit is not None and self.limit < 0:
            raise ValueError("budget limit must be non-negative")
        if self.used < 0:
            raise ValueError("budget used amount must be non-negative")
        if not self.unit.strip():
            raise ValueError("budget unit must not be empty")
        if self.limit is not None and self.used > self.limit:
            raise BudgetExceeded(
                f"budget already exceeds limit: {self.used} > {self.limit} {self.unit}"
            )

    @property
    def remaining(self) -> float | None:
        if self.limit is None:
            return None
        return self.limit - self.used

    def spend(
        self,
        amount: float,
        *,
        label: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> BudgetEntry:
        if amount < 0:
            raise ValueError("amount must be non-negative")
        next_used = self.used + amount
        if self.limit is not None and next_used > self.limit:
            raise BudgetExceeded(
                f"budget exceeded: {next_used} > {self.limit} {self.unit}"
            )

        entry = BudgetEntry(
            amount=amount,
            label=label,
            metadata=dict(metadata or {}),
        )
        self.used = next_used
        self.entries.append(entry)
        return entry

    def to_dict(self) -> dict[str, Any]:
        return {
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining,
            "unit": self.unit,
            "entries": [entry.to_dict() for entry in self.entries],
        }
