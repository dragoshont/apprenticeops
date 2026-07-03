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

## Recommended Next Use

1. Use `pavanmantha/devops-v1` to design **adversarial fixture patterns** for
   Docker/Kubernetes troubleshooting scenarios.
2. Use `mooselab/DevOpsDataCollection` to prioritize higher-quality, source-backed
   datasets for a future Phase 6+ source scan.
3. Do not add either source to `external-candidates-v0` until a new mini-intake
   creates source hashes, rights status, and a candidate-quality review.