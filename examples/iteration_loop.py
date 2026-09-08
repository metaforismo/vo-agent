from pathlib import Path

from quaestio import (
    AgentSpec,
    Budget,
    CommandVerifier,
    IterationLoop,
    IterationPolicy,
    LocalCommandAgent,
    VerificationContext,
    VerifierChain,
    WorkflowRun,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "work"
    work.mkdir(exist_ok=True)

    counter = work / "iteration-counter.txt"
    answer = work / "iteration-answer.txt"
    counter.write_text("0", encoding="utf-8")

    script = work / "iteration-agent-script.py"
    script.write_text(
        "from pathlib import Path\n"
        "counter = Path('iteration-counter.txt')\n"
        "answer = Path('iteration-answer.txt')\n"
        "attempt = int(counter.read_text(encoding='utf-8')) + 1\n"
        "counter.write_text(str(attempt), encoding='utf-8')\n"
        "answer.write_text('ok\\n' if attempt >= 2 else 'bad\\n', encoding='utf-8')\n"
        "print(f'wrote candidate attempt {attempt}')\n",
        encoding="utf-8",
    )

    run = WorkflowRun(
        name="iteration-loop-demo",
        artifact_root=work,
        budget=Budget(limit=2.0, unit="usd"),
    )
    run.add_agent(
        AgentSpec(
            name="solver",
            goal="Revise a candidate until the hard verifier passes.",
        )
    )

    loop = IterationLoop(
        name="hard-test-loop",
        agent_name="solver",
        task="Write 'ok' into iteration-answer.txt.",
        policy=IterationPolicy(
            max_attempts=3,
            budget_per_attempt=0.25,
            budget_label="solver attempt",
        ),
    )
    run.add_iteration_loop(loop)

    verifier = CommandVerifier(
        "python -c \"from pathlib import Path; "
        "raise SystemExit(0 if Path('iteration-answer.txt').read_text().strip() "
        "== 'ok' else 1)\"",
        name="answer-is-ok",
    )
    run.iterate_until_verified(
        loop,
        LocalCommandAgent(["python", str(script)], name="solver"),
        VerifierChain([verifier]),
        VerificationContext(cwd=work),
    )

    run.artifacts.register(answer, kind="candidate", metadata={"loop": loop.name})
    bundle_path = run.write_bundle(work / "iteration-loop-bundle.json")
    report_path = run.write_report(work / "iteration-loop-report.md")
    print(bundle_path.relative_to(root))
    print(report_path.relative_to(root))


if __name__ == "__main__":
    main()
