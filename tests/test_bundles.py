from __future__ import annotations

import json

import pytest

from vo import BundleValidationError, WorkflowRun, load_bundle, validate_bundle_dict


def test_validate_bundle_accepts_workflow_bundle() -> None:
    run = WorkflowRun(name="valid bundle")

    assert validate_bundle_dict(run.to_dict()) is True


def test_validate_bundle_rejects_missing_required_keys() -> None:
    run = WorkflowRun(name="invalid bundle")
    bundle = run.to_dict()
    del bundle["task_graphs"]

    with pytest.raises(
        BundleValidationError,
        match="missing required keys: task_graphs",
    ):
        validate_bundle_dict(bundle)


def test_validate_bundle_rejects_missing_review_panel_key() -> None:
    run = WorkflowRun(name="invalid bundle")
    bundle = run.to_dict()
    del bundle["review_panels"]

    with pytest.raises(
        BundleValidationError,
        match="missing required keys: review_panels",
    ):
        validate_bundle_dict(bundle)


def test_validate_bundle_rejects_missing_iteration_loop_key() -> None:
    run = WorkflowRun(name="invalid bundle")
    bundle = run.to_dict()
    del bundle["iteration_loops"]

    with pytest.raises(
        BundleValidationError,
        match="missing required keys: iteration_loops",
    ):
        validate_bundle_dict(bundle)


def test_validate_bundle_rejects_missing_state_machine_key() -> None:
    run = WorkflowRun(name="invalid bundle")
    bundle = run.to_dict()
    del bundle["state_machines"]

    with pytest.raises(
        BundleValidationError,
        match="missing required keys: state_machines",
    ):
        validate_bundle_dict(bundle)


def test_validate_bundle_rejects_missing_environments_key() -> None:
    run = WorkflowRun(name="invalid bundle")
    bundle = run.to_dict()
    del bundle["environments"]

    with pytest.raises(
        BundleValidationError,
        match="missing required keys: environments",
    ):
        validate_bundle_dict(bundle)


def test_validate_bundle_rejects_missing_agent_environments_key() -> None:
    run = WorkflowRun(name="invalid bundle")
    bundle = run.to_dict()
    del bundle["agent_environments"]

    with pytest.raises(
        BundleValidationError,
        match="missing required keys: agent_environments",
    ):
        validate_bundle_dict(bundle)


def test_validate_bundle_rejects_missing_execution_plans_key() -> None:
    run = WorkflowRun(name="invalid bundle")
    bundle = run.to_dict()
    del bundle["execution_plans"]

    with pytest.raises(
        BundleValidationError,
        match="missing required keys: execution_plans",
    ):
        validate_bundle_dict(bundle)


def test_validate_bundle_rejects_missing_provisioning_results_key() -> None:
    run = WorkflowRun(name="invalid bundle")
    bundle = run.to_dict()
    del bundle["provisioning_results"]

    with pytest.raises(
        BundleValidationError,
        match="missing required keys: provisioning_results",
    ):
        validate_bundle_dict(bundle)


def test_validate_bundle_rejects_missing_plan_execution_results_key() -> None:
    run = WorkflowRun(name="invalid bundle")
    bundle = run.to_dict()
    del bundle["plan_execution_results"]

    with pytest.raises(
        BundleValidationError,
        match="missing required keys: plan_execution_results",
    ):
        validate_bundle_dict(bundle)


def test_validate_bundle_rejects_missing_messages_key() -> None:
    run = WorkflowRun(name="invalid bundle")
    bundle = run.to_dict()
    del bundle["messages"]

    with pytest.raises(
        BundleValidationError,
        match="missing required keys: messages",
    ):
        validate_bundle_dict(bundle)


def test_validate_bundle_rejects_wrong_top_level_shape() -> None:
    with pytest.raises(BundleValidationError, match="bundle must be a JSON object"):
        validate_bundle_dict(["not", "an", "object"])  # type: ignore[arg-type]


def test_load_bundle_reads_and_validates_json(tmp_path) -> None:
    path = tmp_path / "bundle.json"
    expected = WorkflowRun(name="loaded bundle").to_dict()
    path.write_text(json.dumps(expected), encoding="utf-8")

    loaded = load_bundle(path)

    assert loaded["run_id"] == expected["run_id"]
    assert loaded["name"] == "loaded bundle"
