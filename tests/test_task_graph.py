from __future__ import annotations

import pytest

from quaestio import TaskGraph, TaskGraphError, TaskSpec
from quaestio.agents import AgentRun
from quaestio.models import utc_now


def agent_run(task: str, *, exit_code: int = 0) -> AgentRun:
    now = utc_now()
    return AgentRun(
        agent_name="agent",
        task=task,
        command=["agent"],
        exit_code=exit_code,
        stdout="ok\n" if exit_code == 0 else "",
        stderr="" if exit_code == 0 else "failed\n",
        duration_s=0.0,
        started_at=now,
        finished_at=now,
    )


def test_task_spec_validates_required_fields() -> None:
    with pytest.raises(ValueError, match="task name must not be empty"):
        TaskSpec(name="", agent_name="solver", task="do work")

    with pytest.raises(ValueError, match="agent_name must not be empty"):
        TaskSpec(name="search", agent_name="", task="do work")

    with pytest.raises(ValueError, match="task must not be empty"):
        TaskSpec(name="search", agent_name="solver", task="")


def test_task_graph_rejects_duplicate_task_names() -> None:
    graph = TaskGraph(name="research-plan")
    graph.add_task(TaskSpec(name="search", agent_name="solver", task="search"))

    with pytest.raises(ValueError, match="task 'search' already exists"):
        graph.add_task(TaskSpec(name="search", agent_name="solver", task="again"))


def test_task_graph_validate_rejects_missing_dependency() -> None:
    graph = TaskGraph(name="research-plan")
    graph.add_task(
        TaskSpec(
            name="verify",
            agent_name="checker",
            task="verify",
            depends_on=("search",),
        )
    )

    with pytest.raises(TaskGraphError, match="missing dependency 'search'"):
        graph.validate()


def test_task_graph_validate_rejects_cycles() -> None:
    graph = TaskGraph(name="research-plan")
    graph.add_task(
        TaskSpec(name="a", agent_name="solver", task="a", depends_on=("b",))
    )
    graph.add_task(
        TaskSpec(name="b", agent_name="solver", task="b", depends_on=("a",))
    )

    with pytest.raises(TaskGraphError, match="cycle detected"):
        graph.validate()


def test_ready_tasks_follow_dependency_status() -> None:
    graph = TaskGraph(name="research-plan")
    graph.add_task(TaskSpec(name="search", agent_name="solver", task="search"))
    graph.add_task(
        TaskSpec(
            name="verify",
            agent_name="checker",
            task="verify",
            depends_on=("search",),
        )
    )

    assert [task.name for task in graph.ready_tasks()] == ["search"]
    graph.record_agent_run("search", agent_run("search"))

    assert [task.name for task in graph.ready_tasks()] == ["verify"]


def test_resource_safe_batches_separate_conflicting_ready_tasks() -> None:
    graph = TaskGraph(name="research-plan")
    graph.add_task(
        TaskSpec(
            name="write-a",
            agent_name="writer",
            task="write a",
            resources=("file:shared",),
        )
    )
    graph.add_task(
        TaskSpec(
            name="write-b",
            agent_name="writer",
            task="write b",
            resources=("file:shared",),
        )
    )
    graph.add_task(TaskSpec(name="read-c", agent_name="reader", task="read c"))

    batches = graph.ready_batches()

    assert [[task.name for task in batch] for batch in batches] == [
        ["write-a", "read-c"],
        ["write-b"],
    ]


def test_task_graph_serializes_status_and_batches() -> None:
    graph = TaskGraph(name="research-plan")
    graph.add_task(TaskSpec(name="search", agent_name="solver", task="search"))

    bundle = graph.to_dict()

    assert bundle["name"] == "research-plan"
    assert bundle["status"] == "pending"
    assert bundle["tasks"][0]["name"] == "search"
    assert bundle["ready_batches"] == [["search"]]
