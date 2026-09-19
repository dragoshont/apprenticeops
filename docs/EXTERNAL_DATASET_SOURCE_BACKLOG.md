# External Dataset Source Backlog

Status: reviewed source backlog. These sources are **not imported** and are not
part of Core, paper scoring, judge calibration, training, or RAG. They are notes
for future scenario-quality work.

## Rules

- Treat every source here as pattern inspiration only until it passes the rights,
  contamination, and scenario-quality gates in `docs/EXTERNAL_DATASET_RIGHTS_LEDGER.md`.
- Do not copy exact row text, prompts, contexts, expected answers, hostnames, IDs,
  numeric rows, or rationales into held-out tests.
- If a future phase uses a concrete row, record row hashes and run a near-duplicate
  review before any held-out use.
- Do not use these sources for judge calibration, training, RAG, Core promotion,
  or paper claims without a new explicit gate.

## Reviewed Sources

| Source | Type | License / rights signal | Useful for | Current decision |
|---|---|---|---|---|
| `pavanmantha/devops-v1` | Hugging Face dataset, Docker/Kubernetes Q&A pairs | Dataset metadata says `apache-2.0`; Hugging Face public dataset terms still apply. | Docker/Kubernetes troubleshooting patterns; adversarial check design for overly generic remediation; possible examples of unsafe shell-command advice. | Pattern-only backlog. Do not import rows yet. |
| `mooselab/DevOpsDataCollection` | GitHub README index of DevOps/AIOps datasets and benchmarks | No license file found via GitHub API; README-only index. | Source discovery and literature positioning: AIOpsLab, UCR, IBM cloud telemetry, Google/Alibaba/Azure traces, Loghub, OpenStack failure dataset, Nezha, CFDR, Backblaze, ICPE, NAB. | Reference index only. Do not treat as a dataset. |
| Microsoft AIOpsLab | Agent benchmark/framework | GitHub repo is MIT; leaderboard/site are literature/benchmark references. | Positioning comparator and scenario lifecycle model: interactive environments, fault injection, workloads, telemetry, agent-cloud interface, detection/localization/analysis/mitigation tasks. | Cite/compare; do not import rows. |
| IBM Cloud telemetry anomaly dataset | Zenodo dataset | Zenodo page reports CC-BY-4.0; 5.5 GB data; related ICSE-SEIP / arXiv paper. | Real cloud telemetry/anomaly framing; useful for future telemetry/anomaly scenario patterns and artifact positioning. | High-value future source; no download/import now. |
| Nezha / TrainTicket + OnlineBoutique RCA data | GitHub dataset/code | GitHub API reports MIT license. | Multimodal logs+metrics+traces with service/inner-service RCA labels; high value for scenario design and future Architrave Eval telemetry schema. | High-value future source; inspect before any row use. |
| OpenStack failure dataset | Figshare dataset + ESEC/FSE paper | Rights must be checked at source; not reviewed here. | Injected faults with workload, effects, correctness checks, and OpenStack logs; high value for incident scenario design. | High-value future source; rights review needed. |
| Loghub | Log collection | GitHub API reports `NOASSERTION`; README says freely available for research/academic work and asks citation. | Log parsing/anomaly examples and realistic log surface forms. | Pattern/literature only until rights and raw-log handling are reviewed. |
| Google cluster-data | Workload/power traces | README says CC-BY 4.0 for data/docs; GitHub license API has no license file. | Workload/resource/power trace framing; useful for hardware/profile and telemetry positioning, less direct for answer-quality scenarios. | Literature/telemetry framing only; no import. |
| AzurePublicDataset | Cloud traces | GitHub API reports CC-BY-4.0; repo also contains MIT code license. | Cloud VM/function/LLM inference traces; useful for deployment-centric framing and future hardware/runtime profile schemas. | Literature/telemetry framing only; no import. |

## `pavanmantha/devops-v1` Notes

Observed via public Hugging Face APIs on 2026-07-03:

