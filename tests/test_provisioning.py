from __future__ import annotations

import pytest

from vo import (
    ComputeResources,
    EnvironmentSpec,
    ExecutionPlan,
    ExecutionWave,
    LocalProvisioner,
    PlannedTask,
    ProvisionedEnvironment,
    ProvisioningError,
    ProvisioningResult,
)


def environment(name: str = "cpu-worker") -> EnvironmentSpec:
    return EnvironmentSpec(
        name=name,
        kind="vm",
        image="ubuntu:24.04",
        resources=ComputeResources(cpu=4, memory_gb=8),
        setup_commands=("uv sync",),
        metadata={"pool": "warm"},
    )


def execution_plan() -> ExecutionPlan:
    return ExecutionPlan(
        name="research-plan-execution",
        graph_name="research-plan",
        waves=(
            ExecutionWave(
                index=1,
                tasks=(
                    PlannedTask(
                        name="search",
                        agent_name="searcher",
                        task="search",
                        environment="cpu-worker",
                        resources=("repo:notes",),
                    ),
                ),
            ),
        ),
    )


def test_provisioned_environment_validates_name_and_status() -> None:
    with pytest.raises(ValueError, match="environment name must not be empty"):
        ProvisionedEnvironment(
            name="",
            kind="local",
            provider="local",
            status="ready",
        )

    with pytest.raises(ValueError, match="provisioned environment status is invalid"):
        ProvisionedEnvironment(
            name="cpu-worker",
            kind="local",
            provider="local",
            status="warming",
        )


def test_provisioned_environment_serializes_provider_resources_and_metadata() -> None:
    record = ProvisionedEnvironment(
        name="cpu-worker",
        kind="vm",
        provider="local",
        status="ready",
        image="ubuntu:24.04",
        resources={"cpu": 4, "memory_gb": 8, "disk_gb": 20, "gpu_count": 0},
        metadata={"pool": "warm"},
    )

    assert record.to_dict() == {
        "name": "cpu-worker",
        "kind": "vm",
        "provider": "local",
        "status": "ready",
        "image": "ubuntu:24.04",
        "resources": {"cpu": 4, "memory_gb": 8, "disk_gb": 20, "gpu_count": 0},
        "metadata": {"pool": "warm"},
        "error": None,
    }


def test_provisioning_result_validates_plan_name() -> None:
    with pytest.raises(ValueError, match="provisioning plan_name must not be empty"):
        ProvisioningResult(
            plan_name="",
            provider="local",
            environments=(),
        )


def test_provisioning_result_status_reflects_environment_statuses() -> None:
    ready = ProvisionedEnvironment(
        name="cpu-worker",
        kind="local",
        provider="local",
        status="ready",
    )
    failed = ProvisionedEnvironment(
        name="gpu-worker",
        kind="vm",
        provider="local",
        status="failed",
        error={"type": "ProvisioningError", "message": "capacity unavailable"},
    )

    assert ProvisioningResult(
        plan_name="plan",
        provider="local",
        environments=(ready,),
    ).status == "ready"
    assert ProvisioningResult(
        plan_name="plan",
        provider="local",
        environments=(ready, failed),
    ).status == "failed"


def test_local_provisioner_provisions_plan_environments() -> None:
    result = LocalProvisioner(metadata={"mode": "dry-run"}).provision(
        execution_plan(),
        [environment()],
    )

    assert result.plan_name == "research-plan-execution"
    assert result.provider == "local"
    assert result.status == "ready"
    assert len(result.environments) == 1
    assert result.environments[0].name == "cpu-worker"
    assert result.environments[0].kind == "vm"
    assert result.environments[0].status == "ready"
    assert result.environments[0].resources == {
        "cpu": 4,
        "memory_gb": 8,
        "disk_gb": 20,
        "gpu_count": 0,
    }
    assert result.metadata == {"mode": "dry-run"}


def test_local_provisioner_rejects_unknown_plan_environment() -> None:
    with pytest.raises(
        ProvisioningError,
        match="execution plan references unknown environment 'cpu-worker'",
    ):
        LocalProvisioner().provision(execution_plan(), [environment("other-worker")])


def test_provisioning_result_serializes_environment_records() -> None:
    result = LocalProvisioner(metadata={"mode": "dry-run"}).provision(
        execution_plan(),
        [environment()],
    )
    bundle = result.to_dict()

    assert bundle["plan_name"] == "research-plan-execution"
    assert bundle["provider"] == "local"
    assert bundle["status"] == "ready"
    assert bundle["environment_count"] == 1
    assert bundle["metadata"] == {"mode": "dry-run"}
    assert bundle["environments"][0]["name"] == "cpu-worker"
    assert bundle["environments"][0]["metadata"] == {"pool": "warm"}
