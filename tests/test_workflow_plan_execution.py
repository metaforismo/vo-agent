from __future__ import annotations

import json
from pathlib import Path

import pytest

from vo import (
    AgentRun,
    AgentSpec,
    ComputeResources,
    EnvironmentSpec,
    LocalProvisioner,
    PlanExecutionError,
    TaskGraph,
    TaskSpec,
    VerificationContext,
    WorkflowRun,
)
from vo.models import utc_now


class StaticAgent:
    def __init__(self, name: str, *, exit_code: int = 0) -> None:
        self.name = name
        self.exit_code = exit_code
        self.tasks: list[str] = []

    def run(
        self,
        task: str,
        context: VerificationContext | None = None,
    ) -> AgentRun:
        self.tasks.append(task)
        now = utc_now()
        return AgentRun(
            agent_name=self.name,
            task=task,
            command=[self.name],
            exit_code=self.exit_code,
            stdout=f"done {task}" if self.exit_code == 0 else "",
            stderr="" if self.exit_code == 0 else "failed",
            duration_s=0.01,
            started_at=now,
            finished_at=now,
        )


def configured_run() -> tuple[WorkflowRun, object]:
    run = WorkflowRun(name="plan execution workflow")
    run.add_agent(AgentSpec(name="searcher", goal="search"))
    run.add_agent(AgentSpec(name="checker", goal="check"))
    run.add_environment(
        EnvironmentSpec(
            name="local-dev",
            kind="local",
            resources=ComputeResources(cpu=2, memory_gb=4),
        )
    )
    run.assign_agent_environment("searcher", "local-dev")
    run.assign_agent_environment("checker", "local-dev")
    graph = TaskGraph(name="research-plan")
    graph.add_task(TaskSpec(name="search", agent_name="searcher", task="search"))
    graph.add_task(
        TaskSpec(
            name="verify",
            agent_name="checker",
            task="verify",
            depends_on=("search",),
        )
    )
    run.add_task_graph(graph)
    plan = run.plan_task_graph(graph)
    return run, plan


def test_workflow_executes_provisioned_execution_plan() -> None:
    run, plan = configured_run()
    run.provision_execution_plan(plan, LocalProvisioner())

    result = run.execute_execution_plan(
        plan,
        {
            "searcher": StaticAgent("searcher"),
            "checker": StaticAgent("checker"),
        },
    )

    assert run.plan_execution_results == [result]
    assert result.plan_name == "research-plan-execution"
    assert result.status == "passed"
    assert result.wave_count == 2
    assert result.task_count == 2
    assert [agent_run.agent_name for agent_run in run.agent_runs] == [
        "searcher",
        "checker",
    ]


def test_workflow_rejects_unregistered_execution_plan() -> None:
    registered_run, plan = configured_run()
    other_run = WorkflowRun(name="other")

    with pytest.raises(
        ValueError,
        match="execution plan does not belong to this workflow run",
    ):
        other_run.execute_execution_plan(plan, {"searcher": StaticAgent("searcher")})

    assert registered_run.plan_execution_results == []


def test_workflow_rejects_missing_plan_adapters() -> None:
    run, plan = configured_run()
    run.provision_execution_plan(plan, LocalProvisioner())

    with pytest.raises(ValueError, match="missing adapter for agent 'checker'"):
        run.execute_execution_plan(plan, {"searcher": StaticAgent("searcher")})


def test_workflow_requires_ready_provisioning_by_default() -> None:
    run, plan = configured_run()

    with pytest.raises(
        PlanExecutionError,
        match="execution plan 'research-plan-execution' has no ready provisioning result",
    ):
        run.execute_execution_plan(
            plan,
            {
                "searcher": StaticAgent("searcher"),
                "checker": StaticAgent("checker"),
            },
        )


def test_workflow_stops_after_failed_wave() -> None:
    run, plan = configured_run()
    run.provision_execution_plan(plan, LocalProvisioner())
    checker = StaticAgent("checker")

    result = run.execute_execution_plan(
        plan,
        {
            "searcher": StaticAgent("searcher", exit_code=1),
            "checker": checker,
        },
    )

    assert result.status == "failed"
    assert result.wave_count == 1
    assert result.task_count == 1
    assert result.failed_count == 1
    assert checker.tasks == []


def test_workflow_records_plan_execution_events() -> None:
    run, plan = configured_run()
    run.provision_execution_plan(plan, LocalProvisioner())

    run.execute_execution_plan(
        plan,
        {
            "searcher": StaticAgent("searcher"),
            "checker": StaticAgent("checker"),
        },
    )

    event_types = [event.type for event in run.events]
    assert "plan_execution_started" in event_types
    assert event_types.count("plan_wave_started") == 2
    assert event_types.count("plan_wave_finished") == 2
    assert run.events[-1].type == "plan_execution_finished"
    assert run.events[-1].data == {
        "plan": "research-plan-execution",
        "status": "passed",
        "waves": 2,
        "tasks": 2,
        "passed": 2,
        "failed": 0,
    }


def test_workflow_bundle_includes_plan_execution_results(tmp_path: Path) -> None:
    run, plan = configured_run()
    run.provision_execution_plan(plan, LocalProvisioner())
    run.execute_execution_plan(
        plan,
        {
            "searcher": StaticAgent("searcher"),
            "checker": StaticAgent("checker"),
        },
    )

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["plan_execution_results"][0]["plan_name"] == (
        "research-plan-execution"
    )
    assert bundle["plan_execution_results"][0]["status"] == "passed"
    assert bundle["plan_execution_results"][0]["wave_count"] == 2
    assert bundle["plan_execution_results"][0]["waves"][0]["tasks"][0]["name"] == (
        "search"
    )
