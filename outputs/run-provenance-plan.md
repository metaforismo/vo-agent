# Run Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add run provenance to workflow bundles so each run records the local environment that produced its claims, evidence, agent transcripts, resources, and artifacts.

**Architecture:** Introduce `RunProvenance`, `GitInfo`, and `collect_provenance(...)` in a focused module. Provenance captures Python/platform/cwd/argv plus explicitly selected environment variables. Git metadata is best-effort: if `cwd` is not inside a git repository or `git` is unavailable, `git` is `None`.

**Tech Stack:** Python 3.11+, stdlib dataclasses, platform, subprocess, pathlib, pytest.

---

## File Structure

- `src/quaestio/provenance.py`: provenance models and collector.
- `src/quaestio/workflow.py`: add `provenance` to `WorkflowRun` and exported bundles.
- `src/quaestio/__init__.py`: export provenance API.
- `tests/test_provenance.py`: collector behavior.
- `tests/test_workflow_provenance.py`: workflow bundle behavior.
- `README.md`: document provenance and explicit env capture.
- `examples/local_agent_runner.py`: collect an explicit example env key.

---

### Task 1: Red Tests for Provenance

**Files:**
- Create: `tests/test_provenance.py`
- Create: `tests/test_workflow_provenance.py`

- [ ] **Step 1: Write collector tests**

Create `tests/test_provenance.py`:

```python
from pathlib import Path

from quaestio import collect_provenance


def test_collect_provenance_records_runtime_and_selected_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VO_TEST_ENV", "visible")
    monkeypatch.setenv("VO_SECRET_ENV", "hidden")

    provenance = collect_provenance(
        cwd=tmp_path,
        argv=["quaestio", "run"],
        env_keys=["VO_TEST_ENV"],
    )

    assert provenance.cwd == str(tmp_path)
    assert provenance.argv == ["quaestio", "run"]
    assert provenance.env == {"VO_TEST_ENV": "visible"}
    assert "VO_SECRET_ENV" not in provenance.env
    assert provenance.python_version
    assert provenance.platform
    assert provenance.git is None
```

- [ ] **Step 2: Write workflow bundle test**

Create `tests/test_workflow_provenance.py`:

```python
import json
from pathlib import Path

from quaestio import WorkflowRun, collect_provenance


def test_workflow_bundle_includes_provenance(tmp_path: Path):
    provenance = collect_provenance(cwd=tmp_path, argv=["demo"], env_keys=[])
    run = WorkflowRun(name="provenance-demo", provenance=provenance)

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["provenance"]["cwd"] == str(tmp_path)
    assert bundle["provenance"]["argv"] == ["demo"]
    assert bundle["provenance"]["env"] == {}
```

- [ ] **Step 3: Run tests and confirm red**

Run:

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_provenance.py tests/test_workflow_provenance.py -q
```

Expected: import failure for `collect_provenance`.

---

### Task 2: Provenance Models and Collector

**Files:**
- Create: `src/quaestio/provenance.py`
- Modify: `src/quaestio/__init__.py`

- [ ] **Step 1: Implement models**

Create:

- `GitInfo(root, commit, branch, dirty, changed_files, untracked_files)`
- `RunProvenance(cwd, argv, python_version, python_executable, platform, env, git, created_at)`

Both expose `to_dict()`.

- [ ] **Step 2: Implement `collect_provenance()`**

Signature:

```python
def collect_provenance(
    *,
    cwd: str | Path | None = None,
    argv: list[str] | None = None,
    env_keys: list[str] | tuple[str, ...] = (),
) -> RunProvenance:
```

Use `Path.cwd()` when `cwd` is absent. Include only environment variables listed in `env_keys` and present in `os.environ`.

- [ ] **Step 3: Implement best-effort git collector**

Use `git -C <cwd> rev-parse --show-toplevel`, `rev-parse HEAD`, `branch --show-current`, and `status --porcelain`. Return `None` if any required git command fails.

- [ ] **Step 4: Export provenance API**

Export `GitInfo`, `RunProvenance`, and `collect_provenance` from `src/quaestio/__init__.py`.

- [ ] **Step 5: Run provenance tests**

Run:

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_provenance.py -q
```

Expected: pass.

---

### Task 3: Workflow Integration

**Files:**
- Modify: `src/quaestio/workflow.py`

- [ ] **Step 1: Add provenance field**

Add `provenance: RunProvenance | None = None` to `WorkflowRun`. In `__post_init__`, set `self.provenance = collect_provenance()` when absent.

- [ ] **Step 2: Export provenance in bundle**

Add `"provenance": self.provenance.to_dict()` to `WorkflowRun.to_dict()`.

- [ ] **Step 3: Run workflow provenance tests**

Run:

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_workflow_provenance.py -q
```

Expected: pass.

---

### Task 4: Docs, Example, and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `examples/local_agent_runner.py`

- [ ] **Step 1: Update README**

Add a section explaining run provenance and explicit environment capture.

- [ ] **Step 2: Update local agent example**

Set `VO_EXAMPLE_RUN=local-agent` in the example process and pass `provenance=collect_provenance(cwd=root, argv=["examples/local_agent_runner.py"], env_keys=["VO_EXAMPLE_RUN"])` to `WorkflowRun`.

- [ ] **Step 3: Run final verification**

Run:

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/local_agent_runner.py
```

Expected: all tests pass and the example prints `work/local-agent-bundle.json`.

---

## Self-Review

- Spec coverage: The plan adds conservative, explicit run provenance to workflow bundles.
- Placeholder scan: No implementation placeholders are present.
- Type consistency: Tests and tasks consistently use `GitInfo`, `RunProvenance`, `collect_provenance`, and `WorkflowRun.provenance`.
