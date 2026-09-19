# Scenario Lifecycle Schema

Status: v1 draft, created 2026-07-03. This schema is for future ApprenticeOps /
CEOps candidate packs. It is **not** retroactive paper scoring, not a Core
promotion, and not a requirement for the locked 94-model result.

## Purpose

The external-source review showed that stronger ops benchmarks make the
operational lifecycle explicit: the object under evaluation, the task, the fault,
the evidence channels, the action surface, and the evaluator. Current scenarios
often encode those facts in prose. Future candidate packs should encode them in a
small `lifecycle` object that validates against
`data/scenario-lifecycle.schema.json`.

## Contract

The lifecycle object has these required fields:

| Field | Meaning |
|---|---|
| `schema_version` | Schema version. Current value is `1`. |
| `operational_object` | The service, component, network, database, security control, agent, or evaluation harness being tested. |
| `task_lifecycle` | One or more lifecycle verbs such as `detect`, `localize`, `diagnose`, `mitigate`, or `verify`. |
| `fault_model` | The fault class and manifestation: dependency failure, regression, capacity issue, security issue, agent failure, and so on. |
| `workload_evidence` | Evidence channels and source quality: logs, metrics, traces, events, config, user impact, test output, deployment metadata, or synthetic summary. |
| `action_surface` | What kind of action is allowed: prose-only, JSON tool plan, read-only tools, GitOps plan, kubectl plan, or live mutation. |
| `evaluator_shape` | Whether deterministic checks, judge rubric, runtime validator, human review, and adversarial fixtures exist. |
| `promotion_status` | `candidate`, `dev`, `locked-core`, or `retired`. |
| `source_trace` | Source-use and row-rights status. |

## Example

```json
{
  "schema_version": 1,
  "operational_object": {
    "kind": "service",
    "name": "checkout api",
    "boundary": "api-gateway -> payment-provider"
  },
  "task_lifecycle": ["detect", "mitigate", "verify"],
  "fault_model": {
    "category": "dependency",
    "manifestation": "upstream payment timeout"
  },
  "workload_evidence": {
    "channels": ["logs", "metrics", "user-impact", "synthetic-summary"],
    "source_quality": "pattern-only",
    "window": {
      "baseline": "7 days",
      "current": "30 minutes"
    }
  },
  "action_surface": {
    "mode": "prose-only",
    "destructive_risk": "low",
    "permitted_actions": ["degrade checkout", "check provider status"],
    "forbidden_actions": ["restart unrelated workers"]
  },
  "evaluator_shape": {
    "deterministic_checks": true,
    "judge_rubric": true,
    "adversarial_fixtures": true
  },
  "promotion_status": "candidate",
  "source_trace": {
    "use": "pattern-family",
    "row_status": "none",
    "source_families": ["AIOps log anomaly datasets"],
    "rights_gate": "pattern-only; no row text copied"
  }
}
```

## Adoption Rule

Do not mutate `external-candidates-v0` to add this field. That file already has
run artifacts and should remain reproducible. Add `lifecycle` first to a future
candidate-v1 pack or to new scenario proposals, then validate the schema before a
dev run.

## Promotion Discipline

Lifecycle metadata is **necessary-not-sufficient**. A scenario still needs the
existing gates: gold deterministic checks, negative controls, adversarial
fixtures, rights/contamination review, dev-run quality reporting, and a written
scenario-level review before any promotion decision.