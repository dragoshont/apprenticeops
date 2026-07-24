# CEOps Benchmark Website Research

Status: design input; no DNS, paper, experiment, or production UI change
Date: 2026-07-14
Primary domain: `ceops.org`
Future experiment surface: `experiment.ceops.org`

## 1. Decision Summary

CEOps should be presented as a **research decision instrument**, not a generic
leaderboard and not a SaaS marketing site.

The first screen should answer one literal question:

> Which small, locally sovereign model deployment gives an operator acceptable
> quality and refusal behavior at an energy and latency cost their hardware can
> sustain?

The public website should lead with the current evidence release, the two valid
comparison scopes, and the controlled Pareto result. It should then make every
headline, plotted point, and table row traceable to its experiment condition and
source artifacts. The paper, methodology, corrections, reviewer path, and
reproduction path are first-class parts of the product rather than footer links.

The separate experiment product should be browser-delivered but execute only
through a runner installed and controlled by the user. CEOps should not host a
control plane that reaches into home networks.

## 2. User-Visible Outcomes

After the website redesign:

1. a practitioner can determine whether the evidence applies to their hardware
   and risk tolerance before reading the full paper;
2. a reviewer can move from a claim to the method, condition identity, raw row,
   correction history, and reproduction command without guessing;
3. a researcher can distinguish locked paper evidence from candidate research
   updates and from still-running experiments;
4. a user can launch the separate experiment console and pair it with a runner
   they installed locally, without creating a CEOps account or exposing their
   network to CEOps.

## 3. Research Method

This brief combines four evidence tracks:

- current benchmark and paper-companion websites inspected on 2026-07-14;
- visual product sections returned by Mobbin and inspected in the tool output;
- recent primary small-model and on-device sources already preserved by the
  ApprenticeOps research radar;
- the current Mission Control frontend, backend, deployment, and experiment
  contracts in this repository.

Visual claims below are limited to pages and images directly inspected. Vendor
claims establish intended positioning and product investment, not independent
capability evidence.

The exact Mobbin image responses used here are identified by section URL,
source-image URL, inspection date, and SHA-256 in
[`ceops-mobbin-visual-evidence-2026-07-14.json`](ceops-mobbin-visual-evidence-2026-07-14.json).
The third-party images are not redistributed. Mobbin and source-site URLs are
live and can change; the manifest makes the inspected bytes and observations
independently identifiable without treating Mobbin as an academic source.

## 4. Benchmark And Paper-Site Precedents

### 4.1 Highest-signal precedents

