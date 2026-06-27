from pathlib import Path

from vo import AgentSpec, LocalCommandAgent, VerificationContext, WorkflowRun


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "work"
    work.mkdir(exist_ok=True)

    run = WorkflowRun(name="failed-agent-capture-demo")
    run.add_agent(AgentSpec(name="runner", goal="Try a command and record failure"))

    result = run.run_agent(
        "runner",
        LocalCommandAgent(["missing-vo-agent-command"], name="runner"),
        "Run the unavailable command.",
        VerificationContext(cwd=work),
    )

    bundle_path = run.write_bundle(work / "failed-agent-capture-bundle.json")
    report_path = run.write_report(work / "failed-agent-capture-report.md")

    print(result.passed)
    print(result.metadata["error_type"])
    print(bundle_path.relative_to(root))
    print(report_path.relative_to(root))


if __name__ == "__main__":
    main()
