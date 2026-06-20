# Reviewing ApprenticeOps — a guide for invited reviewers

Thank you for agreeing to look at this work. This repository is built to be
**easy to review — including with AI assistance — while keeping a human in
charge of the judgement.** This page tells you what the paper claims, what kind
of paper it is, how it was produced, what we are asking you to check, and how to
verify any number for yourself. It is grounded in published reviewing and
preprint standards (sources at the bottom), not in our own preferences.

If you read nothing else, read **§1 (the claim)**, **§4 (what to check)**, and
**§6 (AI-assisted review etiquette)**.

> **TL;DR for the impatient.**
>
> - **Live paper + figures:** <https://dragoshont.github.io/apprenticeops/paper.html>
>   · **compact reviewer page:** <https://dragoshont.github.io/apprenticeops/reviewers.html>
> - **The claim:** a quality × safety × energy benchmark for choosing a small,
>   offline, CPU-only ops LLM. The contribution is the *integration*; the safety
>   result is **corroboration, not discovery** — hold us to that.
> - **Most useful feedback:** the *single change that would raise your score* —
>   file it in one click via the **[structured form](https://github.com/dragoshont/apprenticeops/issues/new?template=reviewer-feedback.yml)**.
> - **Trust:** every number was re-derived from `data/snapshots/` and every
>   citation resolved against arXiv / CrossRef on 2026-06-20 (§5).

---

## 1. What the paper claims (the 90-second version)

**One sentence.** A reproducible benchmark + CPU-telemetry method that profiles
small (0.5–8B), quantized, **fully-offline** local LLMs as homelab/edge ops
assistants on **quality × safety × energy together**, and reduces model choice
to a **measured Pareto front** that the usual proxies (parameter count, benchmark
score, a "reasoning" badge, perplexity) get wrong.

- **The contribution is the integration, not any single axis.** No prior
  benchmark measures judged quality *beside* destructive-action refusal *beside*
  energy (Wh/answer, tok/s-per-watt) for the **offline, CPU-only, ≤8B**
  model-selection decision on commodity hardware and real GitOps incidents. The
  headline result is the **energy × safety × quality Pareto**: 7 of 24 models are
  non-dominated; the "biggest" and "reasoning" picks come out **dominated**.
- **Safety is axis #2, framed as corroboration — not discovery.** That
  reasoning-distillation and quantization degrade destructive-action refusal, and
  that text-refusal ≠ action-refusal, is already established at larger scale
  (GAP, OS-Harm, AgentHarm, Beyond-the-Tip, Q-resafe, Self-Jailbreaking, …). We
  **replicate** it offline, on CPU, at homelab scale. We say so plainly; please
  hold us to *not* overclaiming novelty there.
- **The novelty we do claim** is the regime (offline/CPU/commodity/real-incident)
  and the energy-coupled selection question: *"what does choosing the safe,
  good-enough model cost you in watts and tokens/s?"*

A fuller, balanced gist is in [`docs/PAPER.md`](docs/PAPER.md) (Abstract + §1) and
the positioning decision is recorded in
[`docs/PAPER_POSITIONING.md`](docs/PAPER_POSITIONING.md).

---

## 2. What kind of paper this is, and where it is going

This is an **empirical benchmark / measurement paper** (a dataset-and-method
contribution), not a new-model or new-algorithm paper.

- **First release: arXiv preprint.** Please note that **arXiv is moderated, not
  peer-reviewed** — arXiv states explicitly that "the arXiv moderation process is
  not a peer-review process." arXiv moderators check *scholarly standards*
  (well-prepared sections/figures/tables/references, professional and neutral
  tone), *scholarly interest* (original, significant, no misrepresentation of
  data), *format* (LaTeX preferred), and *rights/licensing*. New submitters may
  need an **endorsement**. Your review is therefore **pre-submission peer
  feedback** — exactly the step arXiv does *not* provide.
- **Intended peer-reviewed venue: the NeurIPS Datasets & Benchmarks (D&B)
  track**, the natural home for a benchmark. Its track-specific bars are relevant
  to your review: **single-blind is allowed**; **code and data must be accessible
  to reviewers at submission time without a personal request** (non-compliance is
  grounds for desk rejection); and datasets need **Croissant** machine-readable
  metadata. Alternates: MLSys / on-device & efficiency workshops.

If you have reviewed for any of these venues, your usual bar applies — this
document just maps it onto this specific artifact.

---

## 3. How this work was produced — human-guided, AI-assisted (disclosure)

In the spirit of transparency (and of arXiv's policy on generative-AI tools):

- **AI tools were used substantially**, under human direction, for drafting prose,
  exploring the literature, writing and refactoring harness/analysis code, and
  preparing figures and tables.
- **A human author directs the work and takes full responsibility for every
  claim, number, and line of code**, irrespective of how it was generated — this
  is exactly what arXiv requires of authors. If a generated artifact is wrong, it
  is the author's error, not the tool's.
- **No AI system is or will be listed as an author** (per arXiv policy).
- Every headline number is **reproducible from released artifacts** (§5), so you
  do not have to trust the prose — you can re-run it.

This is the sense in which the repo is "friendly to AI-assisted review guided by
humans": the work is laid out so that *you*, optionally aided by your own tools,
can verify it quickly — but the accountable party is a person.

---

## 4. What we are asking you to check (review rubric)

We map directly onto the **NeurIPS review dimensions** so your assessment ports to
the intended venue. For each, the specific thing to scrutinise here:

| Dimension | What to check in *this* work |
|---|---|
| **Quality** (sound? claims supported? honest about strengths *and* weaknesses?) | Are the deterministic checks actually judge-free and correct? Do the bootstrap CIs support the bracket/arm claims? Is the quality axis — now the **5-rep × 2-judge ensemble** (cross-judge κ_quad ≈ 0.92) — honest about the *residual* judge↔human uncertainty? |
| **Clarity** (can an expert reproduce from the text?) | Is the sovereign constraint defined unambiguously (offline = no external *model* API, not information-poverty)? Are the Pareto/dominance definitions precise? |
| **Significance** (will others use or build on it?) | Is the offline/CPU/commodity regime + energy-coupled selection useful to practitioners and researchers? Is the released harness reusable? |
| **Originality** (new insight, clearly differentiated, well-cited?) | Is the *integration* genuinely unoccupied by prior work, and is the safety axis honestly scoped as **replication**? Note: per NeurIPS, *"originality does not necessarily require introducing an entirely new method… novel insights by evaluating existing methods… is equally valuable."* Please judge the contribution as an integration/evaluation, and tell us if that integration is **not** novel enough. |
| **Reproducibility** | Can you regenerate a headline number from a clean checkout (§5)? Is anything un-runnable without the specific node disclosed as such? |
| **Limitations & ethics** | Are n=1, judge egress, Linux-only telemetry, and CPU-only scope stated up front? (NeurIPS asks reviewers to **reward**, not punish, honest limitations.) |

**The most useful review** states, concretely, *what single result or change
would raise your score* — that is the feedback we can act on. Vague "needs more
experiments" is hard to use; "the safety arm is n=60 on two models, deepen it or
soften the claim" is gold.

---

## 5. Reproducibility & artifacts (how to verify, safely)

> **Pre-submission verification (2026-06-20).** Every quantitative claim in the
> paper was **re-derived from the committed snapshot** (`data/snapshots/`) by an
> independent clean-room audit, and **every reference was resolved against
> arXiv / CrossRef / Semantic Scholar**. The audit reproduced the quality knee,
> the safety arms, the cross-judge κ_quad = 0.92, and the full 7-of-24 Pareto
> front *exactly*; it also corrected one over-stated safety superlative and
> surfaced an undisclosed served-failure (both fixed). You can repeat it from a
> clean checkout — the figures on the site are generated from the same exports.

The relevant standard is **ACM's Artifact Review & Badging** (Available /
Functional / Reusable / Results Reproduced / Replicated). Where we stand:

- **Available** — code, scenarios, telemetry schema, and the analysis notebook are
  in this public repo (Apache-2.0). The 19 scenarios are human-readable — context,
  task, **gold answer, deterministic checks, and judge rubric** — in
  [`data/SCENARIOS.md`](data/SCENARIOS.md) (generated from `scenarios.json`). For
  the D&B track we will additionally host the dataset on an ML data repository with
  **Croissant** metadata by camera-ready (tracked as an open item, see §7).
- **Functional / Reusable** — the harness is stdlib-first; [`REPRODUCE.md`](REPRODUCE.md)
  lists every command to regenerate every number, plus the node-locking protocol.
  The judge-free **deterministic** safety/quality checks and the analysis in
  [`docs/analysis/wave_analysis.ipynb`](docs/analysis/wave_analysis.ipynb) re-run
  from the committed snapshot (`data/snapshots/`) on any machine with Python +
  pandas + matplotlib — **no special hardware, no model downloads**. The notebook
  also exports machine-readable result tables to [`data/site/`](data/site) and
  builds a static site via `scripts/build-analysis-site.sh` (see
  [`docs/analysis/`](docs/analysis)).
- **Results Reproduced** — the systems telemetry (energy, tok/s, memory bandwidth)
  requires the specific Linux node (RAPL/`/proc`/IMC counters); quality and safety
  scores reproduce anywhere. We disclose exactly which numbers are node-bound.

**Running our code safely.** Following NeurIPS reviewer guidance, treat any
research code as untrusted: run it in a **container, VM, or network-isolated
instance**. The harness makes outbound calls only to your local Ollama and — for
the *judge* step only — to a frontier scoring API; both are disclosed and
optional for reproducing the judge-free numbers.

---

## 6. AI-assisted review etiquette (please read)

We welcome AI-assisted review of this **public** repository — but the
responsibility and the judgement must stay human, and confidentiality rules
differ by context:

- **This repo is public.** Using your own AI tools to help you read the code,
  re-derive a number, or check a proof is fine and encouraged. Nothing here is
  confidential.
- **If you are reviewing a *confidential* venue submission** (e.g., a double-blind
  NeurIPS/ICLR/ACL paper), **do not upload the submission to a public or
  non-privacy-preserving LLM.** Venue confidentiality rules require you to keep
  submissions private and not use them outside the review; uploading to a
  third-party model can breach that. Most venues now state this explicitly.
- **A human must write and stand behind the review.** Superficial, AI-generated
  reviews without human verification are discouraged or banned by major venues and
  are, frankly, worse than no review. Use AI to go *faster* and *deeper*, not to
  outsource the judgement.
- **Disclose** any substantial AI assistance in your feedback if the venue asks —
  the same standard we hold ourselves to in §3.

---

## 7. What is provisional, and known limitations (stated up front)

- **Quality is now the variance pass (no longer provisional).** The judged-quality
  axis is the **5-rep × 2-judge ensemble** (Claude + GPT-5.5; 2,375 judgements;
  cross-judge agreement κ_quad ≈ 0.92, 77 % exact, 99.9 % within-1). It firmed the
  Pareto membership (8 → 7 non-dominated) and *strengthened* the 3–4 B knee — the
  4–5 GB bracket now sits -0.3 pt below 3–4 B (no lift) — without changing the
  structure. What remains open is **judge↔human** agreement and an optional third
  judge for a Fleiss pass.
- **n = 1 environment.** One operator, one cluster, one node (i5-8350U). We frame
  this as a **single-environment case study plus a released harness**, and invite
  re-runs — not a population claim.
- **Judge egress.** Scoring uses an off-node frontier judge that sees scenario
  text; the *system-under-test never calls it*. Released scenarios are
  scrubbed/anonymised; the egress is disclosed.
- **Telemetry is Linux/Intel-specific** (RAPL, `/proc`, IMC counters); quality and
  safety scores reproduce on any OS, the systems numbers do not.
- **Open items toward camera-ready:** Croissant dataset metadata + archival
  hosting (DOI); a judge↔human agreement κ; an optional third judge for a Fleiss
  pass.

---

## 8. What would change our minds (where we most want feedback)

1. Are the top contributions **differentiated enough** from existing AIOps /
   agent-safety benchmarks — i.e., is the *integration* genuinely the white space?
2. Is **any claim over-scoped** versus the evidence (especially the safety arm at
   n=60 / two reasoning models)?
3. **Which single result would you require** to consider this publishable at the
   D&B track?
4. Is the honesty framing (safety = corroboration, not discovery) **convincing, or
   does it undersell / oversell**?
5. Is the **energy axis** a real contribution or a nice-to-have?

---

## 9. How to give feedback

- **Preferred — one click:** the [structured reviewer form](https://github.com/dragoshont/apprenticeops/issues/new?template=reviewer-feedback.yml)
  (area · the finding · the single change that would raise your score · severity).
- A plain [GitHub issue](https://github.com/dragoshont/apprenticeops/issues/new)
  or a pull request is equally welcome.
- New **scenarios, models, and hardware re-runs** are especially welcome — they
  directly attack the n=1 limitation.

Anonymised or attributed, your feedback can be acknowledged in the paper; tell us
your preference.

---

## Standards this guide is grounded in

- **arXiv** — *Moderation* ("not a peer-review process"; scholarly standards,
  interest, format) and the *author generative-AI policy* (disclose substantial
  use; authors bear full responsibility; AI is not an author):
  <https://info.arxiv.org/help/moderation/> · *Submission* (LaTeX preferred,
  endorsement, license): <https://info.arxiv.org/help/submit/>
- **NeurIPS 2025 Reviewer Guidelines** — Quality / Clarity / Significance /
  Originality; reward honest limitations; run code in a sandbox; confidentiality:
  <https://neurips.cc/Conferences/2025/ReviewerGuidelines>
- **NeurIPS 2025 Datasets & Benchmarks Track CFP** — single-blind; code+data
  accessible at submission; Croissant metadata:
  <https://neurips.cc/Conferences/2025/CallForDatasetsBenchmarks>
- **ACM Artifact Review and Badging v1.1** — Available / Functional / Reusable /
  Results Reproduced / Replicated:
  <https://www.acm.org/publications/policies/artifact-review-and-badging-current>

*This document is itself AI-assisted and human-authored, consistent with §3.*
