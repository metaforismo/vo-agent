# Core Runtime Hardening Plan

This slice turns the current agent workflow core into something easier to bound, inspect, and operate. It keeps the original project direction intact: users write Python state-machine-like programs for coordinating agent teams, while the product handles repeatable execution and infrastructure.

## Objectives

- Add explicit budget accounting so long agent loops can be bounded and audited.
- Add bundle validation and loading so generated run artifacts can be treated as durable records.
- Add markdown reports so humans can quickly inspect what happened in a run.
- Add a small CLI so bundles can be validated and inspected from terminals and automation.
- Keep everything stdlib-only at runtime.
- Preserve the existing public API and examples.

## Executable Checklist

- [x] Read the current package layout before editing.
- [x] Confirm existing workflow serialization shape.
- [x] Confirm public exports before extending the API.
- [x] Write a plan with concrete tasks and verification commands.
- [x] Add tests for budget spending.
- [x] Add tests for budget remaining balance.
- [x] Add tests for budget event entries.
- [x] Add tests for rejecting negative budget spends.
- [x] Add tests for enforcing hard budget limits.
- [x] Add tests for workflow-level budget spending.
- [x] Add tests for budget data in workflow bundles.
- [x] Add tests for bundle validation with a valid run.
- [x] Add tests for bundle validation with missing required keys.
- [x] Add tests for bundle loading from disk.
- [x] Add tests for rejecting malformed bundle JSON shapes.
- [x] Add tests for markdown report rendering from a live workflow.
- [x] Add tests for markdown report rendering from a loaded bundle.
- [x] Add tests for report summary counts.
- [x] Add tests for claim status reporting.
- [x] Add tests for artifact reporting.
- [x] Add tests for agent run reporting.
- [x] Add tests for budget reporting.
- [x] Add tests for workflow report writing.
- [x] Add tests for CLI bundle validation.
- [x] Add tests for CLI bundle inspection.
- [x] Add tests for CLI failure behavior on invalid bundles.
- [x] Run the new tests before implementation and confirm they fail for the expected reasons.
- [x] Implement budget entry serialization.
- [x] Implement budget spending validation.
- [x] Implement hard budget limit enforcement.
- [x] Implement workflow budget integration.
- [x] Implement workflow budget events.
- [x] Implement bundle schema validation helpers.
- [x] Implement bundle disk loading.
- [x] Implement markdown report rendering.
- [x] Implement workflow report writer.
- [x] Implement CLI argument parsing.
- [x] Implement CLI `validate`.
- [x] Implement CLI `inspect`.
- [x] Wire the CLI into `pyproject.toml`.
- [x] Export the new public classes and helpers.
- [x] Update README with the new inspection flow.
- [x] Add or update examples to exercise budgets and reports.
- [x] Run focused tests for budget behavior.
- [x] Run focused tests for bundle behavior.
- [x] Run focused tests for report behavior.
- [x] Run focused tests for CLI behavior.
- [x] Run the full pytest suite.
- [x] Run example workflows end to end.
- [x] Validate generated bundles with the CLI.
- [x] Inspect generated bundles with the CLI.
- [x] Run Python compile checks.
- [x] Confirm this workspace is not a git repository, so tracked diff inspection is unavailable.
- [x] Update this checklist to reflect completion.

## Verification Commands

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_budget.py tests/test_bundles.py tests/test_report.py tests/test_cli.py -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/optimize_with_evidence.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/local_agent_runner.py
UV_PROJECT_ENVIRONMENT=work/.venv uv run quaestio validate work/example-run-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run quaestio inspect work/example-run-bundle.json
UV_PROJECT_ENVIRONMENT=work/.venv uv run python -m compileall -q src tests examples
```

## Verification Results

- Focused new tests: `14 passed in 1.33s`.
- Full test suite: `25 passed in 8.88s`.
- `examples/optimize_with_evidence.py` generated `work/example-run-bundle.json` and `work/example-run-report.md`.
- `examples/local_agent_runner.py` generated `work/local-agent-bundle.json` and `work/local-agent-report.md`.
- CLI validation accepted both generated bundles.
- CLI inspection rendered markdown summaries for both generated bundles.
- Compile and import smoke checks passed.
