from __future__ import annotations

import json
from pathlib import Path

import pytest

from vo import (
    AgentRun,
    AgentSpec,
    Evidence,
    IterationLoop,
    IterationPolicy,
    VerifierChain,
    WorkflowRun,
)
from vo.models import utc_now


class PassingAgent:
    name = "solver"

    def run(self, task, context=None):
        del context
        now = utc_now()
        return AgentRun(
            agent_name=self.name,
            task=task,
            command=["passing-agent"],
            exit_code=0,
            stdout="done\n",
            stderr="",
            duration_s=0.0,
            started_at=now,
            finished_at=now,
        )


class PassingVerifier:
    name = "hard-tests"

    def verify(self, claim, context):
        del claim, context
        return Evidence(name=self.name, passed=True, summary="ok")


def make_loop(name: str = "hard-test-loop") -> IterationLoop:
    return IterationLoop(
        name=name,
        agent_name="solver",
        task="make tests pass",
        policy=IterationPolicy(max_attempts=2),
    )


def make_run() -> WorkflowRun:
    run = WorkflowRun(name="iteration workflow")
    run.add_agent(AgentSpec(name="solver", goal="Make tests pass"))
    return run


def test_workflow_registers_iteration_loop() -> None:
    run = make_run()
    loop = make_loop()

    registered = run.add_iteration_loop(loop)

    assert registered is loop
    assert run.iteration_loops == [loop]
    assert run.events[-1].type == "iteration_loop_added"


def test_workflow_rejects_duplicate_iteration_loop_names() -> None:
    run = make_run()
    run.add_iteration_loop(make_loop("hard-test-loop"))

    with pytest.raises(ValueError, match="iteration loop 'hard-test-loop' already exists"):
        run.add_iteration_loop(make_loop("hard-test-loop"))


def test_workflow_rejects_running_unregistered_iteration_loop() -> None:
    run = make_run()

    with pytest.raises(ValueError, match="iteration loop does not belong"):
        run.iterate_until_verified(
            make_loop(),
            PassingAgent(),
            VerifierChain([PassingVerifier()]),
        )


def test_workflow_bundle_includes_iteration_loop_history(tmp_path: Path) -> None:
    run = make_run()
    loop = make_loop()
    run.add_iteration_loop(loop)
    run.iterate_until_verified(loop, PassingAgent(), VerifierChain([PassingVerifier()]))

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["iteration_loops"][0]["name"] == "hard-test-loop"
    assert bundle["iteration_loops"][0]["status"] == "passed"
    assert bundle["iteration_loops"][0]["attempts"][0]["passed"] is True
    assert bundle["iteration_loops"][0]["attempts"][0]["verification"]["passed"] is True


def test_workflow_iteration_events_are_recorded() -> None:
    run = make_run()
    loop = make_loop()
    run.add_iteration_loop(loop)

    run.iterate_until_verified(loop, PassingAgent(), VerifierChain([PassingVerifier()]))

    event_types = [event.type for event in run.events]
    assert "iteration_started" in event_types
    assert "iteration_attempt_started" in event_types
    assert "iteration_attempt_finished" in event_types
    assert "iteration_finished" in event_types
