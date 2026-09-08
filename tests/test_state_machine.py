from __future__ import annotations

import pytest

from quaestio import StateMachine, StateMachineError


def test_state_machine_dispatches_declared_transition() -> None:
    machine = StateMachine(
        name="research-loop",
        initial_state="drafting",
        data={"attempts": 0},
    )
    machine.on("drafting", "candidate_ready", "verifying")

    record = machine.dispatch("candidate_ready", {"candidate": "proof-v1"})

    assert machine.state == "verifying"
    assert record.passed is True
    assert record.from_state == "drafting"
    assert record.to_state == "verifying"
    assert record.event.type == "candidate_ready"
    assert record.event.data == {"candidate": "proof-v1"}
    assert machine.history == [record]
    assert machine.to_dict()["state"] == "verifying"


def test_state_machine_rejects_unknown_event_for_current_state() -> None:
    machine = StateMachine(name="research-loop", initial_state="drafting")
    machine.on("drafting", "candidate_ready", "verifying")

    with pytest.raises(StateMachineError, match="no transition"):
        machine.dispatch("verification_finished")

    assert machine.state == "drafting"
    assert machine.history == []


def test_state_machine_rejects_duplicate_transition_declarations() -> None:
    machine = StateMachine(name="research-loop", initial_state="drafting")
    machine.on("drafting", "candidate_ready", "verifying")

    with pytest.raises(ValueError, match="duplicate transition"):
        machine.on("drafting", "candidate_ready", "verifying")


def test_guards_select_branch_for_matching_event() -> None:
    machine = StateMachine(name="research-loop", initial_state="verifying")
    machine.on(
        "verifying",
        "verification_finished",
        "accepted",
        guard=lambda context: context.event.data["passed"] is True,
    )
    machine.on(
        "verifying",
        "verification_finished",
        "drafting",
        guard=lambda context: context.event.data["passed"] is False,
    )

    record = machine.dispatch("verification_finished", {"passed": False})

    assert record.passed is True
    assert record.to_state == "drafting"
    assert machine.state == "drafting"


def test_guard_exception_is_captured_without_advancing_state() -> None:
    machine = StateMachine(name="research-loop", initial_state="verifying")
    machine.on(
        "verifying",
        "verification_finished",
        "accepted",
        guard=lambda _context: 1 / 0 == 0,
    )

    record = machine.dispatch("verification_finished")

    assert record.passed is False
    assert record.from_state == "verifying"
    assert record.to_state is None
    assert record.error["type"] == "ZeroDivisionError"
    assert machine.state == "verifying"


def test_handler_can_mutate_data_return_updates_and_emit_events() -> None:
    machine = StateMachine(
        name="research-loop",
        initial_state="verifying",
        data={"attempts": 0},
    )

    def schedule_retry(context):
        context.data["attempts"] += 1
        context.emit("retry_scheduled", {"attempt": context.data["attempts"]})
        return {"last_failure": context.event.data["reason"]}

    machine.on(
        "verifying",
        "verification_failed",
        "drafting",
        handler=schedule_retry,
    )

    record = machine.dispatch("verification_failed", {"reason": "test failure"})

    assert record.passed is True
    assert machine.state == "drafting"
    assert machine.data == {"attempts": 1, "last_failure": "test failure"}
    assert record.emitted_events == [
        {"type": "retry_scheduled", "data": {"attempt": 1}}
    ]


def test_handler_exception_is_captured_without_advancing_state() -> None:
    machine = StateMachine(name="research-loop", initial_state="drafting")

    def broken_handler(_context):
        raise RuntimeError("agent crashed")

    machine.on(
        "drafting",
        "candidate_ready",
        "verifying",
        handler=broken_handler,
    )

    record = machine.dispatch("candidate_ready")

    assert record.passed is False
    assert record.error == {"type": "RuntimeError", "message": "agent crashed"}
    assert machine.state == "drafting"
    assert machine.history == [record]
