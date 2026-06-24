# Scenario Research And Portfolio Recommendation - 2026-06-24

Status: external-research-backed recommendation. This is not a rewrite of
`data/scenarios.json`.

## Scope Honesty

This document updates the same question as
[`SCENARIO_AUDIT_2026-06-24.md`](SCENARIO_AUDIT_2026-06-24.md), but with an
external scan of public AIOps/SRE/DevOps benchmarks and operational guidance. It
is still a design document: it recommends which scenario families should be in a
compact ApprenticeOps corpus before we spend a full 150+ model run.

The objective is not an encyclopedic benchmark. Scenarios are expensive: at 150
models, 20 scenarios, and five repeats, one added scenario costs 750 extra model
answers before judging. The right default is therefore a **small core that spans
failure domains**, plus an extended/rotation pack for specific claims.

## External Sources Consulted

| Source | What It Measures | Signal For ApprenticeOps |
|---|---|---|
| AIOpsLab (`microsoft/AIOpsLab`, arXiv `2501.06706`, arXiv `2407.12165`) | Interactive agent-cloud environments with fault injection, workloads, telemetry, and tasks explicitly framed as **detection / localization / analysis / mitigation**. | Keep the AIOpsLab task verbs as the backbone, but ApprenticeOps should remain frozen/offline rather than interactive self-healing. |
| ITBench (`itbench-hub/ITBench`, arXiv `2502.05352`) | Kubernetes-based scenario environments for SRE, CISO/compliance, and FinOps; README lists high-error-rate checkout, RHEL compliance, and cost-overrun examples. The repo's CISO scenarios include Kyverno policy generation, kubectl+OPA checks, RHEL9+Ansible+OPA checks for SSH X11 forwarding, and policy-update tasks. Paper reports 94 real-world scenarios and low frontier-agent solve rates. | Include SRE + security/compliance + a small cost/capacity axis. ITBench validates generated artifacts and sandboxed evaluation, not only text answers. |
| OpsEval (`NetManAIOps/OpsEval-Datasets`, arXiv `2310.07637`) | 7184 multiple-choice and 1736 QA IT-ops items; categories include wired network, Oracle database, 5G/mobile communication, and log analysis. | Useful breadth signal, but mostly knowledge QA. ApprenticeOps should avoid becoming MCQ-only; use operational evidence and gold actions. |
| CodeFuse DevOps-Eval (`codefuse-ai/codefuse-devops-eval`) | 7486 MCQ items across PLAN/CODE/BUILD/TEST/RELEASE/DEPLOY/OPERATE/MONITOR; AIOps subset covers log parsing, time-series anomaly detection/classification/forecasting, and RCA; ToolLearning covers many tool scenes. | Add explicit build/release/deploy/operate/monitor coverage and keep structured tool/action output, but do not over-weight low-cognition MCQ-like tasks. |
| RCAEval (`phamquiluan/RCAEval`) | Microservice RCA benchmark with 735 real failure cases, nine datasets, and fault types CPU, memory, disk, delay, loss, socket, plus multi-source metrics/logs/traces. | RCA scenarios should distinguish telemetry source and fault type; ApprenticeOps should include at least one multi-source RCA and one network/socket/latency case. |
| SREBench (`MrDunky14/SREBench`) | Smaller OpenEnv-style incident environment with tasks such as OOM, DB connection pool exhaustion, CPU throttling, memory leak, cache fragmentation, disk pressure, DNS resolution, config drift, network partition, DB replica sync, deadlock, and cert expiry. | Not as established as ITBench/AIOpsLab/RCAEval, but its scenario list is a useful sanity check for production-incident coverage. |
| Google SRE Book + Workbook | Monitoring, practical alerting, effective troubleshooting, emergency response, incident management, postmortem culture, testing reliability, release engineering, overload, data integrity, critical state, periodic scheduling. | The scenario corpus needs more data integrity, backup/restore, overload, alerting, and change-management cases. |
| DORA capability catalog | Monitoring/observability, proactive failure notification, deployment automation, continuous delivery, database change management, pervasive security, AI-accessible internal data, healthy data ecosystems, platform engineering. | Measure capabilities, not Four Keys outcomes. Grounded scenarios should test local data/RAG value. |
| Kubernetes docs | Application and cluster debugging; node NotReady/network partition/control-plane failure; resource requests/limits; OOMKilled; node pressure eviction over memory/disk/inodes/PIDs; metrics pipeline. | Must include node/resource pressure, scheduling/OOM, network partition, and app-vs-cluster localization. |
| Flux troubleshooting docs | Ready/Suspend checks for sources/kustomizations/helm releases; chart not ready; install retries exhausted; webhook dry-run failures; drift/event spam from null/empty fields; low-memory controller CrashLoop. | Add Flux drift or source-not-ready scenario; current add-app plan is insufficient for GitOps operations. |
| cert-manager troubleshooting docs | Certificate -> CertificateRequest -> Issuer -> Order -> Challenge chain; use status/events before logs; ACME/DNS-01 failure path. | Existing cert-expiry scenario is good; keep it. |
| restic docs | Restore semantics, dry-run, `check`, `--read-data-subset`, repository locks, wrong password, damaged index, JSON exit codes, restore/delete safety. | Add backup restore verification. A backup that cannot restore is a core homelab failure. |
| Home Assistant docs | Configuration YAML/dependency/integration troubleshooting; recorder disk/DB requirements and corruption; MQTT broker/discovery/availability/retained-message hazards; ZHA coordinator, USB, interference, mesh, and device-support issues; locked-out recovery. | Add Home Assistant scenarios: recorder DB/disk, MQTT availability/discovery, Zigbee coordinator/interference, and auth recovery. |
| Prometheus/Grafana docs | Alert on symptoms, batch jobs not succeeded recently, capacity before outage, metamonitoring, alert rules with `for`, labels, annotations, runbooks. | Alert-plan scenarios should page on symptoms and capacity, not every cause. Add metamonitoring/alert-pipeline blind spot. |
| Linux kernel docs | CPU frequency/boost/thermal tradeoffs; memory reclaim, compaction, OOM killer, page cache. | Add Linux host resource scenario: fan/thermal/CPU governor, memory pressure, or OOM. |
| Cloudflare DNS/Tunnel docs | DNS troubleshooting categories include stale upstream responses, unexpected records, same-name record conflicts, exposed IPs, DNSSEC issues; Tunnel docs separate common errors, connectivity pre-checks, private-network connectivity, and diagnostic logs. | Home-network scenarios should distinguish public DNS, local split horizon, tunnel health, and backend app health instead of restarting workloads. |
| Let's Encrypt docs | HTTP-01 requires port 80 and cannot issue wildcards; DNS-01 supports wildcards and private services but depends on DNS-provider API credentials and propagation; rate limits make repeated failed validation costly. | Keep and deepen DNS-01/cert scenarios; include API-token/proxy/propagation failure without asking models to brute-force renewals. |
| systemd docs | systemd is the Linux system/service manager; its documentation emphasizes failed units, journal logs, networking-online ordering, boot diagnostics, resource pressure handling, and service status. | Linux host scenarios should include failed systemd units/log interpretation, not only Kubernetes pods. |

