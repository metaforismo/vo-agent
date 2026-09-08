from __future__ import annotations

import pytest

from quaestio import Budget, BudgetExceeded, WorkflowRun


def test_budget_tracks_spends_and_remaining_balance() -> None:
    budget = Budget(limit=10.0, unit="usd")

    entry = budget.spend(2.5, label="solver", metadata={"agent": "alpha"})

    assert entry.amount == 2.5
    assert entry.label == "solver"
    assert entry.metadata == {"agent": "alpha"}
    assert budget.used == 2.5
    assert budget.remaining == 7.5
    assert budget.to_dict()["entries"][0]["label"] == "solver"


def test_budget_rejects_negative_spend() -> None:
    budget = Budget(limit=10.0)

    with pytest.raises(ValueError, match="amount must be non-negative"):
        budget.spend(-0.01)


def test_budget_enforces_hard_limit_without_mutating_state() -> None:
    budget = Budget(limit=3.0)
    budget.spend(2.0, label="first")

    with pytest.raises(BudgetExceeded):
        budget.spend(1.5, label="too much")

    assert budget.used == 2.0
    assert [entry.label for entry in budget.entries] == ["first"]


def test_workflow_budget_spend_is_recorded_in_bundle() -> None:
    run = WorkflowRun(name="budgeted search", budget=Budget(limit=5.0, unit="usd"))

    run.spend_budget(1.25, label="critic", metadata={"round": 1})
    bundle = run.to_dict()

    assert bundle["budget"]["used"] == 1.25
    assert bundle["budget"]["remaining"] == 3.75
    assert bundle["budget"]["entries"][0]["metadata"] == {"round": 1}
    assert bundle["events"][-1]["type"] == "budget_spent"
