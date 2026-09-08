"""Run a bounded arithmetic investigation and retain every branch and output."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from quaestio import AgentSpec, LocalCommandAgent, ResearchStore, VerificationContext, WorkflowRun
from quaestio.research_view import render_html

EXPERIMENT = """import json, math
from decimal import Decimal
values = [1e16, 1.0, -1e16]
expected = int(sum(Decimal.from_float(x) for x in values))
naive = 0.0
for value in values:
    naive += value
print(json.dumps({"values": values, "exact": expected,
                  "naive": naive, "builtin_sum": sum(values), "fsum": math.fsum(values)}))
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    script = args.out / "experiment.py"
    script.write_text(EXPERIMENT, encoding="utf-8")
    run = WorkflowRun(name="cancellation-two-process-observation")
    run.add_agent(AgentSpec(name="measurement", goal="Measure one cancellation fixture"))
    runner = LocalCommandAgent([sys.executable, str(script.resolve())], name="measurement", timeout=10)
    observations = []
    for _ in range(2):
        result = run.run_agent("measurement", runner, "Run the fixed arithmetic fixture",
                               VerificationContext(cwd=args.out.resolve()))
        if not result.passed:
            raise RuntimeError(f"measurement failed: {result.stderr}")
        observations.append(json.loads(result.stdout))
    if observations[0] != observations[1]:
        raise RuntimeError("independent experiment processes disagreed")
    observation = observations[0]
    if observation["naive"] != 0 or observation["fsum"] != observation["exact"]:
        raise RuntimeError("cancellation fixture differs from the documented result")
    evidence = json.dumps({"interpreter": sys.version, "observations": observations},
                          indent=2).encode()
    (args.out / "observations.json").write_bytes(evidence)
    with ResearchStore.create(args.out / "study.sqlite", title="Summation under cancellation") as store:
        def node(kind: str, title: str, content: str, parents: list[str], operation: str) -> str:
            return store.create_node(kind=kind, title=title, content=content,
                                     parents=parents, actor="research-example",
                                     operation_id=operation)["id"]

        root = node("question", "Can floating-point summation lose a small term?",
                    "Compare [1e16, 1.0, -1e16] with an exact Decimal reference. "
                    "This investigation covers one fixture, not all inputs.", [], "question")
        naive = node("experiment", "Baseline: sequential addition", "Measure left-to-right floating-point addition.", [root], "baseline")
        precise = node("experiment", "Alternative: math.fsum", "Measure math.fsum(values).", [root], "alternative")
        store.revise_node(naive, expected_revision=1, content="Observed 0.0; exact reference is 1. "
                          "The candidate fails on this fixture.", status="failed",
                          actor="research-example", operation_id="baseline-result")
        store.revise_node(precise, expected_revision=1, content="Observed 1.0, equal to the exact reference "
                          "for this fixture.", status="completed", actor="research-example",
                          operation_id="alternative-result")
        reproduced = node("result", "Independent process reproduction", "A second Python process produced "
                          "the same measurements. No broader accuracy claim is made.", [precise], "reproduction")
        decision = node("decision", "Keep fsum for this cancellation case", "The baseline failure and alternative "
                        "remain visible. Broader numerical properties need additional experiments.",
                        [naive, reproduced], "decision")
        for node_id in [naive, precise, reproduced]:
            store.attach_artifact(node_id, data=evidence, label="Two process measurements",
                                  actor="research-example", operation_id="observations-" + node_id)
        store.attach_artifact(root, data=EXPERIMENT.encode(), label="Executed Python source",
                              actor="research-example", operation_id="source")
        bundle = run.write_bundle(args.out / "run-bundle.json")
        store.record_execution(reproduced, bundle=json.loads(bundle.read_text()),
                               actor="research-example", operation_id="reported-run")
        store.revise_node(decision, expected_revision=1, content=store.get_node(decision)["content"],
                          status="completed", actor="research-example", operation_id="decision-complete")
        (args.out / "graph.html").write_text(render_html(store.snapshot()), encoding="utf-8")
    print(json.dumps({"database": str(args.out / "study.sqlite"), "decision": decision,
                      "exact": observation["exact"], "naive": observation["naive"],
                      "fsum": observation["fsum"], "processes": 2}))


if __name__ == "__main__":
    main()
