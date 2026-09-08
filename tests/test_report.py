from __future__ import annotations

from quaestio import (
    AgentRun,
    AgentSpec,
    Budget,
    CallableVerifier,
    ComputeResources,
    EnvironmentSpec,
    IterationLoop,
    IterationPolicy,
    LocalProvisioner,
    ReviewPanel,
    ReviewPolicy,
    StateMachine,
    TaskGraph,
    TaskSpec,
    VerifierChain,
    WorkflowRun,
)
from quaestio.models import Evidence, utc_now
from quaestio.report import render_markdown_report


class ReportAgent:
    name = "solver"

    def run(self, task, context=None):
        now = utc_now()
        return AgentRun(
            agent_name=self.name,
            task=task,
            command=["report-agent"],
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_s=0.01,
            started_at=now,
            finished_at=now,
        )


def test_render_markdown_report_summarizes_workflow_state(tmp_path) -> None:
    artifact = tmp_path / "answer.txt"
    artifact.write_text("42\n", encoding="utf-8")
    run = WorkflowRun(
        name="inspection run",
        artifact_root=tmp_path,
        budget=Budget(limit=2.0),
    )
    run.add_agent(AgentSpec(name="solver", goal="produce candidate"))
    run.send_message("user", "please inspect the candidate", recipient="solver")
    run.send_message(
        "solver",
        "candidate is ready",
        recipient="user",
        role="agent",
    )
    run.add_environment(
        EnvironmentSpec(
            name="local-dev",
            kind="local",
            resources=ComputeResources(cpu=2, memory_gb=4),
        )
    )
    run.assign_agent_environment("solver", "local-dev")
    machine = StateMachine(name="research-loop", initial_state="drafting")
    machine.on("drafting", "candidate_ready", "verifying")
    run.add_state_machine(machine)
    run.dispatch("research-loop", "candidate_ready")
    loop = IterationLoop(
        name="hard-test-loop",
        agent_name="solver",
        task="make tests pass",
        policy=IterationPolicy(max_attempts=2),
    )
    run.add_iteration_loop(loop)
    panel = ReviewPanel(
        name="proof-review",
        reviewer_names=("solver",),
        policy=ReviewPolicy(min_approvals=1),
    )
    run.add_review_panel(panel)
    graph = TaskGraph(name="research-plan")
    graph.add_task(TaskSpec(name="search", agent_name="solver", task="search"))
    run.add_task_graph(graph)
    plan = run.plan_task_graph(graph)
    run.provision_execution_plan(plan, LocalProvisioner(metadata={"mode": "dry-run"}))
    run.execute_execution_plan(plan, {"solver": ReportAgent()})
    run.spend_budget(0.5, label="solver round")
    run.artifacts.register(artifact, kind="text")
    claim = run.claim("candidate passes invariant")
    run.verify(
        claim,
        VerifierChain(
            [
                CallableVerifier(
                    lambda _context: Evidence(
                        name="invariant",
                        passed=True,
                        summary="ok",
                    )
                )
            ]
        ),
    )

    report = render_markdown_report(run)

    assert "# inspection run" in report
    assert "- Claims: 1 accepted, 0 rejected, 0 pending" in report
    assert "- State machines: 1" in report
    assert "- Iteration loops: 1" in report
    assert "- Review panels: 1" in report
    assert "- Task graphs: 1" in report
    assert "- Execution plans: 1" in report
    assert "- Provisioning results: 1" in report
    assert "- Plan execution results: 1" in report
    assert "- Messages: 2" in report
    assert "- Environments: 1" in report
    assert "- Agent placements: 1" in report
    assert "- Budget: 0.5 / 2.0 units" in report
    assert "| local-dev | local |  | 2 | 4 | 0 | 0 |" in report
    assert "| solver | local-dev |" in report
    assert "| research-loop | verifying | 1 |" in report
    assert "| hard-test-loop | pending | 0 |  |" in report
    assert "| proof-review | pending | 0 | 0 |  |" in report
    assert "| research-plan | pending | 1 | 0 | 0 | 0 |  |" in report
    assert "| research-plan-execution | research-plan | 1 | 1 | local-dev |" in report
    assert "| research-plan-execution | local | ready | 1 |" in report
    assert "| research-plan-execution | passed | 1 | 1 | 1 | 0 |" in report
    assert "| user | solver | user | default | please inspect the candidate |" in report
    assert "| solver | user | agent | default | candidate is ready |" in report
    assert "| accepted | candidate passes invariant |" in report
    assert "| text | answer.txt |" in report


def test_workflow_can_write_markdown_report(tmp_path) -> None:
    run = WorkflowRun(name="writeable report")
    report_path = tmp_path / "report.md"

    written = run.write_report(report_path)

    assert written == report_path
    assert report_path.read_text(encoding="utf-8").startswith("# writeable report")


def test_render_markdown_report_accepts_loaded_bundle() -> None:
    bundle = WorkflowRun(name="loaded report").to_dict()

    report = render_markdown_report(bundle)

    assert "# loaded report" in report
    assert "- Agents: 0" in report


def test_render_markdown_report_shows_agent_run_status_and_metadata() -> None:
    now = utc_now()
    run = WorkflowRun(name="failed agent report")
    run.agent_runs.append(
        AgentRun(
            agent_name="solver",
            task="solve hard case",
            command=["solver"],
            exit_code=-1,
            stdout="",
            stderr="adapter exploded",
            duration_s=0.01,
            started_at=now,
            finished_at=now,
            metadata={"error_type": "RuntimeError", "environment": "local-dev"},
        )
    )

    report = render_markdown_report(run)

    assert "| solver | solve hard case | failed | -1 | 0.01s |" in report
    assert "error_type=RuntimeError" in report
    assert "environment=local-dev" in report
