from pathlib import Path

from vo import (
    AgentSpec,
    ComputeResources,
    EnvironmentSpec,
    LocalCommandAgent,
    LocalProvisioner,
    TaskGraph,
    TaskSpec,
    VerificationContext,
    WorkflowRun,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "work"
    work.mkdir(exist_ok=True)

    script = work / "plan-execution-agent.py"
    script.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "task = sys.stdin.read().strip()\n"
        "Path('plan-execution-output.txt').write_text(\n"
        "    f'executed: {task}\\n',\n"
        "    encoding='utf-8',\n"
        ")\n"
        "print(f'done {task}')\n",
        encoding="utf-8",
    )

    run = WorkflowRun(name="plan-execution-demo", artifact_root=work)
    run.add_agent(AgentSpec(name="solver", goal="Run the planned task"))
    run.add_environment(
        EnvironmentSpec(
            name="local-dev",
            kind="local",
            image="python:3.13",
            resources=ComputeResources(cpu=2, memory_gb=4),
            setup_commands=("uv sync",),
            metadata={"pool": "developer-machine"},
        )
    )
    run.assign_agent_environment("solver", "local-dev")

    graph = TaskGraph(name="solve-plan")
    graph.add_task(
        TaskSpec(
            name="solve",
            agent_name="solver",
            task="produce evidence",
            resources=("repo:evidence",),
        )
    )
    run.add_task_graph(graph)
    plan = run.plan_task_graph(graph)
    run.provision_execution_plan(plan, LocalProvisioner(metadata={"mode": "dry-run"}))
    result = run.execute_execution_plan(
        plan,
        {
            "solver": LocalCommandAgent(
                ["python", str(script)],
                name="solver",
            )
        },
        VerificationContext(cwd=work),
    )
    if result.status != "passed":
        raise SystemExit("plan execution failed")

    run.artifacts.register(
        work / "plan-execution-output.txt",
        kind="execution-output",
        metadata={"plan": plan.name},
    )
    bundle_path = run.write_bundle(work / "plan-execution-bundle.json")
    report_path = run.write_report(work / "plan-execution-report.md")
    print(bundle_path.relative_to(root))
    print(report_path.relative_to(root))


if __name__ == "__main__":
    main()
