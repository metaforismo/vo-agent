# Plan Execution Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add durable plan execution results that record how an execution plan ran wave-by-wave and task-by-task.

**Architecture:** The runtime adds a focused `vo.plan_execution` module with serializable `ExecutedTask`, `ExecutedWave`, and `PlanExecutionResult` records. `WorkflowRun.execute_execution_plan()` executes planned tasks through existing agent adapters, requires a ready provisioning result by default, stops after a failed wave, records events, and exports results in bundles and reports. Execution is local and sequential for now, while preserving the same wave contract future distributed executors can implement concurrently.

**Tech Stack:** Python 3.11+ stdlib dataclasses, existing VO agent adapter, execution-plan, provisioning, workflow, pytest, current `uv` test workflow.

---

## File Structure

- Create: `src/vo/plan_execution.py`
  - Defines `ExecutedTask`, `ExecutedWave`, and `PlanExecutionResult`.
  - Owns validation, aggregate status/counts, and JSON-safe serialization.
- Modify: `src/vo/exceptions.py`
  - Adds `PlanExecutionError` for invalid plan execution attempts.
- Modify: `src/vo/workflow.py`
  - Adds `plan_execution_results`, `execute_execution_plan()`, provisioning readiness checks, bundle export, and execution events.
- Modify: `src/vo/bundles.py`
  - Requires `plan_execution_results` as a top-level bundle list.
- Modify: `src/vo/report.py`
  - Adds execution-result summary and table section.
- Modify: `src/vo/__init__.py`
  - Exports plan execution public API.
- Modify: `README.md`
  - Documents local plan execution as the reference executor.
- Create: `examples/plan_execution.py`
  - Demonstrates plan, provision, execute, bundle, and report.
- Create: `tests/test_plan_execution.py`
  - Tests record validation, aggregate statuses/counts, and serialization.
- Create: `tests/test_workflow_plan_execution.py`
  - Tests workflow execution, provisioning gate, adapter validation, failure stopping, bundle export, and events.
- Modify: `tests/test_bundles.py`
  - Adds required-key validation for `plan_execution_results`.
- Modify: `tests/test_report.py`
  - Tests plan execution visibility in markdown reports.

## Executable Checklist

- [x] Confirm current baseline test suite before editing.
- [x] Inspect current agent run serialization.
- [x] Inspect current execution plan serialization.
- [x] Inspect current provisioning readiness records.
- [x] Inspect current workflow execution helpers.
- [x] Inspect current bundle validator shape.
- [x] Inspect current markdown report structure.
- [x] Write failing test that `ExecutedTask` validates non-empty task name.
- [x] Write failing test that `ExecutedTask.status` follows agent run exit code.
- [x] Write failing test that `ExecutedTask.to_dict()` serializes environment and agent run.
- [x] Write failing test that `ExecutedWave` validates positive index.
- [x] Write failing test that `ExecutedWave.status` is failed when any task failed.
- [x] Write failing test that `PlanExecutionResult` validates non-empty plan name.
- [x] Write failing test that `PlanExecutionResult` aggregates task, passed, failed, and wave counts.
- [x] Write failing test that `PlanExecutionResult.to_dict()` serializes waves and counts.
- [x] Write failing workflow test that `execute_execution_plan()` runs a provisioned plan.
- [x] Write failing workflow test that unregistered plans cannot execute.
- [x] Write failing workflow test that missing adapters are rejected.
- [x] Write failing workflow test that execution requires ready provisioning by default.
- [x] Write failing workflow test that failed tasks stop later waves.
- [x] Write failing workflow test that plan execution records events.
- [x] Write failing workflow test that workflow bundles include plan execution results.
- [x] Write failing bundle validation test requiring `plan_execution_results`.
- [x] Write failing report test that plan execution results appear in summary and table.
- [x] Run focused tests and confirm failures are for missing plan-execution support.
- [x] Implement `PlanExecutionError`.
- [x] Implement `ExecutedTask` validation, status, and serialization.
- [x] Implement `ExecutedWave` validation, status, and serialization.
- [x] Implement `PlanExecutionResult` validation, counts, status, and serialization.
- [x] Export plan-execution APIs from `vo`.
- [x] Add `plan_execution_results` storage to `WorkflowRun`.
- [x] Implement ready provisioning lookup in `WorkflowRun`.
- [x] Implement adapter validation in `WorkflowRun.execute_execution_plan()`.
- [x] Execute each wave sequentially through `WorkflowRun.run_agent()`.
- [x] Preserve planned task environment metadata through existing agent run metadata.
- [x] Stop after a failed wave.
- [x] Record `plan_execution_started` event.
- [x] Record `plan_wave_started` events.
- [x] Record `plan_wave_finished` events.
- [x] Record `plan_execution_finished` event.
- [x] Include `plan_execution_results` in workflow bundles.
- [x] Update bundle validator required keys and list sections.
- [x] Render plan execution count in report summary.
- [x] Render plan execution results in markdown reports.
- [x] Add runnable plan execution example.
- [x] Update README with plan execution usage.
- [x] Run focused plan-execution tests.
- [x] Run report and bundle tests.
- [x] Run the full pytest suite.
- [x] Run all examples end to end.
- [x] Validate generated bundles through the CLI.
- [x] Inspect generated plan-execution bundle through the CLI.
- [x] Run compile checks.
- [x] Run import smoke checks.
- [x] Remove generated Python and pytest cache directories.
- [x] Update this plan with completed checkboxes and verification evidence.

