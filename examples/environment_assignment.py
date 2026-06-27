from pathlib import Path

from vo import (
    AgentSpec,
    ComputeResources,
    EnvironmentSpec,
    LocalCommandAgent,
    VerificationContext,
    WorkflowRun,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "work"
    work.mkdir(exist_ok=True)

    script = work / "environment-agent.py"
    script.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "task = sys.stdin.read().strip()\n"
        "Path('environment-output.txt').write_text(\n"
        "    f'assigned task: {task}\\n',\n"
        "    encoding='utf-8',\n"
        ")\n"
        "print('environment assignment complete')\n",
        encoding="utf-8",
    )

    run = WorkflowRun(name="environment-assignment-demo", artifact_root=work)
    run.add_agent(AgentSpec(name="writer", goal="Write a placement proof"))
    run.add_environment(
        EnvironmentSpec(
            name="local-dev",
            kind="local",
            image="python:3.13",
            resources=ComputeResources(cpu=2, memory_gb=4),
            setup_commands=("uv sync",),
            env={"PYTHONUNBUFFERED": "1"},
            secret_names=("OPENAI_API_KEY",),
            metadata={"pool": "developer-machine"},
        )
    )
    run.add_environment(
        EnvironmentSpec(
            name="gpu-worker",
            kind="vm",
            image="ubuntu:24.04",
            resources=ComputeResources(cpu=8, memory_gb=32, gpu_count=1),
            setup_commands=("uv sync --extra gpu",),
            secret_names=("WANDB_API_KEY",),
            metadata={"pool": "prewarmed-cloud"},
        )
    )
    run.assign_agent_environment("writer", "local-dev")

    result = run.run_agent(
        "writer",
        LocalCommandAgent(["python", str(script)], name="writer"),
        "record the environment assignment",
        VerificationContext(cwd=work),
    )
    if not result.passed:
        raise SystemExit(result.stderr or "environment agent failed")

    run.artifacts.register(
        work / "environment-output.txt",
        kind="placement-proof",
        metadata={"agent": "writer", "environment": "local-dev"},
    )
    bundle_path = run.write_bundle(work / "environment-assignment-bundle.json")
    report_path = run.write_report(work / "environment-assignment-report.md")
    print(bundle_path.relative_to(root))
    print(report_path.relative_to(root))


if __name__ == "__main__":
    main()
