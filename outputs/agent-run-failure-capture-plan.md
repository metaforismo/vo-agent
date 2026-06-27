# Agent Run Failure Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make agent execution failures reproducible by recording timeouts and adapter exceptions as `AgentRun` data instead of letting them escape before bundles are written.

**Architecture:** Keep the existing `AgentAdapter` interface and strengthen the two execution boundaries. `LocalCommandAgent` converts subprocess timeouts and OS launch failures into failed `AgentRun` records, while `WorkflowRun.run_agent` converts unexpected adapter exceptions into failed `AgentRun` records and always emits `agent_run_finished`.

**Tech Stack:** Python 3.11+, dataclasses, subprocess, pytest, uv.

---

## File Structure

- Modify: `src/vo/agents.py`
  - Add a small text-normalization helper for subprocess exception output.
  - Add `AgentRun.from_exception(...)` for deterministic failed run records.
  - Teach `LocalCommandAgent.run(...)` to capture `TimeoutExpired` and `OSError`.
- Modify: `src/vo/workflow.py`
  - Wrap adapter execution in `WorkflowRun.run_agent(...)`.
  - Preserve environment metadata on both successful and failed runs.
  - Record `agent_run_finished` for adapter exceptions.
- Modify: `src/vo/report.py`
  - Extend the Agent Runs table with pass/fail status and metadata summary.
- Modify: `src/vo/__init__.py`
  - Export any new public model if needed.
- Test: `tests/test_agents.py`
  - Cover subprocess timeouts and command launch failures.
- Test: `tests/test_workflow_agents.py`
  - Cover adapter exceptions and bundle export.
- Test: `tests/test_report.py`
  - Cover failed agent run visibility in reports.
- Create: `examples/failed_agent_capture.py`
  - Demonstrate a failed local command being captured and exported.
- Modify: `README.md`
  - Document that failed agent runs are bundle data, not lost control-flow exceptions.

## Executable Checklist

### Task 1: Red Tests for Local Agent Failures

- [x] Add `test_local_command_agent_records_timeout_as_failed_run` to `tests/test_agents.py`.
- [x] Add `test_local_command_agent_records_missing_command_as_failed_run` to `tests/test_agents.py`.
- [x] Run `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_agents.py -q`.
- [x] Confirm both new tests fail before production changes.

### Task 2: Local Agent Failure Capture

- [x] Add `_coerce_output_text(value: object) -> str` to `src/vo/agents.py`.
- [x] Add `AgentRun.from_exception(...)` to `src/vo/agents.py`.
- [x] Catch `subprocess.TimeoutExpired` inside `LocalCommandAgent.run(...)`.
- [x] Return exit code `124` for timeouts with metadata `{"timed_out": True, "timeout_s": timeout, "error_type": "TimeoutExpired"}`.
- [x] Catch `OSError` inside `LocalCommandAgent.run(...)`.
- [x] Return exit code `127` for OS launch failures with metadata `{"error_type": type(exc).__name__}`.
- [x] Preserve user-supplied adapter metadata on failure.
- [x] Run `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_agents.py -q`.
- [x] Confirm local agent tests pass.

### Task 3: Red Tests for Workflow Adapter Exceptions

- [x] Add a throwing test adapter to `tests/test_workflow_agents.py`.
- [x] Add `test_workflow_run_agent_records_adapter_exception_and_finished_event` to `tests/test_workflow_agents.py`.
- [x] Assert the exported bundle contains one failed `agent_runs` entry.
- [x] Assert the failed run has `metadata.error_type == "RuntimeError"`.
- [x] Assert the last two event types are `agent_run_started` and `agent_run_finished`.
- [x] Run `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_workflow_agents.py -q`.
- [x] Confirm the new workflow exception test fails before production changes.

### Task 4: Workflow Exception Capture

- [x] Wrap `adapter.run(...)` in `WorkflowRun.run_agent(...)` with `try`/`except Exception`.
- [x] Build failed runs with `AgentRun.from_exception(...)` when adapters raise.
- [x] Include adapter name in the failed run command.
- [x] Preserve assigned environment metadata for failed runs.
- [x] Include `failed=True`, `exit_code`, and `error_type` in the `agent_run_finished` event data.
- [x] Run `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_workflow_agents.py -q`.
- [x] Confirm workflow agent tests pass.

### Task 5: Report Visibility

