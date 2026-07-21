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
- Recurring research radar: `.github/skills/literature-radar/SKILL.md`,
  `docs/analysis/research-radar/`, and
  `.architrave/runs/literature-radar-20260713/phase-ledger.md`. Radar evidence is
  candidate-only; the literature catalog, bibliography, and paper require a
  separate human-approved promotion.
- Current paper-impact packet:
    `docs/analysis/research-radar/2026-07-13-paper-impact.md`. It records
    source-ranked recommendations without changing canon; operations benchmark
    depth is the main novelty pressure, while adaptation, specialist routing, and
    executed recovery remain separate studies.
- Parent recovery bundle index: `data/completed-runs/full-chatok-core20-r5-ollama-20260705-150053-dd262a5c94593cb4b35bbb3554cc7ed1d608fab8b16160a3215329637c614baa.summary.json`; full bytes remain in two verified archives.

## Build And Test

- Build/syntax: configured in `architrave.config.json`; shell syntax plus Python compilation.
- Recovery tests: analyzer, run-environment, retry-aware report, privacy, promoter, local persistence receipts, command-level scheduler/readiness/retry behavior, doc links, and diff check.
- Full paper gate: `scripts/audit-paper-data.py`, claim/link/privacy checks, isolated notebook verification, Quarto HTML/Typst when changing claim-bearing surfaces.
- Research radar gate: `scripts/test-validate-literature-radar.py` and
	`scripts/validate-literature-radar.py complete --scan-id <scan-id>`; ordinary
	scans fail if canonical literature or paper files change.

## Architecture Map

`home` orchestrates judges/persistence; `home-ai` performs locked local inference. `run.py` emits raw rows, runner shells enforce preflight/reset/provenance, the judge scheduler appends attempts, completed-run promotion produces immutable canonical evidence, and analysis consumes only verified/privacy-cleared bundles.

The literature radar is a separate read-only knowledge lane. It records exact
queries, immutable source versions, claim lineage, negative searches, and dated
synthesis without changing the experiment or canonical paper evidence.

## Recurring Gotchas

- Raw judge attempts may exceed canonical count when parse-failed retries precede one valid success; use the shared judgement contract, not raw row equality.
- Missing Ollama models cannot all be pre-pulled for the 21-model recovery cohort: source artifacts require about 88.7 GiB while the node had about 59 GiB free. Use disk-bounded pull, exact digest verify before inference, and remove only newly pulled models.
- `length` is token-budget censoring, not timeout DNF.
- The source run was Ollama; llama.cpp is a separate runtime condition and covers only a small subset of affected artifacts.
- Launching from dirty or divergent source invalidates clean provenance; use a clean committed checkout and verify `env.harness_*`.
- The timeout recovery uses only the dedicated `experiment/<RUN_ID>` result branch authorized on 2026-07-13; `main`, arbitrary branches, parent evidence, and paper claims remain no-push. `run.meta.persist_mode=git-push` is authoritative, the branch is derived from `RUN_ID`, and consumer/model/receipt/index validation must pass before producer launch or each commit.

## Validated Facts

| Fact | Evidence | Last Checked |
|---|---|---|
| Parent run has 15,200 results and 30,400 canonical judgements plus 41 retries | completed-run bundle gate report | 2026-07-12 |
| Parent DNF = 204 timeout + 4 completion-frame; affected models = 21 | failure analyzer summary and independent raw checks | 2026-07-12 |
| Parent bundle verifies and privacy scan reports zero secret hits | `lock-completed-run.py verify`; `privacy-scan.py` | 2026-07-12 |
| Frozen public paper source remains `data/analysis-manifest.json` | manifest and claim audit | 2026-07-12 |
| Architrave kit copied at v0.10.3 | `gates/.kit-version` | 2026-07-12 |
| Initial research radar validates 29 queries, 42 immutable source versions, 42 scoped claims, and zero promotions | `scripts/validate-literature-radar.py complete --scan-id radar-20260713-initial` | 2026-07-13 |
| Research radar and paper-impact packet are locally preserved with dual-family PASS; canon and active timeout evidence remain unchanged | commits `27ab2c7` and `18ba9c9`; run judge and gate artifacts | 2026-07-13 |

## Last Reviewed

2026-07-13 during Architrave runs `timeout-recovery-20260712` and
`literature-radar-20260713`. Validate facts against the current branch before
reuse.

