from __future__ import annotations

import json
from pathlib import Path

import pytest

from vo import (
    AgentRun,
    AgentSpec,
    ComputeResources,
    EnvironmentSpec,
    VerificationContext,
    WorkflowRun,
)
from vo.models import utc_now


class EchoAgent:
    name = "writer"

    def run(
        self,
        task: str,
        context: VerificationContext | None = None,
    ) -> AgentRun:
        now = utc_now()
        return AgentRun(
            agent_name=self.name,
            task=task,
            command=["echo-agent"],
            exit_code=0,
            stdout=f"done: {task}",
            stderr="",
            duration_s=0.01,
            started_at=now,
            finished_at=now,
            metadata={"origin": "test"},
        )


def environment(name: str = "local-dev") -> EnvironmentSpec:
    return EnvironmentSpec(
        name=name,
        kind="local",
        resources=ComputeResources(cpu=2, memory_gb=4),
    )


def test_workflow_registers_environment() -> None:
    run = WorkflowRun(name="env workflow")
    env = environment()

    registered = run.add_environment(env)

    assert registered is env
    assert run.environments == [env]
    assert run.events[-1].type == "environment_added"
    assert run.events[-1].data == {
        "name": "local-dev",
        "kind": "local",
    }


def test_workflow_rejects_duplicate_environment_names() -> None:
    run = WorkflowRun(name="env workflow")
    run.add_environment(environment())

    with pytest.raises(ValueError, match="environment 'local-dev' already exists"):
        run.add_environment(environment())


def test_assign_agent_environment_validates_agent_and_environment() -> None:
    run = WorkflowRun(name="env workflow")
    run.add_agent(AgentSpec(name="writer", goal="write"))
    run.add_environment(environment())

    run.assign_agent_environment("writer", "local-dev")

    assert run.agent_environments == {"writer": "local-dev"}
    assert run.events[-1].type == "agent_environment_assigned"
    assert run.events[-1].data == {
        "agent_name": "writer",
        "environment": "local-dev",
    }
    with pytest.raises(ValueError, match="agent 'missing' is not registered"):
        run.assign_agent_environment("missing", "local-dev")
    with pytest.raises(ValueError, match="environment 'missing-env' is not registered"):
        run.assign_agent_environment("writer", "missing-env")


def test_run_agent_records_assigned_environment_metadata() -> None:
    run = WorkflowRun(name="env workflow")
    run.add_agent(AgentSpec(name="writer", goal="write"))
    run.add_environment(environment())
    run.assign_agent_environment("writer", "local-dev")

    result = run.run_agent("writer", EchoAgent(), "hello")

    assert result.metadata == {"origin": "test", "environment": "local-dev"}
    assert run.agent_runs[0].metadata["environment"] == "local-dev"


def test_workflow_bundle_includes_environments_and_assignments(tmp_path: Path) -> None:
    run = WorkflowRun(name="env workflow")
    run.add_agent(AgentSpec(name="writer", goal="write"))
    run.add_environment(environment())
    run.assign_agent_environment("writer", "local-dev")
    run.run_agent("writer", EchoAgent(), "hello")

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["environments"][0]["name"] == "local-dev"
    assert bundle["environments"][0]["resources"] == {
        "cpu": 2,
        "memory_gb": 4,
        "disk_gb": 20,
        "gpu_count": 0,
    }
    assert bundle["agent_environments"] == {"writer": "local-dev"}
    assert bundle["agent_runs"][0]["metadata"]["environment"] == "local-dev"
