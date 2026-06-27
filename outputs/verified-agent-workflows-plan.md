# Verified Agent Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working slice of a Python library for reproducible, evidence-gated agent workflows.

**Architecture:** The first slice is local-first and deterministic. It models agents, resources, claims, evidence, verifier chains, and run bundles without depending on a hosted control plane or live LLM APIs. Cloud VMs, remote agents, and UI steering remain future layers over the same data model.

**Tech Stack:** Python 3.11+, stdlib dataclasses, pathlib, subprocess, json, pytest.

---

## File Structure

- `pyproject.toml`: package metadata, pytest configuration, editable install support.
- `README.md`: product position, first API example, and current scope.
- `src/vo/__init__.py`: public API exports.
- `src/vo/exceptions.py`: domain exceptions for resource conflicts and verification failures.
- `src/vo/models.py`: dataclasses for agent specs, claims, evidence records, events, and JSON conversion.
- `src/vo/resources.py`: explicit resource lease manager so agents cannot silently collide on shared state.
- `src/vo/verifiers.py`: verifier protocol, command verifier, callable verifier, and verifier chain.
- `src/vo/workflow.py`: `WorkflowRun`, the high-level object that ties agents, resources, claims, evidence, events, and bundle export together.
- `tests/test_resources.py`: resource lease behavior.
- `tests/test_verifiers.py`: evidence-gated verifier chain behavior.
- `tests/test_workflow.py`: end-to-end workflow bundle behavior.
- `examples/optimize_with_evidence.py`: small runnable example showing a speed/test gate shape.

---

### Task 1: Project Skeleton and Red Tests

**Files:**
- Create: `pyproject.toml`
- Create: `tests/test_resources.py`
- Create: `tests/test_verifiers.py`
- Create: `tests/test_workflow.py`

- [ ] **Step 1: Create package metadata**

Create `pyproject.toml` with editable package configuration and pytest defaults:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "vo-agent"
version = "0.1.0"
description = "Evidence-gated workflows for coordinating coding agents."
readme = "README.md"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Write failing resource tests**

Create `tests/test_resources.py`:

```python
import pytest

from vo import ResourceConflict, ResourceManager


def test_resource_manager_blocks_conflicting_active_lease():
    resources = ResourceManager()
    lease = resources.acquire("repo:src/parser.py", owner="optimizer")

    with pytest.raises(ResourceConflict):
        resources.acquire("repo:src/parser.py", owner="reviewer")

    lease.release()
    second = resources.acquire("repo:src/parser.py", owner="reviewer")

    assert second.owner == "reviewer"
    assert resources.snapshot()["repo:src/parser.py"]["owner"] == "reviewer"
```

- [ ] **Step 3: Write failing verifier tests**

Create `tests/test_verifiers.py`:

```python
from pathlib import Path

from vo import Claim, CommandVerifier, VerificationContext, VerifierChain


def test_verifier_chain_accepts_claim_when_all_checks_pass(tmp_path: Path):
    claim = Claim(statement="tests pass before merge")
    chain = VerifierChain(
        [
            CommandVerifier("python -c 'print(42)'", name="smoke"),
            CommandVerifier("python -c 'raise SystemExit(0)'", name="exit-zero"),
        ]
    )

    result = chain.verify(claim, VerificationContext(cwd=tmp_path))

    assert result.passed is True
    assert claim.status == "accepted"
    assert [e.name for e in claim.evidence] == ["smoke", "exit-zero"]
    assert claim.evidence[0].data["stdout"].strip() == "42"


def test_verifier_chain_rejects_claim_on_first_failing_check(tmp_path: Path):
    claim = Claim(statement="benchmark improved")
    chain = VerifierChain(
        [
            CommandVerifier("python -c 'print(\"before\")'", name="before"),
            CommandVerifier("python -c 'raise SystemExit(7)'", name="benchmark"),
            CommandVerifier("python -c 'print(\"after\")'", name="after"),
        ]
    )

    result = chain.verify(claim, VerificationContext(cwd=tmp_path))

    assert result.passed is False
    assert claim.status == "rejected"
    assert [e.name for e in claim.evidence] == ["before", "benchmark"]
    assert claim.evidence[-1].data["exit_code"] == 7
```

- [ ] **Step 4: Write failing workflow bundle tests**

Create `tests/test_workflow.py`:

```python
import json
from pathlib import Path

from vo import AgentSpec, CommandVerifier, VerificationContext, VerifierChain, WorkflowRun


def test_workflow_run_records_agents_claims_evidence_and_bundle(tmp_path: Path):
    run = WorkflowRun(name="parser-speed")
    run.add_agent(AgentSpec(name="optimizer", goal="Improve parser latency"))
    run.resources.acquire("repo:src/parser.py", owner="optimizer")
    claim = run.claim("parser latency improved", metric="latency")

    chain = VerifierChain([CommandVerifier("python -c 'print(\"ok\")'", name="tests")])
    result = run.verify(claim, chain, VerificationContext(cwd=tmp_path))

    bundle_path = run.write_bundle(tmp_path / "run-bundle.json")
    bundle = json.loads(bundle_path.read_text())

    assert result.passed is True
    assert bundle["name"] == "parser-speed"
    assert bundle["agents"][0]["name"] == "optimizer"
    assert bundle["claims"][0]["status"] == "accepted"
    assert bundle["claims"][0]["metadata"] == {"metric": "latency"}
    assert bundle["claims"][0]["evidence"][0]["name"] == "tests"
    assert bundle["resources"]["repo:src/parser.py"]["owner"] == "optimizer"
```

