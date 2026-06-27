"""Durable records for execution-plan runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vo.agents import AgentRun
from vo.models import jsonable, utc_now


@dataclass(slots=True)
class ExecutedTask:
    """Captured result of one planned task execution."""

    name: str
    agent_name: str
    environment: str
    agent_run: AgentRun
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("executed task name must not be empty")
        if not self.agent_name.strip():
            raise ValueError("executed task agent_name must not be empty")
        if not self.environment.strip():
            raise ValueError("executed task environment must not be empty")
        self.metadata = dict(self.metadata)

    @property
    def status(self) -> str:
        return "passed" if self.agent_run.passed else "failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "agent_name": self.agent_name,
            "environment": self.environment,
            "status": self.status,
            "metadata": jsonable(self.metadata),
            "agent_run": self.agent_run.to_dict(),
        }


@dataclass(slots=True)
class ExecutedWave:
    """Captured result of one execution-plan wave."""

    index: int
    tasks: tuple[ExecutedTask, ...]

    def __post_init__(self) -> None:
        if self.index <= 0:
            raise ValueError("executed wave index must be positive")
        self.tasks = tuple(self.tasks)
        if not self.tasks:
            raise ValueError("executed wave must contain at least one task")

    @property
    def status(self) -> str:
        if any(task.status == "failed" for task in self.tasks):
            return "failed"
        return "passed"

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    @property
    def passed_count(self) -> int:
        return sum(1 for task in self.tasks if task.status == "passed")

    @property
    def failed_count(self) -> int:
        return sum(1 for task in self.tasks if task.status == "failed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "status": self.status,
            "task_count": self.task_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "tasks": [task.to_dict() for task in self.tasks],
        }


@dataclass(slots=True)
class PlanExecutionResult:
    """Captured result of running an execution plan."""

    plan_name: str
    waves: tuple[ExecutedWave, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=utc_now)
    finished_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.plan_name.strip():
            raise ValueError("plan execution plan_name must not be empty")
        self.waves = tuple(self.waves)
        self.metadata = dict(self.metadata)

    @property
    def status(self) -> str:
        if any(wave.status == "failed" for wave in self.waves):
            return "failed"
        return "passed"

    @property
    def wave_count(self) -> int:
        return len(self.waves)

    @property
    def task_count(self) -> int:
        return sum(wave.task_count for wave in self.waves)

    @property
    def passed_count(self) -> int:
        return sum(wave.passed_count for wave in self.waves)

    @property
    def failed_count(self) -> int:
        return sum(wave.failed_count for wave in self.waves)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_name": self.plan_name,
            "status": self.status,
            "wave_count": self.wave_count,
            "task_count": self.task_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "metadata": jsonable(self.metadata),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "waves": [wave.to_dict() for wave in self.waves],
        }
