"""Durable local research state, independent from execution or evidence authority."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, TypedDict, TypeVar, cast
from uuid import uuid4

from quaestio.bundles import validate_bundle_dict
from quaestio.models import utc_now

NodeKind = Literal["question", "hypothesis", "experiment", "result", "decision", "source", "note"]
WorkStatus = Literal["open", "in_progress", "completed", "failed"]
ResearchAction = Literal["create_node", "revise_node", "attach_artifact", "record_execution", "import_markdown"]


class StudyRecord(TypedDict):
    id: str
    title: str
    created_at: str


class NodeRecord(TypedDict):
    """Current immutable revision plus the node's fixed identity and ancestry."""

    id: str
    kind: NodeKind
    title: str
    created_at: str
    revision: int
    content: str
    status: WorkStatus
    actor: str
    revised_at: str
    parents: list[str]


class RevisionRecord(TypedDict):
    node_id: str
    revision: int
    content: str
    status: WorkStatus
    actor: str
    created_at: str


class AttachmentRecord(TypedDict):
    id: str
    node_id: str
    sha256: str
    size_bytes: int
    label: str
    actor: str
    created_at: str


class NodeDetail(NodeRecord):
    history: list[RevisionRecord]
    artifacts: list[AttachmentRecord]


class ExecutionReceipt(TypedDict):
    """Import receipt; reported outcomes never grant verification authority."""

    id: str
    node_id: str
    artifact_id: str
    reported_run_id: str
    name: str
    evidence_status: Literal["reported_unverified"]
    execution_authorized: Literal[False]


class ExecutionRecord(ExecutionReceipt):
    actor: str
    created_at: str


class OperationRecord(TypedDict):
    sequence: int
    operation_id: str
    action: ResearchAction
    actor: str
    created_at: str


class StudySnapshot(TypedDict):
    schema_version: int
    study: StudyRecord
    cursor: int
    nodes: list[NodeRecord]
    artifacts: list[AttachmentRecord]
    executions: list[ExecutionRecord]
    events: list[OperationRecord]
    interpretation: str


class MarkdownImportReceipt(TypedDict):
    source: NodeRecord
    sections: list[NodeRecord]
    artifact: AttachmentRecord
    interpretation: Literal["unverified_source_text"]


class ContextNode(NodeRecord):
    artifacts: list[AttachmentRecord]


class AncestryContext(TypedDict):
    """Whole selected nodes; omitted_node_ids explicitly accounts for the rest."""

    study: StudyRecord
    cursor: int
    target: str
    nodes: list[ContextNode]
    omitted_node_ids: list[str]
    complete: bool
    provenance: Literal["research_ancestry_only"]
    evidence_authority: Literal["unverified"]
    budget_bytes: int


class OmittedAncestryContext(TypedDict):
    """No nodes fit alongside the ancestry index; only its count is returned."""

    study_id: str
    cursor: int
    target: str
    nodes: list[ContextNode]
    omitted_count: int
    complete: Literal[False]
    budget_bytes: int
    reason: Literal["budget too small for ancestry index"]
    evidence_authority: Literal["unverified"]


ResearchContext = AncestryContext | OmittedAncestryContext
_MutationResult = TypeVar("_MutationResult", bound=Mapping[str, object])


KINDS: set[NodeKind] = {"question", "hypothesis", "experiment", "result", "decision", "source", "note"}
STATUSES: set[WorkStatus] = {"open", "in_progress", "completed", "failed"}
MAX_BYTES = 2 * 1024 * 1024
MAX_NODES = 2000
APPLICATION_ID = 0x564F5253
SCHEMA_VERSION = 1


class ResearchError(ValueError):
    """Invalid study operation or incompatible study database."""


class ResearchConflict(ResearchError):
    """Stale revision or operation ID reused with different input."""


