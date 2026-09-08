from __future__ import annotations

import pytest

from quaestio import Message, MessageLog


def test_message_validates_sender_and_content() -> None:
    with pytest.raises(ValueError, match="message sender must not be empty"):
        Message(sender="", content="hello")

    with pytest.raises(ValueError, match="message content must not be empty"):
        Message(sender="user", content="")


def test_message_validates_role() -> None:
    with pytest.raises(ValueError, match="message role is invalid"):
        Message(sender="user", content="hello", role="critic")


def test_message_serializes_core_fields_and_metadata() -> None:
    message = Message(
        sender="user",
        recipient="solver",
        role="user",
        thread="geometry",
        content="try the hard case",
        metadata={"priority": "high"},
    )
    bundle = message.to_dict()

    assert bundle["id"]
    assert bundle["sender"] == "user"
    assert bundle["recipient"] == "solver"
    assert bundle["role"] == "user"
    assert bundle["thread"] == "geometry"
    assert bundle["content"] == "try the hard case"
    assert bundle["metadata"] == {"priority": "high"}
    assert bundle["created_at"]


def test_message_log_appends_messages_in_order() -> None:
    log = MessageLog()
    first = log.append(Message(sender="user", content="first"))
    second = log.append(Message(sender="solver", content="second", role="agent"))

    assert log.messages == [first, second]
    assert log.to_list()[0]["content"] == "first"
    assert log.to_list()[1]["content"] == "second"


def test_message_log_filters_inbox_by_recipient() -> None:
    log = MessageLog()
    solver_message = log.append(
        Message(sender="user", recipient="solver", content="please solve")
    )
    log.append(Message(sender="user", recipient="critic", content="please review"))

    assert log.inbox("solver") == [solver_message]


def test_message_log_filters_by_thread() -> None:
    log = MessageLog()
    geometry = log.append(
        Message(sender="user", content="geometry", thread="geometry")
    )
    log.append(Message(sender="user", content="algebra", thread="algebra"))

    assert log.thread("geometry") == [geometry]
