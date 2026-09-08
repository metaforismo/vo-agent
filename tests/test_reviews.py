from __future__ import annotations

import pytest

from quaestio import (
    ReviewPanel,
    ReviewParseError,
    ReviewPolicy,
    ReviewResult,
    parse_review_decision,
)
from quaestio.agents import AgentRun
from quaestio.models import utc_now


def agent_run(stdout: str, *, reviewer: str = "critic", exit_code: int = 0) -> AgentRun:
    now = utc_now()
    return AgentRun(
        agent_name=reviewer,
        task="review claim",
        command=["reviewer"],
        exit_code=exit_code,
        stdout=stdout,
        stderr="" if exit_code == 0 else "failed\n",
        duration_s=0.0,
        started_at=now,
        finished_at=now,
    )


def test_review_policy_requires_positive_min_approvals() -> None:
    with pytest.raises(ValueError, match="min_approvals must be at least 1"):
        ReviewPolicy(min_approvals=0)


def test_review_panel_requires_reviewers() -> None:
    with pytest.raises(ValueError, match="reviewer_names must not be empty"):
        ReviewPanel(
            name="empty-panel",
            reviewer_names=(),
            policy=ReviewPolicy(min_approvals=1),
        )


def test_review_panel_rejects_impossible_quorum() -> None:
    with pytest.raises(ValueError, match="min_approvals cannot exceed reviewers"):
        ReviewPanel(
            name="impossible-panel",
            reviewer_names=("critic",),
            policy=ReviewPolicy(min_approvals=2),
        )


def test_parse_review_decision_accepts_approve_and_comment() -> None:
    parsed = parse_review_decision("decision: approve\ncomment: proof is tight\n")

    assert parsed == {"decision": "approve", "comment": "proof is tight"}


def test_parse_review_decision_accepts_freeform_comment_text() -> None:
    parsed = parse_review_decision("decision: revise\nNeeds a stronger lemma.\n")

    assert parsed == {"decision": "revise", "comment": "Needs a stronger lemma."}


def test_parse_review_decision_rejects_missing_decision() -> None:
    with pytest.raises(ReviewParseError, match="missing decision"):
        parse_review_decision("looks good\n")


def test_parse_review_decision_rejects_unknown_decision() -> None:
    with pytest.raises(ReviewParseError, match="unknown decision"):
        parse_review_decision("decision: maybe\n")


def test_review_panel_resolves_approved_quorum() -> None:
    panel = ReviewPanel(
        name="proof-review",
        reviewer_names=("critic", "checker"),
        policy=ReviewPolicy(min_approvals=2),
    )
    panel.record_result(
        ReviewResult(
            reviewer_name="critic",
            agent_run=agent_run("decision: approve\n", reviewer="critic"),
            decision="approve",
            comment="ok",
        )
    )
    panel.record_result(
        ReviewResult(
            reviewer_name="checker",
            agent_run=agent_run("decision: approve\n", reviewer="checker"),
            decision="approve",
            comment="ok",
        )
    )

    panel.resolve()

    assert panel.status == "approved"
    assert panel.stop_reason == "quorum_approved"
    assert panel.to_dict()["approval_count"] == 2
