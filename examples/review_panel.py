from pathlib import Path

from vo import AgentSpec, LocalCommandAgent, ReviewPanel, ReviewPolicy, WorkflowRun


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "work"
    work.mkdir(exist_ok=True)

    critic_script = work / "critic-reviewer.py"
    critic_script.write_text(
        "print('decision: approve')\n"
        "print('comment: proof handles the stated invariant')\n",
        encoding="utf-8",
    )
    checker_script = work / "checker-reviewer.py"
    checker_script.write_text(
        "print('decision: approve')\n"
        "print('comment: tests and claim are aligned')\n",
        encoding="utf-8",
    )

    run = WorkflowRun(name="review-panel-demo")
    run.add_agent(AgentSpec(name="critic", goal="Challenge the candidate claim"))
    run.add_agent(AgentSpec(name="checker", goal="Check the candidate claim"))

    claim = run.claim(
        "candidate proof is ready for the next stage",
        artifact="proof-sketch.md",
    )
    panel = ReviewPanel(
        name="proof-review",
        reviewer_names=("critic", "checker"),
        policy=ReviewPolicy(min_approvals=2),
    )
    run.add_review_panel(panel)
    run.run_review_panel(
        panel,
        claim,
        {
            "critic": LocalCommandAgent(["python", str(critic_script)], name="critic"),
            "checker": LocalCommandAgent(["python", str(checker_script)], name="checker"),
        },
    )

    bundle_path = run.write_bundle(work / "review-panel-bundle.json")
    report_path = run.write_report(work / "review-panel-report.md")
    print(bundle_path.relative_to(root))
    print(report_path.relative_to(root))


if __name__ == "__main__":
    main()
