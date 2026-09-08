"""Durable message records for workflow coordination."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quaestio.models import jsonable, short_id, utc_now

MESSAGE_ROLES = {"user", "agent", "system"}


@dataclass(slots=True)
class Message:
    """One durable message exchanged during a workflow run."""

    sender: str
    content: str
    recipient: str | None = None
    role: str = "user"
    thread: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=short_id)
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.sender.strip():
            raise ValueError("message sender must not be empty")
        if not self.content.strip():
            raise ValueError("message content must not be empty")
        if self.recipient is not None and not self.recipient.strip():
            raise ValueError("message recipient must not be empty")
        if self.role not in MESSAGE_ROLES:
            raise ValueError("message role is invalid")
        if not self.thread.strip():
            raise ValueError("message thread must not be empty")
        self.metadata = dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "sender": self.sender,
            "recipient": self.recipient,
            "role": self.role,
            "thread": self.thread,
            "content": self.content,
            "metadata": jsonable(self.metadata),
        }


@dataclass(slots=True)
class MessageLog:
    """Ordered collection of workflow messages."""

    messages: list[Message] = field(default_factory=list)

    def append(self, message: Message) -> Message:
        self.messages.append(message)
        return message

    def inbox(self, recipient: str) -> list[Message]:
        return [message for message in self.messages if message.recipient == recipient]

    def thread(self, name: str) -> list[Message]:
        return [message for message in self.messages if message.thread == name]

    def to_list(self) -> list[dict[str, Any]]:
        return [message.to_dict() for message in self.messages]
