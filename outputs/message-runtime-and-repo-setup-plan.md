# Message Runtime And Repo Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add durable workflow messages and turn the workspace into a clean local git repository ready to push.

**Architecture:** The runtime adds a focused `vo.messages` module with immutable-ish message records and a small log helper. `WorkflowRun` records messages, emits message events, exports messages in bundles, and renders them in reports. Repository setup adds standard Python project hygiene files, keeps generated runtime artifacts out of git, and creates an initial local commit after verification.

**Tech Stack:** Python 3.11+ stdlib dataclasses, existing VO workflow/report/bundle models, pytest, uv, git.

---

## File Structure

- Create: `src/vo/messages.py`
  - Defines `Message` and `MessageLog`.
  - Owns validation, inbox/thread filtering, JSON-safe serialization, and stable timestamps/ids.
- Modify: `src/vo/workflow.py`
  - Adds `messages`, `send_message()`, `messages_for()`, bundle export, and `message_sent` events.
- Modify: `src/vo/bundles.py`
  - Requires `messages` as a top-level bundle list.
- Modify: `src/vo/report.py`
  - Adds message summary and message table section.
- Modify: `src/vo/__init__.py`
  - Exports message public API.
- Modify: `README.md`
  - Documents messages and repository status/license note.
- Create: `examples/messaging.py`
  - Demonstrates user-to-agent, agent-to-agent, and agent-to-user messages.
- Create: `tests/test_messages.py`
  - Tests message validation, serialization, inbox filtering, thread filtering, and log append behavior.
- Create: `tests/test_workflow_messages.py`
  - Tests workflow messaging, events, bundle export, and filters.
- Modify: `tests/test_bundles.py`
  - Adds required-key validation for `messages`.
- Modify: `tests/test_report.py`
  - Tests message visibility in markdown reports.
- Create: `.gitignore`
  - Ignores generated artifacts, virtual environments, caches, coverage, builds, and OS/editor noise.
- Create: `CONTRIBUTING.md`
  - Documents setup, testing, examples, bundle validation, and contribution expectations.
- Create: `SECURITY.md`
  - Documents safe reporting and secret-handling expectations.
- Create: `CHANGELOG.md`
  - Starts a simple changelog for the current local-first runtime.
- Create: `docs/architecture.md`
  - Captures the current runtime layers and bundle contract.
- Modify: `pyproject.toml`
  - Adds common project metadata and package discovery already implied by the repository.

## Executable Checklist

- [x] Confirm current baseline test suite before editing.
- [x] Inspect current workflow serialization.
- [x] Inspect current bundle validator shape.
- [x] Inspect current report structure.
- [x] Inspect current public exports.
- [x] Inspect existing generated files and decide `.gitignore` boundaries.
- [x] Write failing test that `Message` validates non-empty sender.
- [x] Write failing test that `Message` validates non-empty content.
- [x] Write failing test that `Message` validates role values.
- [x] Write failing test that `Message.to_dict()` serializes sender, recipient, role, thread, content, and metadata.
- [x] Write failing test that `MessageLog.append()` stores messages in order.
- [x] Write failing test that `MessageLog.inbox()` filters by recipient.
- [x] Write failing test that `MessageLog.thread()` filters by thread.
- [x] Write failing workflow test for `WorkflowRun.send_message()`.
- [x] Write failing workflow test for `WorkflowRun.messages_for()`.
- [x] Write failing workflow test that message events are recorded.
- [x] Write failing workflow test that bundles include messages.
- [x] Write failing bundle validation test requiring `messages`.
- [x] Write failing report test that message counts and rows render.
- [x] Run focused tests and confirm failures are for missing message support.
- [x] Implement `Message`.
- [x] Implement `MessageLog`.
- [x] Export message APIs from `vo`.
- [x] Add message storage to `WorkflowRun`.
- [x] Implement `WorkflowRun.send_message()`.
- [x] Implement `WorkflowRun.messages_for()`.
- [x] Record `message_sent` events.
- [x] Include `messages` in workflow bundles.
- [x] Update bundle validator required keys and list sections.
- [x] Render message count in report summary.
- [x] Render messages in markdown reports.
- [x] Add runnable messaging example.
- [x] Update README with messaging usage.
- [x] Add `.gitignore`.
- [x] Add `CONTRIBUTING.md`.
- [x] Add `SECURITY.md`.
- [x] Add `CHANGELOG.md`.
- [x] Add `docs/architecture.md`.
- [x] Update `pyproject.toml` metadata.
- [x] Run focused message tests.
- [x] Run report and bundle tests.
- [x] Run the full pytest suite.
- [x] Run all examples end to end.
- [x] Validate generated bundles through the CLI.
- [x] Inspect generated messaging bundle through the CLI.
- [x] Run compile checks.
- [x] Run import smoke checks.
- [x] Remove generated Python and pytest cache directories.
- [x] Initialize local git repository if one does not exist.
- [x] Verify `.gitignore` keeps `work/`, caches, and virtual environments out of git.
- [x] Stage repository source/docs/tests/examples/config.
- [x] Create initial local git commit.
- [x] Verify git status is clean after commit.
- [x] Update this plan with completed checkboxes and verification evidence.

## Verification Commands

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_messages.py tests/test_workflow_messages.py tests/test_bundles.py tests/test_report.py -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/optimize_with_evidence.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/local_agent_runner.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/state_machine_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/iteration_loop.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/review_panel.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/task_graph_workflow.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/environment_assignment.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/execution_plan.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/provisioning.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/plan_execution.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/messaging.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run vo validate work/messaging-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run vo inspect work/messaging-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples
git status --short
```

## Verification Evidence

- Baseline before this slice: `129 passed in 1.89s`.
- Red phase focused suite failed as intended with missing `Message` / `MessageLog` exports.
- Focused message/workflow/report/bundle suite after implementation: `26 passed in 0.50s`.
- Full pytest suite after implementation: `140 passed in 1.99s`.
- Final post-doc full pytest suite: `140 passed in 1.89s`.
- All examples ran end to end and generated fresh bundles/reports, including `work/messaging-bundle.json`.
- CLI validation accepted every generated bundle: environment assignment, toy optimization, execution plan, iteration loop, local agent, messaging, plan execution, provisioning, review panel, state machine, and task graph.
- CLI inspection of `work/messaging-bundle.json` showed 2 agents and 3 durable messages in the `geometry` thread.
- Compile check passed with `python -m compileall -q src tests examples`.
- Import smoke confirmed `Message`, `MessageLog`, `WorkflowRun`, inbox filtering, and serialized messaging bundle shape work together.
- Package build passed with `uv build`, producing an sdist and wheel before generated `dist/` artifacts were removed.

## Expected Public API Shape

```python
from vo import AgentSpec, WorkflowRun

run = WorkflowRun(name="message-demo")
run.add_agent(AgentSpec(name="solver", goal="Solve the problem"))
run.send_message("user", "Please try the geometry case.", recipient="solver")
run.send_message("solver", "I found a counterexample.", recipient="user", role="agent")

assert len(run.messages_for("solver")) == 1
```

## Self-Review

- Spec coverage: the plan implements durable messages, workflow integration, bundle/report/docs/example coverage, repository hygiene files, local git initialization, and verification.
- Placeholder scan: every checklist item names concrete behavior or a concrete file change.
- Type consistency: public names are consistently `Message`, `MessageLog`, `WorkflowRun.send_message()`, and `WorkflowRun.messages_for()`.
