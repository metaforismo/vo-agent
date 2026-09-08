from pathlib import Path

from quaestio import Claim, CommandVerifier, VerificationContext, VerifierChain


def test_verifier_chain_accepts_claim_when_all_checks_pass(tmp_path: Path):
    claim = Claim(statement="tests pass before merge")
    chain = VerifierChain(
        [
            CommandVerifier("python -c 'print(42)'", name="smoke"),
            CommandVerifier("python -c 'raise SystemExit(0)'", name="exit-zero"),
        ]
    )

    result = chain.verify(claim, VerificationContext(cwd=tmp_path))

    assert result.passed is True
    assert claim.status == "accepted"
    assert [e.name for e in claim.evidence] == ["smoke", "exit-zero"]
    assert claim.evidence[0].data["stdout"].strip() == "42"


def test_verifier_chain_rejects_claim_on_first_failing_check(tmp_path: Path):
    claim = Claim(statement="benchmark improved")
    chain = VerifierChain(
        [
            CommandVerifier("python -c 'print(\"before\")'", name="before"),
            CommandVerifier("python -c 'raise SystemExit(7)'", name="benchmark"),
            CommandVerifier("python -c 'print(\"after\")'", name="after"),
        ]
    )

    result = chain.verify(claim, VerificationContext(cwd=tmp_path))

    assert result.passed is False
    assert claim.status == "rejected"
    assert [e.name for e in claim.evidence] == ["before", "benchmark"]
    assert claim.evidence[-1].data["exit_code"] == 7