- [ ] **Step 5: Run tests and confirm red**

Run:

```bash
python3 -m pytest -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'vo'`.

---

### Task 2: Core Models and Resource Leases

**Files:**
- Create: `src/vo/__init__.py`
- Create: `src/vo/exceptions.py`
- Create: `src/vo/models.py`
- Create: `src/vo/resources.py`

- [ ] **Step 1: Implement domain exceptions**

Create `src/vo/exceptions.py` with `VoError`, `ResourceConflict`, and `VerificationError`.

- [ ] **Step 2: Implement serializable models**

Create `src/vo/models.py` with:

- `AgentSpec(name, goal, model=None, tools=(), metadata={})`
- `Evidence(name, passed, summary, kind="generic", data={}, created_at=...)`
- `Claim(statement, id=..., status="pending", metadata={}, evidence=[])`
- `VerificationResult(passed, evidence, failed_evidence=None)`
- `WorkflowEvent(type, data, created_at=...)`

Every model exposes `to_dict()` returning JSON-safe primitives.

- [ ] **Step 3: Implement resource leasing**

Create `src/vo/resources.py` with `ResourceLease` and `ResourceManager`. `ResourceManager.acquire(name, owner)` raises `ResourceConflict` when another active owner already holds the resource. Releasing a lease removes it only if the same lease is still active.

- [ ] **Step 4: Export public API**

Create `src/vo/__init__.py` exporting the exceptions, models, and resource manager.

- [ ] **Step 5: Run resource tests**

Run:

```bash
python3 -m pytest tests/test_resources.py -q
```

Expected: pass.

---

### Task 3: Verifier Chains

**Files:**
- Create: `src/vo/verifiers.py`
- Modify: `src/vo/__init__.py`

- [ ] **Step 1: Implement verification context**

Create `VerificationContext(cwd=None, env={}, timeout=None)` in `src/vo/verifiers.py`.

- [ ] **Step 2: Implement command verifier**

Create `CommandVerifier(command, name=None, timeout=None)`. It runs the command with `subprocess.run(..., shell=True, text=True, capture_output=True)` using the context cwd/env, records duration, stdout, stderr, exit code, and passes only on exit code `0`.

- [ ] **Step 3: Implement callable verifier**

Create `CallableVerifier(fn, name=None)`. It calls `fn(context)` or `fn()` and accepts either a bool or an `Evidence` instance.

- [ ] **Step 4: Implement verifier chain**

Create `VerifierChain(verifiers)`. `verify(claim, context)` runs verifiers in order, appends evidence to the claim, marks the claim `accepted` only when all checks pass, and marks it `rejected` when the first check fails.

- [ ] **Step 5: Export verifier API and run verifier tests**

Run:

```bash
python3 -m pytest tests/test_verifiers.py -q
```

Expected: pass.

---

### Task 4: Workflow Run and Bundle Export

**Files:**
- Create: `src/vo/workflow.py`
- Modify: `src/vo/__init__.py`

- [ ] **Step 1: Implement `WorkflowRun`**

Create `WorkflowRun(name)`, with methods:

- `add_agent(agent: AgentSpec) -> AgentSpec`
- `claim(statement: str, **metadata) -> Claim`
- `record_event(type: str, data=None) -> WorkflowEvent`
- `verify(claim: Claim, chain: VerifierChain, context=None) -> VerificationResult`
- `to_dict() -> dict`
- `write_bundle(path) -> Path`

- [ ] **Step 2: Connect workflow verification to event log**

`WorkflowRun.verify()` records `verification_started` and `verification_finished` events with claim id and pass/fail status.

- [ ] **Step 3: Export `WorkflowRun` and run workflow tests**

Run:

```bash
python3 -m pytest tests/test_workflow.py -q
```

Expected: pass.

---

### Task 5: Docs and Example

**Files:**
- Create: `README.md`
- Create: `examples/optimize_with_evidence.py`

- [ ] **Step 1: Write README**

Document the product thesis, current local-first scope, and a short API example that creates a workflow, records an agent, claims a result, verifies it with a command chain, and writes a JSON bundle.

- [ ] **Step 2: Write runnable example**

Create `examples/optimize_with_evidence.py` that imports `vo`, verifies a toy command chain, writes `work/example-run-bundle.json`, and prints the output path.

- [ ] **Step 3: Run full verification**

Run:

```bash
python3 -m pytest -q
python3 examples/optimize_with_evidence.py
```

Expected: all tests pass and the example prints `work/example-run-bundle.json`.

---

## Self-Review

- Spec coverage: The plan implements the first local-first library slice for typed-ish agents, resource ownership, claims, evidence, verifier chains, and reproducible JSON bundles.
- Placeholder scan: The plan contains no open implementation placeholders. Future cloud, UI, live agent execution, and remote VM provisioning are intentionally out of this first slice.
- Type consistency: Tests and implementation tasks use the same public names: `AgentSpec`, `Claim`, `CommandVerifier`, `VerificationContext`, `VerifierChain`, `ResourceManager`, `ResourceConflict`, and `WorkflowRun`.
