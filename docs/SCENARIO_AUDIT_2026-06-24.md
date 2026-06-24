# ApprenticeOps Scenario Audit - 2026-06-24

Status: audit and recommendation, not a scenario rewrite.

Follow-up: [`SCENARIO_RESEARCH_2026-06-24.md`](SCENARIO_RESEARCH_2026-06-24.md)
adds an external benchmark/framework scan and supersedes this document's 18-case
default with a research-backed **Core 20** recommendation. For the short decision
summary, see
[`SCENARIO_INDEPENDENT_ANALYSIS_2026-06-24.md`](SCENARIO_INDEPENDENT_ANALYSIS_2026-06-24.md).

## Scope Honesty

The source of truth is `data/scenarios.json`, not the older prose in `README.md`
or `docs/TAXONOMY.md`. As of this audit, the corpus has **27 scenarios**, not the
older 19-scenario description. This document evaluates whether those 27 cases are
useful for a home homelab server with Kubernetes, Flux/GitOps, Traefik, Authentik,
External Secrets/Azure Key Vault, media services, Sideport/iPhone operations,
observability, storage, and physical-node constraints.

The goal is not to maximize count. The better target is a **compact but broad**
set that exposes model capability: detection, localization, RCA, safe mitigation,
security judgment, capacity forecasting, structured output, and calibration.

## Current Inventory

| # | Scenario | Class | Difficulty | Grounding | Primary capability | Audit tier |
|---:|---|---|---|---|---|---|
| 1 | `detect-01-crashloop-triage` | detect | medium | closed-book | cumulative-vs-active restart triage | Core |
| 2 | `localize-02-externalsecret` | diagnose | medium | closed-book | localize ESO/Key Vault missing secret | Core |
| 3 | `monitor-03-health-summary` | monitor | medium | closed-book | multi-app health summary from logs | Core |
| 4 | `expand-04-add-app` | expand | medium | grounded | GitOps app onboarding plan | Core |
| 5 | `upgrade-05-helmrelease` | upgrade | hard | grounded | safe Helm upgrade with rollback | Core |
| 6 | `test-06-probe-vs-app` | test | medium | closed-book | distinguish app failure from bad probe | Core |
| 7 | `augment-07-events-to-json` | augment | easy | closed-book | strict JSON extraction | Extended |
| 8 | `guard-08-destructive` | guard | medium | closed-book | refuse catastrophic command | Core |
| 9 | `secure-09-plaintext-secret` | secure | easy | closed-book | plaintext secret in Git | Core |
| 10 | `secure-10-ingress-no-auth` | secure | easy | closed-book | unauthenticated sensitive ingress | Core |
| 11 | `secure-11-privileged-container` | secure | easy | closed-book | container hardening baseline | Extended |
| 12 | `secure-12-broad-rbac` | secure | medium | closed-book | least-privilege RBAC | Core |
| 13 | `secure-13-latest-tag` | secure | easy | closed-book | image pinning / supply-chain reproducibility | Extended |
| 14 | `foresee-14-disk-fill-predict` | capacity | medium | closed-book | disk growth forecasting | Core |
| 15 | `foresee-15-pvc-pressure` | capacity | hard | closed-book | PVC pressure with storage constraints | Core |
| 16 | `foresee-16-smart-prefail` | capacity | medium | closed-book | SMART trend over surface PASS | Core |
| 17 | `foresee-17-cert-expiry` | capacity | hard | closed-book | DNS-01/cert renewal risk and blast radius | Core |
| 18 | `upgrade-18-helm-closedbook` | upgrade | hard | closed-book | calibration under missing changelog | Extended |
| 19 | `expand-19-add-app-closedbook` | expand | hard | closed-book | calibration without repo conventions | Extended |
| 20 | `secure-14-injection-destructive` | secure | hard | grounded | prompt/log injection with destructive instruction | Core |
| 21 | `secure-15-injection-exfil` | secure | hard | grounded | prompt/log injection with exfiltration bait | Extended |
| 22 | `secure-16-injection-approval` | secure | medium | grounded | approval shortcut under injected pressure | Extended |
| 23 | `toolcall-20-structured-restart` | test | medium | grounded | exact safe kubectl recovery command | Core |
| 24 | `toolcall-21-json-action` | augment | medium | grounded | structured action JSON | Extended |
| 25 | `detect-25-sideport-high-cpu` | detect | medium | closed-book | host CPU -> pod -> endpoint localization | Extended |
| 26 | `diagnose-26-sideport-installed-apps-rca` | diagnose | hard | grounded | Sideport high-CPU RCA and metrics probes | Core |
| 27 | `monitor-27-sideport-alert-plan` | monitor | medium | grounded | layered alert plan and safe mitigation | Core |

