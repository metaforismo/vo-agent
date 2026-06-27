# Environment Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add explicit execution environment specs and agent placements as the declarative boundary for future VM provisioning.

**Architecture:** The runtime adds a focused `vo.environments` module for compute resources and environment specs. `WorkflowRun` registers environment specs, assigns agents to environments, includes placement metadata on local agent runs, and exports all placement state in bundles and reports without leaking secret values.

**Tech Stack:** Python 3.11+ stdlib dataclasses, existing VO workflow and agent models, pytest, current `uv` test workflow.

---

## File Structure

- Create: `src/vo/environments.py`
  - Defines `ComputeResources` and `EnvironmentSpec`.
  - Owns validation, JSON-safe serialization, and secret-name-only handling.
- Modify: `src/vo/workflow.py`
  - Adds `environments`, `agent_environments`, `add_environment()`, and `assign_agent_environment()`.
  - Adds assigned environment metadata to `AgentRun` records.
- Modify: `src/vo/bundles.py`
  - Requires `environments` and `agent_environments` as top-level bundle sections.
- Modify: `src/vo/report.py`
  - Adds environment and placement summary/table sections.
- Modify: `src/vo/__init__.py`
  - Exports environment public API.
- Modify: `README.md`
  - Documents environment specs and local placement metadata.
- Create: `examples/environment_assignment.py`
  - Demonstrates two agent specs assigned to different declarative environments.
- Create: `tests/test_environments.py`
  - Tests resource validation, environment validation, and safe serialization.
- Create: `tests/test_workflow_environments.py`
  - Tests workflow registration, assignment, run metadata, events, and bundles.
- Modify: `tests/test_bundles.py`
  - Updates required-key expectations for `environments` and `agent_environments`.
- Modify: `tests/test_report.py`
  - Tests environment and placement visibility in reports.

## Executable Checklist

- [x] Confirm current baseline test suite before editing.
- [x] Inspect current workflow serialization.
- [x] Inspect current agent run metadata behavior.
- [x] Inspect current bundle validator shape.
- [x] Inspect current report rendering.
- [x] Write failing test that `ComputeResources` rejects non-positive CPU.
- [x] Write failing test that `ComputeResources` rejects non-positive memory.
- [x] Write failing test that `ComputeResources` rejects negative GPU count.
- [x] Write failing test that `EnvironmentSpec` validates name.
- [x] Write failing test that `EnvironmentSpec` validates kind.
- [x] Write failing test that setup commands serialize as lists.
- [x] Write failing test that env values serialize.
- [x] Write failing test that secret names serialize without secret values.
- [x] Write failing workflow test for registering an environment.
- [x] Write failing workflow test for duplicate environment names.
- [x] Write failing workflow test for assigning an agent to an environment.
- [x] Write failing workflow test that unknown agents cannot be assigned.
- [x] Write failing workflow test that unknown environments cannot be assigned.
- [x] Write failing workflow test that `run_agent()` records environment metadata.
- [x] Write failing workflow test that bundles include environments and placements.
- [x] Write failing workflow test that placement events are recorded.
- [x] Write failing bundle validation test requiring `environments`.
- [x] Write failing bundle validation test requiring `agent_environments`.
- [x] Write failing report test that environments and placements appear in markdown output.
- [x] Run focused tests and confirm failures are for missing environment support.
- [x] Implement `ComputeResources` validation and serialization.
- [x] Implement `EnvironmentSpec` validation and serialization.
- [x] Add environment storage to `WorkflowRun`.
- [x] Add agent environment placement mapping to `WorkflowRun`.
- [x] Implement `WorkflowRun.add_environment()`.
- [x] Implement `WorkflowRun.assign_agent_environment()`.
- [x] Record `environment_added` events.
- [x] Record `agent_environment_assigned` events.
- [x] Annotate agent run metadata with assigned environment.
- [x] Include `environments` in workflow bundles.
- [x] Include `agent_environments` in workflow bundles.
- [x] Update bundle validator required keys.
- [x] Export environment APIs from `vo`.
- [x] Render environments in markdown reports.
- [x] Render agent placements in markdown reports.
- [x] Add a runnable environment assignment example.
- [x] Update README with environment usage.
- [x] Run focused environment tests.
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
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_environments.py tests/test_workflow_environments.py tests/test_bundles.py tests/test_report.py -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/optimize_with_evidence.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/local_agent_runner.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/state_machine_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/iteration_loop.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/review_panel.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/task_graph_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/environment_assignment.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run vo validate work/environment-assignment-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run vo inspect work/environment-assignment-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples
```

## Verification Evidence

- Baseline before this slice: `77 passed in 1.51s`.
- Red phase focused suite failed as intended with missing `ComputeResources` / `EnvironmentSpec` imports.
- Focused environment/report/bundle suite after implementation: `22 passed in 0.48s`.
- Full pytest suite after implementation: `89 passed in 1.35s`.
- Final post-cleanup full pytest suite: `89 passed in 2.27s`.
- All examples ran end to end and generated fresh bundles/reports, including `work/environment-assignment-bundle.json`.
- CLI validation accepted every generated bundle: environment assignment, toy optimization, iteration loop, local agent, review panel, state machine, and task graph.
- CLI inspection of `work/environment-assignment-bundle.json` showed 2 environments, 1 placement, 1 agent run, and 1 artifact.
- Compile check passed with `python -m compileall -q src tests examples`.
- Import smoke confirmed `ComputeResources`, `EnvironmentSpec`, `WorkflowRun`, and report rendering work together, and the raw bundle does not contain a fake secret value.

## Expected Public API Shape

```python
from vo import ComputeResources, EnvironmentSpec, WorkflowRun

env = EnvironmentSpec(
    name="gpu-worker",
    kind="vm",
    image="ubuntu:24.04",
    resources=ComputeResources(cpu=8, memory_gb=32, gpu_count=1),
    setup_commands=("uv sync",),
    env={"PYTHONUNBUFFERED": "1"},
    secret_names=("OPENAI_API_KEY",),
)

run = WorkflowRun(name="placement-demo")
run.add_environment(env)
run.assign_agent_environment("solver", "gpu-worker")
```

## Self-Review

- Spec coverage: the plan implements the infrastructure boundary for VM/sandbox provisioning with explicit resources, setup commands, env vars, secret names, agent placement, bundles, reports, docs, examples, and tests.
- Placeholder scan: every checklist item names concrete behavior or a concrete file change.
- Type consistency: public names are consistently `ComputeResources`, `EnvironmentSpec`, `add_environment()`, and `assign_agent_environment()`.
