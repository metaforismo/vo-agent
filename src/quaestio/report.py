"""Markdown reports for workflow run bundles."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from quaestio.bundles import validate_bundle_dict


class SupportsBundle(Protocol):
    def to_dict(self) -> dict[str, Any]:
        ...


def render_markdown_report(run_or_bundle: SupportsBundle | dict[str, Any]) -> str:
    """Render a concise markdown report for a workflow run."""

    bundle = _as_bundle(run_or_bundle)
    lines: list[str] = [
        f"# {_cell(bundle['name'])}",
        "",
        "## Summary",
        "",
        f"- Run ID: `{bundle['run_id']}`",
        f"- Created: {bundle['created_at']}",
        f"- Agents: {len(bundle['agents'])}",
        f"- Environments: {len(bundle['environments'])}",
        f"- Agent placements: {len(bundle['agent_environments'])}",
        f"- Agent runs: {len(bundle['agent_runs'])}",
        f"- State machines: {len(bundle['state_machines'])}",
        f"- Iteration loops: {len(bundle['iteration_loops'])}",
        f"- Review panels: {len(bundle['review_panels'])}",
        f"- Task graphs: {len(bundle['task_graphs'])}",
        f"- Execution plans: {len(bundle['execution_plans'])}",
        f"- Provisioning results: {len(bundle['provisioning_results'])}",
        f"- Plan execution results: {len(bundle['plan_execution_results'])}",
        f"- Messages: {len(bundle['messages'])}",
        f"- Claims: {_claim_summary(bundle['claims'])}",
        f"- Artifacts: {len(bundle['artifacts'])}",
        f"- Budget: {_budget_summary(bundle['budget'])}",
        "",
        "## Environments",
        "",
    ]
    lines.extend(_environments_table(bundle["environments"]))
    lines.extend([
        "",
        "## Agent Placements",
        "",
    ])
    lines.extend(_agent_placements_table(bundle["agent_environments"]))
    lines.extend([
        "",
        "## State Machines",
        "",
    ])
    lines.extend(_state_machines_table(bundle["state_machines"]))
    lines.extend([
        "",
        "## Iteration Loops",
        "",
    ])
    lines.extend(_iteration_loops_table(bundle["iteration_loops"]))
    lines.extend([
        "",
        "## Review Panels",
        "",
    ])
    lines.extend(_review_panels_table(bundle["review_panels"]))
    lines.extend([
        "",
        "## Task Graphs",
        "",
    ])
    lines.extend(_task_graphs_table(bundle["task_graphs"]))
    lines.extend([
        "",
        "## Execution Plans",
        "",
    ])
    lines.extend(_execution_plans_table(bundle["execution_plans"]))
    lines.extend([
        "",
        "## Provisioning",
        "",
    ])
    lines.extend(_provisioning_results_table(bundle["provisioning_results"]))
    lines.extend([
        "",
        "## Plan Executions",
        "",
    ])
    lines.extend(_plan_execution_results_table(bundle["plan_execution_results"]))
    lines.extend([
        "",
        "## Messages",
        "",
    ])
    lines.extend(_messages_table(bundle["messages"]))
    lines.extend([
        "",
        "## Claims",
        "",
    ])
    lines.extend(_claims_table(bundle["claims"]))
    lines.extend(["", "## Agent Runs", ""])
    lines.extend(_agent_runs_table(bundle["agent_runs"]))
    lines.extend(["", "## Artifacts", ""])
    lines.extend(_artifacts_table(bundle["artifacts"]))
    lines.extend(["", "## Provenance", ""])
    lines.extend(_provenance_lines(bundle["provenance"]))
    lines.append("")
    return "\n".join(lines)


def write_markdown_report(
    run_or_bundle: SupportsBundle | dict[str, Any],
    path: str | Path,
) -> Path:
    """Write a markdown report for a workflow run."""

    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown_report(run_or_bundle), encoding="utf-8")
    return report_path


def _as_bundle(run_or_bundle: SupportsBundle | dict[str, Any]) -> dict[str, Any]:
    if hasattr(run_or_bundle, "to_dict"):
        bundle = run_or_bundle.to_dict()
    else:
        bundle = run_or_bundle
    validate_bundle_dict(bundle)
    return bundle


def _claim_summary(claims: list[dict[str, Any]]) -> str:
    accepted = sum(1 for claim in claims if claim.get("status") == "accepted")
    rejected = sum(1 for claim in claims if claim.get("status") == "rejected")
    pending = sum(1 for claim in claims if claim.get("status") == "pending")
    return f"{accepted} accepted, {rejected} rejected, {pending} pending"


def _budget_summary(budget: dict[str, Any] | None) -> str:
    if budget is None:
        return "not declared"
    used = budget.get("used", 0)
    unit = budget.get("unit", "units")
    limit = budget.get("limit")
    if limit is None:
        return f"{used} / unbounded {unit}"
    return f"{used} / {limit} {unit}"


def _claims_table(claims: list[dict[str, Any]]) -> list[str]:
    if not claims:
        return ["_No claims recorded._"]
    rows = ["| Status | Statement | Evidence |", "| --- | --- | --- |"]
    for claim in claims:
        rows.append(
            "| "
            f"{_cell(claim.get('status', 'unknown'))} | "
            f"{_cell(claim.get('statement', ''))} | "
            f"{len(claim.get('evidence', []))} |"
        )
    return rows


def _environments_table(environments: list[dict[str, Any]]) -> list[str]:
    if not environments:
        return ["_No environments recorded._"]
    rows = [
        "| Name | Kind | Image | CPU | Memory | GPU | Secrets |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for environment in environments:
        resources = environment.get("resources", {})
        rows.append(
            "| "
            f"{_cell(environment.get('name', ''))} | "
            f"{_cell(environment.get('kind', ''))} | "
            f"{_cell(environment.get('image') or '')} | "
            f"{resources.get('cpu', '')} | "
            f"{resources.get('memory_gb', '')} | "
            f"{resources.get('gpu_count', '')} | "
            f"{len(environment.get('secret_names', []))} |"
        )
    return rows


def _agent_placements_table(agent_environments: dict[str, Any]) -> list[str]:
    if not agent_environments:
        return ["_No agent placements recorded._"]
    rows = ["| Agent | Environment |", "| --- | --- |"]
    for agent_name, environment_name in sorted(agent_environments.items()):
        rows.append(f"| {_cell(agent_name)} | {_cell(environment_name)} |")
    return rows


def _state_machines_table(machines: list[dict[str, Any]]) -> list[str]:
    if not machines:
        return ["_No state machines recorded._"]
    rows = ["| Name | State | Dispatches |", "| --- | --- | --- |"]
    for machine in machines:
        rows.append(
            "| "
            f"{_cell(machine.get('name', ''))} | "
            f"{_cell(machine.get('state', ''))} | "
            f"{len(machine.get('history', []))} |"
        )
    return rows


def _iteration_loops_table(loops: list[dict[str, Any]]) -> list[str]:
    if not loops:
        return ["_No iteration loops recorded._"]
    rows = ["| Name | Status | Attempts | Stop reason |", "| --- | --- | --- | --- |"]
    for loop in loops:
        rows.append(
            "| "
            f"{_cell(loop.get('name', ''))} | "
            f"{_cell(loop.get('status', ''))} | "
            f"{len(loop.get('attempts', []))} | "
            f"{_cell(loop.get('stop_reason') or '')} |"
        )
    return rows


def _review_panels_table(panels: list[dict[str, Any]]) -> list[str]:
    if not panels:
        return ["_No review panels recorded._"]
    rows = [
        "| Name | Status | Approvals | Results | Stop reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for panel in panels:
        rows.append(
            "| "
            f"{_cell(panel.get('name', ''))} | "
            f"{_cell(panel.get('status', ''))} | "
            f"{panel.get('approval_count', 0)} | "
            f"{len(panel.get('results', []))} | "
            f"{_cell(panel.get('stop_reason') or '')} |"
        )
    return rows


def _task_graphs_table(graphs: list[dict[str, Any]]) -> list[str]:
    if not graphs:
        return ["_No task graphs recorded._"]
    rows = [
        "| Name | Status | Tasks | Passed | Failed | Blocked | Stop reason |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for graph in graphs:
        rows.append(
            "| "
            f"{_cell(graph.get('name', ''))} | "
            f"{_cell(graph.get('status', ''))} | "
            f"{graph.get('task_count', 0)} | "
            f"{graph.get('passed_count', 0)} | "
            f"{graph.get('failed_count', 0)} | "
            f"{graph.get('blocked_count', 0)} | "
            f"{_cell(graph.get('stop_reason') or '')} |"
        )
    return rows


def _execution_plans_table(plans: list[dict[str, Any]]) -> list[str]:
    if not plans:
        return ["_No execution plans recorded._"]
    rows = [
        "| Name | Graph | Waves | Tasks | Environments |",
        "| --- | --- | --- | --- | --- |",
    ]
    for plan in plans:
        rows.append(
            "| "
            f"{_cell(plan.get('name', ''))} | "
            f"{_cell(plan.get('graph_name', ''))} | "
            f"{plan.get('wave_count', 0)} | "
            f"{plan.get('task_count', 0)} | "
            f"{_cell(', '.join(plan.get('environment_names', [])))} |"
        )
    return rows


def _provisioning_results_table(results: list[dict[str, Any]]) -> list[str]:
    if not results:
        return ["_No provisioning results recorded._"]
    rows = [
        "| Plan | Provider | Status | Environments |",
        "| --- | --- | --- | --- |",
    ]
    for result in results:
        rows.append(
            "| "
            f"{_cell(result.get('plan_name', ''))} | "
            f"{_cell(result.get('provider', ''))} | "
            f"{_cell(result.get('status', ''))} | "
            f"{result.get('environment_count', 0)} |"
        )
    return rows


def _plan_execution_results_table(results: list[dict[str, Any]]) -> list[str]:
    if not results:
        return ["_No plan execution results recorded._"]
    rows = [
        "| Plan | Status | Waves | Tasks | Passed | Failed |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        rows.append(
            "| "
            f"{_cell(result.get('plan_name', ''))} | "
            f"{_cell(result.get('status', ''))} | "
            f"{result.get('wave_count', 0)} | "
            f"{result.get('task_count', 0)} | "
            f"{result.get('passed_count', 0)} | "
            f"{result.get('failed_count', 0)} |"
        )
    return rows


def _messages_table(messages: list[dict[str, Any]]) -> list[str]:
    if not messages:
        return ["_No messages recorded._"]
    rows = [
        "| Sender | Recipient | Role | Thread | Content |",
        "| --- | --- | --- | --- | --- |",
    ]
    for message in messages:
        rows.append(
            "| "
            f"{_cell(message.get('sender', ''))} | "
            f"{_cell(message.get('recipient') or '')} | "
            f"{_cell(message.get('role', ''))} | "
            f"{_cell(message.get('thread', ''))} | "
            f"{_cell(message.get('content', ''))} |"
        )
    return rows


def _agent_runs_table(agent_runs: list[dict[str, Any]]) -> list[str]:
    if not agent_runs:
        return ["_No agent runs recorded._"]
    rows = [
        "| Agent | Task | Status | Exit code | Duration | Metadata |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for run in agent_runs:
        status = "passed" if run.get("passed") else "failed"
        rows.append(
            "| "
            f"{_cell(run.get('agent_name', ''))} | "
            f"{_cell(run.get('task', ''))} | "
            f"{status} | "
            f"{run.get('exit_code', '')} | "
            f"{run.get('duration_s', '')}s | "
            f"{_cell(_metadata_summary(run.get('metadata', {})))} |"
        )
    return rows


def _artifacts_table(artifacts: list[dict[str, Any]]) -> list[str]:
    if not artifacts:
        return ["_No artifacts recorded._"]
    rows = ["| Kind | Path | SHA-256 | Size |", "| --- | --- | --- | --- |"]
    for artifact in artifacts:
        rows.append(
            "| "
            f"{_cell(artifact.get('kind', ''))} | "
            f"{_cell(artifact.get('path', ''))} | "
            f"`{artifact.get('sha256', '')}` | "
            f"{artifact.get('size_bytes', '')} |"
        )
    return rows


def _provenance_lines(provenance: dict[str, Any]) -> list[str]:
    git = provenance.get("git")
    lines = [
        f"- CWD: `{provenance.get('cwd', '')}`",
        f"- Python: `{provenance.get('python_version', '')}`",
        f"- Platform: `{provenance.get('platform', '')}`",
    ]
    if git:
        lines.append(
            f"- Git: `{git.get('branch', '')}` at `{git.get('commit', '')}` "
            f"(dirty={git.get('dirty')})"
        )
    else:
        lines.append("- Git: not detected")
    return lines


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _metadata_summary(metadata: Any) -> str:
    if not isinstance(metadata, dict) or not metadata:
        return ""
    return ", ".join(
        f"{key}={metadata[key]}" for key in sorted(metadata)
    )
