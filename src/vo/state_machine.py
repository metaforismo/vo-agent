"""Deterministic state machines for agent workflow control flow."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from vo.exceptions import StateMachineError
from vo.models import jsonable, utc_now


@dataclass(slots=True)
class MachineEvent:
    """An event dispatched into a state machine."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.type.strip():
            raise ValueError("event type must not be empty")
        self.data = dict(self.data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "data": jsonable(self.data),
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class StateMachineContext:
    """Context passed to transition guards and handlers."""

    machine_name: str
    from_state: str
    event: MachineEvent
    data: dict[str, Any]
    emitted_events: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, type: str, data: Mapping[str, Any] | None = None) -> None:
        if not type.strip():
            raise ValueError("emitted event type must not be empty")
        self.emitted_events.append(
            {
                "type": type,
                "data": jsonable(dict(data or {})),
            }
        )


Guard = Callable[[StateMachineContext], bool]
Handler = Callable[[StateMachineContext], Mapping[str, Any] | None]


@dataclass(slots=True)
class Transition:
    """A declared state transition for one event type."""

    from_state: str
    event_type: str
    to_state: str
    guard: Guard | None = field(default=None, repr=False, compare=False)
    handler: Handler | None = field(default=None, repr=False, compare=False)
    name: str | None = None

    def __post_init__(self) -> None:
        if not self.from_state.strip():
            raise ValueError("from_state must not be empty")
        if not self.event_type.strip():
            raise ValueError("event_type must not be empty")
        if not self.to_state.strip():
            raise ValueError("to_state must not be empty")

    @property
    def id(self) -> str:
        return self.name or f"{self.from_state}:{self.event_type}->{self.to_state}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "from_state": self.from_state,
            "event_type": self.event_type,
            "to_state": self.to_state,
            "has_guard": self.guard is not None,
            "has_handler": self.handler is not None,
        }


@dataclass(slots=True)
class DispatchRecord:
    """Serializable result of dispatching one event."""

    machine_name: str
    event: MachineEvent
    from_state: str
    to_state: str | None
    passed: bool
    transition_id: str | None = None
    emitted_events: list[dict[str, Any]] = field(default_factory=list)
    error: dict[str, str] | None = None
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "machine_name": self.machine_name,
            "event": self.event.to_dict(),
            "from_state": self.from_state,
            "to_state": self.to_state,
            "passed": self.passed,
            "transition_id": self.transition_id,
            "emitted_events": jsonable(self.emitted_events),
            "error": jsonable(self.error),
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class StateMachine:
    """A deterministic state machine with explicit transitions."""

    name: str
    initial_state: str
    data: dict[str, Any] = field(default_factory=dict)
    state: str | None = None
    transitions: list[Transition] = field(default_factory=list)
    history: list[DispatchRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("state machine name must not be empty")
        if not self.initial_state.strip():
            raise ValueError("initial_state must not be empty")
        self.data = dict(self.data)
        if self.state is None:
            self.state = self.initial_state
        if not self.state.strip():
            raise ValueError("state must not be empty")

    def on(
        self,
        from_state: str,
        event_type: str,
        to_state: str,
        *,
        guard: Guard | None = None,
        handler: Handler | None = None,
        name: str | None = None,
    ) -> Transition:
        transition = Transition(
            from_state=from_state,
            event_type=event_type,
            to_state=to_state,
            guard=guard,
            handler=handler,
            name=name,
        )
        if any(
            existing.from_state == transition.from_state
            and existing.event_type == transition.event_type
            and existing.to_state == transition.to_state
            for existing in self.transitions
        ):
            raise ValueError(f"duplicate transition: {transition.id}")
        self.transitions.append(transition)
        return transition

    def dispatch(
        self,
        event_type: str,
        data: Mapping[str, Any] | None = None,
        **event_data: Any,
    ) -> DispatchRecord:
        event_payload = dict(data or {})
        event_payload.update(event_data)
        event = MachineEvent(type=event_type, data=event_payload)
        from_state = self.state or self.initial_state
        candidates = [
            transition
            for transition in self.transitions
            if transition.from_state == from_state
            and transition.event_type == event.type
        ]
        if not candidates:
            raise StateMachineError(
                f"no transition for event {event.type!r} from state {from_state!r}"
            )

        selected = self._select_transition(candidates, event, from_state)
        if isinstance(selected, DispatchRecord):
            self.history.append(selected)
            return selected
        if selected is None:
            raise StateMachineError(
                f"no transition guard passed for event {event.type!r} "
                f"from state {from_state!r}"
            )

        record = self._apply_transition(selected, event, from_state)
        self.history.append(record)
        return record

    def _select_transition(
        self,
        candidates: list[Transition],
        event: MachineEvent,
        from_state: str,
    ) -> Transition | DispatchRecord | None:
        for transition in candidates:
            if transition.guard is None:
                return transition
            context = StateMachineContext(
                machine_name=self.name,
                from_state=from_state,
                event=event,
                data=self.data,
            )
            try:
                if transition.guard(context):
                    return transition
            except Exception as exc:
                return self._failed_record(event, from_state, transition, exc)
        return None

    def _apply_transition(
        self,
        transition: Transition,
        event: MachineEvent,
        from_state: str,
    ) -> DispatchRecord:
        context = StateMachineContext(
            machine_name=self.name,
            from_state=from_state,
            event=event,
            data=self.data,
        )
        before_data = dict(self.data)
        try:
            if transition.handler is not None:
                updates = transition.handler(context)
                if updates is not None:
                    if not isinstance(updates, Mapping):
                        raise TypeError("transition handler must return a mapping or None")
                    self.data.update(dict(updates))
            self.state = transition.to_state
            return DispatchRecord(
                machine_name=self.name,
                event=event,
                from_state=from_state,
                to_state=transition.to_state,
                passed=True,
                transition_id=transition.id,
                emitted_events=list(context.emitted_events),
            )
        except Exception as exc:
            self.data = before_data
            return self._failed_record(event, from_state, transition, exc)

    def _failed_record(
        self,
        event: MachineEvent,
        from_state: str,
        transition: Transition,
        exc: Exception,
    ) -> DispatchRecord:
        return DispatchRecord(
            machine_name=self.name,
            event=event,
            from_state=from_state,
            to_state=None,
            passed=False,
            transition_id=transition.id,
            error={"type": type(exc).__name__, "message": str(exc)},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "initial_state": self.initial_state,
            "state": self.state,
            "data": jsonable(self.data),
            "transitions": [transition.to_dict() for transition in self.transitions],
            "history": [record.to_dict() for record in self.history],
        }
