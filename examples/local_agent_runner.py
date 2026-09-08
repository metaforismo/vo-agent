import os
from pathlib import Path

from quaestio import (
    AgentSpec,
    Budget,
    LocalCommandAgent,
    VerificationContext,
    WorkflowRun,
    collect_provenance,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "work"
    work.mkdir(exist_ok=True)
    os.environ["VO_EXAMPLE_RUN"] = "local-agent"

    script = work / "local-agent-script.py"
    script.write_text(
        "import pathlib, sys\n"
        "task = sys.stdin.read().strip()\n"
        "pathlib.Path('local-agent-output.txt').write_text(\n"
        "    'summary: ' + task + '\\n',\n"
        "    encoding='utf-8',\n"
        ")\n"
        "print('summary written')\n",
        encoding="utf-8",
    )

    run = WorkflowRun(
        name="local-agent-demo",
        artifact_root=work,
        budget=Budget(limit=2.0, unit="usd"),
        provenance=collect_provenance(
            cwd=root,
            argv=["examples/local_agent_runner.py"],
            env_keys=["VO_EXAMPLE_RUN"],
        ),
    )
    run.add_agent(AgentSpec(name="writer", goal="Summarize a patch"))
    run.spend_budget(0.35, label="writer summary", metadata={"agent": "writer"})
    result = run.run_agent(
        "writer",
        LocalCommandAgent(["python", str(script)], name="writer"),
        "Summarize the parser optimization.",
        VerificationContext(cwd=work),
    )
    if not result.passed:
        raise SystemExit(result.stderr or "local agent failed")

    run.artifacts.register(
        work / "local-agent-output.txt",
        kind="summary",
        metadata={"agent": "writer"},
    )
    bundle_path = run.write_bundle(work / "local-agent-bundle.json")
    report_path = run.write_report(work / "local-agent-report.md")
    print(bundle_path.relative_to(root))
    print(report_path.relative_to(root))


if __name__ == "__main__":
    main()
