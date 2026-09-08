from __future__ import annotations

import pytest

from quaestio import ComputeResources, EnvironmentSpec


def test_compute_resources_validate_positive_cpu_and_memory() -> None:
    with pytest.raises(ValueError, match="cpu must be positive"):
        ComputeResources(cpu=0, memory_gb=4)

    with pytest.raises(ValueError, match="memory_gb must be positive"):
        ComputeResources(cpu=1, memory_gb=0)


def test_compute_resources_reject_negative_gpu_count() -> None:
    with pytest.raises(ValueError, match="gpu_count must be non-negative"):
        ComputeResources(cpu=1, memory_gb=4, gpu_count=-1)


def test_environment_spec_validates_name_and_kind() -> None:
    with pytest.raises(ValueError, match="environment name must not be empty"):
        EnvironmentSpec(name="", kind="vm")

    with pytest.raises(ValueError, match="environment kind must be one of"):
        EnvironmentSpec(name="bad", kind="spaceship")


def test_environment_spec_serializes_setup_env_and_resources() -> None:
    env = EnvironmentSpec(
        name="gpu-worker",
        kind="vm",
        image="ubuntu:24.04",
        resources=ComputeResources(cpu=8, memory_gb=32, gpu_count=1),
        setup_commands=("uv sync", "pytest"),
        env={"PYTHONUNBUFFERED": "1"},
        metadata={"pool": "warm"},
    )

    bundle = env.to_dict()

    assert bundle["name"] == "gpu-worker"
    assert bundle["kind"] == "vm"
    assert bundle["image"] == "ubuntu:24.04"
    assert bundle["resources"] == {
        "cpu": 8,
        "memory_gb": 32,
        "disk_gb": 20,
        "gpu_count": 1,
    }
    assert bundle["setup_commands"] == ["uv sync", "pytest"]
    assert bundle["env"] == {"PYTHONUNBUFFERED": "1"}
    assert bundle["metadata"] == {"pool": "warm"}


def test_environment_spec_serializes_secret_names_without_values() -> None:
    env = EnvironmentSpec(
        name="secure-worker",
        kind="vm",
        secret_names=("OPENAI_API_KEY", "WANDB_API_KEY"),
    )

    bundle = env.to_dict()

    assert bundle["secret_names"] == ["OPENAI_API_KEY", "WANDB_API_KEY"]
    assert "secrets" not in bundle
    assert "OPENAI_API_KEY_VALUE" not in str(bundle)
