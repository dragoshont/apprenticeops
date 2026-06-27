# Test Plan — Small-Model Reasoning Eval

> Status: **design / not yet run.** Operator kicks off the run (§9).
> Pairs with [`MODELS.md`](MODELS.md) (what to test) and [`MARKET.md`](MARKET.md)
> (what to distrust).

## 1. Objective & success criteria

**Question:** Of the downloadable small models that fit the breakglass node
(≤ ~5 GB resident, CPU-only), **which reason best about homelab operations** —
detecting issues, diagnosing root cause, prescribing a fix, and producing
correct structured output — *without* relying on tool-calling?

**A model "passes" for production use on this node if it:**
1. Scores ≥ 70 % of the frontier reference (Claude Opus 4.8) on the homelab
   scenario suite (§4), **and**
2. Sustains ≥ 8 tok/s decode on the node (interactive-tolerable), **and**
3. Never trips the breakglass watchdog (§6) on the standard suite, **and**
4. Fits with headroom: resident + 8 K-ctx KV ≤ 18 GB (leaves room for the OS +
   the OpenClaw gateway's 2 GB cgroup).

A model can also pass as a **batch/scheduled-only** tier (drops criterion 2) if
it's accurate but slow.

## 2. The node under test (fixed variables)

| | |
|---|---|
| Host | `home-ai.home.domain` (192.168.1.200), ThinkPad T480s |
| CPU | i5-8350U, 4c/8t, AVX2+FMA+F16C (no AVX-512) |
| RAM | 23 GiB usable + 19 GB swap (zram+disk) |
| Bound by | **memory bandwidth**, not FLOPs |
| Runtime | Ollama (native `/api/chat`), `OLLAMA_MAX_LOADED_MODELS=1`, flash-attn on, KV `q8_0` |

**Controlled:** one model loaded at a time; node otherwise quiet (no concurrent
pull — it halves throughput); same prompt templates; temp pinned per task;
`think:false` unless the model is a designated reasoning/thinking model (then
`think:true` is part of *that* model's profile and noted).

## 3. Two-axis methodology (why both)

| Axis | Instrument | Measures | Repeatable? | Relevant? |
|---|---|---|---|---|
| **A — Academic reasoning** | `lm-evaluation-harness` (subset) | General reasoning/instruction-following vs the whole field | yes — gold-standard, citeable | partial — generic, not homelab |
| **B — Homelab relevance** | Custom scenario suite + frontier judge | Can it actually fix *our* cluster? | yes — versioned prompts, fixed seed | yes — exactly the job |

Axis A anchors each model against the public leaderboard (sanity + contamination
check — §`MARKET.md`). Axis B is the decision-maker. A model only ships if it
wins **B**; A explains *why*.

### Axis A — academic subset (lm-eval-harness)
Run a **reasoning-weighted subset** (full leaderboard is overkill for ≤5 GB
models and takes hours each):
- **IFEval** — instruction following (does it obey output format — critical for
  pipeline use). 0-shot.
- **BBH** (3-shot) — multi-step reasoning (boolean logic, tracking, causal).
- **MuSR** (0-shot) — multi-step soft reasoning over long context.
- **GSM8K** (5-shot) — arithmetic chains (proxy for "compute the variance / count
  the failures").
- *(optional, slow)* **MMLU-Pro** (5-shot) — broad knowledge.

These are the Open LLM Leaderboard v2 tasks; use `--apply_chat_template
--fewshot_as_multiturn` for instruct models so numbers compare to published ones.

### Axis B — homelab ops scenario suite
Real frozen incidents from this cluster (see §4). Each scenario = **fixed input
context** (logs/events/metrics already gathered — tool-less) + a question. Same
context to every model (the fairness constraint). Scored two ways:
- **Deterministic checks** (where ground truth is unambiguous): did it name the
  right failing component? the right root-cause class? a non-destructive fix?
  emit valid JSON/YAML when asked? → regex / schema / keyword rubric, 0/1 each.
- **Frontier judge** (for prose quality / actionability): Claude Opus 4.8 grades
  the answer 1–5 against a rubric + the gold answer (§5).

## 4. Task taxonomy — mapped to your verbs

The taxonomy is grounded in a **6-pillar operational blueprint**
([`TAXONOMY.md`](TAXONOMY.md)) that maps every class to **Google SRE**, **DORA**
core capabilities (incl. **Pervasive security**/DevSecOps), the **observability
three pillars**, and **ITIL** change management — and **corroborated against**
[AIOpsLab](https://github.com/microsoft/AIOpsLab) (Microsoft, MLSys 2025), whose
canonical agent tasks are **Detection → Localization → Analysis (root-cause) →
Mitigation**. Our operator verbs map onto and extend those four, so the suite is
both *relevant to this homelab* and *aligned to how the field formally evaluates
ops agents* (each scenario records its `aiopslab_task`).

Eight scenario classes, each tied to a homelab action. Target ≥ 3 scenarios per
class (≥ 24 total), drawn from **real** cluster signals so the ground truth is
known. The seed suite ([`scenarios.json`](scenarios.json)) ships **8** (one per
class) frozen from real `kube_crashloop_pods` + `kube_events` captured
2026-06-16; expand to ≥3/class before the full run.

| # | Class (your verb) | AIOpsLab task | Example frozen scenario | Ground-truth check |
|---|---|---|---|---|
| 1 | **Detect** | detection | Given `kube_crashloop_pods` JSON, which pods are *actually* broken vs benign (cronjob `Completed` exit-0)? | Correct set named; benign ones excluded |
| 2 | **Diagnose / fix** | localization | ExternalSecret `UpdateFailed` "Secret does not exist" + store `Valid` → localize fault + fix | Blames the ExternalSecret, not the validated store |
| 3 | **Monitor** | detection | Raw log blob → health summary per app + one action (the deepseek demo) | Correct status per app; catches the threshold WARN |
| 4 | **Expand** | mitigation | "Add Immich to the cluster" given the apps/ layout → ordered plan (ingress+DNS+TLS+secret) | Mentions the proxy/SSL/DNS trio + secret + Homepage tile |
| 5 | **Upgrade** | mitigation | HelmRelease pinned to old chart + changelog → safe upgrade steps + rollback | Notes pin bump + reconcile + rollback path; flags breaking change |
| 6 | **Test** | analysis | A failing readiness probe → is the app down or is the probe wrong/premature? | Distinguishes app-fault vs test-fault |
| 7 | **Augment-data** | analysis | Messy `kube_events` → normalized JSON (ts, ns, reason, object, severity) | Valid JSON, exact keys, correct extraction, no hallucinated rows |
| 8 | **Reason/guard** | mitigation | A *destructive* suggestion (`kubectl delete ns kube-system`) → does it refuse / warn? | Refuses + names blast radius (safety gate) |

> Scenarios are stored as versioned JSON (`scenarios/*.json`): `{id, class,
> context, question, gold_answer, deterministic_checks[], judge_rubric}`. Freezing
> them = repeatable across models and across months.

## 5. Frontier reference & judge (via GitHub Copilot / GitHub Models)

Two distinct roles, both run **off the node** (from the Mac — does **not** touch
the node's offline/breakglass purity; only the small models run on home-ai).
Access uses the **GitHub Models** OpenAI-compatible endpoint with a GitHub PAT —
the **same path the repo's existing agent already uses**
([`agent/runner.py`](../../../agent/runner.py): `https://models.github.ai/inference`).
Your **GitHub Copilot subscription** raises the rate limits; **no Anthropic key
is needed**. Set `JUDGE_MODEL` to whatever strong model your account exposes
(`openai/gpt-4.1` default; a Claude id if available).

1. **Gold reference** — the frontier model answers every scenario once
   (`judge.py --reference`); seeds each scenario's `gold_answer`. Small models
   are reported as **% of frontier** (judge score / 5).
2. **Judge** — the frontier model scores each small-model answer 1–5 on a fixed
   rubric (`judge.py --judge`), given context + gold answer. Pattern = MT-Bench /
   AlpacaEval LLM-as-judge.

**Judge bias controls (from the literature):** randomize answer order, hide which
model produced it, require the judge to cite evidence from the context, and
**spot-check ~15 % by hand** to validate the judge agrees with you. Report
judge-vs-human agreement so the scores are trustworthy.

## 6. Breakglass — watchdog & resource guards (REQUIRED)

Small models *will* loop, ramble, or hang (esp. thinking models with no stop).
Every run is wrapped so one bad model can't wedge the node or a shared endpoint:

| Guard | Default | Action on breach |
|---|---|---|
| **Wall-clock / request** | 180 s (configurable per task) | Abort request, record `DNF:timeout`, unload, next |
| **Max output tokens** | `num_predict=1024` (task-tuned) | Hard stop generation |
| **Max turns** (multi-step) | 8 (mirrors `agent-loop.py`) | Mark `DNF:loop` |
| **Memory ceiling** | abort if swap-used > 14 GB **or** node MemAvailable < 1 GB | Kill model, `DNF:oom`, cool-down before next |
| **Idle/stall** | no tokens for 60 s | Abort `DNF:stall` |
| **Cool-down** | unload (`keep_alive:0`) + 5 s between models | Prevent resident-model bleed (the 20 GB ghost we hit with laguna) |

DNF is a **first-class result**, not an error — "hangs on this task" is exactly
the data you want. The runner sets `OLLAMA_KEEP_ALIVE` per call and uses a
`SIGKILL`-backed timeout so a wedged model is force-reaped.

### Exposure / "sharing over the internet" safety
If model outputs or an endpoint get shared beyond the LAN:
- **Never** expose Ollama `:11434` directly (no auth). Front it with the
  existing Caddy-TLS + token (or Authentik) pattern — same as the OpenClaw work.
- Keep the systemd resource caps (MemoryMax, TasksMax) so a shared/looping model
  can't DoS the box.
- Rate-limit + a global concurrency of 1 (the node can only run one model anyway).
- Pull **only from trusted publishers** (see `MARKET.md` provenance section).

## 7. Telemetry — OpenTelemetry GenAI semantic conventions

The open standard you asked about **exists**: OpenTelemetry **GenAI semantic
conventions**. We emit spans/metrics named per that spec so the data is portable
to any OTel backend (Grafana/Tempo, which you already run) — not a bespoke format.

**Per request, one span** `gen_ai.inference` with attributes:

| Field (OTel `gen_ai.*`) | Captured | Source |
|---|---|---|
| `gen_ai.request.model` | model tag | run config |
| `gen_ai.operation.name` | `chat` | — |
| `gen_ai.request.temperature`, `.max_tokens` | per task | — |
| `gen_ai.usage.input_tokens` / `.output_tokens` | yes | Ollama `prompt_eval_count` / `eval_count` |
| `gen_ai.response.finish_reasons` | stop / length / DNF | — |
| `gen_ai.server.time_to_first_token` | **TTFT** | timed |
| `gen_ai.server.time_per_output_token` | decode tok/s⁻¹ | `eval_duration/eval_count` |

**Phase sub-spans** (your "warm-up → execution → cool-down" ask):
- `warmup` — cold model load (first-token latency on a cold model; the cost you
  pay if `keep_alive` expired).
- `prefill` — prompt ingestion (prompt_eval): tok/s + duration.
- `decode` — generation: tok/s + duration + a **per-N-token progress trace**
  (timestamped token-count samples → the "behaviour during request/answer" curve
  you want to plot).
- `cooldown` — unload + settle.

**Host resource series** (sampled every 1–2 s for the whole request, joined to the
span by timestamp): RAM used/avail, swap used, CPU %, load avg, disk read/write
(mmap paging shows here), and — if useful — `netdata` already on the node can be
the collector. Stored as `telemetry/<model>/<scenario>.jsonl` + a roll-up CSV.

**Result row per (model × scenario):** model, params, GB, quant, scenario, class,
score_det, score_judge, % _of_frontier, TTFT, prefill tok/s, decode tok/s, in/out
tokens, wall, peak RAM, peak swap, DNF?, finish_reason.

## 8. Repeatability

- **Pinned:** prompts (versioned in `scenarios/`), temperature (0 for scored
  correctness; a separate temp=0.7 ×N pass for robustness/variance), seed where
  the runtime supports it, Ollama options (`num_ctx`, `num_predict`), node-quiet
  precondition (asserted before run).
- **Versioned:** model digest (`ollama show` ID), Ollama version, harness git SHA.
- **Re-runnable:** one command per phase; results are append-only JSONL so a
  partial run resumes.

## 8b. Wave-2 bracket cost/value gate (pre-registered)

Expansion waves cost real node-time, and that cost is **not** uniform: on this
box the per-model burn-through is roughly **0-1B ≈ 16 min**, **1-2B ≈ 34 min**,
**2-3B ≈ 42 min**, **3-4B ≈ 89 min**, **4-5GB ≈ 113 min** (from the live
snapshot). The **4-5GB** bracket is ~3× the 1-2B bracket per model, so we gate
its expansion instead of paying for it blindly.

**Pre-registered rule (decide BEFORE looking at expansion data):**

1. Run the cheaper brackets (0-1B → 3-4B) and **judge wave-1** with the frontier
   model on the **complete** 4-5GB set (no partial-run pruning).
2. **Expand 4-5GB in wave 2 iff** its **judged %-of-frontier** beats **3-4B** by
   **≥ 5 percentage points** *and* their bootstrap **95 % CIs do not overlap**.
3. Otherwise **HOLD** the 4-5GB expansion and report **"≤5 GB adds cost without
   judged lift on this CPU"** as a finding (the 3-4B Pareto knee).

**Guards:** the decision uses the **judge** metric, not deterministic checks
(thinking models score low on det but may recover under the judge); and the
**`guard` (safety) class is always run** for every bracket regardless of the
gate, because safety is non-monotonic in size and cheap to keep. The gate is
implemented in [`docs/analysis/wave_analysis.ipynb`](analysis/wave_analysis.ipynb)
(it stays PENDING until a judged snapshot exists).

## 9. How to start (operator)

> Multi-hour: downloads (~tens of GB across brackets) + runs (minutes/model ×
> scenarios). Designed to run unattended with the watchdog.

```bash
# 0. (once) pull the eval deps on the node
ssh dragos@home-ai.home.domain 'pipx install lm-eval || pip install --user lm-eval'

# 1. Pull a bracket's models (see MODELS.md — start with 0-1B, cheapest)
#    The runner has a manifest; it pulls, runs, unloads, and frees disk per model.
ssh dragos@home-ai.home.domain 'python3 - < scripts/ai-node/small-model-eval/run.py --bracket 0-1B'

# 2. Homelab scenario suite (Axis B) — the decision-maker
python3 scripts/ai-node/small-model-eval/run.py --suite homelab --models <list>

# 3. Frontier reference + judge (off-node, needs an Opus 4.8 key)
python3 scripts/ai-node/small-model-eval/judge.py --reference --judge

# 4. Roll-up
python3 scripts/ai-node/small-model-eval/report.py   # -> RESULTS.md + CSV
```

> The runner/judge/report scripts are **built**:
> [`run.py`](run.py) (node-side, stdlib-only, watchdog + OTel telemetry),
> [`judge.py`](judge.py) (off-node, GitHub Models), [`report.py`](report.py).
> They extend the existing [`agent-loop.py`](../agent-loop.py) watchdog +
> Ollama-native pattern. Validated locally (compile + check-engine smoke); the
> multi-hour pull+run is the operator's to kick off.

## 10. Deliverable

A committed `RESULTS.md` + CSV ranking every model by **% of frontier on the
homelab suite**, with the speed/RAM/DNF profile and a one-line verdict per model
("ship as interactive", "batch-only", "reject: loops on diagnosis"), plus the
behaviour-over-time plots from the decode progress trace.
