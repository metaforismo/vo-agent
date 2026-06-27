"""Provisioning records and provider interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol

from vo.environments import EnvironmentSpec
from vo.exceptions import ProvisioningError
from vo.execution_plan import ExecutionPlan
from vo.models import jsonable, utc_now

PROVISIONING_STATUSES = {"ready", "failed"}


@dataclass(slots=True)
class ProvisionedEnvironment:
    """Recorded readiness state for one execution environment."""

    name: str
    kind: str
    provider: str
    status: str
    image: str | None = None
    resources: dict[str, int | float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("environment name must not be empty")
        if not self.kind.strip():
            raise ValueError("environment kind must not be empty")
        if not self.provider.strip():
            raise ValueError("provisioning provider must not be empty")
        if self.status not in PROVISIONING_STATUSES:
            raise ValueError("provisioned environment status is invalid")
        self.resources = dict(self.resources)
        self.metadata = dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "provider": self.provider,
            "status": self.status,
            "image": self.image,
            "resources": jsonable(self.resources),
            "metadata": jsonable(self.metadata),
            "error": jsonable(self.error),
        }


@dataclass(slots=True)
class ProvisioningResult:
    """Result of preparing environments for an execution plan."""

    plan_name: str
    provider: str
    environments: tuple[ProvisionedEnvironment, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=utc_now)
    finished_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.plan_name.strip():
            raise ValueError("provisioning plan_name must not be empty")
        if not self.provider.strip():
            raise ValueError("provisioning provider must not be empty")
        self.environments = tuple(self.environments)
        self.metadata = dict(self.metadata)

    @property
    def status(self) -> str:
        if any(environment.status == "failed" for environment in self.environments):
            return "failed"
        return "ready"

    @property
    def environment_count(self) -> int:
        return len(self.environments)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_name": self.plan_name,
            "provider": self.provider,
            "status": self.status,
            "environment_count": self.environment_count,
            "metadata": jsonable(self.metadata),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "environments": [
                environment.to_dict() for environment in self.environments
            ],
        }


class Provisioner(Protocol):
    """Interface for preparing environments for an execution plan."""

    name: str

    def provision(
        self,
        plan: ExecutionPlan,
        environments: Iterable[EnvironmentSpec],
    ) -> ProvisioningResult:
        """Prepare the environments required by an execution plan."""


class LocalProvisioner:
    """No-op provider that records declared environments as ready."""

    name = "local"

    def __init__(self, metadata: dict[str, Any] | None = None) -> None:
        self.metadata = dict(metadata or {})

    def provision(
        self,
        plan: ExecutionPlan,
        environments: Iterable[EnvironmentSpec],
    ) -> ProvisioningResult:
        environment_map = {environment.name: environment for environment in environments}
        missing = [
            name for name in plan.environment_names if name not in environment_map
        ]
        if missing:
            raise ProvisioningError(
                f"execution plan references unknown environment {missing[0]!r}"
            )

        records = tuple(
            _record_ready_environment(environment_map[name], provider=self.name)
            for name in plan.environment_names
        )
        return ProvisioningResult(
            plan_name=plan.name,
            provider=self.name,
            environments=records,
            metadata=dict(self.metadata),
        )


def _record_ready_environment(
    environment: EnvironmentSpec,
    *,
    provider: str,
) -> ProvisionedEnvironment:
    return ProvisionedEnvironment(
        name=environment.name,
        kind=environment.kind,
        provider=provider,
        status="ready",
        image=environment.image,
        resources=environment.resources.to_dict(),
        metadata=dict(environment.metadata),
    )