Note: OpenWrt documentation was attempted for WAN/DHCP/DNS topics but was behind
an anti-bot challenge during this pass, so it is not cited as evidence here. Home
network/ISP scenarios below are derived from the local homelab topology plus
Kubernetes/network/Home Assistant evidence, not from OpenWrt text. Direct URLs
are listed in the source appendix.

## What Other Benchmarks Teach Us

1. **AIOpsLab and ITBench validate lifecycle coverage.** A strong corpus needs
   detection, localization, analysis/RCA, and mitigation; it also needs SRE,
   security/compliance, and cost/capacity-like decisions.
2. **OpsEval and CodeFuse show the danger of easy breadth.** Large MCQ/QA banks
   cover many labels, but they do not necessarily test operational judgement,
   safe action, or local-grounding behavior. ApprenticeOps should stay evidence-
   based and action-oriented.
3. **RCAEval highlights fault-type breadth.** CPU/memory/disk/delay/loss/socket
   are a good minimum set for RCA. ApprenticeOps currently has CPU, disk, cert,
   and some logs, but network loss/socket/latency and memory/OOM are weak.
4. **SREBench's incident list matches practical intuition.** Even if it is less
   established, its OOM, connection pool, CPU throttling, cache, disk pressure,
   DNS, config drift, network partition, replica sync, deadlock, and cert expiry
   list is a useful check against missing production-style failures.
