from __future__ import annotations

import pytest

from quaestio import (
    ComputeResources,
    EnvironmentSpec,
    ExecutionPlanError,
    TaskGraph,
    TaskSpec,
    build_execution_plan,
)


def environment(name: str = "cpu-worker") -> EnvironmentSpec:
    return EnvironmentSpec(
        name=name,
        resources=ComputeResources(cpu=4, memory_gb=8),
    )


def test_build_execution_plan_orders_dependency_waves() -> None:
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

    plan = build_execution_plan(
        graph,
        agent_environments={"searcher": "cpu-worker", "checker": "cpu-worker"},
        environments=[environment()],
    )

    assert plan.name == "research-plan-execution"
    assert plan.graph_name == "research-plan"
    assert [[task.name for task in wave.tasks] for wave in plan.waves] == [
        ["search"],
        ["verify"],
    ]
    assert plan.task_count == 2
    assert plan.wave_count == 2


def test_build_execution_plan_batches_independent_non_conflicting_tasks() -> None:
    graph = TaskGraph(name="parallel-plan")
    graph.add_task(
        TaskSpec(
            name="alpha",
            agent_name="alpha",
            task="alpha",
            resources=("artifact:alpha",),
        )
    )
    graph.add_task(
        TaskSpec(
            name="beta",
            agent_name="beta",
            task="beta",
            resources=("artifact:beta",),
        )
    )

    plan = build_execution_plan(
        graph,
        agent_environments={"alpha": "cpu-worker", "beta": "cpu-worker"},
        environments=[environment()],
    )

    assert [[task.name for task in wave.tasks] for wave in plan.waves] == [
        ["alpha", "beta"],
    ]


def test_build_execution_plan_splits_resource_conflicts_into_later_waves() -> None:
    graph = TaskGraph(name="conflict-plan")
    graph.add_task(
        TaskSpec(
            name="first",
            agent_name="writer",
            task="first",
            resources=("repo:src",),
        )
    )
    graph.add_task(
        TaskSpec(
            name="second",
            agent_name="checker",
            task="second",
            resources=("repo:src",),
        )
    )

    plan = build_execution_plan(
        graph,
        agent_environments={"writer": "cpu-worker", "checker": "cpu-worker"},
        environments=[environment()],
    )

    assert [[task.name for task in wave.tasks] for wave in plan.waves] == [
        ["first"],
        ["second"],
    ]


def test_build_execution_plan_preserves_multi_level_dependencies() -> None:
    graph = TaskGraph(name="multi-level-plan")
    graph.add_task(TaskSpec(name="search", agent_name="searcher", task="search"))
    graph.add_task(
        TaskSpec(
            name="prove",
            agent_name="prover",
            task="prove",
            depends_on=("search",),
        )
    )
    graph.add_task(
        TaskSpec(
            name="redteam",
            agent_name="critic",
            task="redteam",
            depends_on=("search",),
        )
    )
    graph.add_task(
        TaskSpec(
            name="publish",
            agent_name="writer",
            task="publish",
            depends_on=("prove", "redteam"),
        )
    )

    plan = build_execution_plan(
        graph,
        agent_environments={
            "searcher": "cpu-worker",
            "prover": "cpu-worker",
            "critic": "cpu-worker",
            "writer": "cpu-worker",
        },
        environments=[environment()],
    )

    assert [[task.name for task in wave.tasks] for wave in plan.waves] == [
        ["search"],
        ["prove", "redteam"],
        ["publish"],
    ]


def test_build_execution_plan_requires_agent_environment_placement() -> None:
    graph = TaskGraph(name="missing-placement")
    graph.add_task(TaskSpec(name="search", agent_name="searcher", task="search"))

    with pytest.raises(
        ExecutionPlanError,
        match="agent 'searcher' has no assigned environment",
    ):
        build_execution_plan(
            graph,
            agent_environments={},
            environments=[environment()],
        )


def test_build_execution_plan_rejects_unknown_environment_placement() -> None:
    graph = TaskGraph(name="unknown-placement")
    graph.add_task(TaskSpec(name="search", agent_name="searcher", task="search"))

    with pytest.raises(
        ExecutionPlanError,
        match="agent 'searcher' is assigned to unknown environment 'missing'",
    ):
        build_execution_plan(
            graph,
            agent_environments={"searcher": "missing"},
            environments=[environment()],
        )


def test_execution_plan_serializes_waves_and_tasks() -> None:
    graph = TaskGraph(name="serializable-plan")
    graph.add_task(
        TaskSpec(
            name="search",
            agent_name="searcher",
            task="search",
            resources=("db:candidates",),
            metadata={"kind": "explore"},
        )
    )

    plan = build_execution_plan(
        graph,
        agent_environments={"searcher": "cpu-worker"},
        environments=[environment()],
    )
    bundle = plan.to_dict()

    assert bundle["name"] == "serializable-plan-execution"
    assert bundle["graph_name"] == "serializable-plan"
    assert bundle["wave_count"] == 1
    assert bundle["task_count"] == 1
    assert bundle["environment_names"] == ["cpu-worker"]
    assert bundle["waves"][0]["index"] == 1
    assert bundle["waves"][0]["tasks"][0] == {
        "name": "search",
        "agent_name": "searcher",
        "task": "search",
        "environment": "cpu-worker",
        "depends_on": [],
        "resources": ["db:candidates"],
        "metadata": {"kind": "explore"},
    }
