# VO Agent

VO Agent is a Python library for evidence-gated agent workflows.

The long-term goal is a language and runtime for coordinating coding agents
across machines: agents propose work, execute it in isolated environments, and
can only advance by producing verifiable evidence.

This first slice is intentionally local-first. It gives us the clean core
objects before cloud provisioning, hosted dashboards, live LLM adapters, or VM
backends:

- `AgentSpec`: declares who is working and what goal they own
- `EnvironmentSpec`: declares where agents should run
- `ResourceManager`: prevents silent conflicts on shared resources
- `Claim`: records what an agent says is true
- `Evidence`: records what was actually checked
- `VerifierChain`: gates claims through command or Python checks
- `Budget`: records bounded spend for long-running agent loops
- `StateMachine`: declares deterministic workflow control flow
- `IterationLoop`: repeats agent execution until verification passes
- `ReviewPanel`: coordinates reviewer agents around a claim
- `TaskGraph`: declares dependency and resource shape for agent work
- `ExecutionPlan`: turns task graphs into placement-aware execution waves
- `LocalProvisioner`: records local readiness for planned environments
- `MessageLog`: records durable user and agent messages
- `WorkflowRun`: exports a reproducible JSON bundle for inspection

## Example

```python
from pathlib import Path

from vo import (
    AgentSpec,
    Budget,
    CommandVerifier,
    VerificationContext,
    VerifierChain,
    WorkflowRun,
)

run = WorkflowRun(name="parser-speed", budget=Budget(limit=1.0, unit="usd"))
run.add_agent(AgentSpec(name="optimizer", goal="Improve parser latency"))
run.resources.acquire("repo:src/parser.py", owner="optimizer")
run.spend_budget(0.20, label="optimizer proposal")

claim = run.claim("parser latency improved", metric="latency")
chain = VerifierChain(
    [
        CommandVerifier("python -c 'print(\"tests ok\")'", name="tests"),
        CommandVerifier("python -c 'print(\"median_ms=12.3\")'", name="benchmark"),
    ]
)

result = run.verify(claim, chain, VerificationContext(cwd=Path.cwd()))
bundle = run.write_bundle("work/example-run-bundle.json")
report = run.write_report("work/example-run-report.md")

print(result.passed)
print(bundle)
print(report)
```

Run it:

```bash
python3 examples/optimize_with_evidence.py
```

Validate or inspect the generated bundle:

```bash
vo validate work/example-run-bundle.json
vo inspect work/example-run-bundle.json
```

## Current Scope

VO Agent does not yet launch live coding agents or provision VMs. The first
library boundary is the reproducible protocol around the agents: explicit
environments, explicit resources, explicit state machines, explicit claims,
explicit evidence, and exported run state. Cloud execution and LLM adapters can
be layered on top without changing this core contract.

## Execution Environments

Environment specs describe placement targets before any cloud provisioner
exists. A workflow can record local execution, a container image, or a future VM
request with resource requirements, setup commands, non-secret environment
variables, and secret names:

```python
from vo import AgentSpec, ComputeResources, EnvironmentSpec, WorkflowRun

run = WorkflowRun(name="placement-demo")
run.add_agent(AgentSpec(name="solver", goal="Solve the hard case"))
run.add_environment(
    EnvironmentSpec(
        name="gpu-worker",
        kind="vm",
        image="ubuntu:24.04",
        resources=ComputeResources(cpu=8, memory_gb=32, gpu_count=1),
        setup_commands=("uv sync --extra gpu",),
        secret_names=("OPENAI_API_KEY",),
    )
)
run.assign_agent_environment("solver", "gpu-worker")
```

Agent runs include their assigned environment in metadata, and bundles expose
both the environment declarations and the agent placement map. Secret values are
not serialized.

Run the environment example:

```bash
python3 examples/environment_assignment.py
vo inspect work/environment-assignment-bundle.json
```

## Execution Plans

Execution plans are the handoff between workflow language and provisioning.
They turn a task graph plus agent placements into deterministic waves:

```python
from vo import AgentSpec, ComputeResources, EnvironmentSpec, TaskGraph, TaskSpec, WorkflowRun

run = WorkflowRun(name="planning-demo")
run.add_agent(AgentSpec(name="searcher", goal="Find candidates"))
run.add_agent(AgentSpec(name="checker", goal="Verify candidates"))
run.add_environment(
    EnvironmentSpec(
        name="cpu-worker",
        resources=ComputeResources(cpu=4, memory_gb=8),
    )
)
run.assign_agent_environment("searcher", "cpu-worker")
run.assign_agent_environment("checker", "cpu-worker")

graph = TaskGraph(name="research-plan")
graph.add_task(TaskSpec(name="search", agent_name="searcher", task="search"))
graph.add_task(
    TaskSpec(
        name="verify",
        agent_name="checker",
        task="verify",
        depends_on=("search",),
    )
)

run.add_task_graph(graph)
plan = run.plan_task_graph(graph)
```

