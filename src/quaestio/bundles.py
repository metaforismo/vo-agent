"""Load and validate workflow run bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quaestio.exceptions import BundleValidationError

REQUIRED_BUNDLE_KEYS = {
    "run_id",
    "name",
    "created_at",
    "provenance",
    "budget",
    "agents",
    "environments",
    "agent_environments",
    "agent_runs",
    "state_machines",
    "iteration_loops",
    "review_panels",
    "task_graphs",
    "execution_plans",
    "provisioning_results",
    "plan_execution_results",
    "messages",
    "claims",
    "resources",
    "artifacts",
    "events",
}

LIST_SECTIONS = (
    "agents",
    "environments",
    "agent_runs",
    "state_machines",
    "iteration_loops",
    "review_panels",
    "task_graphs",
    "execution_plans",
    "provisioning_results",
    "plan_execution_results",
    "messages",
    "claims",
    "artifacts",
    "events",
)


def validate_bundle_dict(bundle: Any) -> bool:
    """Validate the stable top-level shape of a workflow bundle."""

    if not isinstance(bundle, dict):
        raise BundleValidationError("bundle must be a JSON object")

    missing = sorted(REQUIRED_BUNDLE_KEYS - set(bundle))
    if missing:
        raise BundleValidationError(f"missing required keys: {', '.join(missing)}")

    for key in ("run_id", "name", "created_at"):
        if not isinstance(bundle[key], str) or not bundle[key].strip():
            raise BundleValidationError(f"{key} must be a non-empty string")

    if not isinstance(bundle["provenance"], dict):
        raise BundleValidationError("provenance must be an object")
    if bundle["budget"] is not None and not isinstance(bundle["budget"], dict):
        raise BundleValidationError("budget must be null or an object")
    if not isinstance(bundle["resources"], dict):
        raise BundleValidationError("resources must be an object")
    if not isinstance(bundle["agent_environments"], dict):
        raise BundleValidationError("agent_environments must be an object")

    for key in LIST_SECTIONS:
        if not isinstance(bundle[key], list):
            raise BundleValidationError(f"{key} must be a list")

    return True


def load_bundle(path: str | Path) -> dict[str, Any]:
    """Read a workflow bundle from disk and validate its top-level shape."""

    bundle_path = Path(path)
    try:
        loaded = json.loads(bundle_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BundleValidationError(f"invalid JSON: {exc.msg}") from exc

    validate_bundle_dict(loaded)
    return loaded