- Repository: `https://huggingface.co/datasets/pavanmantha/devops-v1`
- Revision: `048b3e550743bda05f3c41ed09da79d759279c6c`
- Public, not gated.
- Tags: Docker, Kubernetes, troubleshooting, DevOps, cloud-native, EKS, AKS.
- Files: `README.md`, `data/train-00000-of-00001.parquet`.
- Splits: `train` only.
- Schema: `question: string`, `solution: string`.
- Row count is inconsistent across surfaces: the card text says 256 pairs; the
  dataset viewer reports 312 rows. Treat 312 as the current viewer count until a
  local manifest verifies the parquet.

Quality-use assessment:

- Good source for **common Docker/Kubernetes troubleshooting surface forms**.
- Weak as held-out benchmark data because many rows are generic Q&A and may be
  close to public docs or StackOverflow-style answers.
- Potentially useful for creating **negative/adversarial fixtures**: answers that
  recommend restarts, stale PID deletion, `docker group` changes, or `--no-cache`
  too eagerly without discriminating root cause.
- Best next use is a small manual pass to extract **test-quality patterns**, not
  scenario rows.

## `mooselab/DevOpsDataCollection` Notes

Observed via GitHub API on 2026-07-03:

- Repository: `https://github.com/mooselab/DevOpsDataCollection`
- Description: collection of DevOps datasets for DevOps intelligence research.
- Files: README only.
- License API returned 404: no repository license file detected.
- Stars/forks at review time: small public index; no releases.

Quality-use assessment:

- Useful as a **map of external evaluation/data families**, not as data.
- Best candidates to inspect later for ApprenticeOps-style scenario quality:
  - OpenStack failure dataset: injected faults with workload/effects/logs.
  - Nezha / DeepTraLog: multimodal microservice logs, metrics, traces.
  - IBM cloud telemetry anomaly dataset: industry cloud telemetry and ICSE-SEIP paper.
  - Loghub / CFDR / Backblaze: useful for telemetry/anomaly/failure framing, less direct for ops-agent answer quality.
- Because this repo is an index with no license file, cite it only as a discovery
  aid if needed; cite the original datasets/papers for any substantive claim.

## Microsoft AIOpsLab Notes

Observed via public site/GitHub on 2026-07-03:

- Repository: `https://github.com/microsoft/AIOpsLab`
- Leaderboard: `https://microsoft.github.io/AIOpsLab/pages/leaderboard/`
- License: MIT in repository metadata.
- Purpose: holistic framework to design, develop, and evaluate autonomous AIOps
  agents. It deploys microservice environments, injects faults, generates
  workloads, exports telemetry, and provides an agent-cloud interface.
- Problem shape: application + task + fault + workload + evaluator.
- Task verbs: detection, localization, analysis, mitigation.
- Leaderboard reports average accuracy and time. Observed examples include
  GPT-4-based agents in the 49-79 average-accuracy range, DeepSeek-R1 around 50,
  and Llama3-8B agents lower.

Quality-use assessment:

- This is the strongest **positioning comparator** for ApprenticeOps. AIOpsLab
  evaluates interactive autonomous agents in live/simulated cloud environments;
  ApprenticeOps evaluates small local deployments on frozen homelab scenarios
  with energy/reliability telemetry.
- Use its lifecycle design to sanity-check scenario coverage: task, fault,
  workload, observability, evaluator.
- Do not try to import AIOpsLab problems into `external-candidates-v0`; use it to
  sharpen the taxonomy and to explain why ApprenticeOps is complementary, not a
  replacement.

## Mooselab Index Triage

The Mooselab README is useful as a discovery map. The table below ranks sources
for future ApprenticeOps/Architrave Eval work. It is **not** permission to import
raw data.