5. **Homelab reality adds domains public-cloud benchmarks miss.** ISP, Wi-Fi,
   DNS split horizon, NAS/backup, Home Assistant, Zigbee/MQTT, physical USB/iOS
   devices, and consumer hardware thermals are not edge cases for a home server;
   they are the environment.
6. **Security scenarios should include evidence generation, not only advice.**
  ITBench's CISO tasks require agents to produce Kyverno/OPA/Ansible artifacts
  and then run an evaluator. ApprenticeOps can stay text-only for cost, but its
  gold answers should still ask for evidence collection and exact policy/runbook
  boundaries.

## Failure-Domain Taxonomy For This Homelab

| Domain | Representative failures | Current coverage | Verdict |
|---|---|---|---|
| Kubernetes app lifecycle | CrashLoop, OOMKilled, bad readiness probe, image pull, init container, service selector | crashloop, probe-vs-app | Missing OOM/image/init/service-selector |
| Kubernetes node/control plane | Node NotReady, kubelet down, API server/backing store, DiskPressure, MemoryPressure, PIDPressure | partial via capacity | Missing explicit node/control-plane case |
| GitOps/IaC | Flux source not ready, Kustomization suspended, HelmRelease install retries, webhook dry-run, drift spam | add-app only | Gap |
| Secrets/identity | ESO remoteRef missing, Key Vault auth, Authentik/OIDC redirect/session, API auth | ESO only | Missing Authentik/OIDC and token/session cases |
| Ingress/DNS/TLS | Traefik routing, middleware auth, Cloudflare DNS, DNS-01, split horizon, cert expiry | ingress auth, cert expiry, add-app | Missing split-horizon / ISP / Cloudflare auth failure |
| Observability | Prometheus/Loki/Grafana availability, alert routing, metamonitoring, noisy alerts | health summary, Sideport alert plan | Missing monitoring-pipeline blind spot |
| Backup/storage/NAS | restic repo lock/wrong password/damaged index, restore drill, NFS mount, NAS full/offline | none direct | Critical gap |
| Linux host | high CPU/fan, cpufreq/turbo/governor, OOM killer, memory reclaim, SMART, disk IO | SMART, Sideport CPU | Missing Linux memory/OOM/thermal root cause |
| Home Assistant | YAML/config dependency, recorder DB/disk, MQTT broker/discovery/availability, Zigbee coordinator/interference/mesh, lockout | none | Gap |
| Linux services | failed systemd units, dependency ordering, journal evidence, network-online, service restart policy | none direct | Gap |
| Media stack | Plex transcode/GPU, qbit disk, *arr indexer/API, import pipeline | monitor-03 only | Thin |
| Sideport / device ops | iPhone visibility, usbmux/netmuxd, Anisette, installed-apps CPU, scheduler jobs | high CPU RCA/alert | Good enough; do not add more by default |
| Security/safety | Plaintext secrets, RBAC, ingress auth, privileged containers, image tags, prompt injection | strong | Overweighted |
| Cost/energy/capacity | disk trends, model/node energy, cloud cost if any, resource limits | capacity, paper telemetry | Good for current scope, missing FinOps-style case |
| Structured action/tool use | exact safe command, JSON action, event extraction | present | Good; can be compressed |

## Scenario Selection Criteria

A scenario belongs in the expensive core only if it satisfies most of these:

1. **High blast radius** in this homelab: outage, data loss, credential exposure,
   unsafe mutation, or persistent toil.
2. **Model-discriminating reasoning:** likely to separate small models by
   localization, calibration, safe-action choice, or multi-signal synthesis.
3. **Evidence-shaped:** logs, events, metrics, manifests, or runbook snippets can
   be frozen into a stable prompt.
4. **Actionable gold answer:** not just "explain X"; it should require a next
   check, mitigation, refusal, or runbook decision.
5. **Not redundant** with an existing scenario unless it intentionally forms a
   closed-book/grounded pair.
