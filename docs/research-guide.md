# Working with a research study

Install the checkout with `python -m pip install -e '.[dev]'` inside an activated
virtual environment. `quaestio research --help` lists the command contract. JSON
is written to stdout; invalid operations return exit status 1 and an error on
stderr. Argument usage errors return 2. `serve` prints its loopback URL.

## Create, branch and merge

```bash
quaestio research --db study.sqlite init --title 'Retrieval study'
quaestio research --db study.sqlite create --kind question --title 'Does reranking help?' \
  --content 'Keep queries, corpus and budget fixed.' --actor researcher --operation-id question-1
```

Copy the returned `id` into `ROOT`. Each operation ID identifies one exact request.

```bash
quaestio research --db study.sqlite branch "$ROOT" --title 'Baseline' \
  --actor agent-a --operation-id baseline-1
quaestio research --db study.sqlite branch "$ROOT" --title 'Reranked' \
  --actor agent-b --operation-id reranked-1
```

Use the two returned IDs as `BASELINE` and `ALTERNATIVE`. A merge creates a new
node with both parents; it does not erase either branch or certify its conclusion.

```bash
quaestio research --db study.sqlite merge --parent "$BASELINE" --parent "$ALTERNATIVE" \
  --title 'Comparison decision' --content 'Review measurements before accepting a conclusion.' \
  --actor researcher --operation-id decision-1
quaestio research --db study.sqlite revise "$BASELINE" --expected-revision 1 \
  --content 'Experiment completed; interpretation pending.' --status completed \
  --actor agent-a --operation-id baseline-finish
```

Node kinds: question, hypothesis, experiment, result, decision, source, note.
Work states: open, in_progress, completed, failed. Completion is workflow state,
not a truth or verification label. Parent edges and node identity are immutable;
`show ID` includes every content revision and attachment metadata.

## Retry and concurrency

Reuse an operation ID only for the same action, actor and payload. An exact retry
returns its original receipt even after reopening the database. A changed request
with the same ID fails without a partial write. `revise` requires the latest
revision number. If another writer wins, read `show ID`, reconcile deliberately,
and submit a new operation ID with the new expected revision. Never blindly retry
a stale edit as though it had succeeded. `init` always refuses an existing file.

## Evidence, source import and execution records

```bash
quaestio research --db study.sqlite attach "$BASELINE" measurements.json \
  --label 'Fixed query measurements' --actor agent-a --operation-id measurements-1
quaestio research --db study.sqlite import-markdown source.md --title 'Source notes' \
  --actor researcher --operation-id import-1
quaestio research --db study.sqlite record-run "$BASELINE" run-bundle.json \
  --actor agent-a --operation-id reported-run-1
```

Evidence is retained inside SQLite with SHA-256 and size. `artifact ATTACHMENT_ID
--out evidence.bin` verifies bytes before writing. Outputs require `--overwrite`
to replace an existing file and cannot replace the study database. Markdown
import preserves the original file and indexes headings as unverified notes;
it is a structural import, not extraction or verification of scientific claims.
Run import validates the existing bundle's top-level shape and stores it as
`reported_unverified`, with `execution_authorized: false`. It never executes
embedded commands or trusts claimed outcomes. No personal memory is imported.

## Context and inspection

```bash
quaestio research --db study.sqlite context "$ALTERNATIVE" --budget-bytes 8000
quaestio research --db study.sqlite export-html --out graph.html
quaestio research --db study.sqlite serve --port 4208
```

Context prioritizes the selected node, then ancestors. It includes evidence
metadata, not evidence bodies. `complete` and omission fields expose truncation.
The byte budget measures compact UTF-8 JSON, excluding the CLI's final newline.
This export is research context, not canonical Tabularium memory authority.

The local viewer supports node selection, ancestry, evidence downloads, title /
content / actor search and work-state filters. Changes from CLI writers refresh
in the live view; disconnects retain the last snapshot with a visible warning.
Offline HTML is a snapshot with attachment metadata; retrieve bytes from the
study with the CLI. Untrusted content is displayed as text.

One database is one trusted local study. There is no authentication, tenant
isolation or sandbox. Actors are attribution labels. The server binds only to
127.0.0.1, exposes reads and rejects foreign Host headers. Keep the database on a
local filesystem and stop writers before copying it for backup. Limits: 2,000
nodes per study, 64 parents per node, 2 MiB per artifact/source/bundle and 60
Markdown headings per import. A context budget is 1,024 bytes to 2 MiB.
