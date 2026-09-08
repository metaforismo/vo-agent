# Task Graph Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit task dependency graphs so agent work can be scheduled in deterministic, resource-safe parallel waves.

**Architecture:** The runtime adds a focused `quaestio.task_graph` module for task specs, dependency validation, cycle detection, ready-task calculation, and resource-safe batching. `WorkflowRun.run_task_graph()` composes registered agents, local adapters, task status updates, events, bundles, and reports while preserving the dependency graph for future cloud scheduling.

**Tech Stack:** Python 3.11+ stdlib dataclasses, existing VO agent/workflow/resource models, pytest, current `uv` test workflow.

---

## File Structure

- Create: `src/quaestio/task_graph.py`
  - Defines `TaskSpec`, `TaskGraph`, and `TaskGraphError`.
  - Owns validation, cycle detection, status transitions, ready tasks, resource-safe batches, and serialization.
- Modify: `src/quaestio/workflow.py`
  - Adds `task_graphs`, `add_task_graph()`, and `run_task_graph()`.
  - Records graph lifecycle events and appends task agent runs.
- Modify: `src/quaestio/bundles.py`
  - Requires `task_graphs` as a top-level bundle list.
- Modify: `src/quaestio/report.py`
  - Adds task graph count and markdown table.
- Modify: `src/quaestio/__init__.py`
  - Exports task graph public API.
- Modify: `src/quaestio/exceptions.py`
  - Adds `TaskGraphError`.
- Modify: `README.md`
  - Documents dependency graphs and resource-safe batches.
- Create: `examples/task_graph_workflow.py`
  - Demonstrates two independent tasks feeding one dependent integration task.
- Create: `tests/test_task_graph.py`
  - Tests validation, ready tasks, cycles, batches, and serialization.
- Create: `tests/test_workflow_task_graph.py`
  - Tests workflow integration, events, failure blocking, and bundle serialization.
- Modify: `tests/test_bundles.py`
  - Updates required-key expectations for `task_graphs`.
- Modify: `tests/test_report.py`
  - Tests task graph visibility in reports.

## Executable Checklist

- [x] Confirm current baseline test suite before editing.
- [x] Inspect current workflow serialization.
- [x] Inspect current bundle validator shape.
- [x] Inspect current report rendering.
- [x] Write failing test that `TaskSpec` validates required fields.
- [x] Write failing test that `TaskGraph` rejects duplicate task names.
- [x] Write failing test that `TaskGraph.validate()` rejects missing dependencies.
- [x] Write failing test that `TaskGraph.validate()` rejects cycles.
- [x] Write failing test that `TaskGraph.ready_tasks()` returns dependency-free tasks.
- [x] Write failing test that completed dependencies unlock dependent tasks.
- [x] Write failing test that resource-safe batches separate ready tasks sharing resources.
- [x] Write failing test that `TaskGraph.to_dict()` serializes tasks and batches.
- [x] Write failing workflow test for registering a task graph.
- [x] Write failing workflow test for duplicate task graph names.
- [x] Write failing workflow test that running a graph executes all tasks in dependency order.
- [x] Write failing workflow test that failed tasks block dependents.
- [x] Write failing workflow test that graph lifecycle events are recorded.
- [x] Write failing bundle validation test requiring `task_graphs`.
- [x] Write failing report test that task graphs appear in markdown output.
- [x] Run focused tests and confirm failures are for missing task graph support.
- [x] Implement `TaskGraphError`.
- [x] Implement `TaskSpec` validation and serialization.
- [x] Implement `TaskGraph.add_task()`.
- [x] Implement dependency existence validation.
- [x] Implement cycle detection.
- [x] Implement task lookup.
- [x] Implement ready task calculation.
- [x] Implement resource-safe batching.
- [x] Implement task status transitions.
- [x] Implement blocked-dependent marking.
- [x] Implement `TaskGraph.to_dict()`.
- [x] Add task graph storage to `WorkflowRun`.
- [x] Implement `WorkflowRun.add_task_graph()`.
- [x] Implement `WorkflowRun.run_task_graph()`.
- [x] Record `task_graph_started` events.
- [x] Record `task_batch_started` events.
- [x] Record `task_started` events.
- [x] Record `task_finished` events.
- [x] Record `task_graph_finished` events.
- [x] Include `task_graphs` in workflow bundles.
- [x] Update bundle validator required keys.
- [x] Export task graph APIs from `quaestio`.
- [x] Render task graphs in markdown reports.
- [x] Add a runnable task-graph example.
- [x] Update README with task-graph usage.
- [x] Run focused task graph tests.
- [x] Run report and bundle tests.
- [x] Run the full pytest suite.
- [x] Run all examples end to end.
- [x] Validate generated bundles through the CLI.
- [x] Inspect generated bundles through the CLI.
- [x] Run compile checks.
- [x] Run import smoke checks.
- [x] Remove generated Python and pytest cache directories.
- [x] Update this plan with completed checkboxes and verification evidence.

