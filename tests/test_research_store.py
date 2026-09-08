from __future__ import annotations

import hashlib
import multiprocessing
import os
import sqlite3

import pytest

from quaestio import WorkflowRun
from quaestio.exceptions import BundleValidationError
from quaestio.research import (
    APPLICATION_ID,
    MAX_BYTES,
    ResearchConflict,
    ResearchError,
    ResearchStore,
    serialize_json,
)


@pytest.fixture
def store(tmp_path):
    with ResearchStore.create(tmp_path / "study.sqlite", title="Shared research") as study:
        yield study


def node(store, operation="root", **kwargs):
    return store.create_node(kind="question", title=operation, content="Question",
                             actor="researcher", operation_id=operation, **kwargs)


def race_revision(path, node_id, operation_id, ready, start, results):
    with ResearchStore(path) as study:
        ready.put(True)
        assert start.wait(10)
        try:
            result = study.revise_node(node_id, expected_revision=1, content=operation_id,
                                       status="in_progress", actor="worker", operation_id=operation_id)
        except ResearchConflict:
            result = "conflict"
        results.put(result)


def interrupt_import(path):
    with ResearchStore(path) as study:
        original = study._attach

        def attach_then_exit(*args):
            original(*args)
            os._exit(23)

        study._attach = attach_then_exit
        study.import_markdown(data=b"# Question\nUnknown", title="Interrupted source",
                              actor="worker", operation_id="interrupted")


def test_restart_preserves_history_edges_artifacts_and_exact_retry(tmp_path):
    path = tmp_path / "study.sqlite"
    with ResearchStore.create(path, title="Durable study") as study:
        root = node(study)
        child = node(study, "branch", parents=[root["id"]])
        revision_args = dict(expected_revision=1, content="Measured result", status="completed",
                             actor="agent", operation_id="revise")
        changed = study.revise_node(child["id"], **revision_args)
        artifact = study.attach_artifact(child["id"], data=b"exact retained evidence\x00", label="result",
                                         actor="agent", operation_id="attach")
        expected = study.snapshot()
    with ResearchStore(path) as reopened:
        assert reopened.snapshot() == expected
        assert reopened.revise_node(child["id"], **revision_args) == changed
        assert node(reopened) == root
        assert reopened.artifact_bytes(artifact["id"]) == b"exact retained evidence\x00"
        history = reopened.get_node(child["id"])["history"]
        assert [r["content"] for r in history] == ["Question", "Measured result"]
        assert [r["revision"] for r in history] == [1, 2]
        assert reopened.snapshot() == expected


@pytest.mark.parametrize("same_operation", [False, True])
def test_concurrent_processes_compare_and_swap_or_share_exact_receipt(store, same_operation):
    root = node(store)
    context = multiprocessing.get_context("spawn")
    ready, start, outcomes = context.Queue(), context.Event(), context.Queue()
    processes = [context.Process(target=race_revision,
                                args=(str(store.path), root["id"],
                                      "same" if same_operation else f"worker-{i}", ready, start, outcomes))
                 for i in range(2)]
    try:
        for process in processes:
            process.start()
        assert ready.get(timeout=15)
        assert ready.get(timeout=15)
        start.set()
        results = [outcomes.get(timeout=15) for _ in processes]
        for process in processes:
            process.join(timeout=15)
            assert process.exitcode == 0
    finally:
        for process in processes:
            if process.is_alive():
                process.kill()
                process.join()
        for queue in (ready, outcomes):
            queue.close()
            queue.join_thread()
    if same_operation:
        assert results[0] == results[1]
    else:
        assert results.count("conflict") == 1
    assert len(store.get_node(root["id"])["history"]) == 2
    assert store.snapshot()["cursor"] == 2


@pytest.mark.parametrize("changed", [dict(content="other"), dict(actor="other"), dict(title="other")])
def test_operation_id_cannot_be_reused_for_different_input(store, changed):
    arguments = dict(kind="question", title="Question", content="Original", actor="author", operation_id="op")
    store.create_node(**arguments)
    before = store.snapshot()
    with pytest.raises(ResearchConflict, match="different input"):
        store.create_node(**(arguments | changed))
    assert store.snapshot() == before


