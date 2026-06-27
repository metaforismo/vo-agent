import json
from pathlib import Path

from vo import AgentSpec, LocalCommandAgent, VerificationContext, WorkflowRun


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
