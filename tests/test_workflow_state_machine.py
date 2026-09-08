from __future__ import annotations

import json
from pathlib import Path

import pytest

from quaestio import StateMachine, StateMachineError, WorkflowRun


def test_workflow_registers_and_dispatches_state_machine() -> None:
    run = WorkflowRun(name="machine workflow")
    machine = StateMachine(name="research-loop", initial_state="drafting")
    machine.on("drafting", "candidate_ready", "verifying")

    run.add_state_machine(machine)
    record = run.dispatch(
        "research-loop",
        "candidate_ready",
        {"candidate": "proof-v1"},
    )

    assert record.passed is True
    assert machine.state == "verifying"
    assert run.state_machines[0] is machine
    assert run.events[-1].type == "state_machine_dispatched"
    assert run.events[-1].data["machine"] == "research-loop"
    assert run.events[-1].data["event_type"] == "candidate_ready"
    assert run.events[-1].data["passed"] is True


def test_workflow_rejects_duplicate_state_machine_names() -> None:
    run = WorkflowRun(name="machine workflow")
    run.add_state_machine(StateMachine(name="research-loop", initial_state="drafting"))

    with pytest.raises(ValueError, match="state machine 'research-loop' already exists"):
        run.add_state_machine(
            StateMachine(name="research-loop", initial_state="verifying")
        )


def test_workflow_dispatch_rejects_unknown_machine() -> None:
    run = WorkflowRun(name="machine workflow")

    with pytest.raises(StateMachineError, match="state machine 'missing' is not registered"):
        run.dispatch("missing", "candidate_ready")


def test_workflow_bundle_includes_state_machine_history(tmp_path: Path) -> None:
    run = WorkflowRun(name="machine workflow")
    machine = StateMachine(name="research-loop", initial_state="drafting")
    machine.on("drafting", "candidate_ready", "verifying")
    run.add_state_machine(machine)
    run.dispatch("research-loop", "candidate_ready")

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["state_machines"][0]["name"] == "research-loop"
    assert bundle["state_machines"][0]["state"] == "verifying"
    assert bundle["state_machines"][0]["history"][0]["passed"] is True
