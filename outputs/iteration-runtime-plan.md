# Iteration Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class runtime primitive for forcing agents to iterate against verification until they pass or exhaust explicit limits.

**Architecture:** The runtime adds a focused `vo.iterations` module with an `IterationPolicy`, serializable attempt records, and an `IterationLoop` object. `WorkflowRun.iterate_until_verified()` composes existing agent adapters, verifier chains, claims, budgets, and event recording so iteration is reproducible and inspectable in bundles and reports.

**Tech Stack:** Python 3.11+ stdlib dataclasses, existing VO agent/verifier/workflow models, pytest, current `uv` test workflow.

---

## File Structure

- Create: `src/vo/iterations.py`
  - Defines `IterationPolicy`, `IterationAttempt`, and `IterationLoop`.
  - Owns validation, attempt serialization, loop status, and stop reasons.
- Modify: `src/vo/workflow.py`
  - Adds `iteration_loops`, `add_iteration_loop()`, and `iterate_until_verified()`.
  - Records iteration lifecycle events and exports loops in bundles.
- Modify: `src/vo/bundles.py`
  - Requires `iteration_loops` as a top-level bundle list.
- Modify: `src/vo/report.py`
  - Adds an iteration-loop summary line and table.
- Modify: `src/vo/__init__.py`
  - Exports iteration public API.
- Modify: `README.md`
  - Documents verification-driven iteration.
- Create: `examples/iteration_loop.py`
  - Demonstrates an agent improving output until a hard command verifier passes.
- Create: `tests/test_iterations.py`
  - Tests pure policy and loop record behavior through workflow execution.
- Create: `tests/test_workflow_iterations.py`
  - Tests workflow integration, bundle serialization, and event records.
- Modify: `tests/test_bundles.py`
  - Updates required-key expectations for `iteration_loops`.
- Modify: `tests/test_report.py`
  - Tests report visibility for iteration loops.

## Executable Checklist

- [x] Confirm current baseline test suite before editing.
- [x] Inspect current agent adapter serialization.
- [x] Inspect current verifier chain result serialization.
- [x] Inspect current workflow bundle serialization.
- [x] Inspect current report and bundle validation shapes.
- [x] Write failing test that `IterationPolicy` rejects `max_attempts < 1`.
- [x] Write failing test that `IterationPolicy` rejects negative per-attempt budget cost.
- [x] Write failing test that a loop stops when verification passes on a later attempt.
- [x] Write failing test that a loop records rejected claims for failed verification attempts.
- [x] Write failing test that a loop stops after `max_attempts`.
- [x] Write failing test that per-attempt budget spending is recorded.
- [x] Write failing test that a failed agent run is recorded without creating a verification claim.
- [x] Write failing test that a loop can recover after an agent failure on a later attempt.
- [x] Write failing workflow test for registering an iteration loop.
- [x] Write failing workflow test for duplicate loop names.
- [x] Write failing workflow test that bundles include iteration loop history.
- [x] Write failing workflow test that iteration lifecycle events are recorded.
- [x] Write failing bundle validation test requiring `iteration_loops`.
- [x] Write failing report test that iteration loops appear in markdown output.
- [x] Run focused tests and confirm failures are for missing iteration runtime support.
- [x] Implement `IterationPolicy` validation.
- [x] Implement `IterationAttempt` serialization.
- [x] Implement `IterationLoop` validation.
- [x] Implement `IterationLoop.record_attempt()`.
- [x] Implement `IterationLoop.to_dict()`.
- [x] Add iteration loop storage to `WorkflowRun`.
- [x] Implement `WorkflowRun.add_iteration_loop()`.
- [x] Implement `WorkflowRun.iterate_until_verified()`.
- [x] Record `iteration_started` events.
- [x] Record `iteration_attempt_started` events.
- [x] Record `iteration_attempt_finished` events.
- [x] Record `iteration_finished` events.
- [x] Spend budget per attempt when configured.
- [x] Create one verification claim per successful agent attempt.
- [x] Skip verification when the agent run fails.
- [x] Stop immediately when verification passes.
- [x] Mark loops failed when attempts are exhausted.
- [x] Include `iteration_loops` in workflow bundles.
- [x] Update bundle validator required keys.
- [x] Export iteration APIs from `vo`.
- [x] Render iteration loops in markdown reports.
- [x] Add a runnable iteration-loop example.
- [x] Update README with iteration-loop usage.
- [x] Run focused iteration tests.
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
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_iterations.py tests/test_workflow_iterations.py tests/test_bundles.py tests/test_report.py -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/optimize_with_evidence.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/local_agent_runner.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/state_machine_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/iteration_loop.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run vo validate work/iteration-loop-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run vo inspect work/iteration-loop-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples
```

## Verification Results

- Baseline before the slice: `36 passed in 5.91s`.
- Red phase: focused iteration tests failed during collection because `IterationLoop` was not exported yet.
- Focused iteration/report/bundle tests: `19 passed in 0.55s`.
- Full test suite after implementation: `48 passed in 0.97s`.
- Fresh full test suite after example/docs polish: `48 passed in 5.08s`.
- `examples/optimize_with_evidence.py` generated `work/example-run-bundle.json` and `work/example-run-report.md`.
- `examples/local_agent_runner.py` generated `work/local-agent-bundle.json` and `work/local-agent-report.md`.
- `examples/state_machine_workflow.py` generated `work/state-machine-bundle.json` and `work/state-machine-report.md`.
- `examples/iteration_loop.py` generated `work/iteration-loop-bundle.json` and `work/iteration-loop-report.md`.
- CLI validation accepted `toy-optimization`, `local-agent-demo`, `state-machine-demo`, and `iteration-loop-demo`.
- CLI inspection showed `hard-test-loop` with status `passed`, `2` attempts, and stop reason `verification_passed`.
- Compile check passed with `python -m compileall -q src tests examples`.
- Import and JSON smoke check passed, including assertions for failed first verification and passed second verification.

## Expected Public API Shape

```python
from vo import IterationLoop, IterationPolicy, WorkflowRun

loop = IterationLoop(
    name="hard-test-loop",
    agent_name="solver",
    task="Make the test pass.",
    policy=IterationPolicy(max_attempts=3, budget_per_attempt=0.25),
)

run = WorkflowRun(name="loop-demo")
run.add_iteration_loop(loop)
run.iterate_until_verified(loop, agent_adapter, verifier_chain)
```

## Self-Review

- Spec coverage: the plan implements the “iterate against hard tests until it passes” product example with explicit limits, evidence, budgets, events, bundles, reports, docs, examples, and tests.
- Placeholder scan: every checklist item names an observable behavior or concrete file change.
- Type consistency: public names are consistently `IterationPolicy`, `IterationAttempt`, `IterationLoop`, and `iterate_until_verified()`.