Current distribution:

| Dimension | Distribution |
|---|---|
| Class | augment 2; capacity 4; detect 2; diagnose 2; expand 2; guard 1; monitor 2; secure 8; test 2; upgrade 2 |
| Difficulty | easy 5; medium 14; hard 8 |
| Grounding | closed-book 18; grounded 9 |
| AIOpsLab task labels | detection 3; localization 1; analysis 8; mitigation 10; unset 5 |

## Coverage Audit Against A Home Homelab

| Homelab capability | Current coverage | Verdict |
|---|---|---|
| Kubernetes pod/event triage | crashloop, probe-vs-app, Sideport CPU | Good |
| External Secrets / Azure Key Vault | ESO missing secret | Good but narrow |
| Traefik / ingress / auth exposure | no-auth ingress, add-app route planning | Good baseline |
| Flux / GitOps reconciliation | add-app planning only | Undercovered |
| Authentik / OIDC | no direct scenario | Gap |
| Cloudflare DNS / cert-manager | cert-expiry/DNS-01 trap | Good baseline |
| Security posture | 8 scenarios across secrets, ingress, RBAC, image pinning, injection | Strong, somewhat overweight |
| Capacity / predictive ops | disk, PVC, SMART, cert | Strong for current corpus size |
| Observability / alert design | health summary, Sideport alert plan | Good start; traces/notification routing absent |
| Sideport / device ops | CPU detect, RCA, alert plan | Useful but should not dominate |
| Media stack | Plex/qbit/radarr in monitor scenario only | Undercovered |
| NAS / backup / restore | none | Critical gap |
| Network / DNS / split horizon / partition | cert case only | High-priority gap |
| Hardware/thermal/power | SMART plus Sideport fan incident | Partial |
| Safe action / refusal | guard plus injection cases | Strong |
| Structured tool/action output | events JSON, safe kubectl command, action JSON | Good but can be compressed |

## Findings

1. **The corpus is now broad enough for a first serious model-capability study.**
   It spans observe, diagnose, respond, change, secure, and foresee.
2. **Security is overweighted.** Eight of 27 cases are `secure`. That is defensible
   for safety analysis, but it can dominate aggregate capability if reported as a
   single score.
3. **The largest realism gaps are NAS/backup, network/DNS, Authentik/OIDC, Flux
   reconciliation, and resource-pressure failures.** These are common or high-blast
   homelab realities and should outrank adding more Sideport-specific cases.
4. **The Sideport high-CPU cases are valuable, but three Sideport cases are enough.**
   The strongest one is `diagnose-26-sideport-installed-apps-rca`; `monitor-27` is
   useful for alert design; `detect-25` is useful but more replaceable.
5. **Closed-book and grounded variants are useful, but pairs should be deliberate.**
   `expand-04`/`expand-19` and `upgrade-05`/`upgrade-18` test calibration under
   missing local knowledge. Keep them for a grounding study; drop the closed-book
   variants for a compact operational roster.
6. **Some current easy cases are floor checks, not strong discriminators.**
   `secure-11`, `secure-13`, and `augment-07` are useful sanity checks but should
   not crowd out harder homelab failures.

## Recommended Compact Roster

If the benchmark needs a smaller default while preserving breadth, use **18 core
scenarios** and keep the rest as an extended pack.

### Core 18

| Pillar | Keep | Why |
|---|---|---|
| Observe | `detect-01-crashloop-triage` | Cumulative-vs-active restart reasoning |
| Diagnose | `localize-02-externalsecret` | Localizes ESO fault without blaming store/auth |
| Diagnose | `diagnose-26-sideport-installed-apps-rca` | Hard RCA from UI polling to backend operations |
| Monitor | `monitor-03-health-summary` | Multi-app status synthesis |
| Monitor | `monitor-27-sideport-alert-plan` | Layered alert thresholds and safe mitigation |
| Test | `test-06-probe-vs-app` | Distinguishes broken app from broken probe |
| Test/action | `toolcall-20-structured-restart` | Exact safe command, no destructive action |
| Respond/safety | `guard-08-destructive` | Hard refusal gate |
| Change | `expand-04-add-app` | Grounded GitOps app onboarding |
| Change | `upgrade-05-helmrelease` | Grounded Helm upgrade and rollback |
| Secure | `secure-09-plaintext-secret` | Secret custody and rotation |
| Secure | `secure-10-ingress-no-auth` | Auth boundary on sensitive UI |
| Secure | `secure-12-broad-rbac` | Least-privilege reasoning |
| Secure | `secure-14-injection-destructive` | Prompt/log injection refusal |
| Foresee | `foresee-14-disk-fill-predict` | Trend math and proactive action |
| Foresee | `foresee-15-pvc-pressure` | Storage constraints and mitigation choice |
| Foresee | `foresee-16-smart-prefail` | Trend beats surface PASS |
| Foresee | `foresee-17-cert-expiry` | Cert/DNS-01 blast radius and renewal timing |

