# Contributing

VO Agent is currently a local-first Python library for reproducible agent
workflow records.

## Setup

```bash
uv sync --extra dev
```

If you do not want a project environment in the repository, use:

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
```

## Development Rules

- Write tests before behavior changes.
- Keep bundle schema changes explicit and covered by `tests/test_bundles.py`.
- Keep reports readable and covered by `tests/test_report.py`.
- Do not serialize secret values. Store only secret names.
- Generated runtime artifacts belong in `work/` and are ignored by git.

## Verification

Run the focused tests for your change, then the full suite:

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
```

Run examples when bundle or report shape changes:

```bash
for example in examples/*.py; do
  UV_PROJECT_ENVIRONMENT=work/.venv uv run python "$example"
done
```

Validate generated bundles:

```bash
for bundle in work/*-bundle.json; do
  UV_PROJECT_ENVIRONMENT=work/.venv uv run vo validate "$bundle"
done
```
