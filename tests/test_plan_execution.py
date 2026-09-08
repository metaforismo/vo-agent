from __future__ import annotations

import pytest

from quaestio import AgentRun, ExecutedTask, ExecutedWave, PlanExecutionResult
from quaestio.models import utc_now


def agent_run(*, exit_code: int = 0, task: str = "solve") -> AgentRun:
    now = utc_now()
    return AgentRun(
        agent_name="solver",
        task=task,
        command=["solver"],
        exit_code=exit_code,
        stdout="ok" if exit_code == 0 else "",
        stderr="" if exit_code == 0 else "failed",
        duration_s=0.01,
        started_at=now,
        finished_at=now,
    )


def executed_task(name: str = "solve", *, exit_code: int = 0) -> ExecutedTask:
    return ExecutedTask(
        name=name,
        agent_name="solver",
        environment="local-dev",
        agent_run=agent_run(exit_code=exit_code),
    )


def test_executed_task_validates_name() -> None:
    with pytest.raises(ValueError, match="executed task name must not be empty"):
        ExecutedTask(
            name="",
            agent_name="solver",
            environment="local-dev",
            agent_run=agent_run(),
        )


def test_executed_task_status_follows_agent_run_exit_code() -> None:
    assert executed_task(exit_code=0).status == "passed"
    assert executed_task(exit_code=1).status == "failed"


def test_executed_task_serializes_environment_and_agent_run() -> None:
    bundle = executed_task().to_dict()

    assert bundle["name"] == "solve"
    assert bundle["agent_name"] == "solver"
    assert bundle["environment"] == "local-dev"
    assert bundle["status"] == "passed"
    assert bundle["agent_run"]["agent_name"] == "solver"
    assert bundle["agent_run"]["passed"] is True


def test_executed_wave_validates_positive_index() -> None:
    with pytest.raises(ValueError, match="executed wave index must be positive"):
        ExecutedWave(index=0, tasks=(executed_task(),))


def test_executed_wave_status_fails_when_any_task_failed() -> None:
    assert ExecutedWave(index=1, tasks=(executed_task(),)).status == "passed"
    assert ExecutedWave(
        index=1,
        tasks=(executed_task("ok"), executed_task("bad", exit_code=2)),
    ).status == "failed"


def test_plan_execution_result_validates_plan_name() -> None:
    with pytest.raises(ValueError, match="plan execution plan_name must not be empty"):
        PlanExecutionResult(plan_name="", waves=())


def test_plan_execution_result_aggregates_counts_and_status() -> None:
    result = PlanExecutionResult(
        plan_name="solver-plan-execution",
        waves=(
            ExecutedWave(index=1, tasks=(executed_task("one"),)),
            ExecutedWave(
                index=2,
                tasks=(executed_task("two"), executed_task("three", exit_code=1)),
            ),
        ),
    )

    assert result.status == "failed"
    assert result.wave_count == 2
    assert result.task_count == 3
    assert result.passed_count == 2
    assert result.failed_count == 1


def test_plan_execution_result_serializes_waves_and_counts() -> None:
    result = PlanExecutionResult(
        plan_name="solver-plan-execution",
        waves=(ExecutedWave(index=1, tasks=(executed_task(),)),),
        metadata={"mode": "local"},
    )
    bundle = result.to_dict()

    assert bundle["plan_name"] == "solver-plan-execution"
    assert bundle["status"] == "passed"
    assert bundle["wave_count"] == 1
    assert bundle["task_count"] == 1
    assert bundle["passed_count"] == 1
    assert bundle["failed_count"] == 0
    assert bundle["metadata"] == {"mode": "local"}
    assert bundle["waves"][0]["tasks"][0]["name"] == "solve"