6. **No hidden dependency on public cloud APIs** during inference; all context is
   in the prompt.

## Recommended Portfolio

The best default is a **Core 20**. It is larger than the previous 18 because the
external scan makes backup, home network, Flux/GitOps, Home Assistant, and Linux
resource pressure hard to ignore. It is still smaller than the current 27 and
much smaller than an unbounded benchmark.

### Core 20

| Slot | Scenario | Source | Capability tested | Why it is core |
|---:|---|---|---|---|
| 1 | `detect-01-crashloop-triage` | existing | cumulative-vs-active Kubernetes triage | Common false alarm; tests restraint. |
| 2 | `localize-02-externalsecret` | existing | ESO/Key Vault localization | Core secret-sync plane. |
| 3 | `monitor-03-health-summary` | existing | multi-app health summary | Broad media/app signal synthesis. |
| 4 | `test-06-probe-vs-app` | existing | app-vs-probe failure | Kubernetes docs treat app debugging separately from cluster debugging; this catches false outages. |
| 5 | `guard-08-destructive` | existing | refuse catastrophic mutation | Non-negotiable safety gate. |
| 6 | `expand-04-add-app` | existing | grounded GitOps app onboarding | Tests repo-convention use and change planning. |
| 7 | `upgrade-05-helmrelease` | existing | grounded upgrade/rollback | Tests release/change management. |
| 8 | `secure-09-plaintext-secret` | existing | secret hygiene and rotation | High-risk, common, deterministic. |
| 9 | `secure-10-ingress-no-auth` | existing | auth boundary on sensitive UI | Homelab ingress risk. |
| 10 | `secure-12-broad-rbac` | existing | least privilege | Security without being merely policy trivia. |
| 11 | `secure-14-injection-destructive` | existing | prompt/log injection refusal | Tests untrusted telemetry safety. |
| 12 | `foresee-14-disk-fill-predict` | existing | trend/capacity math | Proactive failure notification. |
| 13 | `foresee-17-cert-expiry` | existing | cert/DNS-01 blast radius | Keeps TLS/DNS chain. |
| 14 | `toolcall-20-structured-restart` | existing | exact safe kubectl command | Preserves structured-action discipline in the default score. |
| 15 | `diagnose-26-sideport-installed-apps-rca` | existing | deep RCA + metrics probes | Strong real incident; keep one Sideport deep case. |
| 16 | `new-backup-restore-drill` | new | restic restore/check/repo-lock/data-integrity | Critical gap; backups are only useful if restorable. |
| 17 | `new-home-network-wan-dns` | new | ISP/WAN vs LAN/DNS/split-horizon localization | Homelab-specific and high blast radius. |
| 18 | `new-flux-drift-source-not-ready` | new | GitOps drift/source/Helm readiness | Flux is the source of truth; current coverage is too thin. |
| 19 | `new-homeassistant-recorder-or-mqtt` | new | HA recorder DB/disk or MQTT availability/discovery | Home automation is a real home-server workload, not generic cloud. |
| 20 | `new-linux-oom-or-node-pressure` | new | Linux/Kubernetes memory/OOM/node pressure | External benchmarks cover OOM/resource pressure; current corpus lacks it. |

### Why Core 20 Is Preferable To Core 18

The previous 18-case audit was internally reasonable, but the external scan makes
five additions non-optional for a home server: backup/restore, home network/ISP,
Flux/GitOps reconciliation, Home Assistant, and Linux/Kubernetes resource
pressure. Core 20 also keeps one exact-command scenario, so structured-action
reporting remains grounded in a default-core item. The trade-off is rotating
`foresee-16-smart-prefail`; SMART remains valuable, but Linux resource pressure
is broader and better aligned with public AIOps incident families.

### If Runtime Cost Forces A Smaller Core

Use **Core 16**, not random pruning:

`detect-01-crashloop-triage`, `localize-02-externalsecret`,
`monitor-03-health-summary`, `test-06-probe-vs-app`, `guard-08-destructive`,
`expand-04-add-app`, `upgrade-05-helmrelease`, `secure-09-plaintext-secret`,
`secure-10-ingress-no-auth`, `secure-12-broad-rbac`,
`secure-14-injection-destructive`, `foresee-14-disk-fill-predict`,
`foresee-17-cert-expiry`, `toolcall-20-structured-restart`,
`new-backup-restore-drill`, `new-home-network-wan-dns`.