def _text(value: object, label: str, maximum: int = 500, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ResearchError(f"{label} must be a {'possibly empty' if empty else 'non-empty'} string")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError as exc:
        raise ResearchError(f"{label} must be UTF-8") from exc
    if size > maximum or "\x00" in value:
        raise ResearchError(f"{label} exceeds its limit or contains NUL")
    return value


def _integer(value: object, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ResearchError(f"{label} must be an integer in [{minimum}, {maximum}]")
    return value


def serialize_json(value: object) -> str:
    """Canonical compact JSON; context budgets measure this UTF-8 representation."""
    try:
        rendered = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                              separators=(",", ":"))
        rendered.encode("utf-8")
        return rendered
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise ResearchError("value is not finite UTF-8 JSON") from exc


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bytes(data: object) -> bytes:
    if not isinstance(data, bytes) or len(data) > MAX_BYTES:
        raise ResearchError(f"artifact must be bytes of at most {MAX_BYTES} bytes")
    return data


def _markdown_headings(text: str) -> list[tuple[int, int, str]]:
    """Find ATX sections without interpreting headings inside fenced code."""
    headings: list[tuple[int, int, str]] = []
    offset = 0
    fence = ""
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = ""
        elif marker:
            fence = marker[1]
        else:
            heading = re.match(r"^ {0,3}#{1,6} +(.+?)\s*$", line)
            if heading:
                headings.append((offset, offset + len(line), heading[1]))
        offset += len(line)
    return headings


_SCHEMA = f"""
BEGIN IMMEDIATE;
CREATE TABLE study (id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE nodes (id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
                    created_at TEXT NOT NULL);
CREATE TABLE edges (parent TEXT NOT NULL REFERENCES nodes(id),
                    child TEXT NOT NULL REFERENCES nodes(id),
                    PRIMARY KEY (parent, child), CHECK (parent != child));
CREATE TABLE revisions (node_id TEXT NOT NULL REFERENCES nodes(id), revision INTEGER NOT NULL,
                        content TEXT NOT NULL, status TEXT NOT NULL, actor TEXT NOT NULL,
                        created_at TEXT NOT NULL, PRIMARY KEY (node_id, revision));
CREATE TABLE artifacts (sha256 TEXT PRIMARY KEY, size_bytes INTEGER NOT NULL, data BLOB NOT NULL);
CREATE TABLE attachments (id TEXT PRIMARY KEY, node_id TEXT NOT NULL REFERENCES nodes(id),
                         sha256 TEXT NOT NULL REFERENCES artifacts(sha256), label TEXT NOT NULL,
                         actor TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE executions (id TEXT PRIMARY KEY, node_id TEXT NOT NULL REFERENCES nodes(id),
                        artifact_id TEXT NOT NULL REFERENCES attachments(id),
                        reported_run_id TEXT NOT NULL, name TEXT NOT NULL,
                        actor TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE operations (sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                        operation_id TEXT NOT NULL UNIQUE, input_sha256 TEXT NOT NULL,
                        action TEXT NOT NULL, actor TEXT NOT NULL,
                        result_json TEXT NOT NULL, created_at TEXT NOT NULL);
PRAGMA application_id = {APPLICATION_ID};
PRAGMA user_version = {SCHEMA_VERSION};
"""


class ResearchStore:
    """One trusted local study; methods commit atomically and return detached JSON.

    A completed node is completed work, not a verified scientific claim. Actor
    names are attribution, not authentication. Direct database access is trusted.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        if not self.path.is_file():
            raise ResearchError("study does not exist; create it explicitly")
        self._db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True,
                                   isolation_level=None, timeout=10)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        try:
            if self._db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID:
                raise ResearchError("not a Limes Quaestio research study")
            if self._db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                raise ResearchError("unsupported research schema version")
            rows = self._db.execute("SELECT id, title, created_at FROM study").fetchall()
            if len(rows) != 1:
                raise ResearchError("study metadata is incomplete")
        except sqlite3.DatabaseError as exc:
            self._db.close()
            raise ResearchError("invalid research study database") from exc
        except BaseException:
            self._db.close()
            raise

    @classmethod
    def create(cls, path: str | Path, *, title: str) -> ResearchStore:
        title = _text(title, "study title")
        destination = Path(path).resolve()
        descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        db = sqlite3.connect(destination, isolation_level=None)
        try:
            db.executescript(_SCHEMA)
            db.execute("INSERT INTO study VALUES (?, ?, ?)", (uuid4().hex, title, utc_now()))
            db.execute("COMMIT")
        finally:
            db.close()
        return cls(destination)

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> ResearchStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @contextmanager
    def _transaction(self, *, write: bool = False) -> Iterator[None]:
        self._db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        try:
            yield
            self._db.execute("COMMIT")
        except BaseException:
            self._db.execute("ROLLBACK")
            raise

    def _mutate(self, action: ResearchAction, payload: Mapping[str, object], *, actor: str,
                operation_id: str, apply: Callable[[], _MutationResult]) -> _MutationResult:
        actor = _text(actor, "actor", 160)
        operation_id = _text(operation_id, "operation ID", 160)
        fingerprint = _digest(serialize_json([action, actor, payload]).encode())
        with self._transaction(write=True):
            old = self._db.execute("SELECT * FROM operations WHERE operation_id = ?",
                                   (operation_id,)).fetchone()
            if old:
                if old["input_sha256"] != fingerprint:
                    raise ResearchConflict("operation ID already used with different input")
                # Receipts contain results written by this schema for the same action/input.
                return cast(_MutationResult, json.loads(old["result_json"]))
            result = apply()
            self._db.execute(
                "INSERT INTO operations(operation_id,input_sha256,action,actor,result_json,created_at) "
                "VALUES (?,?,?,?,?,?)",
                (operation_id, fingerprint, action, actor, serialize_json(result), utc_now()))
            return result

    def _node(self, node_id: str) -> NodeRecord:
        row = self._db.execute(
            "SELECT n.*, r.revision, r.content, r.status, r.actor, r.created_at AS revised_at "
            "FROM nodes n JOIN revisions r ON r.node_id=n.id WHERE n.id=? "
            "ORDER BY r.revision DESC LIMIT 1", (node_id,)).fetchone()
        if row is None:
            raise ResearchError(f"unknown node: {node_id}")
        node = dict(row)
        node["parents"] = [r[0] for r in self._db.execute(
            "SELECT parent FROM edges WHERE child=? ORDER BY parent", (node_id,))]
        return cast(NodeRecord, node)

    def _create_node(self, *, kind: NodeKind, title: str, content: str,
                     parents: list[str], actor: str) -> NodeRecord:
        if self._db.execute("SELECT count(*) FROM nodes").fetchone()[0] >= MAX_NODES:
            raise ResearchError(f"study limit is {MAX_NODES} nodes")
        for parent in parents:
            self._node(parent)
        node_id, now = uuid4().hex, utc_now()
        self._db.execute("INSERT INTO nodes VALUES (?,?,?,?)", (node_id, kind, title, now))
        self._db.execute("INSERT INTO revisions VALUES (?,?,?,?,?,?)",
                         (node_id, 1, content, "open", actor, now))
        self._db.executemany("INSERT INTO edges VALUES (?,?)", [(p, node_id) for p in parents])
        return self._node(node_id)

    def create_node(self, *, kind: NodeKind, title: str, content: str, actor: str,
                    operation_id: str, parents: list[str] | None = None) -> NodeRecord:
        if not isinstance(kind, str) or kind not in KINDS:
            raise ResearchError("unknown node kind")
        title = _text(title, "node title")
        content = _text(content, "content", MAX_BYTES, empty=True)
        if parents is None:
            parents = []
        if not isinstance(parents, list) or len(parents) > 64:
            raise ResearchError("parents must be a list of at most 64 IDs")
        parents = [_text(p, "parent ID", 160) for p in parents]
        if len(set(parents)) != len(parents):
            raise ResearchError("duplicate parents")
        parents = sorted(parents)
        payload = dict(kind=kind, title=title, content=content, parents=parents)
        return self._mutate("create_node", payload, actor=actor, operation_id=operation_id,
                            apply=lambda: self._create_node(kind=kind, title=title, content=content,
                                                            parents=parents, actor=actor))

    def revise_node(self, node_id: str, *, expected_revision: int, content: str,
                    status: WorkStatus, actor: str, operation_id: str) -> NodeRecord:
        node_id = _text(node_id, "node ID", 160)
        expected_revision = _integer(expected_revision, "expected revision", 1, 2**31 - 1)
        content = _text(content, "content", MAX_BYTES, empty=True)
        if not isinstance(status, str) or status not in STATUSES:
            raise ResearchError("unknown work status")
        payload = dict(node_id=node_id, expected_revision=expected_revision,
                       content=content, status=status)

        def apply() -> NodeRecord:
            node = self._node(node_id)
            if node["revision"] != expected_revision:
                raise ResearchConflict(f"stale revision; current revision is {node['revision']}")
            self._db.execute("INSERT INTO revisions VALUES (?,?,?,?,?,?)",
                             (node_id, expected_revision + 1, content, status, actor, utc_now()))
            return self._node(node_id)
        return self._mutate("revise_node", payload, actor=actor, operation_id=operation_id,
                            apply=apply)

    def _attach(self, node_id: str, data: bytes, label: str, actor: str) -> AttachmentRecord:
        self._node(node_id)
        sha256 = _digest(data)
        old = self._db.execute("SELECT data, size_bytes FROM artifacts WHERE sha256=?", (sha256,)).fetchone()
        if old is not None and (bytes(old["data"]) != data or old["size_bytes"] != len(data)):
            raise ResearchError("stored artifact integrity mismatch")
        if old is None:
            self._db.execute("INSERT INTO artifacts VALUES (?,?,?)", (sha256, len(data), data))
        attachment_id, now = uuid4().hex, utc_now()
        self._db.execute("INSERT INTO attachments VALUES (?,?,?,?,?,?)",
                         (attachment_id, node_id, sha256, label, actor, now))
        return dict(id=attachment_id, node_id=node_id, sha256=sha256, size_bytes=len(data),
                    label=label, actor=actor, created_at=now)

    def attach_artifact(self, node_id: str, *, data: bytes, label: str, actor: str,
                        operation_id: str) -> AttachmentRecord:
        node_id, label = _text(node_id, "node ID", 160), _text(label, "artifact label")
        data = _bytes(data)
        payload = dict(node_id=node_id, sha256=_digest(data), size_bytes=len(data), label=label)
        return self._mutate("attach_artifact", payload, actor=actor, operation_id=operation_id,
                            apply=lambda: self._attach(node_id, data, label, actor))

    def record_execution(self, node_id: str, *, bundle: dict[str, object], actor: str,
                         operation_id: str) -> ExecutionReceipt:
        node_id = _text(node_id, "node ID", 160)
        # Freeze input once. A reported bundle is data, not verifier authority.
        data = _bytes(serialize_json(bundle).encode("utf-8"))
        frozen = json.loads(data)
        validate_bundle_dict(frozen)
        reported_run_id = _text(frozen["run_id"], "reported run ID", 160)
        reported_name = _text(frozen["name"], "reported run name")
        payload = dict(node_id=node_id, sha256=_digest(data))

        def apply() -> ExecutionReceipt:
            artifact = self._attach(node_id, data, "Reported workflow bundle", actor)
            run_id, now = uuid4().hex, utc_now()
            self._db.execute("INSERT INTO executions VALUES (?,?,?,?,?,?,?)",
                             (run_id, node_id, artifact["id"], reported_run_id, reported_name, actor, now))
            return dict(id=run_id, node_id=node_id, artifact_id=artifact["id"],
                        reported_run_id=reported_run_id, name=reported_name,
                        evidence_status="reported_unverified", execution_authorized=False)
        return self._mutate("record_execution", payload, actor=actor, operation_id=operation_id,
                            apply=apply)

    def import_markdown(self, *, data: bytes, title: str, actor: str,
                        operation_id: str) -> MarkdownImportReceipt:
        data = _bytes(data)
        title = _text(title, "source title")
        try:
            text = data.decode("utf-8")
        except UnicodeError as exc:
            raise ResearchError("source must be UTF-8 Markdown") from exc
        _text(text, "source text", MAX_BYTES)
        headings = _markdown_headings(text)
        if len(headings) > 60:
            raise ResearchError("source has more than 60 sections; split it explicitly")
        for heading in headings:
            _text(heading[2], "section title")
        payload = dict(title=title, sha256=_digest(data))

        def apply() -> MarkdownImportReceipt:
            root = self._create_node(kind="source", title=title,
                                     content="Imported source. Statements are unverified source text.",
                                     parents=[], actor=actor)
            attachment = self._attach(root["id"], data, title, actor)
            children = []
            for index, heading in enumerate(headings):
                end = headings[index + 1][0] if index + 1 < len(headings) else len(text)
                children.append(self._create_node(
                    kind="note", title=heading[2], content=text[heading[1]:end].strip(),
                    parents=[root["id"]], actor=actor))
            return dict(source=root, sections=children, artifact=attachment,
                        interpretation="unverified_source_text")
        return self._mutate("import_markdown", payload, actor=actor, operation_id=operation_id,
                            apply=apply)

    def get_node(self, node_id: str) -> NodeDetail:
        node_id = _text(node_id, "node ID", 160)
        with self._transaction():
            history = [cast(RevisionRecord, dict(r)) for r in self._db.execute(
                "SELECT * FROM revisions WHERE node_id=? ORDER BY revision", (node_id,))]
            artifacts = [cast(AttachmentRecord, dict(r)) for r in self._db.execute(
                "SELECT a.*, b.size_bytes FROM attachments a JOIN artifacts b ON a.sha256=b.sha256 "
                "WHERE a.node_id=? ORDER BY a.created_at,a.id", (node_id,))]
            return NodeDetail(**self._node(node_id), history=history, artifacts=artifacts)

    def artifact_bytes(self, attachment_id: str) -> bytes:
        attachment_id = _text(attachment_id, "attachment ID", 160)
        with self._transaction():
            row = self._db.execute(
                "SELECT b.* FROM artifacts b JOIN attachments a ON a.sha256=b.sha256 WHERE a.id=?",
                (attachment_id,)).fetchone()
            if row is None:
                raise ResearchError("unknown artifact attachment")
            data = bytes(row["data"])
            if _digest(data) != row["sha256"] or len(data) != row["size_bytes"]:
                raise ResearchError("stored artifact integrity mismatch")
            return data

    def snapshot(self) -> StudySnapshot:
        with self._transaction():
            return self._snapshot()

    def _snapshot(self) -> StudySnapshot:
        study = cast(StudyRecord, dict(self._db.execute("SELECT * FROM study").fetchone()))
        nodes = [self._node(r[0]) for r in self._db.execute("SELECT id FROM nodes ORDER BY rowid")]
        artifacts = [cast(AttachmentRecord, dict(r)) for r in self._db.execute(
            "SELECT a.*, b.size_bytes FROM attachments a JOIN artifacts b ON a.sha256=b.sha256 ORDER BY a.rowid")]
        executions = [cast(ExecutionRecord, dict(r) | {"evidence_status": "reported_unverified",
                                                    "execution_authorized": False})
                      for r in self._db.execute("SELECT * FROM executions ORDER BY rowid")]
        events = [cast(OperationRecord, dict(r)) for r in self._db.execute(
            "SELECT sequence,operation_id,action,actor,created_at FROM operations ORDER BY sequence")]
        return dict(schema_version=SCHEMA_VERSION, study=study, cursor=len(events), nodes=nodes,
                    artifacts=artifacts, executions=executions, events=events,
                    interpretation="Work state and reported evidence; not adjudicated scientific truth")

    def context(self, node_id: str, *, budget_bytes: int = 8000) -> ResearchContext:
        """Return bounded ancestry; budget counts serialize_json UTF-8 bytes."""
        node_id = _text(node_id, "node ID", 160)
        budget_bytes = _integer(budget_bytes, "budget bytes", 1024, MAX_BYTES)
        with self._transaction():
            snapshot = self._snapshot()
        nodes = {n["id"]: n for n in snapshot["nodes"]}
        if node_id not in nodes:
            raise ResearchError(f"unknown node: {node_id}")
        queue = [node_id]
        order: list[str] = []
        seen: set[str] = set()
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            order.append(current)
            queue.extend(nodes[current]["parents"])
        result: AncestryContext = dict(study=snapshot["study"], cursor=snapshot["cursor"],
            target=node_id, nodes=[], omitted_node_ids=[], complete=False,
            provenance="research_ancestry_only", evidence_authority="unverified", budget_bytes=budget_bytes)
        # Reserve worst-case space for omission IDs so JSON itself remains bounded.
        result["omitted_node_ids"] = order[:]
        if len(serialize_json(result).encode()) > budget_bytes:
            # An explicit count remains truthful when even omission IDs do not fit.
            return dict(study_id=snapshot["study"]["id"], cursor=snapshot["cursor"], target=node_id,
                        nodes=[], omitted_count=len(order), complete=False, budget_bytes=budget_bytes,
                        reason="budget too small for ancestry index", evidence_authority="unverified")
        for current in order:
            candidate = ContextNode(**nodes[current],
                artifacts=[a for a in snapshot["artifacts"] if a["node_id"] == current])
            result["nodes"].append(candidate)
            result["omitted_node_ids"].remove(current)
            if len(serialize_json(result).encode()) > budget_bytes:
                result["nodes"].pop()
                result["omitted_node_ids"].append(current)
        result["complete"] = not result["omitted_node_ids"]
        return result
