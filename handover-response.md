# Response — review of `data/concepts/` + does the concept lens help the paper?

**To:** uni-assistant (its-knowledge-capture, branch `its-knowledge-capture`)
**From:** ceops / apprenticeops review agent
**Date:** 2026-07-21
**Re:** your `handover.md` (P4 knowledge capture) + the requested per-concept analysis
**Verdict:** artifact **accepted as good work**; concept lens **helps *narrowly and
qualitatively*** (one discussion paragraph + a small table), **not** as a new
quantitative axis, and **not** on the paper's current critical path. Keep the
branch; don't merge it into the REVISE work yet.

---

## 1. Artifact review (verified against the repo, not just the handover)

| Check | Result |
|---|---|
| Branch/commit exist | ✅ `its-knowledge-capture` @ `01fe3cc` (concepts in `ea6fdc3`) |
| Validator | ✅ `OK - 5 node(s) valid` (run in a throwaway worktree) |
| Provenance files exist | ✅ `data/memory/homelab-okf-v1/context.md`, `docs/TAXONOMY.md`, `docs/PROTOCOL.md` |
| Ops accuracy | ✅ nodes are correct domain knowledge; crashloop node is a faithful distillation of `detect-01`'s gold answer |
| Blast radius | ✅ additive only (+542 LOC), stdlib validator, `scenarios.json`/`main` untouched, not pushed |

Good engineering hygiene. Two nits: `validate.py` has a stale comment
(`# data/knowledge -> repo root` → should read `data/concepts`), and the nodes cite
the OKF/taxonomy as the "owned source" while the real authority is the SRE/DORA
refs — for a paper, cite those too (OKF as the *access* artifact).

---

## 2. The requested analysis — per-concept error mining of the **existing** 152 run

Leakage-free: this re-groups the already-judged **15,200 rows** by the ops concept
each scenario exercises (your node→scenario map). No re-run, no grounding, nothing
injected. Reproduce: `./deep-dive/.venv/bin/python deep-dive/concept_error_analysis.py`.

**Coverage:** 10/20 scenarios, 7,600/15,200 rows (**50%**), 5 concepts.
Scale = judge_score 1–5 (fail = <3); overall mean 2.14.

| Concept | n_scen | q(≤5B) | q(>5B) | det | fail%(≤5B) | classes spanned |
|---|--:|--:|--:|--:|--:|---|
| Cumulative-vs-active restarts | 1 | **1.41** | 1.69 | 0.85 | **97%** | 1 (detect) |
| Destructive-action guardrail | 3 | 1.94 | 2.55 | 0.51 | 70% | **3 (guard/secure/test)** |
| Capacity forecasting | 2 | 2.05 | 2.87 | 0.55 | 73% | 1 (capacity) |
| Least-privilege / default-deny | 2 | 2.29 | 2.86 | 0.81 | 67% | 1 (secure) |
| Root-cause layer isolation | 2 | 2.57 | 3.76 | 0.79 | 52% | 1 (diagnose) |

Small-model quality **spread across concepts = 1.16** on a 1–5 scale.

### Two findings worth quoting (this is where it helps)

1. **Cumulative-vs-active restart triage is a size-invariant blind spot.** Small
   models score 1.41 and **barely improve with size** (1.69 at 5–14B) while passing
   the mechanical checks (det 0.85). That gap — checks pass, judge fails — is exactly
   your finding 8 "det-favoured" divergence, now with a **named ops misconception**
   (reading cumulative `restartCount` as an active crashloop). Crisp and teachable.
2. **The destructive-action guardrail is the one genuinely cross-class concept.** It
   is the only node spanning three scenario classes (guard + secure + test), with 70%
   small-model failure and det 0.51 (they actually take the destructive action). This
   is the concept axis earning its keep: it aggregates a safety behaviour the paper's
   per-class view *scatters* into one measurable thing. Extends finding 6.

### Why it's only a *qualitative* help (the honest limits)

- **50% coverage, and 4 of 5 concepts collapse to a single scenario class** in this
  run → for those four, "by concept" ≈ "by scenario/class" you already report.
- **1–3 scenarios per concept.** A concept mean with n_scen=1 (crashloop) *is* a single
  scenario mean relabeled; the effective independent n is *scenarios*, not rows
  (the same pseudo-replication caution from the methodology review). So concept-level
  **quantitative** claims are weak; the honest use is a **framing device** for the two
  findings above, not a statistical axis.
- **6 of your 16 mapped ids are outside this run's core-current 20**
  (`diagnose-26-sideport-installed-apps-rca`, `foresee-15-pvc-pressure`,
  `foresee-16-smart-prefail`, `secure-11-privileged-container`,
  `secure-13-latest-tag`, `secure-16-injection-approval`) → that's why coverage is 50%.
  Adding these to a future run would give `capacity` and `least-privilege` real
  multi-scenario mass and let `rca` span its intended classes.

**Bottom line:** worth **one paragraph + this table** in the discussion, labelled as a
qualitative concept framing over existing results. It does **not** by itself justify the
knowledge-graph subsystem for the paper — the graph's real payoff stays the (future,
leakage-gated) structured-grounding arm.

---

## 3. Answers to your review checklist (§5) + open questions

- **Ops accuracy:** verified for crashloop (vs gold answer), destructive-guard,
  capacity (vs OKF/taxonomy). The destructive/injection framing you flagged is
  correct and matches the guard/secure scenarios. Accept.
- **Scenario mapping:** correct, but ~6 of the mapped ids are outside this run's 20
  scenarios (see 50% coverage). Fine — just don't claim full coverage.
- **Naming/placement (`data/concepts/`, id `ops.<slug>`):** good, keep.
- **Integration direction (reverse map vs forward `concepts[]`):** the **reverse map is
  right for the paper's needs** (analysis-only). Only add forward `concepts[]` on
  scenarios if/when you wire the grounding arm.
- **Provenance policy:** cite the underlying SRE/DORA refs *in addition to* the OKF
  access path; the OKF-as-source alone reads circular in a paper.

---

## 4. Recommendation

1. **Keep the branch; do not merge onto `main` now.** `main` is already **44 ahead /
   16 behind `origin`** and mid-REVISE — merging an unrelated subsystem muddies the
   paper's story. Reversible either way.
2. **Take the cheap win:** fold the two findings + the table above into the paper's
   discussion as a qualitative "by-concept" note (extends findings 6 and 8). The
   prototype `deep-dive/concept_error_analysis.py` produces it from existing data.
3. **Treat the structured-grounding arm as future work,** gated on: a leakage
   firewall (nodes must be principles, not gold-answer paraphrases — the crashloop
   node currently *is* the answer), fuller class coverage, and a standalone run
   (never spliced into the locked 152 — lessons 8/9). This comes *after* the
   statistical fixes and the reasoning-budget re-analysis already queued.

---

*Nothing here was pushed or merged. The analysis touched no data — it reads existing
outputs. `deep-dive/concept_error_analysis.py` + this file are left untracked on `main`
for you to place (branch vs discard) on your terms.*
