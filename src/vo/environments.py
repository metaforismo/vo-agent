"""Execution environment declarations for agent runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from vo.models import jsonable

EnvironmentKind = Literal["local", "container", "vm"]
VALID_ENVIRONMENT_KINDS = {"local", "container", "vm"}


@dataclass(slots=True)
class ComputeResources:
    """Portable resource request for an execution environment."""

    cpu: int
    memory_gb: float
    disk_gb: float = 20
    gpu_count: int = 0

    def __post_init__(self) -> None:
        if self.cpu <= 0:
            raise ValueError("cpu must be positive")
        if self.memory_gb <= 0:
            raise ValueError("memory_gb must be positive")
        if self.disk_gb <= 0:
            raise ValueError("disk_gb must be positive")
        if self.gpu_count < 0:
            raise ValueError("gpu_count must be non-negative")

    def to_dict(self) -> dict[str, int | float]:
        return {
            "cpu": self.cpu,
            "memory_gb": self.memory_gb,
            "disk_gb": self.disk_gb,
            "gpu_count": self.gpu_count,
        }


@dataclass(slots=True)
class EnvironmentSpec:
    """Declarative placement target for one or more agents."""

    name: str
    kind: EnvironmentKind = "local"
    image: str | None = None
    resources: ComputeResources = field(
        default_factory=lambda: ComputeResources(cpu=1, memory_gb=2)
    )
    setup_commands: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)
    secret_names: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("environment name must not be empty")
        if self.kind not in VALID_ENVIRONMENT_KINDS:
            allowed = ", ".join(sorted(VALID_ENVIRONMENT_KINDS))
            raise ValueError(f"environment kind must be one of: {allowed}")
        self.setup_commands = tuple(str(command) for command in self.setup_commands)
        self.env = {str(key): str(value) for key, value in self.env.items()}
        self.secret_names = tuple(str(name) for name in self.secret_names)
        if any(not name.strip() for name in self.secret_names):
            raise ValueError("secret names must not be empty")
        self.metadata = dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "image": self.image,
            "resources": self.resources.to_dict(),
            "setup_commands": list(self.setup_commands),
            "env": dict(self.env),
            "secret_names": list(self.secret_names),
            "metadata": jsonable(self.metadata),
        }