## Verification Commands

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_plan_execution.py tests/test_workflow_plan_execution.py tests/test_bundles.py tests/test_report.py -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/optimize_with_evidence.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/local_agent_runner.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/state_machine_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/iteration_loop.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/review_panel.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/task_graph_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/environment_assignment.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/execution_plan.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/provisioning.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/plan_execution.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run vo validate work/plan-execution-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run vo inspect work/plan-execution-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples
```

## Verification Evidence

- Baseline before this slice: `113 passed in 1.66s`.
- Red phase focused suite failed as intended with missing `ExecutedTask` / `PlanExecutionResult` / `PlanExecutionError` exports.
- Focused plan-execution/workflow/report/bundle suite after implementation: `30 passed in 1.11s`.
- Full pytest suite after implementation: `129 passed in 1.95s`.
- Final post-plan full pytest suite: `129 passed in 13.30s`.
- All examples ran end to end and generated fresh bundles/reports, including `work/plan-execution-bundle.json`.
- CLI validation accepted every generated bundle: environment assignment, toy optimization, execution plan, iteration loop, local agent, plan execution, provisioning, review panel, state machine, and task graph.
- CLI inspection of `work/plan-execution-bundle.json` showed 1 agent, 1 environment, 1 placement, 1 task graph, 1 execution plan, 1 ready provisioning result, 1 passed plan execution result, 1 agent run, and 1 artifact.
- Compile check passed with `python -m compileall -q src tests examples`.
- Import smoke confirmed `ExecutedTask`, `ExecutedWave`, `PlanExecutionResult`, `WorkflowRun`, and serialized plan-execution bundle shape work together.

## Expected Public API Shape

```python
from vo import LocalProvisioner, WorkflowRun

run = WorkflowRun(name="execute-demo")
# add agents, environments, task graph, execution plan, and adapters first
plan = run.plan_task_graph(graph)
run.provision_execution_plan(plan, LocalProvisioner())
result = run.execute_execution_plan(plan, adapters)

assert result.status == "passed"
```

## Self-Review

- Spec coverage: the plan implements durable local execution records, provisioning gating, wave/task serialization, workflow integration, bundle/report/docs/example coverage, and tests.
- Placeholder scan: every checklist item names concrete behavior or a concrete file change.
- Type consistency: public names are consistently `ExecutedTask`, `ExecutedWave`, `PlanExecutionResult`, `PlanExecutionError`, and `WorkflowRun.execute_execution_plan()`.
