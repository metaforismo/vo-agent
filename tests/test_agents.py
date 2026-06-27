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
