from __future__ import annotations

import json
from pathlib import Path

from quaestio import AgentSpec, WorkflowRun


def test_workflow_send_message_records_message() -> None:
    run = WorkflowRun(name="message workflow")
    run.add_agent(AgentSpec(name="solver", goal="solve"))

    message = run.send_message(
        "user",
        "try the geometry case",
        recipient="solver",
        thread="geometry",
        metadata={"priority": "high"},
    )

    assert run.messages.messages == [message]
    assert message.sender == "user"
    assert message.recipient == "solver"
    assert message.thread == "geometry"
    assert message.metadata == {"priority": "high"}


def test_workflow_messages_for_filters_recipient() -> None:
    run = WorkflowRun(name="message workflow")
    solver = run.send_message("user", "solve", recipient="solver")
    run.send_message("user", "review", recipient="critic")

    assert run.messages_for("solver") == [solver]


def test_workflow_message_events_are_recorded() -> None:
    run = WorkflowRun(name="message workflow")

    run.send_message("solver", "I found evidence", recipient="user", role="agent")

    assert run.events[-1].type == "message_sent"
    assert run.events[-1].data == {
        "message_id": run.messages.messages[-1].id,
        "sender": "solver",
        "recipient": "user",
        "role": "agent",
        "thread": "default",
    }


def test_workflow_bundle_includes_messages(tmp_path: Path) -> None:
    run = WorkflowRun(name="message workflow")
    run.send_message("user", "start", recipient="solver")

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["messages"][0]["sender"] == "user"
    assert bundle["messages"][0]["recipient"] == "solver"
    assert bundle["messages"][0]["content"] == "start"
