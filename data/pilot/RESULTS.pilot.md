# Small-Model Reasoning Eval — Results

_25 models × 8 scenarios. Ranked by % of frontier (judge/5). See PLAN.md for method._

| Model | Bracket | det | det 95%CI | judge/5 | % frontier | closed-book | grounded | paired RAG lift | tok/s | warmup | peak swap MB | DNF | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ministral-3:3b | 2-3B | 0.958 | 0.882–1.035 | None | None | None | None | None | 8.1 | 20.01 | 1402 | 0 | marginal (extraction/format only) |
| qwen3:4b-instruct-2507-q8_0 | 4-5GB | 0.927 | 0.838–1.016 | None | None | None | None | None | 4.8 | 3.78 | 1402 | 0 | marginal (extraction/format only) |
| qwen3:4b-instruct-2507-q4_K_M | 3-4B | 0.917 | 0.764–1.069 | None | None | None | None | None | 8.0 | 3.72 | 1402 | 0 | marginal (extraction/format only) |
| qwen2.5:7b | 4-5GB | 0.917 | 0.764–1.069 | None | None | None | None | None | 4.5 | 7.69 | 1402 | 0 | marginal (extraction/format only) |
| qwen2.5:3b | 2-3B | 0.865 | 0.769–0.96 | None | None | None | None | None | 9.8 | 3.77 | 1402 | 0 | marginal (extraction/format only) |
| gemma2:2b | 2-3B | 0.854 | 0.699–1.009 | None | None | None | None | None | 10.7 | 3.14 | 1402 | 0 | marginal (extraction/format only) |
| granite4:tiny-h | 4-5GB | 0.854 | 0.699–1.009 | None | None | None | None | None | 15.9 | 8.8 | 1402 | 0 | marginal (extraction/format only) |
| qwen3:1.7b | 1-2B | 0.823 | 0.649–0.997 | None | None | None | None | None | 17.6 | 2.01 | 1402 | 0 | marginal (extraction/format only) |
| stablelm2:1.6b | 1-2B | 0.823 | 0.672–0.974 | None | None | None | None | None | 21.3 | 1.44 | 1402 | 0 | marginal (extraction/format only) |
| phi4-mini | 3-4B | 0.823 | 0.672–0.974 | None | None | None | None | None | 7.6 | 3.84 | 1402 | 0 | marginal (extraction/format only) |
| llama3.2:3b | 3-4B | 0.823 | 0.672–0.974 | None | None | None | None | None | 9.9 | 3.74 | 1402 | 0 | marginal (extraction/format only) |
| mistral:7b-instruct-q4_K_M | 4-5GB | 0.823 | 0.649–0.997 | None | None | None | None | None | 4.9 | 5.72 | 1402 | 0 | marginal (extraction/format only) |
| granite4:micro | 2-3B | 0.812 | 0.658–0.967 | None | None | None | None | None | 8.9 | 5.59 | 1402 | 0 | marginal (extraction/format only) |
| smollm2:1.7b | 1-2B | 0.792 | 0.583–1.0 | None | None | None | None | None | 11.3 | 1.59 | 1402 | 0 | marginal (extraction/format only) |
| gemma3:4b-it-qat | 3-4B | 0.792 | 0.623–0.96 | None | None | None | None | None | 6.2 | 4.56 | 1402 | 0 | marginal (extraction/format only) |
| qwen2.5:1.5b | 1-2B | 0.781 | 0.611–0.952 | None | None | None | None | None | 19.1 | 2.14 | 1402 | 0 | marginal (extraction/format only) |
| qwen3:0.6b | 0-1B | 0.76 | 0.559–0.961 | None | None | None | None | None | 40.7 | 1.36 | 1402 | 0 | marginal (extraction/format only) |
| llama3.2:1b | 0-1B | 0.719 | 0.527–0.91 | None | None | None | None | None | 15.4 | 1.89 | 1402 | 0 | marginal (extraction/format only) |
| qwen3:4b | 3-4B | 0.698 | 0.478–0.918 | None | None | None | None | None | 6.8 | 4.48 | 1402 | 0 | marginal (extraction/format only) |
| qwen2.5:0.5b | 0-1B | 0.615 | 0.356–0.873 | None | None | None | None | None | 44.3 | 1.19 | 1402 | 0 | marginal (extraction/format only) |
| granite4:1b-h | 0-1B | 0.583 | 0.354–0.812 | None | None | None | None | None | 13.2 | 1.75 | 1402 | 0 | reject (weak reasoning) |
| smollm2:360m | 0-1B | 0.562 | 0.278–0.847 | None | None | None | None | None | 29.4 | 0.75 | 1402 | 0 | reject (weak reasoning) |
| deepseek-r1:1.5b | 1-2B | 0.552 | 0.268–0.836 | None | None | None | None | None | 19.4 | 1.9 | 1402 | 0 | reject (weak reasoning) |
| deepseek-r1:7b | 4-5GB | 0.437 | 0.201–0.673 | None | None | None | None | None | 4.5 | 6.65 | 1402 | 2 | reject (weak reasoning) |
| phi:2.7b | 2-3B | 0.125 | 0.013–0.237 | None | None | None | None | None | None | 1.72 | 1402 | 8 | reject (weak reasoning) |

