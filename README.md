# ApprenticeOps

**Evaluating Small Locally-Run LLMs as Homelab Operations Assistants**

> *Your 3 GB model doesn't have Copilot's AGI. So we measured what it actually does.*

## What is ApprenticeOps?

This is an **open, reproducible benchmark** for evaluating small, locally-run LLMs (≤ ~5 GB) as **homelab and edge operations assistants**—detecting failures, diagnosing incidents, planning fixes, and *safely refusing* to break things.

Unlike existing AIOps benchmarks that assume frontier models with unlimited compute and external APIs, **ApprenticeOps measures the ceiling of what small models can do offline**: 
- No escalation to Claude / GPT / Azure AI.
- No live fault injection or golden answers from human operators.
- Just a 2018 ThinkPad, Ollama, and 404 real homelab incidents.

The research question: **where does a 0.5–5 GB local model hit the wall?** And more usefully: *which bracket is worth your disk space and latency budget?*

## The core insight: "offline" is not information-starvation

| Crutch | Online agents use | Local-sovereign equivalent |
|--------|-------------------|---------------------------|
| **Escalate to frontier** | "I'll call Claude if stuck" | Model must decide alone. No second opinion. |
| **External docs** | Web search, vendor changelogs | **Local RAG, in-org MCP servers, runbooks** (allowed). |
| **On-demand telemetry** | "Fetch more logs" | **Operator/harness retrieves**; model reasons over it. |

So "offline" isn't dumb—it just redraws the lines: *retrieval is the operator's job; reasoning is the model's.*

## What we measure

- **7 research questions** on reasoning, safety, grounding, speed, and energy across size brackets.
- **Real incident scenarios** (404 of them) from a production homelab, labelled by difficulty and task class.
- **Two grounding modes**: closed-book (in-weights knowledge only) and grounded (simulated RAG upper bound).
- **Deterministic + variance passes** with 95% confidence intervals.
- **System telemetry** (OTel GenAI, RAPL energy, RAM/swap, CPU microarch counters) so you see *why* a model is fast or slow.
- **Safety-by-default checks** (does it refuse to delete production namespaces?).

## Key documents

| Doc | Purpose |
|-----|---------|
| [`PAPER.md`](PAPER.md) | **Experimental design spec** — read this first for the science (RQs, threats, stats plan). |
| [`REPRODUCE.md`](REPRODUCE.md) | **Reproducibility contract** — clone, run, regenerate every number. Covers dependencies, commands, pinning, and caveats. |
| [`MODELS.md`](MODELS.md) | The vetted model list — size, quant, license, capability, source for every model tested. |
| [`PLAN.md`](PLAN.md) | Operational how-to — task taxonomy, scoring logic, judge backend, watchdog, repeatability. |
| [`MARKET.md`](MARKET.md) | Adversarial take — reasoning claims in the wild, benchmark contamination, supply-chain risks. |

## Quick start

**Clone & smoke-test (5 min):**
```bash
git clone https://github.com/dragoshont/apprenticeops.git && cd apprenticeops
ollama --version                # >= 0.30
python3 run.py --help           # stdlib-only harness
python3 baselines.py --out /tmp/bl.jsonl   # sanity check (no model)
```

**Pilot run — one model, all scenarios (~5 min):**
```bash
printf '# bracket: 0-1B\nqwen2.5:0.5b\n' > one.txt
python3 run.py --models one.txt
# See per-scenario det=x/y tok/s, and results.jsonl with OTel fields.
```

**Full powered run (hours to days):**
```bash
python3 run.py --models models.txt --temp 0 --repeats 1 --out results.det.jsonl  # deterministic
python3 run.py --models models.txt --temp 0.7 --repeats 5 --out results.var.jsonl  # variance + CIs
```

See [`REPRODUCE.md`](REPRODUCE.md) for the full pipeline (lock the node, judge, report, extract data for ML).

## The AIOps maturity ladder (and where this fits)

```
Autonomous   ← preventive action, closed-loop, no human in the loop
Predictive   ← forecast failures before they happen
Preventive   ← act to prevent known failure modes
Proactive    ← act ahead of user request
Reactive     ← respond to alerts/incidents
           ↑ This paper measures the bottom rungs.
```

An apprentice starts **reactive** (detect/diagnose/test/augment) and earns its way toward higher rungs. This benchmark proves whether it has the *foundation* to get there.

## What you get

- **Artifact**: the harness + scenario suite + telemetry schema. *This is the primary contribution.*
- **Dataset**: 404 results across 25 models (0.5–8B) with per-task accuracy, speed, energy, and safety labels. Ready for your own ML analysis.
- **Reference runs**: reproducible results + ENVIRONMENT.md pinning (CPU, Ollama version, model digests) so a stranger with Ollama can regenerate every number.

## Caveats (state upfront, as is right)

1. **Judge egress**: we use Claude 4.8 to *score* answers. The system-under-test (your model) never calls it—but the judge *sees* the scenario text (real cluster names, Azure Key Vault, etc.). Released scenarios are scrubbed. See [`PAPER.md` §0b](PAPER.md#0b-public-service-dependency-map).
2. **Grounded = oracle retrieval**: we inject the *correct* reference text directly. Real RAG adds retrieval error, so grounded numbers are the **ceiling**, not expected value.
3. **Telemetry needs Linux**: `/proc` reads for RAM/swap. macOS/Windows runs work for quality; energy series will be empty.
4. **CPU-only inference**: this measures the *floor* of local inference (no GPU). With a local GPU you'd see faster speeds and different thermal patterns.

## Standards this uses

- **Telemetry**: [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai) — the open standard for model-execution tracing.
- **Reasoning eval**: [EleutherAI lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) — the engine behind HuggingFace Open LLM Leaderboard.
- **Relevance scoring**: frontier LLM-as-judge, the MT-Bench / AlpacaEval pattern.

## Citation

```bibtex
@misc{apprenticeops2026,
  title={ApprenticeOps: Evaluating Small Locally-Run LLMs as Homelab Operations Assistants},
  author={Hont, Dragos},
  year={2026},
  note={Open benchmark and reproducible study. GitHub: dragoshont/apprenticeops}
}
```

(Update with venue + DOI after acceptance.)

## License

Apache 2.0. See [`LICENSE`](LICENSE).

---

**Questions?** File an issue. **Want to contribute a model or scenario?** PRs welcome. **Found a bug in the harness?** Let's fix it together.

**Next: read [`PAPER.md`](PAPER.md) to understand the research questions, or [`REPRODUCE.md`](REPRODUCE.md) to run it yourself.**
