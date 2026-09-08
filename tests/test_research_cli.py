from __future__ import annotations

import json
from pathlib import Path

from quaestio.cli import main
from quaestio.research import ResearchStore
from quaestio.research_view import render_html


def test_cli_study_retry_conflict_evidence_and_bounded_context(tmp_path, capsys):
    database = tmp_path / "study.sqlite"
    prefix = ["research", "--db", str(database)]

    def invoke(*args):
        assert main(prefix + list(args)) == 0
        captured = capsys.readouterr()
        assert captured.err == ""
        return json.loads(captured.out)

    invoke("init", "--title", "Cancellation")
    operation = ["create", "--kind", "question", "--title", "Why?", "--content", "é" * 3000,
                 "--actor", "researcher", "--operation-id", "question-1"]
    root = invoke(*operation)
    assert invoke(*operation) == root
    alternate = invoke("branch", root["id"], "--title", "Alternative", "--actor", "agent",
                       "--operation-id", "alternative-1")
    decision = invoke("merge", "--parent", root["id"], "--parent", alternate["id"],
                      "--title", "Decision", "--content", "Keep both branches", "--actor", "researcher",
                      "--operation-id", "merge-1")
    assert set(decision["parents"]) == {root["id"], alternate["id"]}
    invoke("revise", root["id"], "--expected-revision", "1", "--content", "measured", "--status",
           "completed", "--actor", "researcher", "--operation-id", "revision-1")
    assert main(prefix + ["revise", root["id"], "--expected-revision", "1", "--content", "stale",
                          "--status", "failed", "--actor", "other", "--operation-id", "stale-1"]) == 1
    assert "revision" in capsys.readouterr().err
    evidence = tmp_path / "evidence.txt"
    evidence.write_bytes(b"retained evidence")
    attached = invoke("attach", root["id"], str(evidence), "--label", "Measurement",
                      "--actor", "researcher", "--operation-id", "attach-1")
    evidence.unlink()
    output = tmp_path / "recovered.txt"
    invoke("artifact", attached["id"], "--out", str(output))
    assert output.read_bytes() == b"retained evidence"
    assert main(prefix + ["context", decision["id"], "--budget-bytes", "1024"]) == 0
    raw = capsys.readouterr().out.rstrip("\n")
    assert len(raw.encode()) <= 1024
    assert json.loads(raw)["complete"] is False
    assert invoke("show", root["id"])["content"] == "measured"


def test_export_does_not_replace_database_or_existing_output(tmp_path, capsys):
    db = tmp_path / "study.sqlite"
    with ResearchStore.create(db, title="Study"):
        pass
    prefix = ["research", "--db", str(db), "export-html"]
    before = db.read_bytes()
    assert main(prefix + ["--out", str(db), "--overwrite"]) == 1
    assert "must not replace" in capsys.readouterr().err
    assert db.read_bytes() == before
    output = tmp_path / "graph.html"
    output.write_text("existing")
    assert main(prefix + ["--out", str(output)]) == 1
    capsys.readouterr()
    assert output.read_text() == "existing"
    assert main(prefix + ["--out", str(output), "--overwrite"]) == 0
    assert "Offline snapshot" in output.read_text()


def test_export_preserves_source_text_without_interpreting_template_markers(tmp_path):
    title = 'A < B & __LIVE__ __SNAPSHOT__'
    with ResearchStore.create(tmp_path / "study.sqlite", title=title) as store:
        html = render_html(store.snapshot())
    payload = html.split('<script type="application/json" id="snapshot">', 1)[1].split('</script>', 1)[0]
    assert '<' not in payload
    assert json.loads(payload)["study"]["title"] == title