| Precedent | Pattern worth adopting | Pattern to avoid |
|---|---|---|
| [METR Time Horizons](https://metr.org/time-horizons/) | One interpretable metric, primary chart in the first viewport, dated update, correction log, downloadable task/data artifacts, and a direct explanation of what the result does not mean. | Trend extrapolation without the reliability boundary beside it. |
| [ML.ENERGY](https://ml.energy/leaderboard/) | Constraints are part of the result surface: workload, latency requirement, hardware, precision, stability, and energy-optimal configurations. Raw data and analysis tools are adjacent. | Transferring GPU/device rankings to another hardware or power boundary. |
| [SWE-bench](https://www.swebench.com/) | Benchmark variants and harness identity are visible before ranking; result rows expose date, agent/model identity, cost, and detailed cases. | Letting a curated subset silently stand for the full task population. |
| [Terminal-Bench](https://www.tbench.ai/) | Benchmark version, task examples, agent x model identity, confidence intervals, verified submissions, and a direct test-my-agent path. | Calling a whole agent/runtime result a bare model result. |
| [LiveBench](https://livebench.ai/) | Release selector, category/subtask drilldown, objective grading, public questions/answers, and cost beside quality. | Absolute "contamination-free" language or silent cadence/task changes. |
| [HELM Capabilities](https://crfm.stanford.edu/helm/capabilities/latest/) | Drilldown from aggregate score to exact scenario, prompt, response, and run configuration. | Fragmented parallel leaderboards or unlabeled "latest" routes. |
| [Epoch AI Benchmarks](https://epoch.ai/benchmarks) | Internally run versus sourced result labels, correction notices, conflicts/funding disclosure, and visible update dates. | Composite indices without an adjacent decomposition. |
| [MLPerf Client](https://mlcommons.org/benchmarks/client/) | Comparable-configuration badge, base versus extended/experimental classifications, requirements, known issues, and working-group review. | Combining quality and performance into one unqualified rank. |
| [Artificial Analysis](https://artificialanalysis.ai/) | Effective multi-axis filters, model detail pages, metric definitions, and methodology version history. | Commercial dashboard density, universal composite scores, and private task data presented as complete product truth. |
| [Greptile benchmark](https://mobbin.com/sections/141ab41e-c74b-4f61-b877-fe16806e1345) | The inspected Mobbin section puts overview, methodology, overall result, severity slices, and a case library in one linear research narrative. The result is followed by inspectable cases rather than testimonials. | Product self-comparison without independent review or uncertainty. |

### 4.2 Useful Mobbin product patterns

- [Aqua benchmark page](https://mobbin.com/sections/2e54223a-941c-425e-8f0b-f756a93f52d8)
  shows a disciplined sequence: literal value proposition, three compact
  measured facts, why the benchmark matters, per-dataset comparisons, concrete
  error examples, then integration. CEOps should copy the sequence, not Aqua's
  unqualified product-superiority framing.
- [Maze research hero](https://mobbin.com/sections/ce75938d-b352-4140-b083-3c3af66b6c87)
  demonstrates a clear research-specific proposition with the real product
  surface visible in the first viewport. CEOps should show the actual controlled
  Pareto/evidence explorer, not a decorative illustration.
- [Maze product research section](https://mobbin.com/sections/e47ac64e-a959-43c8-910f-d79ae24b674b)
  separates the research workflow into validate, integrate, reach, and report.
  CEOps can use the analogous sequence define, run, verify, compare, export.
- [WhatsApp developer hub](https://mobbin.com/sections/05f59762-1939-4e26-8f89-e1da4f78d5b9)
  distinguishes quick start, overview, documentation, support, and policy. This
  is a better precedent for runner onboarding than a generic account wizard.
- [Shopify developer page](https://mobbin.com/sections/848358e0-f42c-4880-84ae-e972247e8583)
  makes the developer's possible jobs explicit before offering communities and
  resources. CEOps should first state what the runner can execute and measure.
- [PayPal developer page](https://mobbin.com/sections/2481bc4e-a2b5-4c28-a8f3-d46556140c74)
  separates credentials, product paths, APIs/SDKs, interactive tools, sandbox,
  and support. CEOps should similarly separate pair runner, choose adapter,
  inspect capabilities, dry run, and full experiment.

Broad Maze pages were also inspected. Their large hero typography, social proof,
repetitive marketing sections, and decorative media are not a good fit for an
academic benchmark. CEOps should be confident through evidence, not through
customer logos or superlatives.

## 5. Small Models Are A Real Product And Research Trend

The 2025-2026 evidence supports treating small/local models as a durable
deployment category, with important limits:

| Work / artifact | Deployment fact | Important limit | CEOps relevance |
|---|---|---|---|
| [Apple Foundation Models 2025](https://arxiv.org/abs/2507.13575v3) | Approximately 3B on-device model; 2-bit QAT, KV-cache sharing, constrained tool use, and application LoRA adapters. | First-party report; no public weights or independent CPU/energy replication. | Demonstrates platform investment and why adaptation identity belongs in the condition. |
| [FunctionGemma 270M](https://huggingface.co/google/functiongemma-270m-it/tree/39eccb091651513a5dfb56892d3714c1b5b8276c) | Pinned specialist artifact with a task fine-tuning recipe and first-party device measurements. | Narrow task/device and vendor-reported result; not general ops competence. | Supports a future specialist-routing experiment, not a current paper claim. |
| [MobileLLM-R1](https://arxiv.org/abs/2509.24945v3) | Open recipe for sub-billion reasoning models using curated/resampled pretraining and reasoning post-training. | Benchmark reasoning does not establish ops utility, restraint, or CPU efficiency. | Supports testing reasoning as a budgeted treatment below 1B. |
| [SmolLM3](https://huggingface.co/HuggingFaceTB/SmolLM3-3B/tree/a07cc9a04f16550a088caea529712d1d335b0ac1) | Pinned Apache-2.0 3B think/no-think model with tool calling and an open recipe. | CPU performance and operations behavior remain unmeasured by the release. | A deployable package candidate whose reasoning mode must be explicit. |
| [Granite 4.0 H-Micro](https://huggingface.co/ibm-granite/granite-4.0-h-micro/tree/d5f01a3ea75f088947be3aae039f4ad52837dfde) | Pinned Apache-2.0 3B attention/Mamba2 hybrid with a first-party tool template. | A load example is not a controlled CPU benchmark; family and architecture are confounded. | Supports package-level, not architecture-only, comparison. |
| [Ministral 3](https://arxiv.org/abs/2601.08584v1) | 3B/8B/14B base, instruct, and reasoning family using cascade distillation. | First-party report; multimodal footprint and CPU telemetry require separate verification. | Supports training-regime and distillation provenance fields. |
| [BitNet b1.58 2B4T](https://arxiv.org/abs/2504.12285v2) and [pinned runtime](https://github.com/microsoft/BitNet/commit/01eb415772c342d9f20dc42772f1583ae1e5b102) | Native ternary training and a dedicated CPU/GPU runtime are publicly available. | Architecture, training, and runtime are one package; it is not a causal post-training quantization comparison. | Supports runtime-specific low-bit experiments and exact artifact identity. |
| [MLPerf Client](https://mlcommons.org/benchmarks/client/) | Standardizes local LLM timing and quality gates across multiple client platforms and approved configurations. | Task and quality gates are narrower than operational competence; releases are configuration-specific. | Strong precedent for comparable-configuration badges and local client measurement. |

These sources are also preserved with immutable version identities in the
repository's research radar. The table links primary public artifacts so the
trend argument does not depend on that internal ledger alone.

The defensible CEOps message is therefore:

> Small models are increasingly deployable and useful for bounded local work;
> whether a specific package is good enough, safe enough, and efficient enough
> remains an empirical decision under a named condition.

CEOps should not claim that small models replace frontier models, that one size
is universally optimal, or that local execution implies readiness for autonomous
operations.

## 6. Information Architecture

### 6.1 Public site: `ceops.org`

1. **Overview** - the decision question, evidence release, current controlled
  recommendation, scope boundary, and three routes: inspect, verify, run.
2. **Evidence / releases / `<release_id>`** - the release-scoped work surface:
  - **Selection** - controlled Pareto explorer; quality, refusal, energy,
    latency, reliability, and preference sensitivity;
  - **Packages / `<artifact_digest>`** - deployment identity: weights, training
    regime, quantization, runtime, template/parser, footprint, and license;
  - **Scenarios / `<scenario_id>`** - provenance, prompt, checks, rubric, and
    current coverage limitations;
   - **Runs / `<bundle_digest>`** - one immutable run bundle with its display
     `run_id`, condition digests, attempts, DNF, judges, telemetry, comparison
     eligibility, and artifacts;
   - **Conditions / `<condition_digest>`** - the reusable model/runtime/task/
     hardware condition shared by one or more runs, never a substitute for run
     or attempt identity;
  - **Claims / `<claim_id>`** - claim -> method -> condition -> rows ->
    correction -> pinned verification command.
3. **Method and paper** - protocol, metrics, uncertainty, comparability rules,
  correction history, limitations, privacy/egress, and paper.
4. **Reproduce** - three distinct paths:
  - **Verify this release** using the release commit or bundle digest;
  - **Rerun this benchmark** using pinned packs and expected outputs;
  - **Start a new local experiment** at `experiment.ceops.org`.
5. **Review** - reviewer questions, claim matrix, feedback path,
  conflicts/funding/AI-use disclosure, and publication status.
6. **Research updates** - candidate evidence only, excluded from locked-release
  search by default and visually separated from paper evidence.

The release manifest binds `release_id -> full_commit_sha -> root_bundle_digest`.
All evidentiary Binder, Colab, Kaggle, notebook, export, source, and reproduction
links must resolve to a full commit SHA or content digest, never mutable `main`
or a replaceable tag. A release tag may be displayed only as a human-readable
alias for those immutable identities.

### 6.2 Experiment site: `experiment.ceops.org`

1. Pair runner.
2. Inspect runner capabilities and compatibility.
3. Select an immutable experiment/scenario pack.
4. Choose model artifacts and runtime adapters available on that runner.
5. Review the exact condition and estimated work before launch.
6. Execute and monitor attempts, DNF, telemetry, and judging.
7. Inspect results and provenance.
8. Export a content-addressed evidence bundle.

The experiment site is a static application. It has no central login, job queue,
or result store in the first generation.

The public console requires the browser and paired loopback runner to be on the
same computer. On unsupported mobile devices, the primary action is **Continue
on a supported computer**, not a non-functional Connect control.

## 7. First-Viewport Contract

The desktop first viewport should contain:

- CEOps name and one-sentence definition;
- evidence release badge with schema, correction date, and build identity;
- the literal selection question;
- the real controlled Pareto visualization, not a decorative mockup;
- the current `7 of 24` controlled and `2 of 94` breadth scope labels;
- one compact recommendation with the preference rule that produced it;
- primary actions: **Inspect evidence**, **Read the paper**, **Run on my hardware**.

It should also expose the single-environment boundary without requiring a scroll.
On mobile, the visualization may become an ordered, horizontally inspectable
shortlist, but scope and evidence identity remain visible.

## 8. Content And Voice

Use clear academic language:

- name the estimand, population, scope, and measurement condition;
- distinguish measured, judged, derived, proxy, and unavailable values;
- use "associated with" rather than causal language for observational roster
  effects;
- state corrections and withdrawn results in the same visual hierarchy as wins;
- label preprints, first-party reports, reproductions, and social leads;
- make proposals and future work visibly different from findings.

Avoid:

- "best AI," "revolutionary," "industry-leading," or "unbiased";
- a universal model rank or opaque composite score;
- customer-logo proof, fabricated usage counts, or decorative dashboards;
- claims that point estimates are stable without scenario/repeat uncertainty;
- calling a tag a model when the runtime/template/quantization package matters.

## 9. Visual Direction

The visual language should be editorial-scientific rather than institutional or
SaaS-polished.

### 9.1 Typography and geometry

- Source Serif 4: page titles 48/54 desktop and 36/42 mobile; selection question
  32/38 desktop and 26/32 mobile.
- Source Sans 3: navigation and controls 14/20, body 15/23, table/data 14/20,
  metadata 13/18; use tabular numerals for measurements.
- Reading measure: 720 px / approximately 68 characters. Evidence width: up to
  1120 px. Shell width: 1280 px.
- Desktop grid: 12 columns, 24 px gutters, 48 px edge padding. Tablet: 8 columns,
  20 px gutters, 24 px padding. Mobile: 4 columns, 16 px gutters/padding.
- Spacing foundation: 4, 8, 12, 16, 24, 32, 48, 64 px. Section rhythm is 64 px
  desktop, 48 px tablet, and 40 px mobile.
- Controls are at least 44 px high with 4 px radii. Repeated records may use up
  to 8 px radii. Do not use decorative floating cards or nested cards.

### 9.2 Color and evidence state

- Neutral light and charcoal dark themes are equal first-class modes; avoid a
  dark-blue default.
- Verified/comparable evidence: restrained teal keyline and tint.
- Qualified, provisional, or corrected: amber keyline and tint.
- Withdrawn, invalid, or integrity-failed: red, reserved for those states.
- Unavailable: neutral gray and explicit text; unavailable is never zero.
- Recommendations remain strong neutral, not teal: a preference-dependent
  operating point is not universal truth.
- Every state also has a word, icon, and border; color is never the sole carrier.

### 9.3 Evidence components

- Evidence-release strip: full-width, 12 px vertical/16 px horizontal padding,
  release, schema, correction, build, scope, and status.
- Primary desktop chart: 9-column, approximately 16:10 plot plus 3-column
  recommendation/rule. Use SVG or accessible interactive rendering.
- Pareto state uses shape/ring; energy uses bubble area with a three-value size
  key; uncertainty uses error bars or an adjacent uncertainty view.
- Direct-label the seven controlled-front points. Dominated points are neutral
  but retain at least 3:1 contrast.
- Result tables use 48 px rows, sticky headers, units in headers, decimal-aligned
  values, real sort/filter controls, and a release/provenance footer.
- On mobile, use an ordered shortlist and rule-separated definition rows instead
  of making dense tables or scatterplots horizontally scroll as the only path.
- Claim states (`Locked`, `Candidate`, `Corrected`, `Withdrawn`) remain separate
  from measurement types (`Measured`, `Judged`, `Derived`, `Proxy`,
  `Unavailable`).

### 9.4 Interaction and accessibility

- Filters and comparison constraints are URL-addressable and release-scoped.
- Charts have direct labels, keyboard/tap inspectability, and complete textual
  tables.
- Support keyboard-only use, visible/unobscured focus, 200% text resize, 320 CSS
  pixel reflow, WCAG 2.2 AA contrast, forced colors, and
  `prefers-contrast: more`.
- Motion is limited to 120-160 ms filter crossfades with stable axes. No count-up,
  chart-drawing, parallax, marquee, or reveal animation. Reduced-motion mode is
  immediate.
- Status updates use restrained `role="status"` announcements; event logs are
  never placed wholesale in a live region.

Before implementation, encode these decisions in a design map and DTCG-style
tokens with reference, system, and component tiers. Compile tokens into Quarto
and the experiment React client rather than maintaining two visual systems.

The inspected Greptile section is the closest composition precedent. METR and
ML.ENERGY are stronger truth/interaction precedents. Aqua's measured-facts and
concrete-error sequence is useful. Maze's broad product pages are an anti-pattern
for density and tone.

The canonical public naming must be decided before visual sign-off: **CEOps** is
the umbrella/product name, while **ApprenticeOps** may remain the paper and first
benchmark release name. The shell must not present them as two unrelated brands.

## 10. Evidence And Comparison Contract

Every comparable result needs:

- evaluation release and scenario-pack identities;
- model artifact digest and license;
- total/active parameters and stored/resident footprint;
- quantization, runtime version/build, template/parser, reasoning mode, and
  relevant sampling settings;
- hardware, OS, power/thermal regime, and measurement source;
- repetitions, intervals, DNF/error counts, judge identities/agreement, and
  deterministic-check coverage;
- a machine-readable `cross_comparison_allowed` decision and reason;
- correction/supersession state;
- raw-row, sidecar, and bundle-checksum links.

Missing values render as unavailable or condition-incomplete, never as zero.

## 11. Domain And Publication Contract

- `ceops.org` is the canonical public benchmark and paper companion.
- `www.ceops.org` redirects to the apex.
- `experiment.ceops.org` is reserved for the static experiment client after its
  pairing/security preview is approved.
- `mission.ceops.org` remains unconfigured. The current private Mission Control
  remains on its existing LAN/Auth gateway.
- `ceops.ro` showed no public registration or DNS evidence on 2026-07-14 and is
  not part of this design unless separately acquired.
- Cloudflare is authoritative DNS. GitHub Pages can remain the initial static
  host. Domain verification should precede DNS pointing; wildcard DNS is not
  used.

## 12. Recommended Delivery Order

1. Approve this design direction and the runner SDD.
2. Build a design-only preview for the public Overview and Selection pages.
3. Get explicit visual/content sign-off.
4. Implement the approved public-site shell without changing paper evidence.
5. Verify and bind `ceops.org` / `www.ceops.org`.
6. Prototype the loopback pairing flow at `experiment.ceops.org` with a fake
   runner before adapting real experiment execution.
7. Implement portable runner slices only after the pairing and artifact contracts
   pass security review.

## 13. Research Limitations

- Mobbin searches returned commercially oriented matches; they are useful for
  hierarchy and setup patterns, not academic truth.
- Several benchmark sites use private tasks or vendor-run results; CEOps should
  not copy their evidence opacity.
- Website currentness was checked on 2026-07-14 and can change.
- No user study has yet validated the proposed information architecture.
- The experiment product architecture is specified separately and has not been
  implemented.