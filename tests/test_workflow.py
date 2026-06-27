import json
from pathlib import Path

from vo import AgentSpec, CommandVerifier, VerificationContext, VerifierChain, WorkflowRun


def test_workflow_run_records_agents_claims_evidence_and_bundle(tmp_path: Path):
    run = WorkflowRun(name="parser-speed")
    run.add_agent(AgentSpec(name="optimizer", goal="Improve parser latency"))
    run.resources.acquire("repo:src/parser.py", owner="optimizer")
    claim = run.claim("parser latency improved", metric="latency")

    chain = VerifierChain([CommandVerifier("python -c 'print(\"ok\")'", name="tests")])
    result = run.verify(claim, chain, VerificationContext(cwd=tmp_path))

    bundle_path = run.write_bundle(tmp_path / "run-bundle.json")
    bundle = json.loads(bundle_path.read_text())

    assert result.passed is True
    assert bundle["name"] == "parser-speed"
    assert bundle["agents"][0]["name"] == "optimizer"
    assert bundle["claims"][0]["status"] == "accepted"
    assert bundle["claims"][0]["metadata"] == {"metric": "latency"}
    assert bundle["claims"][0]["evidence"][0]["name"] == "tests"
    assert bundle["resources"]["repo:src/parser.py"]["owner"] == "optimizer"
