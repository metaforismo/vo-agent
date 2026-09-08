from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from quaestio import AgentRun, AgentSpec, TaskGraph, TaskSpec, WorkflowRun
from quaestio.models import utc_now


class ScriptedAdapter:
    def __init__(self, name: str, exit_codes: Sequence[int] | None = None) -> None:
        self.name = name
        self.exit_codes = list(exit_codes or [0])

    def run(self, task, context=None):
        del context
        now = utc_now()
        exit_code = self.exit_codes.pop(0)
        return AgentRun(
            agent_name=self.name,
            task=task,
            command=["scripted-task"],
            exit_code=exit_code,
            stdout=f"done {task}\n" if exit_code == 0 else "",
            stderr="" if exit_code == 0 else "failed\n",
            duration_s=0.0,
            started_at=now,
            finished_at=now,
        )


def make_run() -> WorkflowRun:
    run = WorkflowRun(name="graph workflow")
    run.add_agent(AgentSpec(name="solver", goal="Solve tasks"))
    run.add_agent(AgentSpec(name="checker", goal="Check tasks"))
    return run


def make_graph() -> TaskGraph:
    graph = TaskGraph(name="research-plan")
    graph.add_task(TaskSpec(name="search", agent_name="solver", task="search"))
    graph.add_task(TaskSpec(name="draft", agent_name="solver", task="draft"))
    graph.add_task(
        TaskSpec(
            name="verify",
            agent_name="checker",
            task="verify",
            depends_on=("search", "draft"),
        )
    )
    return graph


def test_workflow_registers_task_graph() -> None:
    run = make_run()
    graph = make_graph()

    registered = run.add_task_graph(graph)

    assert registered is graph
    assert run.task_graphs == [graph]
    assert run.events[-1].type == "task_graph_added"


def test_workflow_rejects_duplicate_task_graph_names() -> None:
    run = make_run()
    run.add_task_graph(make_graph())

    with pytest.raises(ValueError, match="task graph 'research-plan' already exists"):
        run.add_task_graph(make_graph())


def test_workflow_runs_task_graph_to_completion() -> None:
    run = make_run()
    graph = make_graph()
    run.add_task_graph(graph)

    result = run.run_task_graph(
        graph,
        {
            "solver": ScriptedAdapter("solver", [0, 0]),
            "checker": ScriptedAdapter("checker", [0]),
        },
    )

    assert result is graph
    assert graph.status == "passed"
    assert graph.stop_reason == "all_tasks_passed"
    assert [task.status for task in graph.tasks] == ["passed", "passed", "passed"]
    assert [run.task for run in run.agent_runs] == ["search", "draft", "verify"]


def test_workflow_blocks_dependents_when_task_fails() -> None:
    run = make_run()
    graph = make_graph()
    run.add_task_graph(graph)

    run.run_task_graph(
        graph,
        {
            "solver": ScriptedAdapter("solver", [1, 0]),
            "checker": ScriptedAdapter("checker", [0]),
        },
    )

    assert graph.status == "failed"
    assert graph.stop_reason == "task_failed"
    assert [task.status for task in graph.tasks] == ["failed", "passed", "blocked"]
    assert [run.task for run in run.agent_runs] == ["search", "draft"]


def test_workflow_task_graph_bundle_and_events(tmp_path: Path) -> None:
    run = make_run()
    graph = make_graph()
    run.add_task_graph(graph)
    run.run_task_graph(
        graph,
        {
            "solver": ScriptedAdapter("solver", [0, 0]),
            "checker": ScriptedAdapter("checker", [0]),
        },
    )

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["task_graphs"][0]["name"] == "research-plan"
    assert bundle["task_graphs"][0]["status"] == "passed"
    assert bundle["task_graphs"][0]["tasks"][2]["status"] == "passed"
    event_types = [event["type"] for event in bundle["events"]]
    assert "task_graph_started" in event_types
    assert "task_batch_started" in event_types
    assert "task_started" in event_types
    assert "task_finished" in event_types
    assert "task_graph_finished" in event_types
