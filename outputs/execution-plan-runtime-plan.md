# Execution Plan Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add deterministic execution plans that turn task graphs and environment placements into serializable waves for future VM/container provisioning.

**Architecture:** The runtime adds a focused `vo.execution_plan` module that builds read-only plans from `TaskGraph`, `EnvironmentSpec`, and `agent_environments`. `WorkflowRun` stores generated plans, records planning events, exports plans in bundles, and renders them in reports. The planner does not execute work; it makes parallelism, resource conflicts, dependencies, and placement failures explicit before any agent runs.

**Tech Stack:** Python 3.11+ stdlib dataclasses, existing VO task graph and environment models, pytest, current `uv` test workflow.

---

## File Structure

- Create: `src/vo/execution_plan.py`
  - Defines `PlannedTask`, `ExecutionWave`, `ExecutionPlan`, and `build_execution_plan()`.
  - Owns deterministic topological wave planning, resource-conflict splitting, placement validation, and JSON-safe serialization.
- Modify: `src/vo/exceptions.py`
  - Adds `ExecutionPlanError` for invalid plan construction.
- Modify: `src/vo/workflow.py`
  - Adds `execution_plans`, `plan_task_graph()`, bundle export, and `execution_plan_created` events.
- Modify: `src/vo/bundles.py`
  - Requires `execution_plans` as a top-level bundle list.
- Modify: `src/vo/report.py`
  - Adds execution plan summary and plan table section.
- Modify: `src/vo/__init__.py`
  - Exports execution-plan public API.
- Modify: `README.md`
  - Documents execution planning as the provisioning handoff.
- Create: `examples/execution_plan.py`
  - Demonstrates planning a dependency graph across two environments.
- Create: `tests/test_execution_plan.py`
  - Tests deterministic wave planning, resource conflict splitting, placement validation, and serialization.
- Create: `tests/test_workflow_execution_plan.py`
  - Tests workflow plan registration, bundle export, and events.
- Modify: `tests/test_bundles.py`
  - Adds required-key validation for `execution_plans`.
- Modify: `tests/test_report.py`
  - Tests execution plan visibility in markdown reports.

## Executable Checklist

- [x] Confirm current baseline test suite before editing.
- [x] Inspect current task graph scheduling behavior.
- [x] Inspect current environment placement behavior.
- [x] Inspect current workflow serialization shape.
- [x] Inspect current bundle validator shape.
- [x] Inspect current markdown report structure.
- [x] Write failing test that a simple dependency graph becomes ordered waves.
- [x] Write failing test that independent non-conflicting tasks share a wave.
- [x] Write failing test that independent tasks sharing a resource split across waves.
- [x] Write failing test that dependency order is preserved across multiple levels.
- [x] Write failing test that missing agent environment placement raises `ExecutionPlanError`.
- [x] Write failing test that unknown environment placement raises `ExecutionPlanError`.
- [x] Write failing test that `ExecutionPlan.to_dict()` serializes waves and tasks.
- [x] Write failing workflow test for `WorkflowRun.plan_task_graph()`.
- [x] Write failing workflow test that planning an unregistered graph is rejected.
- [x] Write failing workflow test that plan creation records an event.
- [x] Write failing workflow test that workflow bundles include execution plans.
- [x] Write failing bundle validation test requiring `execution_plans`.
- [x] Write failing report test that execution plans appear in summary and table.
- [x] Run focused tests and confirm failures are for missing execution-plan support.
- [x] Implement `ExecutionPlanError`.
- [x] Implement `PlannedTask`.
- [x] Implement `ExecutionWave`.
- [x] Implement `ExecutionPlan`.
- [x] Implement deterministic planning helper for dependency-ready tasks.
- [x] Implement resource-disjoint wave batching.
- [x] Implement placement lookup from agent to environment.
- [x] Implement unknown placement validation.
- [x] Implement `build_execution_plan()`.
- [x] Export execution-plan APIs from `vo`.
- [x] Add `execution_plans` storage to `WorkflowRun`.
- [x] Implement `WorkflowRun.plan_task_graph()`.
- [x] Record `execution_plan_created` events.
- [x] Include `execution_plans` in workflow bundles.
- [x] Update bundle validator required keys and list sections.
- [x] Render execution plan count in report summary.
- [x] Render execution plan table in markdown reports.
- [x] Add runnable execution plan example.
- [x] Update README with execution planning usage.
- [x] Run focused execution-plan tests.
- [x] Run report and bundle tests.
- [x] Run the full pytest suite.
- [x] Run all examples end to end.
- [x] Validate generated bundles through the CLI.
- [x] Inspect generated execution-plan bundle through the CLI.
- [x] Run compile checks.
- [x] Run import smoke checks.
- [x] Remove generated Python and pytest cache directories.
- [x] Update this plan with completed checkboxes and verification evidence.

## Verification Commands

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_execution_plan.py tests/test_workflow_execution_plan.py tests/test_bundles.py tests/test_report.py -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/optimize_with_evidence.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/local_agent_runner.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/state_machine_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/iteration_loop.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/review_panel.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/task_graph_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/environment_assignment.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/execution_plan.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run vo validate work/execution-plan-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run vo inspect work/execution-plan-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples
```

## Verification Evidence

- Baseline before this slice: `89 passed in 1.45s`.
- Red phase focused suite failed as intended with missing `ExecutionPlanError` / execution-plan exports.
- Focused execution-plan/workflow/report/bundle suite after implementation: `24 passed in 0.52s`.
- Full pytest suite after implementation: `101 passed in 2.00s`.
- Final post-doc full pytest suite: `101 passed in 1.52s`.
- All examples ran end to end and generated fresh bundles/reports, including `work/execution-plan-bundle.json`.
- CLI validation accepted every generated bundle: environment assignment, toy optimization, execution plan, iteration loop, local agent, review panel, state machine, and task graph.
- CLI inspection of `work/execution-plan-bundle.json` showed 4 agents, 2 environments, 4 placements, 1 task graph, 1 execution plan, 3 waves, and 4 planned tasks.
- Compile check passed with `python -m compileall -q src tests examples`.
- Import smoke confirmed `ExecutionPlan`, `ExecutionWave`, `PlannedTask`, `WorkflowRun`, `build_execution_plan()`, and serialized execution-plan bundle shape work together.

## Expected Public API Shape

```python
from vo import (
    AgentSpec,
    ComputeResources,
    EnvironmentSpec,
    TaskGraph,
    TaskSpec,
    WorkflowRun,
)

run = WorkflowRun(name="planning-demo")
run.add_agent(AgentSpec(name="searcher", goal="Find candidates"))
run.add_agent(AgentSpec(name="checker", goal="Verify candidates"))
run.add_environment(
    EnvironmentSpec(
        name="cpu-worker",
        resources=ComputeResources(cpu=4, memory_gb=8),
    )
)
run.assign_agent_environment("searcher", "cpu-worker")
run.assign_agent_environment("checker", "cpu-worker")

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
```

## Self-Review

- Spec coverage: the plan implements deterministic schedule generation, resource-aware waves, environment placement validation, workflow integration, bundle/report/docs/example coverage, and tests.
- Placeholder scan: every checklist item names concrete behavior or a concrete file change.
- Type consistency: public names are consistently `PlannedTask`, `ExecutionWave`, `ExecutionPlan`, `build_execution_plan()`, and `WorkflowRun.plan_task_graph()`.
