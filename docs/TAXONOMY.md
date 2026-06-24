# TAXONOMY — the ApprenticeOps operational blueprint

> **The blueprint we test against.** Every test class is grounded in an established
> operations framework, so the benchmark covers *what operators actually do*, not
> an ad-hoc list. Scenarios are then authored from **real `home.hont.ro` data** to
> fill each cell. Pairs with [`scenarios.json`](scenarios.json) (the cases) and
> [`PAPER.md`](PAPER.md) (the method).

## 1. Grounding frameworks (the sources of truth)

| Framework | What it gives us | Cited as |
|---|---|---|
| **Google SRE** (Book 2017 + Workbook 2018) | the canonical operational task areas (monitoring, troubleshooting, incident response, release eng, config, toil, testing, data integrity) | Beyer et al., *Site Reliability Engineering*; Murphy et al., *The SRE Workbook* |
| **DORA core capabilities** (Google Cloud) | the technical delivery/ops **capabilities** (practices) — NOT the Four-Keys *metrics* | dora.dev/capabilities |
| **Observability — three pillars** | the input *signal types* a model reasons over: **metrics, logs, traces** | Sridharan, *Distributed Systems Observability* (O'Reilly) |
| **AIOps maturity ladder** | the **reactive → proactive → predictive → autonomous** arc (our apprentice→operator framing) | Notaro et al., *A Survey of AIOps Methods for Failure Management* (ACM TIST 2021); Gartner AIOps |
| **AIOpsLab** | the agent task verbs **detection / localization / analysis / mitigation** | Chen/Shetty et al., MLSys 2025 (arXiv 2407.12165) |
| **DevSecOps / hardening** | the **secure** class: misconfig, secret hygiene, blast-radius, least-privilege | CIS Kubernetes Benchmark; OWASP; DORA Pervasive Security |
| **ITIL** (classical ITSM) | incident / problem / **change** management vocabulary (upgrade/rollback, change approval) | ITIL 4 |

## 2. The blueprint: 6 operational pillars → test classes

Operations collapse into **six pillars**. Each maps to framework sources, a
position on the maturity ladder, the observability signal it consumes, and our
test class(es).

| # | Pillar | Maturity rung | Framework anchor | Signal in | Our class(es) | aiopslab_task |
|---|---|---|---|---|---|---|
| **P1** | **Observe** — is something wrong? | reactive | SRE *Monitoring* (Ch6) · DORA *Monitoring & observability* · 3 pillars | metrics, logs | `monitor`, `detect` | detection |
| **P2** | **Diagnose** — what & why? | reactive | SRE *Effective Troubleshooting* (Ch12) · AIOpsLab localization+analysis | logs, traces, events | `diagnose`, `test` (signal-vs-fault) | localization, analysis |
| **P3** | **Respond** — fix it, safely | reactive | SRE *Emergency Response* (Ch13), *Managing Incidents* (Ch14) | incident context | `remediate`*, `guard` (safety) | mitigation |
| **P4** | **Change** — deliver/evolve | reactive→proactive | SRE *Release Eng* (Ch8), *Canarying* (Ch16) · DORA *CD*, *Deployment automation*, *DB change mgmt*, *Change approval* · ITIL change | repo/config/changelog | `expand`, `upgrade`, `config`* | mitigation |
| **P5** | **Secure** — protect (DevSecOps) | reactive→proactive | DORA *Pervasive security* · CIS · OWASP | manifests, RBAC, secrets, audit | `secure`* **(GAP)** | analysis/mitigation |
| **P6** | **Foresee** — prevent/predict | **proactive→predictive** | DORA *Proactive failure notification* · SRE *Addressing Cascading Failures* (Ch22) · AIOps predictive | metric trends, capacity | `capacity`*, `predict`* **(GAP)** | (beyond AIOpsLab) |
| **(cross)** | **Toil/Automate** — reduce manual work | all rungs | SRE *Eliminating Toil* (Ch5), *Automation* (Ch7) · DORA *Test automation* | any | `augment` (data shaping) | analysis |

`*` = proposed (see §4). The maturity column shows the paper tests **P1–P5
(reactive + early-proactive)** thoroughly and **opens P6** as the predictive
frontier (honestly scoped as future work, per PAPER.md §1).

## 3. Original coverage seed and current audit

The table below records the original seed coverage. It is historically useful,
but no longer describes the live corpus: `data/scenarios.json` now has 27
scenarios, including `secure`, `capacity`, and Sideport high-CPU cases. See
[`SCENARIO_AUDIT_2026-06-24.md`](SCENARIO_AUDIT_2026-06-24.md) for the current
inventory, homelab-fidelity audit, and compact-roster recommendation.

| Pillar | Class | Scenarios now | Grounding | Real-data source |
|---|---|---|---|---|
| P1 | `detect` | 1 | closed-book | `kube_crashloop_pods` |
| P1 | `monitor` | 1 | closed-book | pod logs |
| P2 | `diagnose` | 1 | closed-book | `kube_events` (ESO) |
| P2 | `test` | 1 | closed-book | readiness-probe event |
| P3 | `guard` | 1 | closed-book | destructive command |
| P4 | `expand` | 1 | grounded | repo conventions |
| P4 | `upgrade` | 1 | grounded | Helm changelog |
| Toil | `augment` | 1 | closed-book | raw events → JSON |

**Original coverage verdict:** P1–P4 + toil were seeded (1 each); at that point
**P5 Secure and P6 Foresee were absent**. That gap has since been addressed in
the live JSON corpus. The current remaining gaps are different: backup/restore,
network/DNS partition, Flux drift, Authentik/OIDC failures, and resource-pressure
scenarios.

## 4. Gaps to fill (the authoring backlog, from real homelab data)

The highest-priority next additions from the 2026-06-24 audit are backup restore
verification and network/DNS partition scenarios. Prefer replacing lower-priority
extended cases over growing the default set indefinitely.

Target **≥6 scenarios/class**. New classes + concrete cases grounded in data this
cluster actually emits:

### P5 — `secure` (DevSecOps) — **NEW, highest priority**
Real signals available: SOPS/ESO secrets, Traefik ingress, NetworkPolicies,
Kyverno policies, RBAC, cert-manager, image tags.
- A Secret committed in plaintext to a manifest → spot it, prescribe SOPS/ESO.
- An ingress exposing an admin panel with no auth middleware → flag + fix.
- A container running as root / `privileged: true` → CIS finding + remediation.
- An over-broad RBAC `ClusterRole` (`*` verbs) → least-privilege rewrite.
- An expired/expiring cert-manager `Certificate` → renew path.
- A NetworkPolicy gap letting a namespace reach the registry → restrict.
- `:latest` image tag in a Deployment → pin + why (supply-chain).

### P6 — `capacity` / `predict` (proactive) — **NEW**
Real signals: netdata metrics, `host_disk`, `host_smart`, `kube_pvc_usage`,
`media_disk_pressure`.
- Disk at 75% + growth rate → *when* will it fill; act before it does.
- A PVC at 90% → expand vs prune decision.
- SMART pre-fail attributes trending → replace-before-failure call.
- RAM/swap trend under load → capacity headroom verdict.
- Cert expiring in 10 days → renew-ahead (preventive, not reactive).

### P4 — `config` (config validation) — **NEW (or fold into upgrade)**
- A malformed `HelmRelease`/Kustomization YAML → find the error.
- A `values.yaml` change that breaks a dependency → catch pre-apply.

### Deepen existing P1–P4 + toil to ≥6 each
Plenty of real material: OOMKilled events, image-pull-backoff, Flux
reconciliation failures, Traefik 5xx, NFS mount drops, qbt/arr pipeline stalls,
Plex transcode errors, DNS resolution failures, etc.

## 5. Why this blueprint strengthens the paper

- **Construct validity:** classes are no longer ad-hoc — each cites SRE/DORA/
  observability/DevSecOps, so a reviewer can't say "why these tasks?"
- **Completeness:** the pillar model *reveals* the security + predictive gaps a
  flat list hid. Filling them makes the bench representative of real ops.
- **The maturity ladder reads cleanly:** P1–P3 = reactive (apprentice), P4–P5 =
  proactive (journeyman), P6 = predictive (the frontier we open, not close).
- **Breadth answer (your Q "are the task types broad enough?"): not yet** — with
  P5/P6 added it spans **observe → diagnose → respond → change → secure → foresee**,
  which *is* the full operational surface an agent+model would touch in a data
  centre. That's the breadth target.

## 6. Next action

Author the §4 backlog as real-data scenarios (operator reviews the gold answers
per the option-C de-bias flow), add `secure`/`capacity`/`config` to
`scenarios.json` with `grounding` labels, and the per-taxonomy report
([`report.py`](report.py)) will automatically score every new class.

## 7. Connection to DORA (capabilities, NOT the Four-Keys metrics)

DORA has two distinct halves; we connect to one and explicitly NOT the other:

- **DORA *metrics* (Four Keys):** Deployment Frequency, Lead Time for Changes,
  Change Failure Rate, Failed-Deployment Recovery Time — **team-velocity
  OUTCOMES.** ApprenticeOps does **not** measure these (would need a closed-loop
  deployment study).
- **DORA *capabilities* (~30 practices):** the **predictors** DORA research shows
  drive those outcomes. **Our test classes map to these.**

**Class → capability map:** `monitor`/`detect` → *Monitoring & observability*;
`capacity`/`foresee` → *Proactive failure notification*; `expand`/`upgrade` →
*Continuous delivery*, *Deployment automation*, *Database change management*,
*Streamlining change approval*; `secure` → *Pervasive security* (DevSecOps);
`augment` → *Test automation / toil reduction*.

**Causal chain (the "so what"):** `small local model → assists a DORA capability
→ (hypothesis) improves a DORA metric`. We measure the **left arrow** (can the
model do the capability-task — reason, ground, calibrate, stay safe). The right
arrow (does it move CFR/recovery-time) is **scoped as future closed-loop work**;
claiming it now would be overreach.

**DORA validates the offline+RAG design.** DORA's 2024 **AI capabilities**
directly motivate our framing: *AI-accessible internal data* ("connecting AI to
your internal documentation/codebases moves it from a generic assistant to a
specialized expert") = our **`grounded` / local-RAG** condition; *Healthy data
ecosystems* = why we use **real cluster telemetry**; *Platform engineering* = the
OpenClaw+MCP layer. Our **closed-book vs grounded** experiment *measures the lift
DORA asserts* — and specifically how much it's worth for a **small** model.
