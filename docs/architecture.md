# Architecture

Limes Quaestio is organized around durable workflow records. The current runtime is
local-first, but every major object is serializable so a distributed backend can
consume the same contract.

## Runtime Layers

1. **Workflow declaration**
   - Agents declare goals with `AgentSpec`.
   - Environments declare placement targets with `EnvironmentSpec`.
   - Task graphs declare dependencies and shared resources with `TaskGraph`.

2. **Control flow**
   - `StateMachine` records deterministic transitions.
   - `IterationLoop` repeats agent execution until verification passes.
   - `ReviewPanel` records approval, rejection, and revision decisions.

3. **Planning and readiness**
   - `ExecutionPlan` turns task graphs into resource-safe waves.
   - `ProvisioningResult` records which environments are ready for a plan.

4. **Execution**
   - `LocalCommandAgent` is the reference local adapter.
   - `PlanExecutionResult` records wave-by-wave and task-by-task execution.

5. **Evidence and inspection**
   - `Claim`, `Evidence`, and `VerifierChain` record what was checked.
   - `ArtifactStore` records produced files with hashes.
   - `MessageLog` records user and agent communication.
   - Bundles and reports make runs reproducible and inspectable.

## Bundle Contract

`WorkflowRun.to_dict()` is the stable export boundary. Bundle validation checks
that every top-level section exists, even when it is empty. This avoids silent
schema drift as providers and UIs are added.

## Provider Boundary

The current provisioner and executor are local reference implementations. Future
Docker, SSH, VM, or hosted providers should implement the same data contracts
instead of changing workflow bundle shape.

## Generated Files

Examples write generated bundles, reports, temporary scripts, and outputs under
`work/`. The directory is ignored by git.
