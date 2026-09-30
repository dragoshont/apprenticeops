# Analysis-closure research shortlist — 2026-09-08

**Scan:** `radar-20260908-analysis-closure`
**Window:** 2026-07-06–2026-09-08 inclusive.
**State:** complete bounded scan, candidate evidence; independent GPT and Claude
content reviews PASS. **No canonical promotion.** See the
[full report](2026-09-08.md) and [completion plan](../../sdd/152-analysis-closure.md).

## What changed

The completion-plan code inspection—not this research scan—reports that 66/250 human items are
enriched and possibly exposed, with context capped at 1,800 characters and answers
at 2,500; it also flags possible bootstrap multiplicity loss and a `pass_1`
aggregation error. **Do not simply finish the remaining packet and call it
independent validation.** The initial recommendation is superseded; its original
snapshot remains in the session research archive, not this repository.

The finite recommendation set is **10 scientific sources** below. The broader
22-source audit inventory is retained for coverage/history, not a reading list or
an expansion of closure requirements.

## What it confirms or contradicts

- Current artifact + measurement-validity positioning is the right fit. Recent
  PPI, omission and scorer-audit work reinforces validity checks, not another
  model sweep.
- High judge agreement does not establish human construct validity. Neither PPI
  nor weighting can recover text hidden from a rater or automatically undo
  exposure to expected scores.
- Bootstrap multiplicities and `pass^1` definitions are **established older
  methods**, not new contributions. Literature does not itself prove a code bug.
- Preserve frozen 94-model / 24-model evidence separately from the provisional
  152-model analysis. No literature source makes the latter validated.

## Ten sources, ordered by closure use

Every row gives its immutable ledger version. Recent preprints are not independent
replications merely because a repository exists.

