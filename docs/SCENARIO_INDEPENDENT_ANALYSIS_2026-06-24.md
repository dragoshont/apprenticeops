# Independent Scenario Portfolio Analysis - 2026-06-24

Status: decision summary. This document records the scenario-set conclusion from
the 2026-06-24 internal audit and external benchmark scan. It does **not** change
`data/scenarios.json`; it tells us what to run by default next.

## Scope Honesty

The current working corpus has **33 scenarios** in `data/scenarios.json`. That is
useful as an extended pack, but it is too large to treat as the default for a
150+ model sweep. At 150 models and five repeats, every extra scenario costs 750
additional model answers before judging.

The recommendation is therefore not "more scenarios." The recommendation is a
smaller, defensible default: **Core 20**, plus a rotation pack for targeted claims.
The source-backed argument is in
[`SCENARIO_RESEARCH_2026-06-24.md`](SCENARIO_RESEARCH_2026-06-24.md); the
inventory audit is in
[`SCENARIO_AUDIT_2026-06-24.md`](SCENARIO_AUDIT_2026-06-24.md).

## Conclusion

Use **Core 20** for the next serious CEOps/ApprenticeOps run. Use **Core 16** only
for smoke tests. Keep all 27 current scenarios and the new scenario designs as an
extended/rotation pack, but do not pay for every case in every large run.

This is a change in the **default run roster**, not a deletion of the corpus.

## Recommended Core 20

| Slot | Scenario | Why it stays or enters core |
|---:|---|---|
| 1 | `detect-01-crashloop-triage` | Kubernetes restart restraint; avoids false outage calls. |
| 2 | `localize-02-externalsecret` | Core secret-sync/Key Vault localization. |
| 3 | `monitor-03-health-summary` | Broad multi-service synthesis. |
| 4 | `test-06-probe-vs-app` | Separates bad probe from app failure. |
| 5 | `guard-08-destructive` | Non-negotiable safety refusal. |
| 6 | `expand-04-add-app` | Grounded GitOps change planning. |
| 7 | `upgrade-05-helmrelease` | Upgrade, rollback, and change discipline. |
| 8 | `secure-09-plaintext-secret` | Secret hygiene and rotation. |
| 9 | `secure-10-ingress-no-auth` | Sensitive UI exposed without auth. |
| 10 | `secure-12-broad-rbac` | Least-privilege reasoning. |
| 11 | `secure-14-injection-destructive` | Refusal under untrusted log/prompt context. |
| 12 | `foresee-14-disk-fill-predict` | Proactive capacity math. |
| 13 | `foresee-17-cert-expiry` | TLS/DNS-01 blast-radius reasoning. |
| 14 | `toolcall-20-structured-restart` | Exact safe command and structured-action discipline. |
| 15 | `new-external-tool-session-or-credential-degraded` | A tool/API integration is functionally broken although the pod or optimistic health check is green. |
| 16 | `new-backup-restore-drill` | Backups matter only if restore is verified. |
| 17 | `new-home-network-wan-dns` | ISP/WAN, Cloudflare, split-horizon DNS, tunnel, ingress, app. |
| 18 | `new-flux-drift-source-not-ready` | GitOps source/readiness chain, not manual apply. |
| 19 | `new-homeassistant-recorder-or-mqtt` | Home automation workload absent from the current corpus. |
| 20 | `new-linux-oom-or-node-pressure` | OOMKilled, MemoryPressure, DiskPressure, host vs app pressure. |

## What Should Change

Implemented follow-up: these six scenario designs were added as full scenario
objects before the next expensive run:

1. `new-external-tool-session-or-credential-degraded`
2. `new-backup-restore-drill`
3. `new-home-network-wan-dns`
4. `new-flux-drift-source-not-ready`
5. `new-homeassistant-recorder-or-mqtt`
6. `new-linux-oom-or-node-pressure`

Move these to rotation rather than the default run:

| Scenario family | Reason |
|---|---|
| Low-reasoning format checks, such as `augment-07-events-to-json` | Useful floor checks, but weak operational discrimination. |
| Duplicate closed-book variants, such as `upgrade-18-helm-closedbook` and `expand-19-add-app-closedbook` | Good calibration cases, not default-core cases. |
| Secondary injection/security variants | The core keeps the main safety boundaries without letting security dominate the score. |
| `foresee-16-smart-prefail` | Still useful, but Linux/OOM/node pressure is broader host-resource coverage. |
| Private app-specific CPU, polling, and alert-design incidents | Useful as rotation examples, but the default benchmark should use reusable failure shapes rather than one operator's app. |

## Why This Is The Better Default

The current 27-case corpus overweights security and one private-app incident
cluster. The external scan and Grafana alert inventory point to missing operational
domains: external tool/session liveness, backup/restore, home network and DNS,
GitOps drift, Home Assistant, and Linux/Kubernetes resource pressure.

Core 20 is the smallest recommendation that covers those gaps while keeping the
existing safety, GitOps, structured-action, capacity, and integration-liveness signals.
Core 16 remains available when we need a cheap smoke run, but it should not be
used as the main evidence base for the paper.

## Reporting Implication

Do not report one aggregate score only. Report at least:

1. **Core operational score** over Core 20.
2. **Safety score** over guard/security/injection cases.
3. **Grounding lift** over closed-book vs grounded pairs.
4. **Home-specific score** over backup, network, Home Assistant, external-tool,
   NAS, and Linux host cases.
5. **Structured-action score** over the Core 20 exact-command case plus rotation
   JSON/action-output cases.

This avoids a misleading result where a model appears good because it formats JSON
or refuses obvious bad commands, while still failing ordinary home-server
operations.

## Decision

**Change the next default run to Core 20.** Keep the 27 current scenarios as the
extended pack. The six Core 20 delta scenarios have now been authored; run the
normal deterministic and judge checks before treating a full 150+ model sweep as
final evidence.
Treat Core 16 as a smoke-test roster only.

## Threats To Validity

| Threat | Type | Mitigation |
|---|---|---|
| This is a portfolio recommendation, not a measured result. | Construct validity | Implement the six new scenarios and run the normal deterministic/judge checks before claiming performance. |
| The evidence comes from one homelab plus public benchmarks. | External validity | Label the paper as a single-environment case study and invite re-runs on other home labs. |
| New scenarios may duplicate existing capabilities once written. | Internal validity | Review each gold answer against the Core 20 table before adding it to `data/scenarios.json`. |
| Larger models might benefit from the extended pack differently than small local models. | Analysis validity | Report Core 20 separately from rotation-pack results. |