def test_stale_failure_does_not_consume_operation_id(store):
    root = node(store)
    store.revise_node(root["id"], expected_revision=1, content="Latest", status="open",
                      actor="a", operation_id="first")
    before = store.snapshot()
    with pytest.raises(ResearchConflict, match="current revision is 2"):
        store.revise_node(root["id"], expected_revision=1, content="Stale", status="failed",
                          actor="b", operation_id="retry")
    assert store.snapshot() == before
    result = store.revise_node(root["id"], expected_revision=2, content="Updated", status="completed",
                               actor="b", operation_id="retry")
    assert result["revision"] == 3


def test_receipt_failure_rolls_back_import_nodes_artifacts_and_edges(store):
    before = store.snapshot()
    store._db.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON operations "
                      "BEGIN SELECT RAISE(ABORT, 'injected receipt failure'); END")
    arguments = dict(data=b"# First\nA\n# Second\nB", title="Source", actor="a", operation_id="import")
    with pytest.raises(sqlite3.IntegrityError, match="injected receipt failure"):
        store.import_markdown(**arguments)
    assert store.snapshot() == before
    assert store._db.execute("SELECT count(*) FROM artifacts").fetchone()[0] == 0
    assert store._db.execute("SELECT count(*) FROM revisions").fetchone()[0] == 0
    assert store._db.execute("SELECT count(*) FROM edges").fetchone()[0] == 0
    store._db.execute("DROP TRIGGER fail_receipt")
    result = store.import_markdown(**arguments)
    assert len(result["sections"]) == 2
    assert store.import_markdown(**arguments) == result
    assert store.snapshot()["cursor"] == 1


def test_process_exit_before_commit_leaves_no_partial_import(store):
    before = store.snapshot()
    process = multiprocessing.get_context("spawn").Process(target=interrupt_import, args=(str(store.path),))
    process.start()
    process.join(timeout=15)
    if process.is_alive():
        process.kill()
        process.join()
        pytest.fail("interrupted writer did not finish")
    assert process.exitcode == 23
    assert store.snapshot() == before
    assert store._db.execute("SELECT count(*) FROM artifacts").fetchone()[0] == 0
    result = store.import_markdown(data=b"# Question\nUnknown", title="Interrupted source",
                                   actor="worker", operation_id="interrupted")
    assert len(result["sections"]) == 1


def test_branches_and_merge_preserve_dag_and_reject_missing_or_duplicate_parents(store):
    root = node(store)
    left = node(store, "left", parents=[root["id"]])
    right = node(store, "right", parents=[root["id"]])
    merged = node(store, "merge", parents=[left["id"], right["id"]])
    assert merged["parents"] == sorted([left["id"], right["id"]])
    assert node(store, "merge", parents=[right["id"], left["id"]]) == merged
    before = store.snapshot()
    with pytest.raises(ResearchError, match="unknown node"):
        node(store, "missing", parents=["not-created"])
    with pytest.raises(ResearchError, match="duplicate parents"):
        node(store, "duplicate", parents=[root["id"], root["id"]])
    assert store.snapshot() == before
    seen = set()
    for item in before["nodes"]:
        assert set(item["parents"]) <= seen
        seen.add(item["id"])
    store.revise_node(merged["id"], expected_revision=1, content="Revised merge", status="open",
                      actor="a", operation_id="revise-merge")
    assert store.get_node(merged["id"])["parents"] == merged["parents"]


def test_node_limit_failure_is_atomic_across_import(monkeypatch, store):
    monkeypatch.setattr("quaestio.research.MAX_NODES", 2)
    root = node(store)
    before = store.snapshot()
    with pytest.raises(ResearchError, match="study limit"):
        store.import_markdown(data=b"# Section\nText", title="Source", actor="a", operation_id="too-many")
    assert store.snapshot() == before
    assert store._db.execute("SELECT count(*) FROM artifacts").fetchone()[0] == 0
    assert node(store, "still-space", parents=[root["id"]])["revision"] == 1


def test_artifact_retention_deduplicates_bytes_without_merging_attachments(store, tmp_path):
    root = node(store)
    source = tmp_path / "data.csv"
    source.write_bytes(b"value\n42\n")
    data = source.read_bytes()
    first = store.attach_artifact(root["id"], data=data, label="original", actor="a", operation_id="first")
    second = store.attach_artifact(root["id"], data=data, label="copy", actor="b", operation_id="second")
    source.unlink()
    assert first["id"] != second["id"]
    assert first["sha256"] == second["sha256"] == hashlib.sha256(data).hexdigest()
    assert store.artifact_bytes(first["id"]) == store.artifact_bytes(second["id"]) == data
    assert store._db.execute("SELECT count(*) FROM artifacts").fetchone()[0] == 1
    assert len(store.get_node(root["id"])["artifacts"]) == 2


