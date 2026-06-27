from pathlib import Path

from vo import (
    AgentSpec,
    ComputeResources,
    EnvironmentSpec,
    LocalProvisioner,
    TaskGraph,
    TaskSpec,
    WorkflowRun,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "work"
    work.mkdir(exist_ok=True)

    run = WorkflowRun(name="provisioning-demo", artifact_root=work)
    run.add_agent(AgentSpec(name="solver", goal="Solve the benchmark task"))
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

    graph = TaskGraph(name="solver-plan")
    graph.add_task(
        TaskSpec(
            name="solve",
            agent_name="solver",
            task="Solve the benchmark task and write evidence.",
            resources=("repo:solution",),
        )
    )
    run.add_task_graph(graph)
    plan = run.plan_task_graph(graph)
    run.provision_execution_plan(
        plan,
        LocalProvisioner(metadata={"mode": "dry-run"}),
    )

    bundle_path = run.write_bundle(work / "provisioning-bundle.json")
    report_path = run.write_report(work / "provisioning-report.md")
    print(bundle_path.relative_to(root))
    print(report_path.relative_to(root))


if __name__ == "__main__":
    main()
