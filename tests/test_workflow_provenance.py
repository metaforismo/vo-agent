import json
from pathlib import Path

from vo import WorkflowRun, collect_provenance


def test_workflow_bundle_includes_provenance(tmp_path: Path):
    provenance = collect_provenance(cwd=tmp_path, argv=["demo"], env_keys=[])
    run = WorkflowRun(name="provenance-demo", provenance=provenance)

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["provenance"]["cwd"] == str(tmp_path)
    assert bundle["provenance"]["argv"] == ["demo"]
    assert bundle["provenance"]["env"] == {}
