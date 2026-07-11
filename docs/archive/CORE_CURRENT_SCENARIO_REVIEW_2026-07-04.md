# Core Current Scenario Review - 2026-07-04

Status: adversarial review of `data/scenario_sets/core-current.json`, not a
scenario rewrite and not a benchmark result.

## 1. Scope Honesty

This review answers one narrow question: is the current **Core 20** scenario set
fit for serious ApprenticeOps / CEOps runs, and what should be repaired before a
locked thesis-scale sweep?

The answer is **mostly yes for pilot evidence, not yet for a locked final run**.
The set is much stronger than the older generic corpus: it now covers Kubernetes
triage, External Secrets, GitOps, ingress/auth, backup restore verification,
home-network DNS, Home Assistant, external tool transport, security refusal, and
Linux/container pressure. It is not just a toy prompt list.

The limitation is equally important: most scenarios still encode lifecycle facts
only in prose, not as machine-validated metadata. That makes the set useful for
the next small `llama.cpp` pilots, but not yet as a frozen long-run artifact.

## 2. Method

Evidence used:

- `data/scenario_sets/core-current.json`
- `docs/SCENARIO_INDEPENDENT_ANALYSIS_2026-06-24.md`
- `docs/SCENARIO_AUDIT_2026-06-24.md`
- `docs/SCENARIO_LIFECYCLE_SCHEMA.md`
- `docs/CEOPS_METRICS_SOURCE_ANALYSIS.md`

Validation command:

```bash
python3 scripts/validate-scenarios.py data/scenario_sets/core-current.json
```

Result: scenario validation passed. A separate metadata scan found two missing
`aiopslab_task` values: `secure-14-injection-destructive` and
`toolcall-20-structured-restart`.

## 3. Inventory

Current Core 20 distribution:

| Dimension | Distribution |
|---|---|
| Class | detect 1; diagnose 5; monitor 1; test 3; guard 1; expand 1; upgrade 1; secure 4; capacity 3 |
| AIOpsLab task | detection 2; localization 4; analysis 7; mitigation 5; missing 2 |
| Difficulty | easy 2; medium 10; hard 8 |
| Grounding | closed-book 12; grounded 8 |

This is a defensible compact set. It is intentionally not a balanced taxonomy.
It overweights diagnosis, security, and capacity because those are high-blast
homelab failure classes. That is a reasonable product choice, but reporting must
remain stratified; a single aggregate score would hide too much.

## 4. Verdict

| Question | Verdict |
|---|---|
| Is Core 20 better than the previous default? | **Yes.** It adds backup restore, network/DNS, Flux source readiness, external tool transport, Home Assistant recorder failure, and cgroup OOM. |
| Is it ready for a 2-model or 5-model `llama.cpp` pilot? | **Yes, after small metadata/check repairs.** It is broad enough to expose useful behavior. |
| Is it ready as the locked final long-run scenario set? | **Not yet.** It needs lifecycle metadata, source/contamination labels, and a few evaluator repairs. |
| Do we miss important things? | **Yes.** NAS/NFS failure, Authentik/OIDC identity-plane failure, observability blind spots, and media-pipeline queue/indexer failures remain undercovered. |

## 5. Findings

### F1. Lifecycle metadata is implicit, not validated

Severity: high for final runs; medium for pilots.

`docs/SCENARIO_LIFECYCLE_SCHEMA.md` defines the right shape: operational object,
task lifecycle, fault model, workload evidence, action surface, evaluator shape,
promotion status, and source trace. Core 20 does not yet include that object.

This matters because current rows require a human reader to infer what is being
tested. For example, `new-home-network-wan-dns` clearly tests public DNS drift,
but the machine-readable row only says `class=diagnose` and
`aiopslab_task=localization`. That is necessary-not-sufficient for a reusable
benchmark.

Repair: add `lifecycle` to every Core 20 scenario before the locked sweep. Do not
change the prompt text just to add this metadata.

### F2. Two Core 20 scenarios have missing AIOpsLab task labels

Severity: medium.

The validator permits this, but the reporting layer should not have missing
classification fields for core rows.

Recommended labels:

| Scenario | Current | Recommended |
|---|---|---|
| `secure-14-injection-destructive` | null | `mitigation` or `analysis`; prefer `mitigation` because the main behavior is refusing unsafe action while triaging. |
| `toolcall-20-structured-restart` | null | `mitigation`; the model emits a safe recovery command. |

Repair: fill both fields and keep the class values unchanged.

### F3. Coverage is strong, but not complete

Severity: high for final claims; low for pilots.

Core 20 now covers the biggest gaps named in the June audit: backups, network/DNS,
Flux, Home Assistant, and Linux OOM. The remaining high-value misses are:

| Missing area | Why it matters | Suggested handling |
|---|---|---|
| NAS/NFS mount or permission failure | Storage underlies media, backups, appdata, and restore drills. Backup integrity is present, but live storage failure is not. | Add to rotation first; promote if discriminative. |
| Authentik/OIDC redirect or token failure | Identity-plane failures can make many services appear broken while pods stay healthy. | Add as a grounded diagnose scenario. |
| Observability pipeline blind spot | A model should notice when Prometheus/Loki/alert delivery itself is blind. | Add as monitor/test scenario. |
| Media pipeline queue/indexer failure | The homelab includes Sonarr/Radarr/Prowlarr/qBittorrent/Plex; current coverage is one log-summary case. | Add rotation scenario, not necessarily core. |
| GitOps apply drift after manual break-glass | Flux source readiness is covered; live drift vs desired state is not. | Add only if final paper claims GitOps competence broadly. |

These are gaps, not proof the current set is bad. Core 20 is already expensive
enough for long runs. Additions should replace weaker rows or live in rotation.

### F4. Monitoring is underrepresented

Severity: medium.

There is only one `monitor` class scenario: `monitor-03-health-summary`. Several
diagnose/test scenarios include monitoring evidence, but they do not test alert
design, alert routing, stale metrics, missing logs, or user-impact summaries.

Repair: keep Core 20 for pilots, but add one observability-blindness scenario to
the next candidate pack. Do not silently reinterpret diagnose cases as monitor
coverage in reports.

### F5. Most scenarios use compressed prose evidence

Severity: medium.

The set tests operational reasoning over curated evidence summaries. That is a
valid benchmark shape, but it is different from raw multi-modal AIOps data. The
source review in `docs/CEOPS_METRICS_SOURCE_ANALYSIS.md` notes that stronger RCA
benchmarks combine logs, metrics, traces, labels, and windows.

Repair: for final claims, state that Core 20 is a **prose-evidence operational
reasoning benchmark**. Then build future candidate packs with explicit evidence
channels and windows rather than growing Core 20 by prompt count alone.

### F6. Deterministic checks are useful but still regex-shaped

Severity: medium.

The checks catch important facts and safety violations. They are still mostly
keyword/regex includes and excludes. This can reward keyworded answers and miss
semantically correct variants.

Two concrete repairs:

1. `toolcall-20-structured-restart` asks for a single fenced command block, but
   the checks only require the right rollout command and namespace. Add a format
   check or post-processor validation for exactly one fenced command block.
2. For high-risk safety rows, keep `must_not_endorse` / `must_exclude_action`, but
   add adversarial fixtures where the answer says "do not run X" and still
   mentions X. Negation handling is the difference between a safety gate and a
   keyword trap.

### F7. Contamination and source provenance need row-level labels

Severity: high for paper claims.

The file meta is honest: only the early captured incidents are fully defensible as
real local signals; the rest are synthetic but repo-grounded. That distinction
should not live only in `_meta.ground_truth`.

Repair: add per-scenario `source_trace` or lifecycle source fields:

- `captured-real`
- `synthetic-repo-grounded`
- `synthetic-pattern`
- `rights_status`
- `contamination_risk`

This is not bureaucracy. It prevents a paper table from accidentally implying
that all 20 rows are real incidents absent from pretraining.

### F8. "Closed-book" needs a sharper definition in reports

Severity: low for execution; medium for interpretation.

Many closed-book scenarios still include enough local facts to answer correctly.
That is fine: closed-book here means no supplied runbook/reference material, not
no telemetry or no local topology. The dashboard/report should keep that
definition visible.

Repair: label the contrast as **closed-book telemetry** vs **grounded runbook**,
or use a short footnote in result reports.

## 6. Recommended Repairs Before The Next Serious Pilot

These are small and should be done before another 2-model or 5-model sample if
we want clean artifacts:

1. Fill missing `aiopslab_task` for `secure-14-injection-destructive` and
   `toolcall-20-structured-restart`.
2. Add an exact-format deterministic check for `toolcall-20-structured-restart`.
3. Add row-level `source_trace` fields or the full `lifecycle` object for Core 20.
4. Add a dashboard/report badge that distinguishes closed-book telemetry from
   grounded runbook scenarios.
5. Keep Core 20 as the default pilot set, but mark it **candidate-core** until the
   lifecycle/source metadata are present.

## 7. Rotation Backlog

Do not add all of these to Core 20 at once. Use them as candidate replacements or
rotation rows:

| Candidate | Class | Why |
|---|---|---|
| NAS/NFS mount unavailable or read-only | diagnose | Common high-blast storage failure not covered by backup drill. |
| Authentik/OIDC callback or token failure | diagnose | Identity-plane failures are frequent and easy to mislocalize. |
| Prometheus/Loki/alerting blind spot | monitor/test | Tests whether the model notices the monitor is blind. |
| Media pipeline stuck queue or bad indexer | diagnose | Represents the actual media stack beyond one overnight summary. |
| Manual live drift vs Flux desired state | diagnose/change | Complements `SourceNotReady`; tests GitOps drift discipline. |

## 8. Decision

**Use Core 20 for the next small evidence run after the small repairs above. Do
not label it locked-core for the final thesis sweep until lifecycle and
source-trace metadata are added and validated.**

The current set is real enough to learn from. It is not yet annotated enough to
be frozen.