@pytest.mark.parametrize("column,value", [("data", b"corrupt"), ("size_bytes", 999)])
def test_corrupt_artifact_bytes_or_size_fail_retrieval_and_dedup(store, column, value):
    root = node(store)
    attachment = store.attach_artifact(root["id"], data=b"evidence", label="Data", actor="a", operation_id="attach")
    store._db.execute(f"UPDATE artifacts SET {column}=? WHERE sha256=?", (value, attachment["sha256"]))
    with pytest.raises(ResearchError, match="integrity mismatch"):
        store.artifact_bytes(attachment["id"])
    with pytest.raises(ResearchError, match="integrity mismatch"):
        store.attach_artifact(root["id"], data=b"evidence", label="Retry", actor="a", operation_id="another")
    assert store.snapshot()["cursor"] == 2


def test_markdown_is_retained_unverified_and_code_fences_do_not_create_sections(store):
    data = ("Preamble retained verbatim.\n# Question\nUnknown\n```sh\n# Not a section\n"
            "echo never-executed\n```\n## Evidence\n<script>alert(1)</script>\n").encode()
    result = store.import_markdown(data=data, title="Imported", actor="a", operation_id="source")
    assert result["interpretation"] == "unverified_source_text"
    assert result["source"]["kind"] == "source"
    assert [s["title"] for s in result["sections"]] == ["Question", "Evidence"]
    assert "# Not a section" in result["sections"][0]["content"]
    assert all(s["status"] == "open" for s in result["sections"])
    assert store.artifact_bytes(result["artifact"]["id"]) == data
    assert store.snapshot()["executions"] == []


def test_reported_execution_never_gains_verifier_or_execution_authority(store, tmp_path):
    root = node(store)
    marker = tmp_path / "must-not-exist"
    bundle = WorkflowRun(name="Reported execution").to_dict()
    bundle["claims"] = [{"status": "verified", "evidence": "trust me"}]
    bundle["execution_authorized"] = True
    bundle["execution_plans"] = [{"command": f"touch {marker}"}]
    expected_bytes = serialize_json(bundle).encode()
    result = store.record_execution(root["id"], bundle=bundle, actor="importer", operation_id="execution")
    assert result["evidence_status"] == "reported_unverified"
    assert result["execution_authorized"] is False
    assert store.record_execution(root["id"], bundle=bundle, actor="importer", operation_id="execution") == result
    bundle["name"] = "Changed caller object"
    assert store.artifact_bytes(result["artifact_id"]) == expected_bytes
    assert not marker.exists()
    snapshot = store.snapshot()
    assert len(snapshot["executions"]) == len(snapshot["artifacts"]) == 1
    assert snapshot["executions"][0]["execution_authorized"] is False
    assert snapshot["executions"][0]["evidence_status"] == "reported_unverified"


def test_invalid_execution_and_source_leave_no_writes(store):
    root = node(store)
    before = store.snapshot()
    with pytest.raises(BundleValidationError):
        store.record_execution(root["id"], bundle={"name": "partial"}, actor="a", operation_id="invalid")
    with pytest.raises(ResearchError, match="UTF-8"):
        store.import_markdown(data=b"\xff", title="Invalid", actor="a", operation_id="invalid")
    with pytest.raises(ResearchError, match="60 sections"):
        store.import_markdown(data=b"# Title\n" * 61, title="Oversized", actor="a", operation_id="invalid")
    assert store.snapshot() == before


def test_context_is_exact_ancestry_with_unverified_evidence_metadata(store):
    root = node(store)
    left = node(store, "left", parents=[root["id"]])
    right = node(store, "right", parents=[root["id"]])
    merge = node(store, "merge", parents=[left["id"], right["id"]])
    unrelated = node(store, "unrelated")
    store.attach_artifact(root["id"], data=b"source", label="Source", actor="a", operation_id="artifact")
    context = store.context(merge["id"], budget_bytes=16000)
    assert context["complete"] is True
    assert context["omitted_node_ids"] == []
    assert {n["id"] for n in context["nodes"]} == {root["id"], left["id"], right["id"], merge["id"]}
    assert unrelated["id"] not in serialize_json(context)
    assert context["evidence_authority"] == "unverified"
    assert context["provenance"] == "research_ancestry_only"
    assert context["cursor"] == 6
    assert next(n for n in context["nodes"] if n["id"] == root["id"])["artifacts"][0]["label"] == "Source"
    assert context == store.context(merge["id"], budget_bytes=16000)