| Priority | Source family | Why it matters | Best use | Not for |
|---|---|---|---|---|
| P0 | AIOpsLab | Closest benchmark/framework neighbor; agent-cloud interface and task lifecycle. | Related-work positioning; task/fault/workload/evaluator checklist. | Row import or direct scoring comparison. |
| P0 | OpenStack failure dataset | Faults + workload + user-visible effects + correctness checks + logs. | Design better incident scenarios and gold/evaluator structure. | Import before rights/source-row review. |
| P0 | Nezha / DeepTraLog / TrainTicket | Multimodal logs, metrics, traces with RCA labels in microservice systems. | Future multimodal scenario and telemetry schema design. | Immediate Core promotion. |
| P0 | IBM Cloud telemetry anomaly dataset | Real large-scale cloud telemetry with anomaly windows; CC-BY-4.0. | Anomaly/telemetry framing and future prediction tasks. | Text-answer held-out scenarios by itself. |
| P1 | Loghub | Large realistic log surfaces, some labels, widely cited. | Log-surface realism and negative fixture design. | Raw-log copying without license/privacy review. |
| P1 | Google cluster-data + AzurePublicDataset + Alibaba clusterdata | Large workload/resource/power traces. | Deployment-centric telemetry/hardware-profile positioning; future systems analyses. | Ops-answer scenario rows. |
| P1 | CFDR + Backblaze | Failure and disk-health traces. | Capacity/foresee scenario inspiration and reliability framing. | Direct model QA scoring. |
| P2 | UCR anomaly/classification, Yahoo, NAB | Generic time-series anomaly benchmarks. | Baseline anomaly-detection framing and metric vocabulary. | AIOps answer-quality scenarios. |
| P2 | ICPE data challenges, workload traces, DLIM, HiBench, DaCapo | Performance/workload benchmark references. | Future benchmark/hardware-profile and load-generation design. | Current external candidate pack. |
| P3 | SecRepo, VizSec, EDGAR, Stack Exchange/SOTorrent | Security/access logs or public Q&A corpora. | Specialized future source scans with careful privacy/licensing review. | Current paper, Core, or dev scoring. |
| P3 | Microsoft MLOps / AutoML benchmark | MLOps examples and AutoML benchmark references. | General ecosystem awareness. | ApprenticeOps ops-scenario work for now. |

## Test-Quality Takeaways

1. **Scenario lifecycle matters.** AIOpsLab's application/task/fault/workload/
   evaluator framing suggests a quality bar for ApprenticeOps candidates: every
   scenario should state the operational object, the fault signal, what evidence is
   available, what action is being evaluated, and how the answer is judged.
2. **Multimodal evidence is the next real gap.** Nezha/DeepTraLog show that logs,
   metrics, and traces together make better RCA tasks. Current `external-candidates-v0`
   is still mostly text summaries.
3. **Time-series datasets help telemetry, not prose QA.** UCR/Yahoo/NAB and cloud
   workload traces are valuable for future deployment-evaluation schemas, but they
   do not directly produce good LLM answer-quality scenarios.
4. **Large traces are positioning and methods evidence first.** Google/Azure/
   Alibaba traces support the paper's systems-evaluation context, but importing
   them would be a separate systems project.
5. **Privacy/licensing remains the gate.** Loghub explicitly notes many logs are
   not sanitized/anonymized; StackExchange/SecRepo/VizSec sources need separate
   privacy and rights review before any row-level use.

## Recommended Next Use

1. Use `pavanmantha/devops-v1` to design **adversarial fixture patterns** for
   Docker/Kubernetes troubleshooting scenarios.
2. Use `mooselab/DevOpsDataCollection` to prioritize higher-quality, source-backed
   datasets for a future Phase 6+ source scan.
3. Use AIOpsLab as the primary benchmark comparator when tightening paper
  positioning and scenario lifecycle language.
4. Prioritize OpenStack failure + Nezha/DeepTraLog + IBM Cloud telemetry for the
  next source-quality scan, because they have the clearest path to better tests.
5. Do not add any source here to `external-candidates-v0` until a new mini-intake
   creates source hashes, rights status, and a candidate-quality review.