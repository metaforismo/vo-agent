"""High-level workflow run object."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vo.agents import AgentAdapter, AgentRun
from vo.artifacts import ArtifactStore
from vo.budget import Budget, BudgetEntry
from vo.environments import EnvironmentSpec
from vo.exceptions import PlanExecutionError, StateMachineError
from vo.execution_plan import ExecutionPlan, build_execution_plan
from vo.iterations import IterationAttempt, IterationLoop
from vo.messages import Message, MessageLog
from vo.models import (
    AgentSpec,
    Claim,
    VerificationResult,
    WorkflowEvent,
    short_id,
    utc_now,
)
from vo.plan_execution import ExecutedTask, ExecutedWave, PlanExecutionResult
from vo.provenance import RunProvenance, collect_provenance
from vo.provisioning import Provisioner, ProvisioningResult
from vo.resources import ResourceManager
from vo.reviews import ReviewPanel, ReviewResult, parse_review_decision
from vo.state_machine import DispatchRecord, StateMachine
from vo.task_graph import TaskGraph
from vo.verifiers import VerificationContext, VerifierChain


@dataclass(slots=True)
class WorkflowRun:
    """Coordinates agents, resources, claims, evidence, and run export."""

    name: str
    artifact_root: str | Path | None = None
    provenance: RunProvenance | None = None
    budget: Budget | None = None
    run_id: str = field(default_factory=short_id)
    created_at: str = field(default_factory=utc_now)
    resources: ResourceManager = field(default_factory=ResourceManager)
    artifacts: ArtifactStore = field(init=False)
    agents: list[AgentSpec] = field(default_factory=list)
    environments: list[EnvironmentSpec] = field(default_factory=list)
    agent_environments: dict[str, str] = field(default_factory=dict)
    agent_runs: list[AgentRun] = field(default_factory=list)
    state_machines: list[StateMachine] = field(default_factory=list)
    iteration_loops: list[IterationLoop] = field(default_factory=list)
    review_panels: list[ReviewPanel] = field(default_factory=list)
    task_graphs: list[TaskGraph] = field(default_factory=list)
    execution_plans: list[ExecutionPlan] = field(default_factory=list)
    provisioning_results: list[ProvisioningResult] = field(default_factory=list)
    plan_execution_results: list[PlanExecutionResult] = field(default_factory=list)
    messages: MessageLog = field(default_factory=MessageLog)
    claims: list[Claim] = field(default_factory=list)
    events: list[WorkflowEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("workflow run name must not be empty")
        self.artifacts = ArtifactStore(root=self.artifact_root)
        if self.provenance is None:
            self.provenance = collect_provenance()
        self.record_event("run_created", {"name": self.name, "run_id": self.run_id})

    def add_agent(self, agent: AgentSpec) -> AgentSpec:
        if any(existing.name == agent.name for existing in self.agents):
            raise ValueError(f"agent {agent.name!r} already exists")
        self.agents.append(agent)
        self.record_event("agent_added", {"name": agent.name, "goal": agent.goal})
        return agent

    def add_environment(self, environment: EnvironmentSpec) -> EnvironmentSpec:
        if any(existing.name == environment.name for existing in self.environments):
            raise ValueError(f"environment {environment.name!r} already exists")
        self.environments.append(environment)
        self.record_event(
            "environment_added",
            {"name": environment.name, "kind": environment.kind},
        )
        return environment

    def assign_agent_environment(
        self,
        agent_name: str,
        environment_name: str,
    ) -> None:
        if not any(agent.name == agent_name for agent in self.agents):
            raise ValueError(f"agent {agent_name!r} is not registered")
        self._environment(environment_name)
        self.agent_environments[agent_name] = environment_name
        self.record_event(
            "agent_environment_assigned",
            {
                "agent_name": agent_name,
                "environment": environment_name,
            },
        )

    def add_state_machine(self, machine: StateMachine) -> StateMachine:
        if any(existing.name == machine.name for existing in self.state_machines):
            raise ValueError(f"state machine {machine.name!r} already exists")
        self.state_machines.append(machine)
        self.record_event(
            "state_machine_added",
            {
                "name": machine.name,
                "initial_state": machine.initial_state,
                "state": machine.state,
            },
        )
        return machine

    def add_iteration_loop(self, loop: IterationLoop) -> IterationLoop:
        if any(existing.name == loop.name for existing in self.iteration_loops):
            raise ValueError(f"iteration loop {loop.name!r} already exists")
        self.iteration_loops.append(loop)
        self.record_event(
            "iteration_loop_added",
            {
                "name": loop.name,
                "agent_name": loop.agent_name,
                "max_attempts": loop.policy.max_attempts,
            },
        )
        return loop

    def add_review_panel(self, panel: ReviewPanel) -> ReviewPanel:
        if any(existing.name == panel.name for existing in self.review_panels):
            raise ValueError(f"review panel {panel.name!r} already exists")
        self.review_panels.append(panel)
        self.record_event(
            "review_panel_added",
            {
                "name": panel.name,
                "reviewer_names": list(panel.reviewer_names),
                "min_approvals": panel.policy.min_approvals,
            },
        )
        return panel

    def add_task_graph(self, graph: TaskGraph) -> TaskGraph:
        if any(existing.name == graph.name for existing in self.task_graphs):
            raise ValueError(f"task graph {graph.name!r} already exists")
        graph.validate()
        self.task_graphs.append(graph)
        self.record_event(
            "task_graph_added",
            {"name": graph.name, "task_count": len(graph.tasks)},
        )
        return graph

    def plan_task_graph(self, graph: TaskGraph, *, name: str | None = None) -> ExecutionPlan:
        if graph not in self.task_graphs:
            raise ValueError("task graph does not belong to this workflow run")
        plan = build_execution_plan(
            graph,
            agent_environments=self.agent_environments,
            environments=self.environments,
            name=name,
        )
        self.execution_plans.append(plan)
        self.record_event(
            "execution_plan_created",
            {
                "name": plan.name,
                "graph": plan.graph_name,
                "waves": plan.wave_count,
                "tasks": plan.task_count,
            },
        )
        return plan

    def provision_execution_plan(
        self,
        plan: ExecutionPlan,
        provisioner: Provisioner,
    ) -> ProvisioningResult:
        if plan not in self.execution_plans:
            raise ValueError("execution plan does not belong to this workflow run")
        result = provisioner.provision(plan, self.environments)
        self.provisioning_results.append(result)
        self.record_event(
            "provisioning_finished",
            {
                "plan": result.plan_name,
                "provider": result.provider,
                "status": result.status,
                "environments": result.environment_count,
            },
        )
        return result

    def execute_execution_plan(
        self,
        plan: ExecutionPlan,
        adapters: dict[str, AgentAdapter],
        context: VerificationContext | None = None,
        *,
        require_provisioned: bool = True,
    ) -> PlanExecutionResult:
        if plan not in self.execution_plans:
            raise ValueError("execution plan does not belong to this workflow run")
        for wave in plan.waves:
            for task in wave.tasks:
                if task.agent_name not in adapters:
                    raise ValueError(f"missing adapter for agent {task.agent_name!r}")
        if require_provisioned and not self._has_ready_provisioning(plan.name):
            raise PlanExecutionError(
                f"execution plan {plan.name!r} has no ready provisioning result"
            )

        runtime_context = context or VerificationContext()
        executed_waves: list[ExecutedWave] = []
        self.record_event(
            "plan_execution_started",
            {"plan": plan.name, "waves": plan.wave_count, "tasks": plan.task_count},
        )

        for wave in plan.waves:
            self.record_event(
                "plan_wave_started",
                {
                    "plan": plan.name,
                    "wave": wave.index,
                    "tasks": [task.name for task in wave.tasks],
                },
            )
            executed_tasks = []
            for task in wave.tasks:
                agent_run = self.run_agent(
                    task.agent_name,
                    adapters[task.agent_name],
                    task.task,
                    runtime_context,
                )
                executed_tasks.append(
                    ExecutedTask(
                        name=task.name,
                        agent_name=task.agent_name,
                        environment=task.environment,
                        agent_run=agent_run,
                        metadata=dict(task.metadata),
                    )
                )
            executed_wave = ExecutedWave(index=wave.index, tasks=tuple(executed_tasks))
            executed_waves.append(executed_wave)
            self.record_event(
                "plan_wave_finished",
                {
                    "plan": plan.name,
                    "wave": wave.index,
                    "status": executed_wave.status,
                    "tasks": executed_wave.task_count,
                    "passed": executed_wave.passed_count,
                    "failed": executed_wave.failed_count,
                },
            )
            if executed_wave.status == "failed":
                break

        result = PlanExecutionResult(
            plan_name=plan.name,
            waves=tuple(executed_waves),
            metadata={"require_provisioned": require_provisioned},
        )
        self.plan_execution_results.append(result)
        self.record_event(
            "plan_execution_finished",
            {
                "plan": result.plan_name,
                "status": result.status,
                "waves": result.wave_count,
                "tasks": result.task_count,
                "passed": result.passed_count,
                "failed": result.failed_count,
            },
        )
        return result

    def send_message(
        self,
        sender: str,
        content: str,
        *,
        recipient: str | None = None,
        role: str = "user",
        thread: str = "default",
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        message = self.messages.append(
            Message(
                sender=sender,
                recipient=recipient,
                role=role,
                thread=thread,
                content=content,
                metadata=dict(metadata or {}),
            )
        )
        self.record_event(
            "message_sent",
            {
                "message_id": message.id,
                "sender": message.sender,
                "recipient": message.recipient,
                "role": message.role,
                "thread": message.thread,
            },
        )
        return message

    def messages_for(self, recipient: str) -> list[Message]:
        return self.messages.inbox(recipient)

    def claim(self, statement: str, **metadata: Any) -> Claim:
        claim = Claim(statement=statement, metadata=dict(metadata))
        self.claims.append(claim)
        self.record_event(
            "claim_created",
            {"claim_id": claim.id, "statement": statement},
        )
        return claim

    def record_event(self, type: str, data: dict[str, Any] | None = None) -> WorkflowEvent:
        event = WorkflowEvent(type=type, data=data or {})
        self.events.append(event)
        return event

    def spend_budget(
        self,
        amount: float,
        *,
        label: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> BudgetEntry:
        if self.budget is None:
            raise ValueError("workflow run does not declare a budget")
        entry = self.budget.spend(amount, label=label, metadata=metadata)
        self.record_event(
            "budget_spent",
            {
                "amount": entry.amount,
                "label": entry.label,
                "used": self.budget.used,
                "remaining": self.budget.remaining,
                "unit": self.budget.unit,
            },
        )
        return entry

    def dispatch(
        self,
        machine_name: str,
        event_type: str,
        data: dict[str, Any] | None = None,
        **event_data: Any,
    ) -> DispatchRecord:
        machine = self._state_machine(machine_name)
        record = machine.dispatch(event_type, data, **event_data)
        self.record_event(
            "state_machine_dispatched",
            {
                "machine": machine.name,
                "event_type": event_type,
                "from_state": record.from_state,
                "to_state": record.to_state,
                "passed": record.passed,
                "error": record.error,
            },
        )
        for emitted in record.emitted_events:
            self.record_event(
                "state_machine_emitted",
                {
                    "machine": machine.name,
                    "type": emitted["type"],
                    "data": emitted["data"],
                },
            )
        return record

    def verify(
        self,
        claim: Claim,
        chain: VerifierChain,
        context: VerificationContext | None = None,
    ) -> VerificationResult:
        if claim not in self.claims:
            raise ValueError("claim does not belong to this workflow run")
        self.record_event("verification_started", {"claim_id": claim.id})
        result = chain.verify(claim, context or VerificationContext())
        self.record_event(
            "verification_finished",
            {
                "claim_id": claim.id,
                "passed": result.passed,
                "failed_evidence": (
                    result.failed_evidence.name if result.failed_evidence else None
                ),
            },
        )
        return result

    def iterate_until_verified(
        self,
        loop: IterationLoop,
        adapter: AgentAdapter,
        verifier_chain: VerifierChain,
        context: VerificationContext | None = None,
    ) -> IterationLoop:
        if loop not in self.iteration_loops:
            raise ValueError("iteration loop does not belong to this workflow run")
        if not any(agent.name == loop.agent_name for agent in self.agents):
            raise ValueError(f"agent {loop.agent_name!r} is not registered in this run")

        loop.status = "running"
        loop.stop_reason = None
        self.record_event(
            "iteration_started",
            {
                "loop": loop.name,
                "agent_name": loop.agent_name,
                "max_attempts": loop.policy.max_attempts,
            },
        )
        runtime_context = context or VerificationContext()

        for attempt_index in range(len(loop.attempts) + 1, loop.policy.max_attempts + 1):
            self.record_event(
                "iteration_attempt_started",
                {"loop": loop.name, "attempt": attempt_index},
            )
            if loop.policy.budget_per_attempt is not None:
                self.spend_budget(
                    loop.policy.budget_per_attempt,
                    label=loop.policy.budget_label,
                    metadata={"loop": loop.name, "attempt": attempt_index},
                )

            agent_run = self.run_agent(loop.agent_name, adapter, loop.task, runtime_context)
            if not agent_run.passed:
                attempt = loop.record_attempt(
                    IterationAttempt(
                        index=attempt_index,
                        agent_run=agent_run,
                        claim_id=None,
                        verification=None,
                        passed=False,
                        reason="agent_failed",
                    )
                )
                self._record_iteration_attempt(loop, attempt)
                continue

            claim = self.claim(
                loop.claim_for_attempt(attempt_index),
                loop=loop.name,
                attempt=attempt_index,
                agent=loop.agent_name,
            )
            verification = self.verify(claim, verifier_chain, runtime_context)
            passed = verification.passed
            attempt = loop.record_attempt(
                IterationAttempt(
                    index=attempt_index,
                    agent_run=agent_run,
                    claim_id=claim.id,
                    verification=verification,
                    passed=passed,
                    reason="verification_passed" if passed else "verification_failed",
                )
            )
            self._record_iteration_attempt(loop, attempt)
            if passed:
                loop.status = "passed"
                loop.stop_reason = "verification_passed"
                self._record_iteration_finished(loop)
                return loop

        loop.status = "failed"
        loop.stop_reason = "max_attempts"
        self._record_iteration_finished(loop)
        return loop

    def run_review_panel(
        self,
        panel: ReviewPanel,
        claim: Claim,
        reviewers: dict[str, AgentAdapter],
        context: VerificationContext | None = None,
    ) -> ReviewPanel:
        if panel not in self.review_panels:
            raise ValueError("review panel does not belong to this workflow run")
        if claim not in self.claims:
            raise ValueError("claim does not belong to this workflow run")
        missing = [name for name in panel.reviewer_names if name not in reviewers]
        if missing:
            raise ValueError(f"missing reviewer adapters: {', '.join(missing)}")

        panel.status = "running"
        panel.stop_reason = None
        panel.claim_id = claim.id
        self.record_event(
            "review_panel_started",
            {
                "panel": panel.name,
                "claim_id": claim.id,
                "reviewer_names": list(panel.reviewer_names),
            },
        )
        runtime_context = context or VerificationContext()
        task = panel.task_for_claim(claim.statement)

        for reviewer_name in panel.reviewer_names:
            adapter = reviewers[reviewer_name]
            agent_run = self.run_agent(reviewer_name, adapter, task, runtime_context)
            if not agent_run.passed:
                result = ReviewResult(
                    reviewer_name=reviewer_name,
                    agent_run=agent_run,
                    decision="failed",
                    error={
                        "type": "AgentRunFailed",
                        "message": agent_run.stderr or f"exit {agent_run.exit_code}",
                    },
                )
            else:
                try:
                    parsed = parse_review_decision(agent_run.stdout)
                    result = ReviewResult(
                        reviewer_name=reviewer_name,
                        agent_run=agent_run,
                        decision=parsed["decision"],  # type: ignore[arg-type]
                        comment=parsed["comment"],
                    )
                    claim.add_evidence(result.to_evidence(panel.name))
                except Exception as exc:
                    result = ReviewResult(
                        reviewer_name=reviewer_name,
                        agent_run=agent_run,
                        decision="invalid",
                        error={"type": type(exc).__name__, "message": str(exc)},
                    )
            panel.record_result(result)
            self.record_event(
                "review_result_recorded",
                {
                    "panel": panel.name,
                    "claim_id": claim.id,
                    "reviewer_name": reviewer_name,
                    "decision": result.decision,
                },
            )

        panel.resolve()
        if panel.status == "approved":
            claim.accept()
        elif panel.status == "rejected":
            claim.reject()
        self.record_event(
            "review_panel_finished",
            {
                "panel": panel.name,
                "claim_id": claim.id,
                "status": panel.status,
                "stop_reason": panel.stop_reason,
                "approval_count": panel.approval_count,
                "reject_count": panel.reject_count,
            },
        )
        return panel

    def run_task_graph(
        self,
        graph: TaskGraph,
        adapters: dict[str, AgentAdapter],
        context: VerificationContext | None = None,
    ) -> TaskGraph:
        if graph not in self.task_graphs:
            raise ValueError("task graph does not belong to this workflow run")
        for task in graph.tasks:
            if not any(agent.name == task.agent_name for agent in self.agents):
                raise ValueError(f"agent {task.agent_name!r} is not registered in this run")
            if task.agent_name not in adapters:
                raise ValueError(f"missing adapter for agent {task.agent_name!r}")

        graph.validate()
        graph.status = "running"
        graph.stop_reason = None
        runtime_context = context or VerificationContext()
        self.record_event(
            "task_graph_started",
            {"graph": graph.name, "task_count": len(graph.tasks)},
        )

        while True:
            batches = graph.ready_batches()
            if not batches:
                break
            for batch_index, batch in enumerate(batches, start=1):
                self.record_event(
                    "task_batch_started",
                    {
                        "graph": graph.name,
                        "batch": batch_index,
                        "tasks": [task.name for task in batch],
                    },
                )
                for task in batch:
                    task.mark_running()
                    self.record_event(
                        "task_started",
                        {
                            "graph": graph.name,
                            "task": task.name,
                            "agent_name": task.agent_name,
                        },
                    )
                    agent_run = self.run_agent(
                        task.agent_name,
                        adapters[task.agent_name],
                        task.task,
                        runtime_context,
                    )
                    graph.record_agent_run(task.name, agent_run)
                    self.record_event(
                        "task_finished",
                        {
                            "graph": graph.name,
                            "task": task.name,
                            "passed": agent_run.passed,
                            "status": task.status,
                        },
                    )
            graph.mark_blocked_dependents()

        graph.finalize()
        self.record_event(
            "task_graph_finished",
            {
                "graph": graph.name,
                "status": graph.status,
                "stop_reason": graph.stop_reason,
            },
        )
        return graph

    def run_agent(
        self,
        agent_name: str,
        adapter: AgentAdapter,
        task: str,
        context: VerificationContext | None = None,
    ) -> AgentRun:
        if not any(agent.name == agent_name for agent in self.agents):
            raise ValueError(f"agent {agent_name!r} is not registered in this run")
        environment_name = self.agent_environments.get(agent_name)
        self.record_event(
            "agent_run_started",
            {
                "agent_name": agent_name,
                "adapter": adapter.name,
                "environment": environment_name,
            },
        )
        started_at = utc_now()
        started = time.monotonic()
        try:
            result = adapter.run(task, context or VerificationContext())
        except Exception as exc:
            result = AgentRun.from_exception(
                agent_name=agent_name,
                task=task,
                command=[adapter.name],
                exc=exc,
                started_at=started_at,
                started=started,
            )
        if environment_name is not None:
            result.metadata = {
                **result.metadata,
                "environment": environment_name,
            }
        self.agent_runs.append(result)
        self.record_event(
            "agent_run_finished",
            {
                "agent_name": agent_name,
                "passed": result.passed,
                "failed": not result.passed,
                "exit_code": result.exit_code,
                "environment": environment_name,
                "error_type": result.metadata.get("error_type"),
            },
        )
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "name": self.name,
            "created_at": self.created_at,
            "provenance": self.provenance.to_dict(),
            "budget": self.budget.to_dict() if self.budget else None,
            "agents": [agent.to_dict() for agent in self.agents],
            "environments": [
                environment.to_dict() for environment in self.environments
            ],
            "agent_environments": dict(self.agent_environments),
            "agent_runs": [run.to_dict() for run in self.agent_runs],
            "state_machines": [
                machine.to_dict() for machine in self.state_machines
            ],
            "iteration_loops": [loop.to_dict() for loop in self.iteration_loops],
            "review_panels": [panel.to_dict() for panel in self.review_panels],
            "task_graphs": [graph.to_dict() for graph in self.task_graphs],
            "execution_plans": [plan.to_dict() for plan in self.execution_plans],
            "provisioning_results": [
                result.to_dict() for result in self.provisioning_results
            ],
            "plan_execution_results": [
                result.to_dict() for result in self.plan_execution_results
            ],
            "messages": self.messages.to_list(),
            "claims": [claim.to_dict() for claim in self.claims],
            "resources": self.resources.snapshot(),
            "artifacts": self.artifacts.to_list(),
            "events": [event.to_dict() for event in self.events],
        }

    def write_bundle(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def write_report(self, path: str | Path) -> Path:
        from vo.report import write_markdown_report

        return write_markdown_report(self, path)

    def _state_machine(self, name: str) -> StateMachine:
        for machine in self.state_machines:
            if machine.name == name:
                return machine
        raise StateMachineError(f"state machine {name!r} is not registered")

    def _environment(self, name: str) -> EnvironmentSpec:
        for environment in self.environments:
            if environment.name == name:
                return environment
        raise ValueError(f"environment {name!r} is not registered")

    def _has_ready_provisioning(self, plan_name: str) -> bool:
        return any(
            result.plan_name == plan_name and result.status == "ready"
            for result in self.provisioning_results
        )

    def _record_iteration_attempt(
        self,
        loop: IterationLoop,
        attempt: IterationAttempt,
    ) -> None:
        self.record_event(
            "iteration_attempt_finished",
            {
                "loop": loop.name,
                "attempt": attempt.index,
                "passed": attempt.passed,
                "reason": attempt.reason,
                "claim_id": attempt.claim_id,
            },
        )

    def _record_iteration_finished(self, loop: IterationLoop) -> None:
        self.record_event(
            "iteration_finished",
            {
                "loop": loop.name,
                "status": loop.status,
                "stop_reason": loop.stop_reason,
                "attempts": len(loop.attempts),
            },
        )