This keeps the two homelab-specific gaps with highest blast radius and one
structured-action scenario. It drops SMART, the deep Sideport RCA, Home
Assistant, Flux drift, and OOM/resource pressure to the rotation pack. That is
acceptable only for a smoke run.

## Recommended New Scenario Designs

These are scenario specifications, not final gold answers.

### 1. Backup Restore Drill (`new-backup-restore-drill`)

Class: `test` or `diagnose`; difficulty: hard; grounding: grounded.

Evidence shape:

- restic backup JSON summary says last backup succeeded.
- `restic snapshots --json` has recent snapshots.
- `restic check --json` reports `num_errors > 0`, `suggest_repair_index: true`,
  or wrong-password/lock exit code.
- A restore dry-run shows zero files restored for the expected path, or restore
  is aimed at the wrong snapshot because `latest` selected a different host/path.

Question:

- Is the backup safe? What should be done before trusting it? What command should
  be run next?

Model capability:

- Distinguish backup success from restore confidence.
- Use restic `check`, `restore --dry-run`, `snapshots --host/--path`, and repair
  hints correctly.
- Avoid destructive `restore --delete` without dry-run.

Why core:

- This is the largest current homelab gap. It tests data integrity, not just uptime.

### 2. Home Network / ISP / Split-Horizon DNS (`new-home-network-wan-dns`)

Class: `diagnose`; difficulty: hard; grounding: closed-book or grounded.

Evidence shape:

- LAN clients can reach `home.hont.ro` by IP, but public DNS resolves to Cloudflare
  or an old WAN IP.
- `dig @1.1.1.1 service.hont.ro` differs from local CoreDNS/UniFi result.
- Cloudflared tunnel is healthy, Traefik is healthy, pod endpoints are healthy.
- ISP WAN is up/down, DHCP lease changed, or port-forward/tunnel status differs.
- Cloudflare DNS record list has unexpected records, proxy-mode mismatch, stale
  response, or tunnel diagnostic logs show connectivity failure.

Question:

- Localize the failure: ISP/WAN, public DNS, split-horizon DNS, tunnel, ingress,
  or backend app? Give the next non-destructive check.

Model capability:

- Separate LAN vs WAN vs DNS vs ingress vs app.
- Avoid restarting apps when DNS is stale.
- Recognize split-horizon and tunnel semantics.

Why core:

- Public AIOps benchmarks rarely model consumer WAN/DNS, but home servers live
  there.

### 3. Flux Drift / Source Not Ready (`new-flux-drift-source-not-ready`)

Class: `diagnose` or `upgrade`; difficulty: medium-hard; grounding: grounded.

Evidence shape:

- `flux get all -A --status-selector ready=false` shows a GitRepository, Helm
  source, Kustomization, or HelmRelease not ready.
- Events show `HelmChart is not ready`, source 404, install retries exhausted,
  webhook dry-run unsupported, or empty/null field drift spam.
- Git commit is correct but live cluster has not applied it.

Question:

- Which Flux object is the root blockage? What is the safe fix and what should
  not be manually applied?

Model capability:

- Follow GitOps object chain instead of jumping to `kubectl apply`.
- Distinguish source readiness from workload readiness.
- Preserve Git as source of truth.

Why core or near-core:

- This homelab is GitOps-managed; drift/reconcile failures are control-plane
  failures for operations.

### 4. Home Assistant Recorder / MQTT / Zigbee (`new-homeassistant-recorder-or-mqtt`)

Class: `diagnose` or `monitor`; difficulty: medium-hard; grounding: grounded.

Recommended first version: **recorder DB/disk pressure**.

Evidence shape:

- Home Assistant is responsive but history/logbook is slow or missing.
- Recorder DB size is large; free disk below database size or below 2.5x DB size
  for corruption recovery.
- Logs mention database locked, schema migration, purge/repack, or recorder retry.
- MQTT/Zigbee entities are not the primary failure.

Question:

- Is Home Assistant down, or is recorder/storage the issue? What is the safe
  remediation sequence?

Model capability:

- Separate core automation availability from history/recorder persistence.
- Avoid deleting the DB first.
- Recommend backup, purge/repack, exclude noisy entities, or move DB carefully.

Rotation variants:

- MQTT broker/discovery/availability: retained ghost entities vs broker down.
- ZHA coordinator/interference: USB 3.0/interference/mesh/router issue vs device
  unsupported; asks for diagnostics and non-destructive radio checks.
- Automation trace/mode issue: an automation appears broken, but trace shows the
  condition failed, `single` mode suppressed a new run, or a template variable is
  wrong. This is a good lightweight Home Assistant reasoning case if recorder is
  too storage-heavy.
- Reverse-proxy/auth issue: `use_x_forwarded_for` without correct
  `trusted_proxies`, IP ban, MFA/notification delivery, or unprotected `/local/`
  static files.

Why core:

- Home Assistant is a defining home-server workload. It is absent from the current
  corpus.

### 5. Linux / Kubernetes Resource Pressure (`new-linux-oom-or-node-pressure`)

Class: `detect` or `capacity`; difficulty: medium-hard; grounding: closed-book.

Evidence shape:

- Pod restart count with `Last State: OOMKilled`, exit 137, memory limit 256Mi,
  working set near limit.
- Node conditions show MemoryPressure or DiskPressure; kubelet eviction events;
  host `dmesg` OOM killer lines.
- Or CPU fan event with cpufreq/turbo/temp metrics and a process/pod map.

Question:

- Is this an app bug, resource limit issue, node pressure, or host thermal issue?
  What should change and what should be monitored?

Model capability:

- Use pod limit/request and node pressure semantics.
- Avoid treating CPU saturation as a reason to scale a single-signer app.
- Connect Linux host signals to Kubernetes symptoms.

Why core:

- Resource pressure is central in Kubernetes docs and SREBench/RCAEval fault
  families; the current corpus lacks a pure OOM/node-pressure case.

### 6. Authentik / OIDC Redirect Failure (`new-authentik-oidc-redirect`)

Class: `diagnose`; difficulty: medium; grounding: grounded.

Evidence shape:

- Browser login fails with `invalid redirect_uri`.
- Backend health and MCP/API are healthy.
- Authentik provider lacks the portal callback URL.
- A blueprint or provider diff has redirect URIs.

Question:

- What is broken and what should be changed? How do you verify without breaking
  the existing client?

Why rotation:

- We just saw this in the environment. It is valuable, but identity-plane cases
  should rotate unless login/OIDC becomes central to the paper.

### 7. Observability Blind Spot / Alert Pipeline (`new-observability-metamonitoring`)

Class: `monitor`; difficulty: medium; grounding: grounded.

Evidence shape:

- Service outage happened but no alert fired.
- Prometheus target down, scrape disabled, missing ServiceMonitor, Alertmanager
  route silenced, Loki log label mismatch, or Grafana rule pending but not firing.

Question:

- Was the service healthy, or was monitoring blind? What signal would have paged?

Why rotation:

- Prometheus guidance explicitly calls for metamonitoring. Useful, but slightly
  more platform-specific than backup/network/resource-pressure.

### 8. Linux Service Failure (`new-linux-systemd-service`)

Class: `detect` or `diagnose`; difficulty: medium; grounding: closed-book.

Evidence shape:

- `systemctl --failed` shows one failed unit, while Kubernetes pods are healthy.
- `journalctl -u <unit>` shows a missing mount, bad environment file, DNS lookup
  failure, or network-online ordering problem.
- Host metrics show normal CPU/memory; the failure is service-level, not cluster
  resource pressure.

Question:

- Is this a Kubernetes app issue or a Linux host service issue? What is the safe
  next command and what should not be restarted?

Why rotation:

- It directly covers Linux OS operation, but overlaps with `new-linux-oom-or-node-pressure`.
  Use it in the rotation pack unless host-level service failures become central.

## What To Keep, Drop, Or Rotate From The Current 27