Each wave contains tasks that can run together without sharing declared
resources. Every task in the plan has an assigned environment. Missing or
unknown placements fail during planning, before any agent starts.

Run the execution-plan example:

```bash
python3 examples/execution_plan.py
vo inspect work/execution-plan-bundle.json
```

## Provisioning Records

Provisioners prepare the environments required by an execution plan and return a
durable readiness record. The current built-in provisioner is local and
no-op: it validates that the plan references declared environments and records
them as ready.

```python
from vo import LocalProvisioner

plan = run.plan_task_graph(graph)
result = run.provision_execution_plan(
    plan,
    LocalProvisioner(metadata={"mode": "dry-run"}),
)

assert result.status == "ready"
```

Future Docker, SSH, and VM provisioners can implement the same small interface
without changing workflow bundles.

Run the provisioning example:

```bash
python3 examples/provisioning.py
vo inspect work/provisioning-bundle.json
```

## Plan Execution

The reference executor runs a provisioned execution plan locally through agent
adapters and records wave-by-wave results:

```python
from vo import LocalCommandAgent, VerificationContext

result = run.execute_execution_plan(
    plan,
    {
        "solver": LocalCommandAgent(["python", "agent.py"], name="solver"),
    },
    VerificationContext(cwd="work"),
)

assert result.status == "passed"
```

Execution requires a ready provisioning result by default. If a task in a wave
fails, later waves are not run, and the partial result is still exported in the
bundle.

Run the plan-execution example:

```bash
python3 examples/plan_execution.py
vo inspect work/plan-execution-bundle.json
```

## Messages

Messages record the conversations that steer a run. They are serialized into
the bundle alongside events, agent runs, claims, and artifacts:

```python
from vo import AgentSpec, WorkflowRun

run = WorkflowRun(name="message-demo")
run.add_agent(AgentSpec(name="solver", goal="Solve the problem"))

run.send_message(
    "user",
    "Please try the geometry case.",
    recipient="solver",
    thread="geometry",
)
run.send_message(
    "solver",
    "I found a boundary case to check.",
    recipient="user",
    role="agent",
    thread="geometry",
)

assert len(run.messages_for("solver")) == 1
```

Run the messaging example:

```bash
python3 examples/messaging.py
vo inspect work/messaging-bundle.json
```

## State Machines

State machines describe the control flow of an agent process:

```python
from vo import StateMachine, WorkflowRun

run = WorkflowRun(name="verification-loop")
machine = StateMachine(
    name="research-loop",
    initial_state="drafting",
    data={"attempts": 0},
)

machine.on("drafting", "candidate_ready", "verifying")
machine.on(
    "verifying",
    "verification_finished",
    "accepted",
    guard=lambda context: context.event.data["passed"] is True,
)
machine.on(
    "verifying",
    "verification_finished",
    "drafting",
    guard=lambda context: context.event.data["passed"] is False,
    handler=lambda context: {"attempts": context.data["attempts"] + 1},
)

run.add_state_machine(machine)
run.dispatch("research-loop", "candidate_ready")
run.dispatch("research-loop", "verification_finished", {"passed": False})
```

Dispatch records are serialized into the run bundle. Guard and handler failures
are captured as failed dispatch records without advancing the machine state.

Run the state-machine example:

```bash
python3 examples/state_machine_workflow.py
vo inspect work/state-machine-bundle.json
```

## Verification-Driven Iteration

Iteration loops force an agent to keep trying until a verifier passes or an
explicit attempt limit is reached:

```python
from vo import (
    CommandVerifier,
    IterationLoop,
    IterationPolicy,
    LocalCommandAgent,
    VerifierChain,
    WorkflowRun,
)

run = WorkflowRun(name="hard-test-loop")
loop = IterationLoop(
    name="solver-loop",
    agent_name="solver",
    task="Make the tests pass.",
    policy=IterationPolicy(max_attempts=3, budget_per_attempt=0.25),
)

run.add_iteration_loop(loop)
run.iterate_until_verified(
    loop,
    LocalCommandAgent(["python", "agent.py"], name="solver"),
    VerifierChain([CommandVerifier("python -m pytest", name="tests")]),
)
```

Each successful agent execution creates a claim and verifies it. Failed agent
runs are recorded as attempts without creating verification claims. The loop
stops as soon as verification passes, or records `max_attempts` as the stop
reason.