@pytest.mark.parametrize("budget", [1024, 1500, 3000, 8000])
def test_context_utf8_budget_truthfully_reports_whole_node_omissions(store, budget):
    root = store.create_node(kind="question", title="Unicode", content="日本語🌍" * 1000,
                             actor="a", operation_id="root")
    leaf = node(store, "leaf", parents=[root["id"]])
    result = store.context(leaf["id"], budget_bytes=budget)
    assert len(serialize_json(result).encode("utf-8")) <= budget
    assert result["complete"] is False
    assert root["id"] in result["omitted_node_ids"]
    included = {item["id"] for item in result["nodes"]}
    assert included.isdisjoint(result["omitted_node_ids"])
    assert included | set(result["omitted_node_ids"]) == {root["id"], leaf["id"]}


def test_context_reports_omission_count_when_index_exceeds_budget(store):
    parent = node(store)
    for i in range(35):
        parent = node(store, f"child-{i}", parents=[parent["id"]])
    result = store.context(parent["id"], budget_bytes=1024)
    assert len(serialize_json(result).encode()) <= 1024
    assert result["omitted_count"] == 36
    assert result["complete"] is False
    assert result["nodes"] == []
    assert "budget too small" in result["reason"]


@pytest.mark.parametrize("budget", [True, 1023, MAX_BYTES + 1])
def test_invalid_context_budget_fails_explicitly(store, budget):
    root = node(store)
    with pytest.raises(ResearchError, match="budget bytes"):
        store.context(root["id"], budget_bytes=budget)


def test_open_requires_explicit_creation_and_create_never_overwrites(tmp_path):
    path = tmp_path / "study.sqlite"
    with pytest.raises(ResearchError, match="create it explicitly"):
        ResearchStore(path)
    assert not path.exists()
    with ResearchStore.create(path, title="Existing") as study:
        root = node(study)
    with pytest.raises(FileExistsError):
        ResearchStore.create(path, title="Overwrite")
    with ResearchStore(path) as reopened:
        assert reopened.get_node(root["id"])["title"] == "root"


def test_open_rejects_foreign_unknown_schema_and_non_database_files(tmp_path):
    foreign = tmp_path / "foreign.sqlite"
    with sqlite3.connect(foreign) as db:
        db.execute("CREATE TABLE unrelated (id INTEGER)")
    with pytest.raises(ResearchError, match="not a Limes Quaestio"):
        ResearchStore(foreign)
    future = tmp_path / "future.sqlite"
    with sqlite3.connect(future) as db:
        db.execute(f"PRAGMA application_id={APPLICATION_ID}")
        db.execute("PRAGMA user_version=999")
    with pytest.raises(ResearchError, match="unsupported"):
        ResearchStore(future)
    invalid = tmp_path / "invalid.sqlite"
    invalid.write_bytes(b"This is not SQLite")
    with pytest.raises(ResearchError, match="invalid research study database"):
        ResearchStore(invalid)


def test_retry_returns_original_receipt_after_subsequent_revision(store):
    root = node(store)
    arguments = dict(expected_revision=1, content="First result", status="in_progress",
                     actor="a", operation_id="first")
    original = store.revise_node(root["id"], **arguments)
    store.revise_node(root["id"], expected_revision=2, content="Later result", status="completed",
                      actor="b", operation_id="later")
    assert store.revise_node(root["id"], **arguments) == original
    assert store.get_node(root["id"])["revision"] == 3
    assert store.snapshot()["cursor"] == 3


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "\ud800"], ids=["nan", "infinity", "surrogate"])
def test_serializer_rejects_nonfinite_or_non_utf8_json(value):
    with pytest.raises(ResearchError, match="finite UTF-8 JSON"):
        serialize_json({"value": value})


def test_serializer_rejects_cycles_and_preserves_caller_input():
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(ResearchError, match="finite UTF-8 JSON"):
        serialize_json(cyclic)
    assert cyclic[0] is cyclic
    source = {"z": ["日本語", {"b": 2, "a": 1}], "a": True}
    assert serialize_json(source) == '{"a":true,"z":["日本語",{"a":1,"b":2}]}'
    assert list(source) == ["z", "a"]
    assert list(source["z"][1]) == ["b", "a"]