| Current scenario | Recommendation | Reason |
|---|---|---|
| `detect-01-crashloop-triage` | Keep core | Excellent restraint/localization test. |
| `localize-02-externalsecret` | Keep core | Core secret-sync plane. |
| `monitor-03-health-summary` | Keep core | Broad multi-service synthesis. |
| `expand-04-add-app` | Keep core | Grounded GitOps change planning. |
| `upgrade-05-helmrelease` | Keep core | Upgrade/rollback discipline. |
| `test-06-probe-vs-app` | Keep core | Common Kubernetes false-positive pattern. |
| `augment-07-events-to-json` | Rotate | Useful floor check, low operational reasoning. |
| `guard-08-destructive` | Keep core | Safety gate. |
| `secure-09-plaintext-secret` | Keep core | Secret leakage + rotation. |
| `secure-10-ingress-no-auth` | Keep core | Homelab ingress risk. |
| `secure-11-privileged-container` | Rotate | Good floor, less discriminating than RBAC/secrets/injection. |
| `secure-12-broad-rbac` | Keep core | Least privilege and blast radius. |
| `secure-13-latest-tag` | Rotate | Important, but lower severity than backup/network gaps. |
| `foresee-14-disk-fill-predict` | Keep core | Proactive capacity. |
| `foresee-15-pvc-pressure` | Rotate or keep if no NAS scenario yet | Useful storage constraint, but backup/NAS restore is better. |
| `foresee-16-smart-prefail` | Rotate | Good host-hardware signal, but Linux/OOM/node pressure gives broader host-resource coverage in Core 20. |
| `foresee-17-cert-expiry` | Keep core | TLS/DNS blast radius. |
| `upgrade-18-helm-closedbook` | Rotate | Calibration variant; not default. |
| `expand-19-add-app-closedbook` | Rotate | Calibration variant; not default. |
| `secure-14-injection-destructive` | Keep core | Strong safety under untrusted context. |
| `secure-15-injection-exfil` | Rotate | Valuable safety variant, not default. |
| `secure-16-injection-approval` | Rotate | Valuable approval-pressure variant, not default. |
| `toolcall-20-structured-restart` | Keep core | Exact safe command and structured-action discipline. |
| `toolcall-21-json-action` | Rotate | Structured output variant, lower ops fidelity. |
| `detect-25-sideport-high-cpu` | Rotate | Useful but covered better by `diagnose-26`. |
| `diagnose-26-sideport-installed-apps-rca` | Keep core | Strong real incident and RCA. |
| `monitor-27-sideport-alert-plan` | Rotate | Good alert plan, but Sideport-specific and not the best use of the default-core budget. |

## Proposed Reporting Slices

Do not collapse everything into one score. Report:

1. **Core operational score** over Core 20.
2. **Safety score** over `guard`, `secure`, and injection cases.
3. **Grounding lift** over deliberate closed-book/grounded pairs.
4. **Home-specific score** over backup, network, Home Assistant, Sideport, NAS,
   and Linux host scenarios.
5. **Structured-action score** over the Core 20 exact-command case plus
  rotation-pack JSON/action-output cases.

This makes it clear whether a model is broadly useful, merely safe, or merely good
at structured formatting.

## Decision

Use **Core 20** as the next default target. Add the five new core scenarios before
running another expensive 150+ model sweep:

1. `new-backup-restore-drill`
2. `new-home-network-wan-dns`
3. `new-flux-drift-source-not-ready`
4. `new-homeassistant-recorder-or-mqtt`
5. `new-linux-oom-or-node-pressure`

If the run budget forces fewer than 20 scenarios, run Core 16 and keep backup +
home-network as the two non-negotiable additions. They are the biggest current
fidelity gaps for a real home server.

## Source Appendix

Direct references used in this research pass:

- AIOpsLab: <https://github.com/microsoft/AIOpsLab>,
  <https://arxiv.org/abs/2501.06706>, <https://arxiv.org/abs/2407.12165>.
- AIOpsLab problem registry:
  <https://github.com/microsoft/AIOpsLab/blob/main/aiopslab/orchestrator/problems/registry.py>.
- ITBench: <https://github.com/itbench-hub/ITBench>,
  <https://arxiv.org/abs/2502.05352>.
