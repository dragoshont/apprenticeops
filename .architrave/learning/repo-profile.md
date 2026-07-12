# Architrave Repo Profile

## Purpose

ApprenticeOps is a reproducible CPU-local small-model benchmark for homelab operations assistants. It evaluates quality, deterministic safety, reliability, latency, and controlled energy while keeping inference locally sovereign. Evidence and paper claims are separate locks.

## Surfaces And Lanes

`kind: knowledge`. No Architrave UI, backend, IaC, or ops lane is configured. Runtime observation for this program is read-only SSH evidence; inference launch is governed by the recovery SDD, not `architrave.config.json`.

## Source Of Truth

- Experiment protocol and operation: `AGENTS.md`, `REPRODUCE.md`, `data/run-manifest.json`.
- Analysis contract: `analysis_metrics.py`, `data/analysis.schema.json`, `docs/STATISTICS.md`.
- Frozen paper lock: `data/analysis-manifest.json`.
- Completed-run boundary: `docs/sdd/completed-run-promotion.md`, `scripts/lock-completed-run.py`.
- Active timeout recovery: `docs/sdd/timeout-recovery-sensitivity.md` and `.architrave/runs/timeout-recovery-20260712/phase-ledger.md`.
- Parent recovery bundle: `data/completed-runs/full-chatok-core20-r5-ollama-20260705-150053-dd262a5c94593cb4b35bbb3554cc7ed1d608fab8b16160a3215329637c614baa/`.

## Build And Test

- Build/syntax: configured in `architrave.config.json`; shell syntax plus Python compilation.
- Recovery tests: analyzer, run-environment, retry-aware report, privacy, promoter, doc links, and diff check.
- Full paper gate: `scripts/audit-paper-data.py`, claim/link/privacy checks, isolated notebook verification, Quarto HTML/Typst when changing claim-bearing surfaces.

## Architecture Map

`home` orchestrates judges/persistence; `home-ai` performs locked local inference. `run.py` emits raw rows, runner shells enforce preflight/reset/provenance, the judge scheduler appends attempts, completed-run promotion produces immutable canonical evidence, and analysis consumes only verified/privacy-cleared bundles.

## Recurring Gotchas

- Raw judge attempts may exceed canonical count when parse-failed retries precede one valid success; use the shared judgement contract, not raw row equality.
- Missing Ollama models cannot all be pre-pulled for the 21-model recovery cohort: source artifacts require about 88.7 GiB while the node had about 59 GiB free. Use disk-bounded pull, exact digest verify before inference, and remove only newly pulled models.
- `length` is token-budget censoring, not timeout DNF.
- The source run was Ollama; llama.cpp is a separate runtime condition and covers only a small subset of affected artifacts.
- Launching from dirty or divergent source invalidates clean provenance; use a clean committed checkout and verify `env.harness_*`.

## Validated Facts

| Fact | Evidence | Last Checked |
|---|---|---|
| Parent run has 15,200 results and 30,400 canonical judgements plus 41 retries | completed-run bundle gate report | 2026-07-12 |
| Parent DNF = 204 timeout + 4 completion-frame; affected models = 21 | failure analyzer summary and independent raw checks | 2026-07-12 |
| Parent bundle verifies and privacy scan reports zero secret hits | `lock-completed-run.py verify`; `privacy-scan.py` | 2026-07-12 |
| Frozen public paper source remains `data/analysis-manifest.json` | manifest and claim audit | 2026-07-12 |
| Architrave kit copied at v0.10.3 | `gates/.kit-version` | 2026-07-12 |

## Last Reviewed

2026-07-12 during Architrave run `timeout-recovery-20260712`. Validate facts against the current branch before reuse.

