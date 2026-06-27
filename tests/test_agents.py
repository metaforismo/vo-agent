from pathlib import Path

from vo import LocalCommandAgent, VerificationContext


def test_local_command_agent_passes_task_on_stdin_and_captures_output(tmp_path: Path):
    script = tmp_path / "agent.py"
    script.write_text(
        "import pathlib, sys\n"
        "task = sys.stdin.read()\n"
        "pathlib.Path('artifact.txt').write_text(task.upper())\n"
        "print('wrote artifact')\n",
        encoding="utf-8",
    )

    agent = LocalCommandAgent(["python", str(script)], name="script-agent")
    result = agent.run("hello agent", VerificationContext(cwd=tmp_path))

    evidence = result.to_evidence()

    assert result.passed is True
    assert result.stdout.strip() == "wrote artifact"
    assert (tmp_path / "artifact.txt").read_text(encoding="utf-8") == "HELLO AGENT"
    assert evidence.kind == "agent_run"
    assert evidence.data["exit_code"] == 0


def test_local_command_agent_records_timeout_as_failed_run(tmp_path: Path):
    script = tmp_path / "slow_agent.py"
    script.write_text(
        "import sys, time\n"
        "print('started')\n"
        "sys.stdout.flush()\n"
        "time.sleep(2)\n",
        encoding="utf-8",
    )

    agent = LocalCommandAgent(
        ["python", str(script)],
        name="slow-agent",
        timeout=0.2,
        metadata={"role": "worker"},
    )
    result = agent.run("do the slow thing", VerificationContext(cwd=tmp_path))

    assert result.passed is False
    assert result.exit_code == 124
    assert "started" in result.stdout
    assert "timed out" in result.stderr
    assert result.metadata["role"] == "worker"
    assert result.metadata["timed_out"] is True
    assert result.metadata["timeout_s"] == 0.2
    assert result.metadata["error_type"] == "TimeoutExpired"


def test_local_command_agent_records_missing_command_as_failed_run(tmp_path: Path):
    agent = LocalCommandAgent(
        ["missing-vo-agent-command"],
        name="missing-agent",
        metadata={"role": "worker"},
    )

    result = agent.run("run missing command", VerificationContext(cwd=tmp_path))

    assert result.passed is False
    assert result.exit_code == 127
    assert result.stdout == ""
    assert "missing-vo-agent-command" in result.stderr
    assert result.metadata["role"] == "worker"
    assert result.metadata["error_type"] == "FileNotFoundError"
