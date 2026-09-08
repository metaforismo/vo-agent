import json
from pathlib import Path

from quaestio import (
    AgentSpec,
    EnvironmentSpec,
    LocalCommandAgent,
    VerificationContext,
    WorkflowRun,
)


class ThrowingAgent:
    name = "thrower"

    def run(self, task, context=None):
        del task, context
        raise RuntimeError("adapter exploded")


def test_workflow_run_agent_records_run_and_exports_bundle(tmp_path: Path):
    script = tmp_path / "agent.py"
    script.write_text(
        "import sys\n"
        "task = sys.stdin.read().strip()\n"
        "print(f'completed: {task}')\n",
        encoding="utf-8",
    )

    run = WorkflowRun(name="agent-loop")
    run.add_agent(AgentSpec(name="writer", goal="Draft a patch summary"))
    result = run.run_agent(
        "writer",
        LocalCommandAgent(["python", str(script)], name="writer"),
        "summarize patch",
        VerificationContext(cwd=tmp_path),
    )

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert result.passed is True
    assert bundle["agent_runs"][0]["agent_name"] == "writer"
    assert bundle["agent_runs"][0]["stdout"].strip() == "completed: summarize patch"
    assert [event["type"] for event in bundle["events"]][-2:] == [
        "agent_run_started",
        "agent_run_finished",
    ]


def test_workflow_run_agent_records_adapter_exception_and_finished_event(tmp_path: Path):
    run = WorkflowRun(name="adapter-failure")
    run.add_agent(AgentSpec(name="thrower", goal="Raise a controlled exception"))
    run.add_environment(EnvironmentSpec(name="local-dev"))
    run.assign_agent_environment("thrower", "local-dev")

    result = run.run_agent(
        "thrower",
        ThrowingAgent(),
        "try the dangerous task",
        VerificationContext(cwd=tmp_path),
    )

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert result.passed is False
    assert result.exit_code == -1
    assert result.stderr == "adapter exploded"
    assert result.metadata["environment"] == "local-dev"
    assert result.metadata["error_type"] == "RuntimeError"
    assert bundle["agent_runs"][0]["agent_name"] == "thrower"
    assert bundle["agent_runs"][0]["passed"] is False
    assert bundle["agent_runs"][0]["metadata"]["environment"] == "local-dev"
    assert bundle["agent_runs"][0]["metadata"]["error_type"] == "RuntimeError"
    assert [event["type"] for event in bundle["events"]][-2:] == [
        "agent_run_started",
        "agent_run_finished",
    ]
    assert bundle["events"][-1]["data"]["failed"] is True
    assert bundle["events"][-1]["data"]["error_type"] == "RuntimeError"
