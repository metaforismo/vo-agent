# State Machine Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit Python state-machine layer for predictable agent workflow control flow.

**Architecture:** The runtime adds a focused `quaestio.state_machine` module with serializable transition specs, dispatch records, guards, and handlers. `WorkflowRun` owns zero or more machines, records machine dispatches as workflow events, and exports machine state in bundles so reports and CLIs can inspect deterministic progress.

**Tech Stack:** Python 3.11+ stdlib dataclasses, existing VO workflow models, pytest, current `uv` test workflow.

---

## File Structure

- Create: `src/quaestio/state_machine.py`
  - Defines `MachineEvent`, `Transition`, `DispatchRecord`, `StateMachineContext`, and `StateMachine`.
  - Owns dispatch semantics, guard evaluation, handler execution, error capture, and serialization.
- Modify: `src/quaestio/workflow.py`
  - Adds `state_machines`, `add_state_machine()`, `dispatch()`, and bundle serialization.
- Modify: `src/quaestio/report.py`
  - Adds a state-machine section to markdown reports.
- Modify: `src/quaestio/bundles.py`
  - Requires the `state_machines` top-level bundle key and validates that it is a list.
- Modify: `src/quaestio/__init__.py`
  - Exports the state-machine public API.
- Modify: `src/quaestio/exceptions.py`
  - Adds `StateMachineError`.
- Modify: `README.md`
  - Documents state-machine use in the local-first runtime.
- Create: `examples/state_machine_workflow.py`
  - Demonstrates propose → verify → accepted/retry branching.
- Create: `tests/test_state_machine.py`
  - Tests pure state-machine behavior.
- Create: `tests/test_workflow_state_machine.py`
  - Tests workflow integration and serialization.
- Modify: `tests/test_report.py`
  - Tests report visibility for state machines.
- Modify: `tests/test_bundles.py`
  - Updates bundle validation expectations for the new key.

## Executable Checklist

- [x] Inspect current workflow serialization before editing.
- [x] Inspect current bundle validation behavior before editing.
- [x] Inspect current report rendering before editing.
- [x] Run baseline tests before the new slice.
- [x] Write failing pure dispatch test for a declared transition.
- [x] Write failing test that unknown events are rejected.
- [x] Write failing test that duplicate transitions are rejected.
- [x] Write failing test that no matching transition raises a state-machine error.
- [x] Write failing test that guards can block one transition and allow another.
- [x] Write failing test that guard exceptions become failed dispatch records.
- [x] Write failing test that handlers can mutate machine data.
- [x] Write failing test that handler-returned dicts merge into machine data.
- [x] Write failing test that handlers can emit workflow-style event data.
- [x] Write failing test that handler exceptions are captured without advancing state.
- [x] Write failing workflow test for registering a machine.
- [x] Write failing workflow test for dispatching a registered machine.
- [x] Write failing workflow test that bundles include serialized machine state.
- [x] Write failing workflow test that dispatches record workflow events.
- [x] Write failing bundle validation test requiring `state_machines`.
- [x] Write failing report test that state machines appear in markdown output.
- [x] Run the new tests and confirm failures are for missing state-machine support.
- [x] Implement `StateMachineError`.
- [x] Implement `MachineEvent` with JSON-safe serialization.
- [x] Implement `Transition` validation.
- [x] Implement `DispatchRecord` serialization.
- [x] Implement `StateMachineContext` for handler and guard calls.
- [x] Implement `StateMachine.on()` with duplicate protection.
- [x] Implement `StateMachine.dispatch()` for single deterministic transition selection.
- [x] Implement guard evaluation.
- [x] Implement handler execution.
- [x] Implement handler dict result merging.
- [x] Implement emitted event capture.
- [x] Implement error dispatch records that do not advance state.
- [x] Implement `StateMachine.to_dict()`.
- [x] Integrate machines into `WorkflowRun`.
- [x] Add workflow-level dispatch events.
- [x] Add `state_machines` to bundle serialization.
- [x] Update bundle validator required keys.
- [x] Export the new public API.
- [x] Render state machines in markdown reports.
- [x] Add a runnable state-machine example.
- [x] Update README with state-machine usage.
- [x] Run focused state-machine tests.
- [x] Run report and bundle tests.
- [x] Run the full pytest suite.
- [x] Run all examples end to end.
- [x] Validate generated bundles through the CLI.
- [x] Inspect generated bundles through the CLI.
- [x] Run compile checks.
- [x] Run import smoke checks.
- [x] Remove generated Python cache directories.
- [x] Update this plan with completed checkboxes and verification evidence.

## Verification Commands

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_state_machine.py tests/test_workflow_state_machine.py tests/test_bundles.py tests/test_report.py -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/optimize_with_evidence.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/local_agent_runner.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/state_machine_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run quaestio validate work/state-machine-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run quaestio inspect work/state-machine-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples
```

## Verification Results

- Baseline before the slice: `25 passed in 6.45s`.
- Red phase: focused state-machine tests failed during collection because `StateMachine` was not exported yet.
- Focused state-machine/report/bundle tests: `18 passed in 1.23s`.
- Full test suite: `36 passed in 0.62s`.
- `examples/optimize_with_evidence.py` generated `work/example-run-bundle.json` and `work/example-run-report.md`.
- `examples/local_agent_runner.py` generated `work/local-agent-bundle.json` and `work/local-agent-report.md`.
- `examples/state_machine_workflow.py` generated `work/state-machine-bundle.json` and `work/state-machine-report.md`.
- CLI validation accepted `toy-optimization`, `local-agent-demo`, and `state-machine-demo`.
- CLI inspection showed `verification-loop` in state `accepted` with `4` dispatches.
- Compile check passed with `python -m compileall -q src tests examples`.
- Import and JSON smoke check passed, including an assertion for the emitted `retry_scheduled` event.

## Expected Public API Shape

```python
from quaestio import StateMachine, StateMachineError

machine = StateMachine(name="research-loop", initial_state="drafting")
machine.on("drafting", "candidate_ready", "verifying")
machine.on(
    "verifying",
    "verification_failed",
    "drafting",
    guard=lambda context: context.data["attempts"] < 3,
    handler=lambda context: {"attempts": context.data["attempts"] + 1},
)

machine.dispatch("candidate_ready")
machine.dispatch("verification_failed")
```

## Self-Review

- Spec coverage: the plan adds explicit state tracking, events, branching, error behavior, serialization, reports, examples, and tests.
- Placeholder scan: every checklist item is concrete and executable.
- Type consistency: public names are consistently `StateMachine`, `MachineEvent`, `Transition`, `DispatchRecord`, `StateMachineContext`, and `StateMachineError`.
