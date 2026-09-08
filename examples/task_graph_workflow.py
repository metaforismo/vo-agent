from pathlib import Path

from quaestio import (
    AgentSpec,
    LocalCommandAgent,
    TaskGraph,
    TaskSpec,
    VerificationContext,
    WorkflowRun,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "work"
    work.mkdir(exist_ok=True)

    script = work / "task-graph-agent.py"
    script.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "task = sys.stdin.read().strip()\n"
        "if task == 'alpha':\n"
        "    Path('alpha.txt').write_text('alpha\\n', encoding='utf-8')\n"
        "elif task == 'beta':\n"
        "    Path('beta.txt').write_text('beta\\n', encoding='utf-8')\n"
        "elif task == 'combine':\n"
        "    alpha = Path('alpha.txt').read_text(encoding='utf-8').strip()\n"
        "    beta = Path('beta.txt').read_text(encoding='utf-8').strip()\n"
        "    Path('combined.txt').write_text(f'{alpha}+{beta}\\n', encoding='utf-8')\n"
        "else:\n"
        "    raise SystemExit(f'unknown task: {task}')\n"
        "print(f'done {task}')\n",
        encoding="utf-8",
    )

    run = WorkflowRun(name="task-graph-demo", artifact_root=work)
    run.add_agent(AgentSpec(name="alpha", goal="Produce the alpha artifact"))
    run.add_agent(AgentSpec(name="beta", goal="Produce the beta artifact"))
    run.add_agent(AgentSpec(name="integrator", goal="Combine upstream artifacts"))

    graph = TaskGraph(name="artifact-plan")
    graph.add_task(
        TaskSpec(
            name="alpha",
            agent_name="alpha",
            task="alpha",
            resources=("artifact:alpha",),
        )
    )
    graph.add_task(
        TaskSpec(
            name="beta",
            agent_name="beta",
            task="beta",
            resources=("artifact:beta",),
        )
    )
    graph.add_task(
        TaskSpec(
            name="combine",
            agent_name="integrator",
            task="combine",
            depends_on=("alpha", "beta"),
            resources=("artifact:combined",),
        )
    )
    run.add_task_graph(graph)
    run.run_task_graph(
        graph,
        {
            "alpha": LocalCommandAgent(["python", str(script)], name="alpha"),
            "beta": LocalCommandAgent(["python", str(script)], name="beta"),
            "integrator": LocalCommandAgent(["python", str(script)], name="integrator"),
        },
        VerificationContext(cwd=work),
    )

    run.artifacts.register(
        work / "combined.txt",
        kind="combined-artifact",
        metadata={"graph": graph.name},
    )
    bundle_path = run.write_bundle(work / "task-graph-bundle.json")
    report_path = run.write_report(work / "task-graph-report.md")
    print(bundle_path.relative_to(root))
    print(report_path.relative_to(root))


if __name__ == "__main__":
    main()
