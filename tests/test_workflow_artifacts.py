import json
from pathlib import Path

from vo import WorkflowRun


def test_workflow_bundle_includes_registered_artifacts(tmp_path: Path):
    artifact_path = tmp_path / "summary.md"
    artifact_path.write_text("# Summary\n", encoding="utf-8")

    run = WorkflowRun(name="artifact-demo", artifact_root=tmp_path)
    run.artifacts.register(artifact_path, kind="summary", metadata={"agent": "writer"})
    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["artifacts"][0]["path"] == "summary.md"
    assert bundle["artifacts"][0]["kind"] == "summary"
    assert bundle["artifacts"][0]["metadata"] == {"agent": "writer"}
