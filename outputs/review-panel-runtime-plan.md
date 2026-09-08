# Review Panel Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-agent review panels where reviewer agents approve, reject, or request revision on workflow claims.

**Architecture:** The runtime adds a focused `quaestio.reviews` module for review policies, decision parsing, panel state, and serializable review results. `WorkflowRun.run_review_panel()` composes existing registered agents and claims, records reviewer agent runs, attaches review evidence to the claim, resolves quorum policy, and exports panels in bundles and reports.

**Tech Stack:** Python 3.11+ stdlib dataclasses, existing VO agent/workflow/evidence models, pytest, current `uv` test workflow.

---

## File Structure

- Create: `src/quaestio/reviews.py`
  - Defines `ReviewPolicy`, `ReviewResult`, `ReviewPanel`, and `parse_review_decision()`.
  - Owns decision validation, quorum resolution, result serialization, and panel status.
- Modify: `src/quaestio/workflow.py`
  - Adds `review_panels`, `add_review_panel()`, and `run_review_panel()`.
  - Records review lifecycle events, appends reviewer agent runs, and attaches review evidence to claims.
- Modify: `src/quaestio/bundles.py`
  - Requires `review_panels` as a top-level bundle list.
- Modify: `src/quaestio/report.py`
  - Adds review panel count and markdown table.
- Modify: `src/quaestio/__init__.py`
  - Exports review public API.
- Modify: `src/quaestio/exceptions.py`
  - Adds `ReviewParseError`.
- Modify: `README.md`
  - Documents multi-agent review panels.
- Create: `examples/review_panel.py`
  - Demonstrates two reviewer agents approving one claim.
- Create: `tests/test_reviews.py`
  - Tests policy validation, decision parsing, and panel serialization.
- Create: `tests/test_workflow_reviews.py`
  - Tests workflow integration, claim status, events, and bundle serialization.
- Modify: `tests/test_bundles.py`
  - Updates required-key expectations for `review_panels`.
- Modify: `tests/test_report.py`
  - Tests review panel visibility in reports.

## Executable Checklist

- [x] Confirm current baseline test suite before editing.
- [x] Inspect current agent run serialization.
- [x] Inspect current claim and evidence serialization.
- [x] Inspect current workflow bundle serialization.
- [x] Inspect current report and bundle validator shapes.
- [x] Write failing test that `ReviewPolicy` rejects `min_approvals < 1`.
- [x] Write failing test that `ReviewPanel` rejects an empty reviewer list.
- [x] Write failing test that `ReviewPanel` rejects impossible quorum.
- [x] Write failing test that decision parsing accepts `decision: approve`.
- [x] Write failing test that decision parsing accepts comments.
- [x] Write failing test that decision parsing rejects missing decisions.
- [x] Write failing test that decision parsing rejects unknown decisions.
- [x] Write failing test that a panel is approved when quorum is met.
- [x] Write failing test that claim evidence includes reviewer decisions.
- [x] Write failing test that a hard reject rejects the panel and claim.
- [x] Write failing test that invalid reviewer output fails the panel and leaves the claim pending.
- [x] Write failing test that reviewer agent failures fail the panel and leave the claim pending.
- [x] Write failing workflow test for registering a review panel.
- [x] Write failing workflow test for duplicate panel names.
- [x] Write failing workflow test that bundles include review panel results.
- [x] Write failing workflow test that review lifecycle events are recorded.
- [x] Write failing bundle validation test requiring `review_panels`.
- [x] Write failing report test that review panels appear in markdown output.
- [x] Run focused tests and confirm failures are for missing review panel support.
- [x] Implement `ReviewParseError`.
- [x] Implement `ReviewPolicy` validation.
- [x] Implement `parse_review_decision()`.
- [x] Implement `ReviewResult` serialization.
- [x] Implement `ReviewPanel` validation.
- [x] Implement `ReviewPanel.task_for_claim()`.
- [x] Implement `ReviewPanel.record_result()`.
- [x] Implement `ReviewPanel.resolve()`.
- [x] Add review panel storage to `WorkflowRun`.
- [x] Implement `WorkflowRun.add_review_panel()`.
- [x] Implement `WorkflowRun.run_review_panel()`.
- [x] Record `review_panel_started` events.
- [x] Record `review_result_recorded` events.
- [x] Record `review_panel_finished` events.
- [x] Attach review evidence to the reviewed claim.
- [x] Accept claims when the review panel is approved.
- [x] Reject claims when a hard reject occurs or quorum is not met.
- [x] Leave claims pending when review parsing or reviewer execution fails.
- [x] Include `review_panels` in workflow bundles.
- [x] Update bundle validator required keys.
- [x] Export review APIs from `quaestio`.
- [x] Render review panels in markdown reports.
- [x] Add a runnable review-panel example.
- [x] Update README with review-panel usage.
- [x] Run focused review tests.
- [x] Run report and bundle tests.
- [x] Run the full pytest suite.
- [x] Run all examples end to end.
- [x] Validate generated bundles through the CLI.
- [x] Inspect generated bundles through the CLI.
- [x] Run compile checks.
- [x] Run import smoke checks.
- [x] Remove generated Python and pytest cache directories.
- [x] Update this plan with completed checkboxes and verification evidence.