| Priority / source and primary URL | Date / evidence status / immutable version | Use and transfer limit |
|---|---|---|
| 1. [Human-evaluation best practices](https://aclanthology.org/W19-8643/) | **Older accepted INLG 2019**; `doi:10.18653/v1/w19-8643@doi-version-2019-proceedings` | Explicit criteria, participants, presentation/order effects and reporting. Supports redesigning the human protocol; gives no universal sample size or clipping-bias effect. Date fields use the October 28 conference start, not a proven online-release day. |
| 2. [Which Metrics Save the Most Human Annotation?](https://arxiv.org/abs/2608.26638v2) | First Aug 27 / v2 Aug 30, **2026 preprint**; `arxiv:2608.26638@arxiv-v2` | Human-corrected estimates and paired comparisons. WMT experiments; labelled-data sampling assumptions must be revisited for clustered/enriched data. PPI is optional after valid human labels, not a substitute for them. |
| 3. [ARES](https://arxiv.org/abs/2311.09476v2) | **Older context**, 2023 work / Mar 31, 2024 v2; `arxiv:2311.09476@arxiv-v2` | Human correction of automated RAG evaluation. Its annotation count is not a guaranteed sample size for this corpus. |
| 4. [LLM Judges Verify Presence, Not Absence](https://arxiv.org/abs/2608.31016v1) | Aug 31, **2026 preprint**; `arxiv:2608.31016@arxiv-v1` | Holistic judges can miss omissions; motivates criterion-level visibility checks. Clinical domain, no external human anchor for the omission arm, failed threshold transfer to real vendor notes. No direct ops effect size. |
| 5. [Bootstrapping data arrays of arbitrary order](https://arxiv.org/abs/1106.2125v3) | **Older accepted Annals of Applied Statistics 2012**, Sep 27 v3 reprint; `arxiv:1106.2125@arxiv-v3` | Resample factor weights and retain their products in the statistic. Dependence/estimand matter. No universal coverage guarantee for a 20-scenario corpus or nonlinear metrics; multiway resampling is not automatically required. |
| 6. [τ-bench](https://arxiv.org/abs/2406.12045v1) | **Older context**, Jun 17, 2024 v1; `arxiv:2406.12045@arxiv-v1` | Per-trial binary success and all-k consistency. `pass^1` is not thresholding a mean ordinal score; all-k is not at-least-one success. |
| 7. [ENAMEL](https://arxiv.org/abs/2406.06647v4) | **Older context**, 2024 work / Feb 19, 2025 v4; `arxiv:2406.06647@arxiv-v4` | Explicit right-censoring in generated-code execution. Useful precedent, not a ready-made estimator for every timeout/OOM/blank/parser failure in inference. |
| 8. [Same Request, Different Answer](https://arxiv.org/abs/2609.04748v1) | Sep 4, **2026 preprint + pinned artifact**; `arxiv:2609.04748@arxiv-v1` | Cache/precision trajectory differences; artifact reports scorer correction on stored outputs reversing apparent precision ordering without new inference. GPU, 7B–14B—not <=5B CPU-only. Code availability is not independent reproduction. |
| 9. [Hydra](https://arxiv.org/abs/2608.25053v1) | Aug 25, **2026 preprint + pinned artifact**; `arxiv:2608.25053@arxiv-v1` | Phase/backend/quantization-aware power accounting. Jetson GPU evidence, not CPU inference; venue acceptance is an artifact claim, not independently verified here. |
| 10. [Cloud-OpsBench v2](https://arxiv.org/abs/2603.00468v2) | **Updated older work**, Aug 22, 2026; `arxiv:2603.00468@arxiv-v2` | 452/40 to 754/57 cases/fault types; diagnostic evidence graphs/process annotations and a verified code revision. Snapshot diagnosis is not live remediation. |

The full report and source rows pin corresponding artifact SHAs and body hashes.
The two newly added older-method PDFs have SHA-256:

- Human design: `7b52799879748629840bb730d7385372b01713d7e8a4b09c6aedf1022f3ad563`.
- Bootstrap: `2292aba23e87a87c75e66ea71e4f05c0f08ca645224e140e04266f0e7edf372b`.

## Gaps ApprenticeOps can fill

1. Validity of this finite CPU-ops measurement artifact: independent human
   anchors, full answer visibility, criterion-level error analysis.
2. Failure-inclusive usefulness and time/energy cost, alongside conditional
   quality. Distinguish genuine right-censoring from crashes, missing artifacts
   and parser outcomes; energy missing after failures is not zero energy.
3. Deployment identity and offline scorer/parser sensitivity on existing outputs,
   without claiming universal CPU or family-level superiority.

## Experiments worth considering

These are proposals for the parent's closure plan, not experiments performed here:

- **P0: fresh human validation.** Freeze the rubric and display protocol, use
  qualified unexposed raters, show complete relevant task input and the entire
  scored answer, and hide automated scores and model identities. Take a
  probability sample with recorded inclusion probabilities; retain coverage of
  agreements, disagreements and failures. Stratification is compatible with this
  if its sampling/weighting is explicit. Keep tuning/pilot labels separate from
  held-out validation. Do not prescribe a magic sample size from another paper.
- **P0: audit two estimand invariants before regenerating uncertainty.**
  A synthetic equal-cluster bootstrap oracle with means A=0, B=1 and draws
  `[A,A,B]` must yield `1/3`, not `1/2`. Preserve copies using draw IDs or weights
  through all grouping and paired model comparisons. For a declared score
  threshold of 4, synthetic repeat scores `[1,5]` give binary success rate `1/2`;
  thresholding their average gives 0 and answers a different question.
- **P1: offline sensitivities only.** Parser/scorer extraction, failure taxonomy,
  response length/visibility, identity aliases, threshold choice and scenario
  influence. PPI or a different bootstrap design is conditional/optional, not a
  prerequisite to completing a defensible finite-corpus analysis.

**No new model sweep, PEFT training or hardware experiment is required to
compute the existing single-node analysis.** The current submission decision
still requires second-hardware evidence unless explicitly amended and reviewed;
see the [completion plan](../../sdd/152-analysis-closure.md).

## Analysis changes

Let `Y[s,r]` be the frozen per-attempt binary usable-success label, with `c_s`
successes among `n_s` intended/eligible repeats under a disclosed failure policy.
For equally weighted scenarios, τ-bench defines:

- `pass^1 = pass@1 = mean_s(c_s / n_s)`.
- `pass^k = mean_s[choose(c_s,k) / choose(n_s,k)]`.
- `pass@k = 1 - mean_s[choose(n_s-c_s,k) / choose(n_s,k)]`.

The latter two estimators require `n_s >= k` and their stated trial assumptions
for probability interpretation. With exactly k observed repeats, empirical
`pass^k` is the fraction of scenarios whose every repeat succeeds. Do not
exponentiate a pooled mean, silently drop non-completions, or infer long-run
population reliability from a few repeats.

Separate sampling bias, measurement/display bias and rater exposure. Weighting
can address a known probability design; it does not make altered or exposed
labels equivalent to fresh full-text labels. Small scenario counts and reused
raters also constrain uncertainty. A bootstrap fix is not proof of nominal
interval coverage.

## Paper-impact candidates

The full report contains the seven-field promotion packets and current manuscript
locations. Prioritize these, pending the parent's results:

1. **Human-validity qualification** — sources 1–4; `add-after-current-run`.
2. **Correct resampling and reliability definitions** — sources 5–6;
   `add-after-current-run`, not novelty.
3. **Censoring/deployment/energy qualifications** — sources 7–9;
   `related-work-only` now as proposals, empirical additions after validated
   analysis. No canonical edit is authorized.
4. **Ops-benchmark positioning update** — source 10; `related-work-only`.

## Social / practitioner leads — not findings

- [Aug 23 M4 Pro discussion](https://news.ycombinator.com/item?id=49410310):
  practitioner test reports, **lead/monitor**, not controlled independent
  validation. Version:
  `web:news.ycombinator.com/item/49410310@web-sha256-a3b73d4c825613c7cf6d70527430ffa24332689112deb158834e0874bac988c7`.
- [Sep 7 llama.cpp schema issue](https://github.com/ggml-org/llama.cpp/issues/28522):
  large optional-parameter tool schema behavior, **lead/monitor**. Version:
  `web:github.com/ggml-org/llama.cpp/issues/28522@web-sha256-8773bf0873fc6ed47d7ebc4f165bbbad8aa37c769ccf4c88a5aa3988ec4a1789`.
- No new controlled independent paper replication was established. The existing
  older xLAM practitioner reproduction remains separately scoped in the full
  report; it is not a new 2026 result.

## What not to claim yet / coverage

**112 exact queries/reads, 107 hashed bodies, 490 invocation-level records
screened, 22 source/claim versions**: 14 primary papers, four model cards, one
company report, one older independent practitioner reproduction and two social
leads. All **10 topics / 9 company channels / 5 source families** have bounded
coverage. This is matrix coverage, not exhaustive freshness discovery.

Two narrow true-zero searches: in-window per-usable-answer energy, and human
evaluation combined with bias/truncation. The bootstrap query screened six of ten
matches. Google search hit a JS challenge; Reddit returned 403. Five early
connectivity probes lack retained bodies. Company-card dates can reflect edits
rather than release dates; full caveats are in the report.

Do not claim independent validation of the 152-model bundle, causal proof of
the code-inspection findings, a new reliability/censoring metric, CPU effects
from GPU evidence, or paper promotion. Scan completion does not close those
gates. The [full report](2026-09-08.md) records the validation scope and the
separate whole-tree privacy-scanner caveat.
