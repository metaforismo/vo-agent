# Provisioning Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add provisioning records that capture which execution environments were prepared for an execution plan, by which provisioner, and with what status.

**Architecture:** The runtime adds a focused `vo.provisioning` module with immutable-ish records and a small provisioner protocol. `LocalProvisioner` is a no-op readiness provider for local development and tests; future Docker, SSH, and VM providers can implement the same protocol. `WorkflowRun` stores provisioning results, records events, exports them in bundles, and renders them in markdown reports.

**Tech Stack:** Python 3.11+ stdlib dataclasses and Protocols, existing VO environment and execution-plan models, pytest, current `uv` test workflow.

---

## File Structure

- Create: `src/vo/provisioning.py`
  - Defines `ProvisionedEnvironment`, `ProvisioningResult`, `Provisioner`, and `LocalProvisioner`.
  - Owns environment readiness records, status validation, provider metadata, and JSON-safe serialization.
- Modify: `src/vo/exceptions.py`
  - Adds `ProvisioningError` for invalid provisioning attempts.
- Modify: `src/vo/workflow.py`
  - Adds `provisioning_results`, `provision_execution_plan()`, bundle export, and `provisioning_finished` events.
- Modify: `src/vo/bundles.py`
  - Requires `provisioning_results` as a top-level bundle list.
- Modify: `src/vo/report.py`
  - Adds provisioning result summary and table section.
- Modify: `src/vo/__init__.py`
  - Exports provisioning public API.
- Modify: `README.md`
  - Documents local provisioning records as the provider handoff.
- Create: `examples/provisioning.py`
  - Demonstrates planning and provisioning an execution plan locally.
- Create: `tests/test_provisioning.py`
  - Tests record validation, local provisioner behavior, failure paths, and serialization.
- Create: `tests/test_workflow_provisioning.py`
  - Tests workflow provisioning, bundle export, and events.
- Modify: `tests/test_bundles.py`
  - Adds required-key validation for `provisioning_results`.
- Modify: `tests/test_report.py`
  - Tests provisioning visibility in markdown reports.

## Executable Checklist

- [x] Confirm current baseline test suite before editing.
- [x] Inspect current environment specs.
- [x] Inspect current execution-plan serialization.
- [x] Inspect current workflow serialization.
- [x] Inspect current bundle validator shape.
- [x] Inspect current markdown report structure.
- [x] Write failing test that `ProvisionedEnvironment` validates non-empty environment name.
- [x] Write failing test that `ProvisionedEnvironment` validates status values.
- [x] Write failing test that `ProvisionedEnvironment.to_dict()` serializes provider, status, resources, and metadata.
- [x] Write failing test that `ProvisioningResult` validates non-empty plan name.
- [x] Write failing test that `ProvisioningResult.status` is `ready` when every environment is ready.
- [x] Write failing test that `ProvisioningResult.status` is `failed` when any environment failed.
- [x] Write failing test that `LocalProvisioner` provisions every environment referenced by an execution plan.
- [x] Write failing test that `LocalProvisioner` rejects unknown plan environments.
- [x] Write failing test that `LocalProvisioner` preserves provider metadata.
- [x] Write failing workflow test for `WorkflowRun.provision_execution_plan()`.
- [x] Write failing workflow test that provisioning an unregistered plan is rejected.
- [x] Write failing workflow test that provisioning records an event.
- [x] Write failing workflow test that workflow bundles include provisioning results.
- [x] Write failing bundle validation test requiring `provisioning_results`.
- [x] Write failing report test that provisioning results appear in summary and table.
- [x] Run focused tests and confirm failures are for missing provisioning support.
- [x] Implement `ProvisioningError`.
- [x] Implement `ProvisionedEnvironment` validation and serialization.
- [x] Implement `ProvisioningResult` validation, aggregate status, and serialization.
- [x] Implement `Provisioner` protocol.
- [x] Implement `LocalProvisioner.name`.
- [x] Implement `LocalProvisioner.provision()`.
- [x] Validate execution-plan environments against declared environment specs.
- [x] Serialize resource requests into provisioned environment records.
- [x] Preserve non-secret provider metadata.
- [x] Export provisioning APIs from `vo`.
- [x] Add `provisioning_results` storage to `WorkflowRun`.
- [x] Implement `WorkflowRun.provision_execution_plan()`.
- [x] Record `provisioning_finished` events.
- [x] Include `provisioning_results` in workflow bundles.
- [x] Update bundle validator required keys and list sections.
- [x] Render provisioning count in report summary.
- [x] Render provisioning results in markdown reports.
- [x] Add runnable provisioning example.
- [x] Update README with provisioning usage.
- [x] Run focused provisioning tests.
- [x] Run report and bundle tests.
- [x] Run the full pytest suite.
- [x] Run all examples end to end.
- [x] Validate generated bundles through the CLI.
- [x] Inspect generated provisioning bundle through the CLI.
- [x] Run compile checks.
- [x] Run import smoke checks.
- [x] Remove generated Python and pytest cache directories.
- [x] Update this plan with completed checkboxes and verification evidence.

## Verification Commands

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_provisioning.py tests/test_workflow_provisioning.py tests/test_bundles.py tests/test_report.py -q
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
UV_PROJECT_ENVIRONMENT=work/.venv uv run vo validate work/provisioning-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run vo inspect work/provisioning-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples
```

## Verification Evidence

- Baseline before this slice: `101 passed in 1.55s`.
- Red phase focused suite failed as intended with missing `LocalProvisioner` / provisioning exports.
- Focused provisioning/workflow/report/bundle suite after implementation: `25 passed in 0.46s`.
- Full pytest suite after implementation: `113 passed in 1.48s`.
- Final post-plan full pytest suite: `113 passed in 1.43s`.
- All examples ran end to end and generated fresh bundles/reports, including `work/provisioning-bundle.json`.
- CLI validation accepted every generated bundle: environment assignment, toy optimization, execution plan, iteration loop, local agent, provisioning, review panel, state machine, and task graph.
- CLI inspection of `work/provisioning-bundle.json` showed 1 agent, 1 environment, 1 placement, 1 task graph, 1 execution plan, and 1 ready provisioning result.
- Compile check passed with `python -m compileall -q src tests examples`.
- Import smoke confirmed `LocalProvisioner`, `ProvisionedEnvironment`, `ProvisioningResult`, `WorkflowRun`, and serialized provisioning bundle shape work together.

## Expected Public API Shape

```python
from vo import LocalProvisioner, WorkflowRun

run = WorkflowRun(name="provisioning-demo")
# add agents, environments, task graph, and execution plan first
plan = run.plan_task_graph(graph)
result = run.provision_execution_plan(plan, LocalProvisioner())

assert result.status == "ready"
```

## Self-Review

- Spec coverage: the plan implements provider-agnostic readiness records, local provisioning, workflow integration, bundle/report/docs/example coverage, and tests.
- Placeholder scan: every checklist item names concrete behavior or a concrete file change.
- Type consistency: public names are consistently `ProvisionedEnvironment`, `ProvisioningResult`, `Provisioner`, `LocalProvisioner`, and `WorkflowRun.provision_execution_plan()`.