## Notes

- **det** = mean deterministic-check pass rate (0-1). For the `capacity`/`foresee` classes the det checks measure answer **shape** (mentions a rate/timeframe/proactive action), not numeric correctness — the judge carries correctness there.
- **det 95%CI** = bootstrap CI of the mean (normal-approx if numpy absent).
- **% frontier** = judge score / 5 (frontier reference = the configured judge; default `copilot:claude-opus-4.8` — see `judge.py --backend`).
- **paired RAG lift** = within-pair grounded−closed-book det on the SAME task (doc on/off); the clean RAG estimate. The bare closed-book/grounded columns are whole-class means and are **confounded** by task difficulty — do not read them as a retrieval effect.
- **DNF** = timeout/stall/oom/loop count (breakglass watchdog).
- The `guard` safety gate is **judge-primary** (majority of unsafe reps → REJECT); the `must_not_endorse` check is the sound fallback when the judge hasn't run.
- Telemetry per request (TTFT, prefill/decode tok/s, RAM/swap series, progress trace) is in results.jsonl, OTel gen_ai.* **schema-aligned** (local JSONL; no exporter wired).

## Per-task-taxonomy scores (det mean, by class)

Each cell = mean deterministic score for that model on that task class. Read columns to see which *task types* small models handle vs fail.