## Verification Commands

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_reviews.py tests/test_workflow_reviews.py tests/test_bundles.py tests/test_report.py -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/optimize_with_evidence.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/local_agent_runner.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/state_machine_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/iteration_loop.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/review_panel.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run quaestio validate work/review-panel-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run quaestio inspect work/review-panel-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples
```

## Verification Results

- Baseline before the slice: `48 passed in 1.04s`.
- Red phase: focused review tests failed during collection because `ReviewPanel` was not exported yet.
- Focused review/report/bundle tests: `24 passed in 9.28s`.
- Full test suite after implementation: `64 passed in 4.73s`.
- Fresh final full test suite: `64 passed in 1.53s`.
- `examples/optimize_with_evidence.py` generated `work/example-run-bundle.json` and `work/example-run-report.md`.
- `examples/local_agent_runner.py` generated `work/local-agent-bundle.json` and `work/local-agent-report.md`.
- `examples/state_machine_workflow.py` generated `work/state-machine-bundle.json` and `work/state-machine-report.md`.
- `examples/iteration_loop.py` generated `work/iteration-loop-bundle.json` and `work/iteration-loop-report.md`.
- `examples/review_panel.py` generated `work/review-panel-bundle.json` and `work/review-panel-report.md`.
- CLI validation accepted `toy-optimization`, `local-agent-demo`, `state-machine-demo`, `iteration-loop-demo`, and `review-panel-demo`.
- CLI inspection showed `proof-review` with status `approved`, `2` approvals, `2` results, and stop reason `quorum_approved`.
- Compile check passed with `python -m compileall -q src tests examples`.
- Import and JSON smoke check passed, including assertions for approved panel status, approval count, and accepted claim status.

## Expected Public API Shape

```python
from quaestio import ReviewPanel, ReviewPolicy, WorkflowRun

panel = ReviewPanel(
    name="proof-review",
    reviewer_names=("critic", "checker"),
    policy=ReviewPolicy(min_approvals=2),
)

run = WorkflowRun(name="review-demo")
run.add_review_panel(panel)
run.run_review_panel(panel, claim, {"critic": critic_agent, "checker": checker_agent})
```

## Self-Review

- Spec coverage: the plan implements the “agents check and challenge each other’s outputs” product example with explicit reviewer agents, decision parsing, quorum, evidence, claim status updates, events, bundles, reports, docs, examples, and tests.
- Placeholder scan: every checklist item names concrete behavior or a concrete file change.
- Type consistency: public names are consistently `ReviewPolicy`, `ReviewResult`, `ReviewPanel`, `parse_review_decision()`, and `run_review_panel()`.
