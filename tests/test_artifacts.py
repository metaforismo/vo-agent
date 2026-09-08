import hashlib
from pathlib import Path

import pytest

from quaestio import ArtifactStore


def test_artifact_store_registers_file_with_hash_size_and_metadata(tmp_path: Path):
    path = tmp_path / "result.txt"
    path.write_text("research output\n", encoding="utf-8")

    store = ArtifactStore(root=tmp_path)
    artifact = store.register(path, kind="report", metadata={"claim": "accepted"})

    expected_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    assert artifact.path == "result.txt"
    assert artifact.kind == "report"
    assert artifact.sha256 == expected_hash
    assert artifact.size_bytes == len("research output\n")
    assert artifact.metadata == {"claim": "accepted"}
    assert store.to_list()[0]["sha256"] == expected_hash


def test_artifact_store_rejects_missing_file(tmp_path: Path):
    store = ArtifactStore(root=tmp_path)

    with pytest.raises(FileNotFoundError):
        store.register(tmp_path / "missing.txt")
