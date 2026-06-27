# Local Agent Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local subprocess-backed agent runner so workflows can execute real commands, capture transcripts, and include agent runs in reproducible bundles.

**Architecture:** Introduce a narrow `AgentAdapter` protocol and one concrete `LocalCommandAgent` implementation. The adapter accepts a task string, runs a command with the task on stdin, captures stdout/stderr/exit status/duration, and returns an `AgentRun` model that can also be attached as evidence. `WorkflowRun.run_agent()` will connect registered `AgentSpec` entries to adapters and record run events.

**Tech Stack:** Python 3.11+, stdlib dataclasses, subprocess, pathlib, pytest.

---

## File Structure

- `src/vo/agents.py`: new adapter protocol, `AgentRun` model, and `LocalCommandAgent`.
- `src/vo/workflow.py`: add `agent_runs` storage and `run_agent()`.
- `src/vo/__init__.py`: export agent runner API.
- `tests/test_agents.py`: local command runner behavior.
- `tests/test_workflow_agents.py`: workflow integration and bundle export.
- `README.md`: document the local runner.
- `examples/local_agent_runner.py`: runnable local-agent example.

---

### Task 1: Red Tests for Local Agent Execution

**Files:**
- Create: `tests/test_agents.py`
- Create: `tests/test_workflow_agents.py`

- [ ] **Step 1: Write local runner test**

Create `tests/test_agents.py`:

```python
from pathlib import Path

from vo import LocalCommandAgent, VerificationContext


def test_local_command_agent_passes_task_on_stdin_and_captures_output(tmp_path: Path):
    script = tmp_path / "agent.py"
    script.write_text(
        "import pathlib, sys\n"
        "task = sys.stdin.read()\n"
        "pathlib.Path('artifact.txt').write_text(task.upper())\n"
        "print('wrote artifact')\n",
        encoding="utf-8",
    )

    agent = LocalCommandAgent(["python", str(script)], name="script-agent")
    result = agent.run("hello agent", VerificationContext(cwd=tmp_path))

    evidence = result.to_evidence()

    assert result.passed is True
    assert result.stdout.strip() == "wrote artifact"
    assert (tmp_path / "artifact.txt").read_text(encoding="utf-8") == "HELLO AGENT"
    assert evidence.kind == "agent_run"
    assert evidence.data["exit_code"] == 0
```

- [ ] **Step 2: Write workflow integration test**

Create `tests/test_workflow_agents.py`:

```python
import json
from pathlib import Path

from vo import AgentSpec, LocalCommandAgent, VerificationContext, WorkflowRun


def test_workflow_run_agent_records_run_and_exports_bundle(tmp_path: Path):
    script = tmp_path / "agent.py"
    script.write_text(
        "import sys\n"
        "task = sys.stdin.read().strip()\n"
        "print(f'completed: {task}')\n",
        encoding="utf-8",
    )

    run = WorkflowRun(name="agent-loop")
    run.add_agent(AgentSpec(name="writer", goal="Draft a patch summary"))
    result = run.run_agent(
        "writer",
        LocalCommandAgent(["python", str(script)], name="writer"),
        "summarize patch",
        VerificationContext(cwd=tmp_path),
    )

    bundle_path = run.write_bundle(tmp_path / "bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert result.passed is True
    assert bundle["agent_runs"][0]["agent_name"] == "writer"
    assert bundle["agent_runs"][0]["stdout"].strip() == "completed: summarize patch"
    assert [event["type"] for event in bundle["events"]][-2:] == [
        "agent_run_started",
        "agent_run_finished",
    ]
```

- [ ] **Step 3: Run tests and confirm red**

Run:

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_agents.py tests/test_workflow_agents.py -q
```

Expected: import failure for `LocalCommandAgent`.

---

### Task 2: Agent Adapter and Local Command Runner

**Files:**
- Create: `src/vo/agents.py`
- Modify: `src/vo/__init__.py`

- [ ] **Step 1: Implement `AgentRun`**

Create `AgentRun` with fields `agent_name`, `task`, `command`, `exit_code`, `stdout`, `stderr`, `duration_s`, `started_at`, `finished_at`, and methods `passed`, `to_dict()`, `to_evidence()`.

- [ ] **Step 2: Implement `AgentAdapter` protocol**

Define a protocol with `name: str` and `run(task: str, context: VerificationContext | None = None) -> AgentRun`.

- [ ] **Step 3: Implement `LocalCommandAgent`**

Run commands with `subprocess.run(command, input=task, text=True, capture_output=True, cwd=context.cwd, env=context.merged_env(), timeout=...)`. Use `shell=False` and `list[str]` commands to keep behavior explicit.

- [ ] **Step 4: Export agent runner API**

Export `AgentAdapter`, `AgentRun`, and `LocalCommandAgent` from `src/vo/__init__.py`.

- [ ] **Step 5: Run local runner tests**

Run:

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_agents.py -q
```

Expected: pass.

---

### Task 3: Workflow Integration

**Files:**
- Modify: `src/vo/workflow.py`

- [ ] **Step 1: Store agent runs**

Add `agent_runs: list[AgentRun]` to `WorkflowRun` and include it in `to_dict()`.

- [ ] **Step 2: Implement `run_agent()`**

`run_agent(agent_name, adapter, task, context=None)` should require that `agent_name` is registered in `self.agents`, record `agent_run_started`, execute the adapter, append the result, and record `agent_run_finished` with `passed` and `exit_code`.

- [ ] **Step 3: Run workflow agent tests**

Run:

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest tests/test_workflow_agents.py -q
```

Expected: pass.

---

### Task 4: Docs, Example, and Full Verification

**Files:**
- Modify: `README.md`
- Create: `examples/local_agent_runner.py`

- [ ] **Step 1: Update README**

Add a short section showing `LocalCommandAgent` and `WorkflowRun.run_agent()`.

- [ ] **Step 2: Add runnable example**

Create an example that writes a tiny local script into `work/local-agent-script.py`, runs it with `LocalCommandAgent`, exports `work/local-agent-bundle.json`, and prints the path.

- [ ] **Step 3: Run final verification**

Run:

```bash
UV_PROJECT_ENVIRONMENT=work/.venv uv run --with pytest pytest -q
UV_PROJECT_ENVIRONMENT=work/.venv uv run python examples/local_agent_runner.py
```

Expected: all tests pass and the example prints `work/local-agent-bundle.json`.

---

## Self-Review

- Spec coverage: This plan adds the first real execution adapter while preserving the existing evidence-gated workflow model.
- Placeholder scan: No open implementation placeholders are present. Live LLM adapters and remote VM execution remain out of scope for this slice.
- Type consistency: Tests and tasks consistently use `AgentRun`, `AgentAdapter`, `LocalCommandAgent`, `VerificationContext`, and `WorkflowRun.run_agent()`.