| Model | Bracket | augment | detect | diagnose | expand | guard | monitor | test | upgrade |
|---|---|---|---|---|---|---|---|---|---|
| ministral-3:3b | 2-3B | 1.0 | 1.0 | 1.0 | 1.0 | 0.67 | 1.0 | 1.0 | 1.0 |
| qwen3:4b-instruct-2507-q8_0 | 4-5GB | 1.0 | 1.0 | 1.0 | 0.75 | 0.67 | 1.0 | 1.0 | 1.0 |
| qwen3:4b-instruct-2507-q4_K_M | 3-4B | 1.0 | 1.0 | 1.0 | 1.0 | 0.33 | 1.0 | 1.0 | 1.0 |
| qwen2.5:7b | 4-5GB | 1.0 | 1.0 | 1.0 | 1.0 | 0.33 | 1.0 | 1.0 | 1.0 |
| qwen2.5:3b | 2-3B | 0.75 | 1.0 | 1.0 | 0.75 | 0.67 | 1.0 | 1.0 | 0.75 |
| gemma2:2b | 2-3B | 0.75 | 1.0 | 1.0 | 0.75 | 0.33 | 1.0 | 1.0 | 1.0 |
| granite4:tiny-h | 4-5GB | 0.75 | 1.0 | 1.0 | 0.75 | 0.33 | 1.0 | 1.0 | 1.0 |
| qwen3:1.7b | 1-2B | 1.0 | 1.0 | 1.0 | 0.5 | 0.33 | 1.0 | 1.0 | 0.75 |
| stablelm2:1.6b | 1-2B | 0.75 | 1.0 | 1.0 | 0.75 | 0.33 | 1.0 | 1.0 | 0.75 |
| phi4-mini | 3-4B | 0.75 | 1.0 | 1.0 | 0.75 | 0.33 | 1.0 | 1.0 | 0.75 |
| llama3.2:3b | 3-4B | 0.75 | 1.0 | 1.0 | 0.75 | 0.33 | 1.0 | 1.0 | 0.75 |
| mistral:7b-instruct-q4_K_M | 4-5GB | 1.0 | 1.0 | 1.0 | 0.5 | 0.33 | 1.0 | 1.0 | 0.75 |
| granite4:micro | 2-3B | 1.0 | 0.67 | 1.0 | 1.0 | 0.33 | 0.75 | 1.0 | 0.75 |
| smollm2:1.7b | 1-2B | 0.75 | 1.0 | 1.0 | 1.0 | 0.33 | 1.0 | 1.0 | 0.25 |
| gemma3:4b-it-qat | 3-4B | 0.75 | 1.0 | 1.0 | 1.0 | 0.33 | 0.75 | 1.0 | 0.5 |
| qwen2.5:1.5b | 1-2B | 0.75 | 0.67 | 1.0 | 0.5 | 0.33 | 1.0 | 1.0 | 1.0 |
| qwen3:0.6b | 0-1B | 0.75 | 1.0 | 1.0 | 0.25 | 0.33 | 1.0 | 1.0 | 0.75 |
| llama3.2:1b | 0-1B | 1.0 | 0.67 | 1.0 | 0.75 | 0.33 | 0.75 | 1.0 | 0.25 |
| qwen3:4b | 3-4B | 0.0 | 0.67 | 1.0 | 0.75 | 0.67 | 1.0 | 1.0 | 0.5 |
| qwen2.5:0.5b | 0-1B | 1.0 | 1.0 | 0.67 | 0.25 | 0.0 | 0.25 | 1.0 | 0.75 |
| granite4:1b-h | 0-1B | 0.75 | 0.33 | 1.0 | 0.0 | 0.33 | 0.75 | 1.0 | 0.5 |
| smollm2:360m | 0-1B | 0.25 | 1.0 | 1.0 | 0.75 | 0.0 | 0.0 | 1.0 | 0.5 |
| deepseek-r1:1.5b | 1-2B | 0.0 | 1.0 | 0.33 | 0.0 | 0.33 | 1.0 | 1.0 | 0.75 |
| deepseek-r1:7b | 4-5GB | 0.0 | 0.33 | 1.0 | 0.0 | 0.33 | 0.75 | 0.33 | 0.75 |
| phi:2.7b | 2-3B | 0.0 | 0.33 | 0.33 | 0.0 | 0.0 | 0.0 | 0.33 | 0.0 |

### Task-class difficulty (mean det across all real models, baselines excluded)

| Class | aiopslab_task | mean det | n models | hardest? |
|---|---|---|---|---|
| guard | mitigation | 0.346 | 25 |   <-- hardest |
| expand | mitigation | 0.62 | 25 |  |
| augment | analysis | 0.7 | 25 |  |
| upgrade | mitigation | 0.71 | 25 |  |
| monitor | detection | 0.84 | 25 |  |
| detect | detection | 0.867 | 25 |  |
| diagnose | localization | 0.933 | 25 |  |
| test | analysis | 0.947 | 25 |  |

## Statistics (pre-registered: see PAPER.md §5)
- Judge-ensemble κ: add a 2nd judge family with `judge.py --ensemble` (not yet present).
- Install `numpy`+`scipy` (off-node) for bootstrap CIs and the Friedman test.
