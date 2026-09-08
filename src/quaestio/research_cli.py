"""JSON CLI for the durable research graph. Import never executes source content."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from collections.abc import Mapping

from quaestio.exceptions import BundleValidationError
from quaestio.research import KINDS, MAX_BYTES, STATUSES, ResearchError, ResearchStore, serialize_json


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", required=True, help="local study SQLite file")
    commands = parser.add_subparsers(dest="research_command", required=True)
    init = commands.add_parser("init", help="create a new study; never overwrite")
    init.add_argument("--title", required=True)
    create = commands.add_parser("create", help="create a question, hypothesis or other node")
    create.add_argument("--kind", required=True, choices=sorted(KINDS))
    create.add_argument("--title", required=True)
    create.add_argument("--content", default="")
    create.add_argument("--parent", action="append", default=[])
    _mutation_options(create)
    branch = commands.add_parser("branch", help="create an alternative under an existing node")
    branch.add_argument("parent")
    branch.add_argument("--kind", choices=sorted(KINDS), default="experiment")
    branch.add_argument("--title", required=True)
    branch.add_argument("--content", default="")
    _mutation_options(branch)
    merge = commands.add_parser("merge", help="record a new decision with multiple parents")
    merge.add_argument("--parent", required=True, action="append")
    merge.add_argument("--title", required=True)
    merge.add_argument("--content", required=True)
    _mutation_options(merge)
    revise = commands.add_parser("revise", help="append a revision using optimistic concurrency")
    revise.add_argument("node")
    revise.add_argument("--expected-revision", required=True, type=int)
    revise.add_argument("--content", required=True)
    revise.add_argument("--status", required=True, choices=sorted(STATUSES))
    _mutation_options(revise)
    attach = commands.add_parser("attach", help="retain evidence bytes with a SHA-256 digest")
    attach.add_argument("node")
    attach.add_argument("file")
    attach.add_argument("--label", required=True)
    _mutation_options(attach)
    record = commands.add_parser("record-run", help="import a reported Quaestio execution bundle")
    record.add_argument("node")
    record.add_argument("bundle")
    _mutation_options(record)
    source = commands.add_parser("import-markdown", help="preserve a source and index headings as unverified notes")
    source.add_argument("file")
    source.add_argument("--title", required=True)
    _mutation_options(source)
    show = commands.add_parser("show", help="read a node and its full revision history")
    show.add_argument("node")
    commands.add_parser("list", help="read a consistent study snapshot")
    context = commands.add_parser("context", help="export bounded ancestry context; not memory authority")
    context.add_argument("node")
    context.add_argument("--budget-bytes", type=int, default=8000)
    artifact = commands.add_parser("artifact", help="retrieve stored evidence and verify its digest")
    artifact.add_argument("attachment")
    artifact.add_argument("--out", required=True)
    artifact.add_argument("--overwrite", action="store_true")
    export = commands.add_parser("export-html", help="write an offline interactive view")
    export.add_argument("--out", required=True)
    export.add_argument("--overwrite", action="store_true")
    serve = commands.add_parser("serve", help="serve the read-only local research view")
    serve.add_argument("--port", type=int, default=4208)


def _mutation_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--actor", required=True, help="attribution label, not authentication")
    parser.add_argument("--operation-id", required=True, help="stable unique retry ID; identical retries are idempotent")


def _read(path: str) -> bytes:
    with Path(path).open("rb") as source:
        data = source.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ResearchError(f"input exceeds {MAX_BYTES} bytes")
    return data


def _write(path: str, data: bytes, *, overwrite: bool) -> None:
    # Opening an output is an explicit caller action; use exclusive creation by default.
    with Path(path).open("wb" if overwrite else "xb") as output:
        output.write(data)


def run(args: argparse.Namespace) -> int:
    result: Mapping[str, object]
    try:
        if args.research_command == "init":
            with ResearchStore.create(args.db, title=args.title) as store:
                result = store.snapshot()
        elif args.research_command == "serve":
            from quaestio.research_view import serve
            serve(args.db, args.port)
            return 0
        else:
            with ResearchStore(args.db) as store:
                result = _dispatch(store, args)
        print(serialize_json(result))
        return 0
    except (ResearchError, BundleValidationError, OSError, sqlite3.Error, UnicodeError,
            json.JSONDecodeError) as exc:
        print(f"invalid research operation: {exc}", file=sys.stderr)
        return 1


def _dispatch(store: ResearchStore, args: argparse.Namespace) -> Mapping[str, object]:
    command = args.research_command
    if command in {"artifact", "export-html"}:
        output = Path(args.out)
        database = Path(args.db)
        if output.resolve() == database.resolve() or (
            output.exists() and output.samefile(database)
        ):
            raise ResearchError("output must not replace the study database")
    if command in {"create", "branch", "merge"}:
        parents = [args.parent] if command == "branch" else args.parent
        if command == "merge" and len(parents) < 2:
            raise ResearchError("a merge needs at least two distinct parents")
        return store.create_node(kind="decision" if command == "merge" else args.kind,
                                 title=args.title, content=args.content, parents=parents,
                                 actor=args.actor, operation_id=args.operation_id)
    if command == "revise":
        return store.revise_node(args.node, expected_revision=args.expected_revision,
                                 content=args.content, status=args.status,
                                 actor=args.actor, operation_id=args.operation_id)
    if command == "attach":
        return store.attach_artifact(args.node, data=_read(args.file), label=args.label,
                                     actor=args.actor, operation_id=args.operation_id)
    if command == "record-run":
        return store.record_execution(args.node, bundle=json.loads(_read(args.bundle)),
                                      actor=args.actor, operation_id=args.operation_id)
    if command == "import-markdown":
        return store.import_markdown(data=_read(args.file), title=args.title,
                                     actor=args.actor, operation_id=args.operation_id)
    if command == "show":
        return store.get_node(args.node)
    if command == "list":
        return store.snapshot()
    if command == "context":
        return store.context(args.node, budget_bytes=args.budget_bytes)
    if command == "artifact":
        data = store.artifact_bytes(args.attachment)
        _write(args.out, data, overwrite=args.overwrite)
        return dict(output=args.out, bytes=len(data), integrity="sha256_verified")
    if command == "export-html":
        from quaestio.research_view import render_html
        data = render_html(store.snapshot()).encode("utf-8")
        _write(args.out, data, overwrite=args.overwrite)
        return dict(output=args.out, bytes=len(data), mode="offline_snapshot")
    raise ResearchError(f"unknown command: {command}")
