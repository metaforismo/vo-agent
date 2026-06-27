from __future__ import annotations

import json
from pathlib import Path

import pytest

from vo import (
    AgentRun,
    AgentSpec,
    ReviewPanel,
    ReviewPolicy,
    WorkflowRun,
)
from vo.models import utc_now


class ReviewAgent:
    def __init__(self, name: str, stdout: str, exit_code: int = 0) -> None:
        self.name = name
        self.stdout = stdout
        self.exit_code = exit_code

    def run(self, task, context=None):
        del context
        now = utc_now()
        return AgentRun(
            agent_name=self.name,
            task=task,
            command=["review-agent"],
            exit_code=self.exit_code,
            stdout=self.stdout,
            stderr="" if self.exit_code == 0 else "reviewer failed\n",
            duration_s=0.0,
            started_at=now,
            finished_at=now,
        )


def make_run() -> WorkflowRun:
    run = WorkflowRun(name="review workflow")
    run.add_agent(AgentSpec(name="critic", goal="Challenge the claim"))
    run.add_agent(AgentSpec(name="checker", goal="Check the claim"))
    return run


def make_panel() -> ReviewPanel:
    return ReviewPanel(
        name="proof-review",
        reviewer_names=("critic", "checker"),
        policy=ReviewPolicy(min_approvals=2),
    )


def test_workflow_registers_review_panel() -> None:
    run = make_run()
    panel = make_panel()

    registered = run.add_review_panel(panel)

    assert registered is panel
    assert run.review_panels == [panel]
    assert run.events[-1].type == "review_panel_added"


def test_workflow_rejects_duplicate_review_panel_names() -> None:
    run = make_run()
    run.add_review_panel(make_panel())

    with pytest.raises(ValueError, match="review panel 'proof-review' already exists"):
        run.add_review_panel(make_panel())


def test_review_panel_approves_claim_when_quorum_is_met() -> None:
    run = make_run()
    claim = run.claim("candidate proof is ready")
    panel = make_panel()
    run.add_review_panel(panel)

    result = run.run_review_panel(
        panel,
        claim,
        {
            "critic": ReviewAgent("critic", "decision: approve\ncomment: solid\n"),
            "checker": ReviewAgent("checker", "decision: approve\ncomment: verified\n"),
        },
    )

    assert result is panel
    assert panel.status == "approved"
    assert panel.stop_reason == "quorum_approved"
    assert claim.status == "accepted"
    assert [evidence.kind for evidence in claim.evidence] == ["review", "review"]
    assert [item.decision for item in panel.results] == ["approve", "approve"]
    assert len(run.agent_runs) == 2


def test_review_panel_rejects_claim_on_hard_reject() -> None:
    run = make_run()
    claim = run.claim("candidate proof is ready")
    panel = make_panel()
    run.add_review_panel(panel)

    run.run_review_panel(
        panel,
        claim,
        {
            "critic": ReviewAgent("critic", "decision: approve\n"),
            "checker": ReviewAgent("checker", "decision: reject\ncomment: false lemma\n"),
        },
    )

    assert panel.status == "rejected"
    assert panel.stop_reason == "reviewer_rejected"
    assert claim.status == "rejected"


def test_invalid_review_output_fails_panel_and_leaves_claim_pending() -> None:
    run = make_run()
    claim = run.claim("candidate proof is ready")
    panel = make_panel()
    run.add_review_panel(panel)

    run.run_review_panel(
        panel,
        claim,
        {
            "critic": ReviewAgent("critic", "decision: approve\n"),
            "checker": ReviewAgent("checker", "no protocol here\n"),
        },
    )

    assert panel.status == "failed"
    assert panel.stop_reason == "invalid_review"
    assert claim.status == "pending"
    assert panel.results[1].decision == "invalid"


def test_reviewer_agent_failure_fails_panel_and_leaves_claim_pending() -> None:
    run = make_run()
    claim = run.claim("candidate proof is ready")
    panel = make_panel()
    run.add_review_panel(panel)

    run.run_review_panel(
        panel,
        claim,
        {
            "critic": ReviewAgent("critic", "decision: approve\n"),
            "checker": ReviewAgent("checker", "", exit_code=1),
        },
    )

    assert panel.status == "failed"
    assert panel.stop_reason == "reviewer_failed"
    assert claim.status == "pending"
    assert panel.results[1].decision == "failed"


def test_review_panel_bundle_and_events(tmp_path: Path) -> None:
    run = make_run()
    claim = run.claim("candidate proof is ready")
    panel = make_panel()
    run.add_review_panel(panel)
    run.run_review_panel(
        panel,
        claim,
        {
            "critic": ReviewAgent("critic", "decision: approve\n"),
            "checker": ReviewAgent("checker", "decision: approve\n"),
        },
    )

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["review_panels"][0]["name"] == "proof-review"
    assert bundle["review_panels"][0]["status"] == "approved"
    assert bundle["review_panels"][0]["results"][0]["decision"] == "approve"
    event_types = [event["type"] for event in bundle["events"]]
    assert "review_panel_started" in event_types
    assert "review_result_recorded" in event_types
    assert "review_panel_finished" in event_types
