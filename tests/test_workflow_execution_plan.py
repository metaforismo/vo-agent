from __future__ import annotations

import json
from pathlib import Path

import pytest

from vo import (
    AgentSpec,
    ComputeResources,
    EnvironmentSpec,
    TaskGraph,
    TaskSpec,
    WorkflowRun,
)


def configured_run() -> WorkflowRun:
    run = WorkflowRun(name="planning workflow")
    run.add_agent(AgentSpec(name="searcher", goal="search"))
    run.add_agent(AgentSpec(name="checker", goal="check"))
    run.add_environment(
        EnvironmentSpec(
            name="cpu-worker",
            resources=ComputeResources(cpu=4, memory_gb=8),
        )
    )
    run.assign_agent_environment("searcher", "cpu-worker")
    run.assign_agent_environment("checker", "cpu-worker")
    return run


def graph() -> TaskGraph:
    task_graph = TaskGraph(name="research-plan")
    task_graph.add_task(TaskSpec(name="search", agent_name="searcher", task="search"))
    task_graph.add_task(
        TaskSpec(
            name="verify",
            agent_name="checker",
            task="verify",
            depends_on=("search",),
        )
    )
    return task_graph


def test_workflow_plans_registered_task_graph() -> None:
    run = configured_run()
    task_graph = graph()
    run.add_task_graph(task_graph)

    plan = run.plan_task_graph(task_graph)

    assert run.execution_plans == [plan]
    assert plan.graph_name == "research-plan"
    assert [[task.name for task in wave.tasks] for wave in plan.waves] == [
        ["search"],
        ["verify"],
    ]


def test_workflow_rejects_planning_unregistered_task_graph() -> None:
    run = configured_run()

    with pytest.raises(ValueError, match="task graph does not belong to this workflow run"):
        run.plan_task_graph(graph())


def test_workflow_records_execution_plan_event() -> None:
    run = configured_run()
    task_graph = graph()
    run.add_task_graph(task_graph)

    run.plan_task_graph(task_graph)

    assert run.events[-1].type == "execution_plan_created"
    assert run.events[-1].data == {
        "name": "research-plan-execution",
        "graph": "research-plan",
        "waves": 2,
        "tasks": 2,
    }


def test_workflow_bundle_includes_execution_plans(tmp_path: Path) -> None:
    run = configured_run()
    task_graph = graph()
    run.add_task_graph(task_graph)
    run.plan_task_graph(task_graph)

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["execution_plans"][0]["name"] == "research-plan-execution"
    assert bundle["execution_plans"][0]["graph_name"] == "research-plan"
    assert bundle["execution_plans"][0]["wave_count"] == 2
    assert bundle["execution_plans"][0]["waves"][0]["tasks"][0]["environment"] == (
        "cpu-worker"
    )
