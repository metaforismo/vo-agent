# Durable research graph

## Problem and existing ownership

`WorkflowRun` owns one in-memory execution and exports a JSON bundle. `TaskGraph`
orders executable tasks inside a run; `ArtifactStore` records file metadata but
does not retain the file. `quaestio validate/inspect` reads these bundles and validates
their top-level shape. None of these objects owns a shared, cross-process history
of questions, competing hypotheses and outcomes. Changing their wire format to
be a database would mix execution and research state and break existing callers.

## Usage

```python
from quaestio.research import ResearchStore

with ResearchStore.create('study.sqlite', title='Retrieval experiment') as store:
    root = store.create_node(kind='question', title='Does reranking help?',
                             content='Compare under a fixed corpus and budget.',
                             actor='researcher', operation_id='question-1')
    branch = store.create_node(kind='experiment', title='Reranker baseline',
                               content='Keep the held-out queries fixed.',
                               parents=[root['id']], actor='agent-a',
                               operation_id='experiment-1')
    store.revise_node(branch['id'], expected_revision=1,
                      content='Completed local measurement; interpretation pending.',
                      status='completed', actor='agent-a', operation_id='finish-1')
```

`quaestio research` exposes the same operations as JSON for any agent with shell access.
The research view reads this state. Evidence bytes can be attached explicitly;
workflow bundles are recorded as reported executions, not trusted verifier results.

## Two design sketches

**A — JSON documents plus append-only JSONL.** Node files and a shared event log
are coordinated by a directory lock; artifact files have content-addressed names.
This makes text diffs easy but pushes crash recovery across several filesystem
writes, lock recovery and mixed-generation snapshots into the public contract.

**B — transactional SQLite study store.** One `ResearchStore` owns immutable node
revisions, ancestry edges, evidence bytes, reported executions and operation
receipts. Readers receive consistent snapshots; compare-and-swap prevents stale
writers from overwriting newer work. One transaction publishes a mutation, its
revision/event and its retry receipt.

## Synthesis decision

Choose B. SQLite is in the Python standard library and hides transaction and
concurrency details behind a small domain API. Existing workflow bundles and
`TaskGraph` remain unchanged. A node may cite only existing parents when created;
ancestry never changes, so cycles cannot be introduced. A merge creates a new
node with multiple parents, preserving every competing branch.

## Shape and invariants

- `ResearchStore.create / ResearchStore(path)`: distinguish new creation from reopening; unknown
  schemas and foreign SQLite files fail instead of being silently initialized.
- `create_node` / `revise_node`: own validation, immutable history, optimistic
  concurrency and exact durable retries. Revisions are work state, not truth.
- `attach_artifact` / `record_execution`: retain explicitly supplied bytes and
  hashes; no commands inside artifacts or imported bundles are executed.
- `snapshot` / `context`: return a transaction-consistent view; context has an
  explicit byte budget and reports omissions, never claims exhaustive knowledge.
- `artifact_bytes`: recheck integrity before returning stored evidence.
- CLI: transports validated domain operations. Visualization: derived read model.

One database is one trusted local study. This is not a tenant authorization
boundary, a sandbox, a remote scheduler or a scientific verifier. A supplied actor
name is attribution, not an authenticated identity. Untrusted writers with direct
file access can modify the SQLite file; the database is not tamper-proof.

## Memory boundary

[Limes-Labs/limes-tabularium](https://github.com/Limes-Labs/limes-tabularium)
owns canonical experience, evidence roles, state adjudication and memory context.
The research graph owns investigation topology and work history. Keep both
projects separate. A future adapter must rehydrate exact memory objects through
that kernel and its transition verifier; copying a graph node into a claim cannot
grant evidence authority. No personal Codex memories are imported in this change.

## Tradeoffs accepted

- We accept local SQLite single-writer serialization for durable multi-process
  state without a new hosted database dependency.
- We accept immutable ancestry for simple, auditable branching and merges;
  revising a hypothesis does not erase its previous content.
- We accept a read-only visual surface plus CLI writes for a smaller first
  operable boundary. Authentication and collaborative web editing are future work.
- We accept reported run outcomes as untrusted records; accepting a bundle never
  verifies the experiment or launches an agent.

## Reference basis

Flywheel separates [nodes, artifacts and executions](https://docs.flywheel.paradigma.inc/concepts/nodes-artifacts-executions).
Its [graph model](https://docs.flywheel.paradigma.inc/concepts/graph-model) motivates
branch-preserving ancestry, not a requirement to reproduce its hosted service.
Anthropic's [Fermat report](https://www.anthropic.com/research/formalizing-fermats-last-theorem)
describes benefits from shared theorem state, separate proof compilation and
search. That account is not a controlled claim that a DAG alone improves agents.

## Verification

Run `python -m pytest -q` in the activated development environment. Store tests
exercise independent processes, interrupted writes, concurrent revisions, retry
receipts and evidence integrity. CLI tests cover a complete study and failed
writes. The local browser view uses the same snapshot contract as the CLI.
