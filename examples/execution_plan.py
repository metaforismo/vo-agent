from pathlib import Path

from quaestio import (
    AgentSpec,
    ComputeResources,
    EnvironmentSpec,
    TaskGraph,
    TaskSpec,
    WorkflowRun,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "work"
    work.mkdir(exist_ok=True)

    run = WorkflowRun(name="execution-plan-demo", artifact_root=work)
    run.add_agent(AgentSpec(name="searcher", goal="Find candidate approaches"))
    run.add_agent(AgentSpec(name="benchmarker", goal="Run hard tests"))
    run.add_agent(AgentSpec(name="critic", goal="Challenge candidate outputs"))
    run.add_agent(AgentSpec(name="writer", goal="Write final report"))

    run.add_environment(
        EnvironmentSpec(
            name="cpu-worker",
            kind="vm",
            image="ubuntu:24.04",
            resources=ComputeResources(cpu=4, memory_gb=8),
            setup_commands=("uv sync",),
        )
    )
    run.add_environment(
        EnvironmentSpec(
            name="gpu-worker",
            kind="vm",
            image="ubuntu:24.04",
            resources=ComputeResources(cpu=8, memory_gb=32, gpu_count=1),
            setup_commands=("uv sync --extra gpu",),
        )
    )
    run.assign_agent_environment("searcher", "cpu-worker")
    run.assign_agent_environment("benchmarker", "gpu-worker")
    run.assign_agent_environment("critic", "cpu-worker")
    run.assign_agent_environment("writer", "cpu-worker")

    graph = TaskGraph(name="autoresearch-plan")
    graph.add_task(
        TaskSpec(
            name="search",
            agent_name="searcher",
            task="Find three candidate optimization ideas.",
            resources=("repo:notes",),
        )
    )
    graph.add_task(
        TaskSpec(
            name="redteam",
            agent_name="critic",
            task="Find flaws in the candidate ideas.",
            resources=("repo:notes",),
        )
    )
    graph.add_task(
        TaskSpec(
            name="benchmark",
            agent_name="benchmarker",
            task="Run the benchmark harness on the best candidate.",
            depends_on=("search",),
            resources=("gpu:0",),
        )
    )
    graph.add_task(
        TaskSpec(
            name="report",
            agent_name="writer",
            task="Summarize the accepted result and evidence.",
            depends_on=("benchmark", "redteam"),
            resources=("repo:report",),
        )
    )
    run.add_task_graph(graph)
    run.plan_task_graph(graph)

    bundle_path = run.write_bundle(work / "execution-plan-bundle.json")
    report_path = run.write_report(work / "execution-plan-report.md")
    print(bundle_path.relative_to(root))
    print(report_path.relative_to(root))


if __name__ == "__main__":
    main()
