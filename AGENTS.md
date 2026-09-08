# Working on Limes Quaestio

Read `docs/architecture.md` and `docs/research-graph-design.md` before changing
ownership boundaries. `docs/research-guide.md` describes the public JSON CLI.

- `WorkflowRun` owns execution records; `TaskGraph` owns within-run scheduling.
  `ResearchStore` owns durable research ancestry, revisions, bytes and receipts.
- Keep store mutations and their retry receipt in one SQLite transaction.
  Preserve immutable parents and compare-and-swap revision semantics.
- Work completion and imported reports do not grant evidence or execution
  authority. Source import never runs commands. Actor labels are not identities.
- Do not silently initialize, replace or repair an existing study file.
- Keep JSON field names explicit and typed. Avoid hidden network calls.
- Generated studies and execution outputs belong in ignored `work/`.

Verify with `uv sync --extra dev`, `uv run pytest -q`, and `uv build`.
Run `uv run python examples/research_study.py --out work/research-check` with a
new output directory; inspect its graph using the local research server.
Material view changes require desktop and mobile browser checks. Local checks
are separate from the Python 3.11/3.12/3.13 CI matrix and any hosted claims.