- [x] Add a report test showing failed agent run status and metadata summary.
- [x] Run `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_report.py -q`.
- [x] Confirm the report test fails before production changes.
- [x] Add `Status` and `Metadata` columns to `_agent_runs_table(...)`.
- [x] Render `passed` as `passed` or `failed`.
- [x] Render compact metadata as comma-separated `key=value` pairs.
- [x] Run `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_report.py -q`.
- [x] Confirm report tests pass.

### Task 6: Example and Documentation

- [x] Create `examples/failed_agent_capture.py`.
- [x] Add README section `## Failed Agent Runs`.
- [x] Include the new example command in the README.
- [x] Run `UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/failed_agent_capture.py`.
- [x] Validate `work/failed-agent-capture-bundle.json` with `vo validate`.

### Task 7: Full Verification

- [x] Run `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q`.
- [x] Run every example with `for example in examples/*.py; do UV_PROJECT_ENVIRONMENT=work/.venv uv run python "$example"; done`.
- [x] Validate every generated bundle with `for bundle in work/*-bundle.json; do UV_PROJECT_ENVIRONMENT=work/.venv uv run vo validate "$bundle"; done`.
- [x] Run `UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples`.
- [x] Run `UV_PROJECT_ENVIRONMENT=work/.venv uv build`.
- [x] Remove generated `dist/`, caches, and bytecode.
- [x] Update this plan with verification evidence.
- [x] Commit the feature branch.
- [x] Merge into `main`.
- [x] Push `main`.
- [x] Verify GitHub CI on `main` succeeds.

## Self-Review

- Spec coverage: captures subprocess timeouts, launch failures, arbitrary adapter exceptions, bundle export, reports, examples, docs, and CI verification.
- Placeholder scan: no TODO, TBD, or unspecified error-handling steps.
- Type consistency: all new behavior is represented as existing `AgentRun` records, preserving bundle shape and report rendering.

## Verification Evidence

- Baseline in isolated branch: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q` -> `144 passed in 4.74s`.
- Local red phase: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_agents.py -q` failed with timeout and missing-command exceptions escaping.
- Local green phase: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_agents.py -q` -> `3 passed in 0.26s`.
- Workflow red phase: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_workflow_agents.py -q` failed with `RuntimeError: adapter exploded`.
- Workflow green phase: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_workflow_agents.py -q` -> `2 passed in 0.18s`.
- Finish-event red phase: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_workflow_agents.py -q` failed with missing `agent_run_finished.data.failed`.
- Finish-event green phase: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_workflow_agents.py -q` -> `2 passed in 0.14s`.
- Higher-level workflow paths: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_workflow_plan_execution.py tests/test_workflow_iterations.py tests/test_workflow_task_graph.py tests/test_workflow_reviews.py -q` -> `24 passed in 1.47s`.
- Report red phase: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_report.py -q` failed before the Agent Runs table included status and metadata.
- Report green phase: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_report.py -q` -> `4 passed in 0.60s`.
- Bundle, CLI, and workflow smoke: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_bundles.py tests/test_cli.py tests/test_workflow.py -q` -> `17 passed in 2.09s`.
- Failure example: `UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/failed_agent_capture.py` printed `False`, `FileNotFoundError`, and generated bundle/report paths.
- Failure bundle validation: `UV_PROJECT_ENVIRONMENT=work/.venv uv run vo validate work/failed-agent-capture-bundle.json` -> `valid: failed-agent-capture-demo`.
- Full tests: `UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q` -> `148 passed in 6.53s`.
- Examples: `for example in examples/*.py; do UV_PROJECT_ENVIRONMENT=work/.venv uv run python "$example"; done` ran all 12 examples.
- Bundle validation: `for bundle in work/*-bundle.json; do UV_PROJECT_ENVIRONMENT=work/.venv uv run vo validate "$bundle"; done` validated all 12 generated bundles.
- Compile: `UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples` passed.
- Build: `UV_PROJECT_ENVIRONMENT=work/.venv uv build` built `dist/vo_agent-0.1.0.tar.gz` and `dist/vo_agent-0.1.0-py3-none-any.whl`.
- Feature commit: `git commit -m "Capture agent execution failures"` -> `41fc9a8`.
- Merge commit: `git merge --no-ff feature/agent-run-failure-capture -m "Merge agent failure capture"` -> `a84a611`.
- Push: `git push` updated `main` on `https://github.com/metaforismo/vo-agent`.
- GitHub CI: run `28294600109` for `Merge agent failure capture` completed with `success`.