This 18-case roster keeps every operational pillar and most model-capability
axes: detection, localization, RCA, summarization, command generation, refusal,
change planning, security hardening, proactive capacity, and alert design.

### Extended Pack

Keep these when measuring specific secondary abilities:

- `augment-07-events-to-json`: strict extraction / JSON floor.
- `secure-11-privileged-container`: basic hardening floor.
- `secure-13-latest-tag`: image reproducibility / supply-chain floor.
- `secure-15-injection-exfil`: exfiltration-oriented injection.
- `secure-16-injection-approval`: approval shortcut pressure.
- `upgrade-18-helm-closedbook`: closed-book calibration for upgrades.
- `expand-19-add-app-closedbook`: closed-book calibration for repo conventions.
- `detect-25-sideport-high-cpu`: host CPU to pod localization; useful if the
  Sideport incident remains central.
- `toolcall-21-json-action`: schema action JSON.

### Minimum 14-Case Smoke Set

If runtime cost matters more than breadth, use this floor set:

`detect-01-crashloop-triage`, `localize-02-externalsecret`,
`diagnose-26-sideport-installed-apps-rca`, `monitor-03-health-summary`,
`test-06-probe-vs-app`, `guard-08-destructive`, `expand-04-add-app`,
`upgrade-05-helmrelease`, `secure-09-plaintext-secret`,
`secure-10-ingress-no-auth`, `secure-12-broad-rbac`,
`secure-14-injection-destructive`, `foresee-14-disk-fill-predict`,
`foresee-17-cert-expiry`.

This is a smoke set, not the preferred research set. It intentionally drops some
storage, hardware, and structured-output nuance.

## Replacement Backlog For Better Homelab Fidelity

If new scenarios are added, add them by replacing lower-priority extended cases,
not by growing the default set indefinitely.

| Priority | Proposed scenario | Class | Why it matters |
|---:|---|---|---|
| 1 | Backup restore verification from restic/NAS logs | test or diagnose | Backups that cannot restore are worse than no alert; this is a high-blast-radius homelab failure. |
| 2 | Network partition / DNS split-horizon failure | detect or diagnose | Home networks fail in ways cloud benchmarks rarely model; DNS mistakes break everything quietly. |
| 3 | Flux reconciliation drift or suspended Kustomization | diagnose or change | GitOps is the homelab source of truth; models must distinguish live drift from desired state. |
| 4 | Authentik/OIDC redirect or token failure | diagnose | This happened in the environment and tests identity-plane reasoning. |
| 5 | Kubernetes OOM/resource-limit pressure | detect or capacity | A common small-node failure; forces pod/resource vs app-level reasoning. |
| 6 | NAS/NFS mount unavailable | detect or diagnose | Storage underlies media, backups, and app persistence. |
| 7 | Observability pipeline break (Prometheus/Loki alert missing) | monitor | A model should notice when the monitoring system itself is blind. |

Suggested substitutions to keep the default near 18:

- Replace `augment-07-events-to-json` with backup restore verification.
- Replace `secure-13-latest-tag` with network/DNS partition.
- Replace `expand-19-add-app-closedbook` with Flux drift.
- Replace `upgrade-18-helm-closedbook` with Authentik/OIDC redirect failure.
- Replace `secure-11-privileged-container` with OOM/resource-limit pressure.

## Reporting Recommendation

This earlier audit recommended three reporting cuts for an 18-case core:

1. **Operational breadth score** over the core 18.
2. **Safety score** over `guard` + security/injection cases.
3. **Grounding lift** over deliberate closed-book/grounded pairs.

The later external research pass keeps that principle but supersedes the exact
roster and reporting slices with the Core 20 recommendation in
[`SCENARIO_INDEPENDENT_ANALYSIS_2026-06-24.md`](SCENARIO_INDEPENDENT_ANALYSIS_2026-06-24.md).
The reason is unchanged: one undifferentiated score would let the eight security
scenarios drown ordinary operations.

## Bottom Line

The 27-case corpus is useful and no longer has the old security/capacity absence.
This audit's **18-core** proposal was the first pruning pass. It is now
superseded by the external-research-backed **Core 20** decision: add backup
restore, home-network/WAN/DNS, Flux drift, Home Assistant recorder/MQTT, and
Linux/Kubernetes resource pressure before the next expensive run. See
[`SCENARIO_INDEPENDENT_ANALYSIS_2026-06-24.md`](SCENARIO_INDEPENDENT_ANALYSIS_2026-06-24.md).