Run the iteration example:

```bash
python3 examples/iteration_loop.py
vo inspect work/iteration-loop-bundle.json
```

## Multi-Agent Review Panels

Review panels let reviewer agents check or challenge a claim before it
advances. Reviewer agents use a small line-oriented protocol:

```text
decision: approve
comment: proof handles the stated invariant
```

Valid decisions are `approve`, `reject`, and `revise`.

```python
from vo import LocalCommandAgent, ReviewPanel, ReviewPolicy, WorkflowRun

run = WorkflowRun(name="review-demo")
claim = run.claim("candidate proof is ready")
panel = ReviewPanel(
    name="proof-review",
    reviewer_names=("critic", "checker"),
    policy=ReviewPolicy(min_approvals=2),
)

run.add_review_panel(panel)
run.run_review_panel(
    panel,
    claim,
    {
        "critic": LocalCommandAgent(["python", "critic.py"], name="critic"),
        "checker": LocalCommandAgent(["python", "checker.py"], name="checker"),
    },
)
```

Approved panels accept the claim. Hard rejects reject it. Reviewer crashes or
invalid reviewer output fail the panel and leave the claim pending.

Run the review-panel example:

```bash
python3 examples/review_panel.py
vo inspect work/review-panel-bundle.json
```

## Dependency Graphs

Task graphs make dependencies explicit so work can be grouped into safe
parallel waves. Each task names its agent, task text, dependencies, and optional
resources:

```python
from vo import TaskGraph, TaskSpec, WorkflowRun

graph = TaskGraph(name="research-plan")
graph.add_task(TaskSpec(name="search", agent_name="solver", task="Find candidates."))
graph.add_task(
    TaskSpec(
        name="verify",
        agent_name="checker",
        task="Verify candidates.",
        depends_on=("search",),
        resources=("repo:proofs",),
    )
)

run = WorkflowRun(name="graph-demo")
run.add_task_graph(graph)
run.run_task_graph(graph, {"solver": solver_agent, "checker": checker_agent})
```

`ready_batches()` returns the tasks that can run together without sharing
declared resources. The local runtime executes sequentially, while preserving
that safe scheduling shape in the bundle for cloud execution.

Run the task-graph example:

```bash
python3 examples/task_graph_workflow.py
vo inspect work/task-graph-bundle.json
```

## Local Agent Runner

The first execution adapter is `LocalCommandAgent`. It runs a local command,
sends the task on stdin, captures stdout/stderr/exit status, and stores the
result in the workflow bundle.

```python
from pathlib import Path

from vo import AgentSpec, LocalCommandAgent, VerificationContext, WorkflowRun

run = WorkflowRun(name="local-agent-demo")
run.add_agent(AgentSpec(name="writer", goal="Summarize a patch"))

result = run.run_agent(
    "writer",
    LocalCommandAgent(["python", "work/local-agent-script.py"], name="writer"),
    "Summarize the parser changes.",
    VerificationContext(cwd=Path.cwd()),
)

print(result.stdout)
run.write_bundle("work/local-agent-bundle.json")
```

This is intentionally not a model adapter yet. It is the stable execution
boundary that future Codex, Claude Code, SSH, Docker, and VM-backed adapters
can implement.

## Artifact Provenance

Register files that matter to the run so bundles contain hashes and metadata:

```python
artifact = run.artifacts.register(
    "work/local-agent-output.txt",
    kind="summary",
    metadata={"agent": "writer"},
)

print(artifact.sha256)
```

Artifacts are recorded, not copied. This keeps the core small while preserving
the information needed to audit which files a run produced.

## Run Provenance

Bundles include local runtime provenance: cwd, argv, Python version, platform,
and best-effort git state. Environment capture is explicit to avoid leaking
secrets:

```python
from vo import WorkflowRun, collect_provenance

run = WorkflowRun(
    name="audited-run",
    provenance=collect_provenance(
        argv=["vo", "run"],
        env_keys=["VO_EXAMPLE_RUN"],
    ),
)
```

If the working directory is not inside a git repository, `git` is recorded as
`null`.

## Bundle Reports

Bundles are durable JSON records. Reports are generated from those bundles for
humans:

```python
from vo import load_bundle, render_markdown_report

bundle = load_bundle("work/example-run-bundle.json")
print(render_markdown_report(bundle))
```

The report summarizes agents, environments, execution plans, provisioning
results, plan execution results, messages, agent runs, claims, artifacts,
budget, and local runtime provenance.

## Repository

Public repository: https://github.com/metaforismo/vo-agent

## License

VO Agent is licensed under Apache-2.0. See [LICENSE](LICENSE).
