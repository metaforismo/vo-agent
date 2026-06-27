from pathlib import Path

from vo import AgentSpec, WorkflowRun


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "work"
    work.mkdir(exist_ok=True)

    run = WorkflowRun(name="messaging-demo", artifact_root=work)
    run.add_agent(AgentSpec(name="solver", goal="Solve the candidate problem"))
    run.add_agent(AgentSpec(name="critic", goal="Challenge the solver output"))

    run.send_message(
        "user",
        "Try the geometry candidate first.",
        recipient="solver",
        thread="geometry",
        metadata={"priority": "high"},
    )
    run.send_message(
        "solver",
        "I found a candidate proof sketch.",
        recipient="critic",
        role="agent",
        thread="geometry",
    )
    run.send_message(
        "critic",
        "The proof sketch needs a boundary-case check.",
        recipient="user",
        role="agent",
        thread="geometry",
    )

    solver_inbox = run.messages_for("solver")
    print(f"solver inbox: {len(solver_inbox)}")

    bundle_path = run.write_bundle(work / "messaging-bundle.json")
    report_path = run.write_report(work / "messaging-report.md")
    print(bundle_path.relative_to(root))
    print(report_path.relative_to(root))


if __name__ == "__main__":
    main()
