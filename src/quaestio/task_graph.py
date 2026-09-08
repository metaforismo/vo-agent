"""Dependency graphs for resource-safe agent task scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quaestio.agents import AgentRun
from quaestio.exceptions import TaskGraphError
from quaestio.models import jsonable, utc_now

TASK_STATUSES = {"pending", "running", "passed", "failed", "blocked"}


@dataclass(slots=True)
class TaskSpec:
    """One task node in an agent dependency graph."""

    name: str
    agent_name: str
    task: str
    depends_on: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    agent_run: AgentRun | None = None
    error: dict[str, str] | None = None
    created_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    finished_at: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("task name must not be empty")
        if not self.agent_name.strip():
            raise ValueError("agent_name must not be empty")
        if not self.task.strip():
            raise ValueError("task must not be empty")
        self.depends_on = tuple(self.depends_on)
        self.resources = tuple(self.resources)
        if self.name in self.depends_on:
            raise ValueError("task cannot depend on itself")
        if self.status not in TASK_STATUSES:
            raise ValueError("task status is invalid")

    def mark_running(self) -> None:
        self.status = "running"
        self.started_at = utc_now()

    def record_agent_run(self, agent_run: AgentRun) -> None:
        self.agent_run = agent_run
        self.finished_at = utc_now()
        if agent_run.passed:
            self.status = "passed"
            self.error = None
        else:
            self.status = "failed"
            self.error = {
                "type": "AgentRunFailed",
                "message": agent_run.stderr or f"exit {agent_run.exit_code}",
            }

    def mark_blocked(self, reason: str) -> None:
        self.status = "blocked"
        self.finished_at = utc_now()
        self.error = {"type": "DependencyBlocked", "message": reason}

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "agent_name": self.agent_name,
            "task": self.task,
            "depends_on": list(self.depends_on),
            "resources": list(self.resources),
            "metadata": jsonable(self.metadata),
            "status": self.status,
            "agent_run": self.agent_run.to_dict() if self.agent_run else None,
            "error": jsonable(self.error),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass(slots=True)
class TaskGraph:
    """A deterministic dependency graph of agent tasks."""

    name: str
    tasks: list[TaskSpec] = field(default_factory=list)
    status: str = "pending"
    stop_reason: str | None = None
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("task graph name must not be empty")
        if self.status not in {"pending", "running", "passed", "failed"}:
            raise ValueError("task graph status is invalid")

    def add_task(self, task: TaskSpec) -> TaskSpec:
        if any(existing.name == task.name for existing in self.tasks):
            raise ValueError(f"task {task.name!r} already exists")
        self.tasks.append(task)
        return task

    def task(self, name: str) -> TaskSpec:
        for task in self.tasks:
            if task.name == name:
                return task
        raise TaskGraphError(f"unknown task {name!r}")

    def validate(self) -> bool:
        names = {task.name for task in self.tasks}
        for task in self.tasks:
            for dependency in task.depends_on:
                if dependency not in names:
                    raise TaskGraphError(
                        f"task {task.name!r} has missing dependency {dependency!r}"
                    )
        self._validate_acyclic()
        return True

    def ready_tasks(self) -> list[TaskSpec]:
        self.validate()
        ready: list[TaskSpec] = []
        for task in self.tasks:
            if task.status != "pending":
                continue
            if all(self.task(dependency).status == "passed" for dependency in task.depends_on):
                ready.append(task)
        return ready

    def ready_batches(self) -> list[list[TaskSpec]]:
        batches: list[list[TaskSpec]] = []
        batch_resources: list[set[str]] = []
        for task in self.ready_tasks():
            resources = set(task.resources)
            for index, used in enumerate(batch_resources):
                if resources.isdisjoint(used):
                    batches[index].append(task)
                    used.update(resources)
                    break
            else:
                batches.append([task])
                batch_resources.append(set(resources))
        return batches

    def record_agent_run(self, task_name: str, agent_run: AgentRun) -> TaskSpec:
        task = self.task(task_name)
        task.record_agent_run(agent_run)
        return task

    def mark_blocked_dependents(self) -> None:
        changed = True
        while changed:
            changed = False
            for task in self.tasks:
                if task.status != "pending":
                    continue
                blockers = [
                    dependency
                    for dependency in task.depends_on
                    if self.task(dependency).status in {"failed", "blocked"}
                ]
                if blockers:
                    task.mark_blocked(
                        f"blocked by dependencies: {', '.join(blockers)}"
                    )
                    changed = True

    def finalize(self) -> None:
        self.mark_blocked_dependents()
        if all(task.status == "passed" for task in self.tasks):
            self.status = "passed"
            self.stop_reason = "all_tasks_passed"
        elif any(task.status == "failed" for task in self.tasks):
            self.status = "failed"
            self.stop_reason = "task_failed"
        elif any(task.status == "blocked" for task in self.tasks):
            self.status = "failed"
            self.stop_reason = "dependency_blocked"
        elif any(task.status == "pending" for task in self.tasks):
            self.status = "failed"
            self.stop_reason = "no_ready_tasks"

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "stop_reason": self.stop_reason,
            "created_at": self.created_at,
            "task_count": len(self.tasks),
            "passed_count": self._count("passed"),
            "failed_count": self._count("failed"),
            "blocked_count": self._count("blocked"),
            "tasks": [task.to_dict() for task in self.tasks],
            "ready_batches": [
                [task.name for task in batch] for batch in self.ready_batches()
            ],
        }

    def _validate_acyclic(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str, path: tuple[str, ...]) -> None:
            if name in visited:
                return
            if name in visiting:
                cycle = " -> ".join((*path, name))
                raise TaskGraphError(f"cycle detected: {cycle}")
            visiting.add(name)
            for dependency in self.task(name).depends_on:
                visit(dependency, (*path, name))
            visiting.remove(name)
            visited.add(name)

        for task in self.tasks:
            visit(task.name, ())

    def _count(self, status: str) -> int:
        return sum(1 for task in self.tasks if task.status == status)
