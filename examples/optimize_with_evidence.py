from pathlib import Path

from vo import (
    AgentSpec,
    Budget,
    CommandVerifier,
    VerificationContext,
    VerifierChain,
    WorkflowRun,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    run = WorkflowRun(name="toy-optimization", budget=Budget(limit=1.0, unit="usd"))
    run.add_agent(
        AgentSpec(
            name="optimizer",
            goal="Improve a toy benchmark while preserving tests.",
            model="local-placeholder",
            tools=("shell", "edit"),
        )
    )
    run.resources.acquire("repo:toy_benchmark.py", owner="optimizer")
    run.spend_budget(0.20, label="optimizer proposal", metadata={"agent": "optimizer"})

    claim = run.claim("toy benchmark is safe to merge", metric="toy_latency")
    chain = VerifierChain(
        [
            CommandVerifier("python -c 'print(\"tests ok\")'", name="tests"),
            CommandVerifier(
                "python -c 'print(\"toy_latency_ms=12.3\")'",
                name="benchmark",
            ),
        ]
    )

    result = run.verify(claim, chain, VerificationContext(cwd=root))
    if not result.passed:
        raise SystemExit("verification failed")

    bundle_path = run.write_bundle(root / "work" / "example-run-bundle.json")
    report_path = run.write_report(root / "work" / "example-run-report.md")
    print(bundle_path.relative_to(root))
    print(report_path.relative_to(root))


if __name__ == "__main__":
    main()
