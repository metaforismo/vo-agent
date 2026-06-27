from pathlib import Path

from vo import AgentSpec, Budget, StateMachine, WorkflowRun


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "work"
    work.mkdir(exist_ok=True)

    run = WorkflowRun(name="state-machine-demo", budget=Budget(limit=3.0, unit="usd"))
    run.add_agent(
        AgentSpec(
            name="solver",
            goal="Produce a candidate and revise it until verification passes.",
        )
    )
    run.add_agent(
        AgentSpec(
            name="verifier",
            goal="Check the candidate and decide whether the loop can finish.",
        )
    )

    machine = StateMachine(
        name="verification-loop",
        initial_state="drafting",
        data={"attempts": 0},
    )
    machine.on("drafting", "candidate_ready", "verifying")

    def schedule_retry(context):
        attempts = context.data["attempts"] + 1
        context.emit("retry_scheduled", {"attempt": attempts})
        return {
            "attempts": attempts,
            "last_failure": context.event.data["reason"],
        }

    machine.on(
        "verifying",
        "verification_finished",
        "accepted",
        guard=lambda context: context.event.data["passed"] is True,
    )
    machine.on(
        "verifying",
        "verification_finished",
        "drafting",
        guard=lambda context: context.event.data["passed"] is False,
        handler=schedule_retry,
    )
    run.add_state_machine(machine)

    run.spend_budget(0.50, label="solver draft", metadata={"agent": "solver"})
    run.dispatch("verification-loop", "candidate_ready", {"candidate": "proof-v1"})
    run.spend_budget(0.25, label="verifier check", metadata={"agent": "verifier"})
    run.dispatch(
        "verification-loop",
        "verification_finished",
        {"passed": False, "reason": "missing lemma"},
    )
    run.spend_budget(0.60, label="solver retry", metadata={"agent": "solver"})
    run.dispatch("verification-loop", "candidate_ready", {"candidate": "proof-v2"})
    run.spend_budget(0.25, label="verifier check", metadata={"agent": "verifier"})
    run.dispatch("verification-loop", "verification_finished", {"passed": True})

    bundle_path = run.write_bundle(work / "state-machine-bundle.json")
    report_path = run.write_report(work / "state-machine-report.md")
    print(bundle_path.relative_to(root))
    print(report_path.relative_to(root))


if __name__ == "__main__":
    main()
