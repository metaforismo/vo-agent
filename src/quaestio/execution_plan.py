"""Deterministic execution plans for task graphs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from quaestio.environments import EnvironmentSpec
from quaestio.exceptions import ExecutionPlanError
from quaestio.models import jsonable, utc_now
from quaestio.task_graph import TaskGraph, TaskSpec


@dataclass(slots=True)
class PlannedTask:
    """One task scheduled into an execution wave."""

    name: str
    agent_name: str
    task: str
    environment: str
    depends_on: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_task(cls, task: TaskSpec, *, environment: str) -> "PlannedTask":
        return cls(
            name=task.name,
            agent_name=task.agent_name,
            task=task.task,
            environment=environment,
            depends_on=task.depends_on,
            resources=task.resources,
            metadata=dict(task.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "agent_name": self.agent_name,
            "task": self.task,
            "environment": self.environment,
            "depends_on": list(self.depends_on),
            "resources": list(self.resources),
            "metadata": jsonable(self.metadata),
        }


@dataclass(slots=True)
class ExecutionWave:
    """A resource-disjoint group of planned tasks."""

    index: int
    tasks: tuple[PlannedTask, ...]

    def __post_init__(self) -> None:
        if self.index <= 0:
            raise ValueError("execution wave index must be positive")
        self.tasks = tuple(self.tasks)
        if not self.tasks:
            raise ValueError("execution wave must contain at least one task")

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    @property
    def environment_names(self) -> list[str]:
        return sorted({task.environment for task in self.tasks})

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "task_count": self.task_count,
            "environment_names": self.environment_names,
            "tasks": [task.to_dict() for task in self.tasks],
        }


@dataclass(slots=True)
class ExecutionPlan:
    """A deterministic schedule for a task graph."""

    name: str
    graph_name: str
    waves: tuple[ExecutionWave, ...]
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("execution plan name must not be empty")
        if not self.graph_name.strip():
            raise ValueError("execution plan graph_name must not be empty")
        self.waves = tuple(self.waves)

    @property
    def wave_count(self) -> int:
        return len(self.waves)

    @property
    def task_count(self) -> int:
        return sum(wave.task_count for wave in self.waves)

    @property
    def environment_names(self) -> list[str]:
        return sorted(
            {environment for wave in self.waves for environment in wave.environment_names}
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "graph_name": self.graph_name,
            "created_at": self.created_at,
            "wave_count": self.wave_count,
            "task_count": self.task_count,
            "environment_names": self.environment_names,
            "waves": [wave.to_dict() for wave in self.waves],
        }


def build_execution_plan(
    graph: TaskGraph,
    *,
    agent_environments: dict[str, str],
    environments: Iterable[EnvironmentSpec],
    name: str | None = None,
) -> ExecutionPlan:
    """Build a resource-aware, placement-aware plan for a task graph."""

    graph.validate()
    environment_names = {environment.name for environment in environments}
    remaining = {task.name: task for task in graph.tasks}
    completed: set[str] = set()
    waves: list[ExecutionWave] = []

    for task in graph.tasks:
        environment_name = agent_environments.get(task.agent_name)
        if environment_name is None:
            raise ExecutionPlanError(
                f"agent {task.agent_name!r} has no assigned environment"
            )
        if environment_name not in environment_names:
            raise ExecutionPlanError(
                f"agent {task.agent_name!r} is assigned to unknown environment "
                f"{environment_name!r}"
            )

    while remaining:
        ready = [
            task
            for task in graph.tasks
            if task.name in remaining
            and all(dependency in completed for dependency in task.depends_on)
        ]
        if not ready:
            raise ExecutionPlanError(
                f"task graph {graph.name!r} has no schedulable tasks"
            )

        selected = _resource_disjoint_tasks(ready)
        planned_tasks = tuple(
            PlannedTask.from_task(
                task,
                environment=agent_environments[task.agent_name],
            )
            for task in selected
        )
        waves.append(ExecutionWave(index=len(waves) + 1, tasks=planned_tasks))
        for task in selected:
            completed.add(task.name)
            del remaining[task.name]

    return ExecutionPlan(
        name=name or f"{graph.name}-execution",
        graph_name=graph.name,
        waves=tuple(waves),
    )


def _resource_disjoint_tasks(tasks: list[TaskSpec]) -> list[TaskSpec]:
    selected: list[TaskSpec] = []
    used_resources: set[str] = set()
    for task in tasks:
        resources = set(task.resources)
        if resources.isdisjoint(used_resources):
            selected.append(task)
            used_resources.update(resources)
    return selected