- ITBench scenarios: <https://github.com/itbench-hub/ITBench/tree/main/scenarios>;
  CISO scenario details: <https://github.com/itbench-hub/ITBench/tree/main/scenarios/ciso>.
- OpsEval: <https://github.com/NetManAIOps/OpsEval-Datasets>,
  <https://arxiv.org/abs/2310.07637>.
- CodeFuse DevOps-Eval: <https://github.com/codefuse-ai/codefuse-devops-eval>.
- RCAEval: <https://github.com/phamquiluan/RCAEval>.
- SREBench: <https://github.com/MrDunky14/SREBench>.
- Google SRE Book table of contents: <https://sre.google/sre-book/table-of-contents/>;
  SRE Workbook table of contents: <https://sre.google/workbook/table-of-contents/>.
- DORA capabilities: <https://dora.dev/capabilities/>.
- Kubernetes debugging overview: <https://kubernetes.io/docs/tasks/debug/>;
  app debugging: <https://kubernetes.io/docs/tasks/debug/debug-application/>;
  cluster debugging: <https://kubernetes.io/docs/tasks/debug/debug-cluster/>.
- Kubernetes resource management: <https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/>;
  node-pressure eviction: <https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/>;
  resource metrics pipeline: <https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-usage-monitoring/>.
- Flux troubleshooting: <https://fluxcd.io/flux/cheatsheets/troubleshooting/>.
- cert-manager troubleshooting: <https://cert-manager.io/docs/troubleshooting/>.
- restic restore/check/scripting docs:
  <https://restic.readthedocs.io/en/latest/050_restore.html>,
  <https://restic.readthedocs.io/en/latest/075_scripting.html>,
  <https://restic.readthedocs.io/en/latest/045_working_with_repos.html>.
- Prometheus alerting practices/rules:
  <https://prometheus.io/docs/practices/alerting/>,
  <https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/>.
- Grafana Alerting: <https://grafana.com/docs/grafana/latest/alerting/>.
- Home Assistant configuration troubleshooting:
  <https://www.home-assistant.io/docs/configuration/troubleshooting/>;
  recorder: <https://www.home-assistant.io/integrations/recorder/>;
  locked out: <https://www.home-assistant.io/docs/locked_out/>;
  HTTP/reverse proxy: <https://www.home-assistant.io/integrations/http/>;
  securing: <https://www.home-assistant.io/docs/configuration/securing/>;
  MFA: <https://www.home-assistant.io/docs/authentication/multi-factor-auth/>.
- Home Assistant MQTT/ZHA/automation docs:
  <https://www.home-assistant.io/integrations/mqtt/>,
  <https://www.home-assistant.io/integrations/zha/>,
  <https://www.home-assistant.io/docs/automation/troubleshooting/>,
  <https://www.home-assistant.io/docs/automation/modes/>,
  <https://www.home-assistant.io/docs/automation/templating/>.
- Linux kernel CPU frequency and memory management docs:
  <https://www.kernel.org/doc/html/latest/admin-guide/pm/cpufreq.html>,
  <https://www.kernel.org/doc/html/latest/admin-guide/mm/concepts.html>.
- systemd overview: <https://systemd.io/>.
- Cloudflare DNS/Tunnel troubleshooting:
  <https://developers.cloudflare.com/dns/troubleshooting/>,
  <https://developers.cloudflare.com/dns/manage-dns-records/troubleshooting/>,
  <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/troubleshoot-tunnels/>.
- Let's Encrypt challenge/rate-limit docs:
  <https://letsencrypt.org/docs/challenge-types/>,
  <https://letsencrypt.org/docs/rate-limits/>.

## Explicit Non-Goals For The Default Corpus

- Do not add a separate scenario for every Home Assistant integration. Use one
  representative recorder/MQTT/Zigbee/automation scenario per run.
- Do not add every Kubernetes failure mode in the docs. Pick one each for app
  failure, node/resource pressure, and GitOps reconciliation.
- Do not over-index on Sideport just because it generated the most recent real
  incident. Keep one deep Sideport RCA case; rotate the others.
- Do not convert the benchmark into a public-cloud FinOps study. A small
  cost/capacity scenario is useful, but ApprenticeOps' differentiator is local
  homelab operations under locally-sovereign inference.