## Verification Commands

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_task_graph.py tests/test_workflow_task_graph.py tests/test_bundles.py tests/test_report.py -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/optimize_with_evidence.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/local_agent_runner.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/state_machine_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/iteration_loop.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/review_panel.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/task_graph_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run quaestio validate work/task-graph-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run quaestio inspect work/task-graph-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples
```

## Verification Results

- Baseline before the slice: `64 passed in 1.01s`.
- Red phase: focused task graph tests failed during collection because `TaskGraph` was not exported yet.
- Focused task-graph/report/bundle tests: `22 passed in 0.81s`.
- Full test suite after implementation: `77 passed in 1.16s`.
- End-to-end example check initially caught a task-graph example cwd bug: `combined.txt` was written outside `work/`.
- Fixed the example by passing `VerificationContext(cwd=work)` into `run_task_graph()`.
- Fresh full test suite after the example fix: `77 passed in 1.18s`.
- `examples/optimize_with_evidence.py` generated `work/example-run-bundle.json` and `work/example-run-report.md`.
- `examples/local_agent_runner.py` generated `work/local-agent-bundle.json` and `work/local-agent-report.md`.
- `examples/state_machine_workflow.py` generated `work/state-machine-bundle.json` and `work/state-machine-report.md`.
- `examples/iteration_loop.py` generated `work/iteration-loop-bundle.json` and `work/iteration-loop-report.md`.
- `examples/review_panel.py` generated `work/review-panel-bundle.json` and `work/review-panel-report.md`.
- `examples/task_graph_workflow.py` generated `work/task-graph-bundle.json` and `work/task-graph-report.md`.
- CLI validation accepted `toy-optimization`, `local-agent-demo`, `state-machine-demo`, `iteration-loop-demo`, `review-panel-demo`, and `task-graph-demo`.
- CLI inspection showed `artifact-plan` with status `passed`, `3` passed tasks, `0` failed tasks, and `0` blocked tasks.
- Compile check passed with `python -m compileall -q src tests examples`.
- Import and JSON smoke check passed, including assertions for passed task graph status, passed count, and relative artifact path `combined.txt`.

## Expected Public API Shape

```python
from quaestio import TaskGraph, TaskSpec, WorkflowRun

graph = TaskGraph(name="research-plan")
graph.add_task(TaskSpec(name="search", agent_name="solver", task="Find candidates."))
graph.add_task(
    TaskSpec(
        name="verify",
        agent_name="checker",
        task="Verify candidates.",
        depends_on=("search",),
    )
)

run = WorkflowRun(name="task-graph-demo")
run.add_task_graph(graph)
run.run_task_graph(graph, {"solver": solver_agent, "checker": checker_agent})
```

## Self-Review

- Spec coverage: the plan implements explicit dependencies, resource-safe parallel batches, workflow execution, events, bundles, reports, docs, examples, and tests.
- Placeholder scan: every checklist item names concrete behavior or a concrete file change.
- Type consistency: public names are consistently `TaskSpec`, `TaskGraph`, `TaskGraphError`, and `run_task_graph()`.
