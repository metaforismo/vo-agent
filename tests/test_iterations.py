from __future__ import annotations

from collections.abc import Sequence

import pytest

from quaestio import (
    AgentRun,
    AgentSpec,
    Budget,
    Evidence,
    IterationLoop,
    IterationPolicy,
    VerifierChain,
    WorkflowRun,
)
from quaestio.models import utc_now
from quaestio.verifiers import VerificationContext


class ScriptedAgent:
    name = "solver"

    def __init__(self, exit_codes: Sequence[int]) -> None:
        self.exit_codes = list(exit_codes)
        self.calls = 0

    def run(
        self,
        task: str,
        context: VerificationContext | None = None,
    ) -> AgentRun:
        del context
        self.calls += 1
        exit_code = self.exit_codes.pop(0)
        now = utc_now()
        return AgentRun(
            agent_name=self.name,
            task=task,
            command=["scripted-agent"],
            exit_code=exit_code,
            stdout=f"attempt {self.calls}\n",
            stderr="" if exit_code == 0 else "agent failed\n",
            duration_s=0.0,
            started_at=now,
            finished_at=now,
            metadata={"call": self.calls},
        )


class SequenceVerifier:
    name = "hard-tests"

    def __init__(self, outcomes: Sequence[bool]) -> None:
        self.outcomes = list(outcomes)

    def verify(self, claim, context):
        del claim, context
        passed = self.outcomes.pop(0)
        return Evidence(
            name=self.name,
            kind="scripted",
            passed=passed,
            summary="tests passed" if passed else "tests failed",
        )


def make_loop(max_attempts: int = 3) -> IterationLoop:
    return IterationLoop(
        name="hard-test-loop",
        agent_name="solver",
        task="make tests pass",
        policy=IterationPolicy(max_attempts=max_attempts),
    )


def make_run(*, budget: Budget | None = None) -> WorkflowRun:
    run = WorkflowRun(name="iteration workflow", budget=budget)
    run.add_agent(AgentSpec(name="solver", goal="Make the hard tests pass"))
    return run


def test_iteration_policy_requires_positive_max_attempts() -> None:
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        IterationPolicy(max_attempts=0)


def test_iteration_policy_rejects_negative_budget_per_attempt() -> None:
    with pytest.raises(ValueError, match="budget_per_attempt must be non-negative"):
        IterationPolicy(max_attempts=1, budget_per_attempt=-0.01)


def test_iteration_loop_stops_when_verification_passes_on_later_attempt() -> None:
    run = make_run()
    loop = make_loop(max_attempts=3)
    run.add_iteration_loop(loop)

    result = run.iterate_until_verified(
        loop,
        ScriptedAgent([0, 0]),
        VerifierChain([SequenceVerifier([False, True])]),
    )

    assert result is loop
    assert loop.status == "passed"
    assert loop.stop_reason == "verification_passed"
    assert [attempt.passed for attempt in loop.attempts] == [False, True]
    assert [attempt.reason for attempt in loop.attempts] == [
        "verification_failed",
        "verification_passed",
    ]
    assert [claim.status for claim in run.claims] == ["rejected", "accepted"]
    assert len(run.agent_runs) == 2


def test_iteration_loop_stops_after_max_attempts() -> None:
    run = make_run()
    loop = make_loop(max_attempts=2)
    run.add_iteration_loop(loop)

    run.iterate_until_verified(
        loop,
        ScriptedAgent([0, 0]),
        VerifierChain([SequenceVerifier([False, False])]),
    )

    assert loop.status == "failed"
    assert loop.stop_reason == "max_attempts"
    assert len(loop.attempts) == 2
    assert all(attempt.reason == "verification_failed" for attempt in loop.attempts)
    assert [claim.status for claim in run.claims] == ["rejected", "rejected"]


def test_iteration_loop_spends_budget_per_attempt() -> None:
    run = make_run(budget=Budget(limit=3.0, unit="usd"))
    loop = IterationLoop(
        name="budgeted-loop",
        agent_name="solver",
        task="make tests pass",
        policy=IterationPolicy(
            max_attempts=3,
            budget_per_attempt=0.5,
            budget_label="solver attempt",
        ),
    )
    run.add_iteration_loop(loop)

    run.iterate_until_verified(
        loop,
        ScriptedAgent([0, 0]),
        VerifierChain([SequenceVerifier([False, True])]),
    )

    assert run.budget is not None
    assert run.budget.used == 1.0
    assert [entry.label for entry in run.budget.entries] == [
        "solver attempt",
        "solver attempt",
    ]
    assert run.budget.entries[1].metadata == {"loop": "budgeted-loop", "attempt": 2}


def test_iteration_loop_records_agent_failure_without_verification_claim() -> None:
    run = make_run()
    loop = make_loop(max_attempts=2)
    run.add_iteration_loop(loop)

    run.iterate_until_verified(
        loop,
        ScriptedAgent([1, 0]),
        VerifierChain([SequenceVerifier([True])]),
    )

    assert loop.status == "passed"
    assert [attempt.reason for attempt in loop.attempts] == [
        "agent_failed",
        "verification_passed",
    ]
    assert loop.attempts[0].claim_id is None
    assert loop.attempts[0].verification is None
    assert len(run.claims) == 1
    assert run.claims[0].status == "accepted"
