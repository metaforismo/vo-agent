from __future__ import annotations

import json
from pathlib import Path

import pytest

from vo import (
    AgentSpec,
    ComputeResources,
    EnvironmentSpec,
    LocalProvisioner,
    TaskGraph,
    TaskSpec,
    WorkflowRun,
)


def configured_run() -> tuple[WorkflowRun, object]:
    run = WorkflowRun(name="provisioning workflow")
    run.add_agent(AgentSpec(name="searcher", goal="search"))
    run.add_environment(
        EnvironmentSpec(
            name="cpu-worker",
            kind="local",
            resources=ComputeResources(cpu=2, memory_gb=4),
        )
    )
    run.assign_agent_environment("searcher", "cpu-worker")
    graph = TaskGraph(name="research-plan")
    graph.add_task(TaskSpec(name="search", agent_name="searcher", task="search"))
    run.add_task_graph(graph)
    plan = run.plan_task_graph(graph)
    return run, plan


def test_workflow_provisions_registered_execution_plan() -> None:
    run, plan = configured_run()

    result = run.provision_execution_plan(plan, LocalProvisioner())

    assert run.provisioning_results == [result]
    assert result.plan_name == "research-plan-execution"
    assert result.status == "ready"
    assert result.environments[0].name == "cpu-worker"


def test_workflow_rejects_provisioning_unregistered_execution_plan() -> None:
    registered_run, plan = configured_run()
    other_run = WorkflowRun(name="other")

    with pytest.raises(
        ValueError,
        match="execution plan does not belong to this workflow run",
    ):
        other_run.provision_execution_plan(plan, LocalProvisioner())

    assert registered_run.provisioning_results == []


def test_workflow_records_provisioning_event() -> None:
    run, plan = configured_run()

    run.provision_execution_plan(plan, LocalProvisioner())

    assert run.events[-1].type == "provisioning_finished"
    assert run.events[-1].data == {
        "plan": "research-plan-execution",
        "provider": "local",
        "status": "ready",
        "environments": 1,
    }


def test_workflow_bundle_includes_provisioning_results(tmp_path: Path) -> None:
    run, plan = configured_run()
    run.provision_execution_plan(plan, LocalProvisioner(metadata={"mode": "dry-run"}))

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["provisioning_results"][0]["plan_name"] == (
        "research-plan-execution"
    )
    assert bundle["provisioning_results"][0]["provider"] == "local"
    assert bundle["provisioning_results"][0]["status"] == "ready"
    assert bundle["provisioning_results"][0]["metadata"] == {"mode": "dry-run"}
    assert bundle["provisioning_results"][0]["environments"][0]["name"] == (
        "cpu-worker"
    )
