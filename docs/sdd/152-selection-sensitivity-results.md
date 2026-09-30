# Completion-proxy and energy-metric selection sensitivity

**Date:** 2026-09-09. **Status:** bounded P2 extension implemented, independently
replayed by the parent and accepted by final GPT/Claude review. P2 is closed
only for retained machine calculations. Results remain **provisional, exploratory,
and machine-calculated**, not human-validated deployment recommendations.

## Scope and evidence

This extension addresses the remaining dimensions of
[STATISTICS §10](../STATISTICS.md#10-rank-and-pareto-robustness) in the
[closure programme](152-analysis-closure.md). It adds **three consensus-only
arms**, plus a repeated reference, without changing the
[original 15 arms](152-selection-stability-results.md). It does not claim to have
computed every sensitivity: served-exclusion outcomes are not identifiable.

The fixed population remains **137 eligible tags × 20 scenarios × five
repetitions = 13,700 assigned attempts**. The
[r5 package](../../deep-dive/out/selection-sensitivity-152-20260909-r5/) anchors the
unchanged r4 core and selection receipts. Its `base/` contains a fresh execution
of all 15 original arms: six CSVs and their receipt are byte-identical to r4.
No existing source file, raw row, r4 receipt, model lock, claim manifest, public
site or human-label record was changed.

The extension reads hash-verified snapshot `finish_reason`, paired consensus
scores and `energy_wh`, and joins recorded `output_chars` from r4 `check_cells.csv`
one-to-one on the frozen cell keys. The named-judge/single-condition compatibility
proof remains the [core r4 contract](152-analysis-repair-results.md). Unknown
metadata and incomplete grids fail closed; no text or model-name heuristics are
used to fill missing evidence.

## Definitions and denominator policy

Let \(I=1\) when recorded `output_chars > 0` and finish reason is `stop` or
`length`. This is a **nonblank terminal-output proxy**, not a determination that
the answer is usable, correct, safe, or semantically nonempty. Positive character
counts do not establish substantive content. Length outputs remain included and
separately flagged; incomplete-finalization and timeout outcomes do not qualify.

For every tag and scenario draw, \(N=100\) assigned attempts, \(S\) is recorded
consensus score, \(C=\sum I\), and \(E\) is total energy over **all assigned
attempts**, including failures:

| Arm | Quality axis to maximize | Cost axis to minimize |
|---|---|---|
| Reference | \(\sum S/N\) | \(E/N\), Wh/attempt |
| Proxy-conditional | \(\sum IS/C\) | \(E/N\) |
| Proxy-unconditional | \(\sum[IS+(1-I)1]/N\) | \(E/N\) |
| Alternative energy | \(\sum S/N\), unchanged raw score | \(E/\sum 1[S\ge3]\), Wh/instrument-positive answer |

The unconditional failure value **1** is declared for this versioned exploratory
sensitivity, not retrospectively preregistered and not substituted into the
original 15 arms. Alternative energy uses the **raw** threshold-3 instrument,
not the completion proxy or the failure-transformed score. Energy is measured
RAPL `package-0`, excluding DRAM and wall-power consumption.

We use the original **4,000 common scenario-cluster draws**, seed **20260725**.
Every selected scenario occurrence retains all five repetitions and all tags.
Conditional quality is a ratio of draw totals, not an average of scenario means.
Ranks use midranks and fractional top-1/5/10 boundary credits. Pareto dominance
requires one strict improvement; equal points remain tied.

If \(C=0\), conditional quality is **not estimable**, never zero. If any tag's
axis is unavailable, that arm's entire fixed-roster draw is not estimable:
we retain every tag and draw, report missingness counts, and never rank a smaller
available-case roster. Frequencies divide by explicitly reported valid-draw
counts; no valid draws gives missing frequencies, not zero. Paired comparisons
use intersections of valid draw IDs.

Positive \(E\) with zero instrument-positive answers gives **infinite cost**;
\(0/0\) is unavailable. Infinite cost is distinguished from missingness and
retained in the extended-real Pareto calculation. A higher-quality infinite-cost
point need not be dominated by lower-quality finite cost, but is never a
finite-cost deployment choice. The fixtures cover both cases.

## Completion-proxy results

There are **13,603 proxy-positive attempts**, **69 blank-stop**, **28 DNF**
(24 timeouts and four incomplete-finalization outcomes), and **1,433 retained
length outputs**. Point proxy denominators range from **87 to 100** per tag.
Across the seeded draws they range from **64 to 100**: no tag/draw has a zero
proxy denominator. All **4,000 draws** and paired comparisons therefore retain
the entire **137-tag** population. `denominators.csv` discloses membership,
per-tag counts/rates, denominator ranges, and zero-denominator counts.

Across tags, the descriptive point mean is **2.060073** for raw score,
**2.064525** for proxy-conditional quality, and **2.057664** for
proxy-unconditional quality. These are equally weighted tag means, not a
pooled proxy-completion mean. The largest conditional–unconditional difference
is `phi3.5:3.8b-mini-instruct-q8_0`: **2.580460 versus 2.375000**,
with 87 proxy-positive attempts; its raw mean is **2.565000**.

| Paired comparison | Mean Kendall τ-b [central resampling range] | Mean front Jaccard | Draws with different fronts |
|---|---|---|---|
| Conditional versus unconditional proxy | 0.987787 [0.982077, 0.993172] | 0.999981 | 1/4,000 |
| Conditional proxy versus raw reference | 0.991788 [0.987354, 0.995538] | 1.000000 | 0/4,000 |
| Unconditional proxy versus raw reference | 0.995062 [0.989448, 0.999301] | 0.999981 | 1/4,000 |

All three point fronts contain the same **11 tags**. Conditional versus
unconditional top-five fractional-credit overlap averages **0.994642**, with
central range **[0.865000, 1.000000]**. Similar fronts in this corpus do not
validate the proxy or remove the conditional-selection limitation.

## Alternative energy-metric results

The numerator is **1,080.46705 Wh** across the full primary population; the raw
threshold-3 instrument has **3,891 positive attempts**. Point costs are finite
for **135 tags**; the other two remain explicitly present:

| Tag | Assigned Wh | Positive attempts | Wh/instrument-positive answer |
|---|---:|---:|---|
| `codegemma:2b` | 10.25050 | 0 | Infinite |
| `starcoder2:3b` | 13.84306 | 0 | Infinite |

Both have zero alternative-front inclusion in these draws; they were not removed.
Finite-cost populations range from **106 to 135** per draw. All 137 tags remain
in the extended-real calculation, with no unavailable \(0/0\) cost.

Replacing Wh/attempt with Wh/instrument-positive answer changes the point front
from **11 to four tags**; the mean resampled front size changes from **11.19125**
[8, 14] to **4.47175** [3, 7]. Paired front Jaccard averages **0.394884**
[0.230769, 0.600000], with point Jaccard **0.363636**. Front membership differs
in all 4,000 paired draws. Quality ranks and top-k credits are unchanged by
construction because their quality axis is unchanged.

| Alternative point-front tag | Raw quality | Wh/instrument-positive answer | Resampled front inclusion |
|---|---:|---:|---:|
| `gemma4:e2b-it-qat` | 3.185 | 0.070072 | 99.100% |
| `hf.co/unsloth/Qwen3-4B-GGUF:Q4_K_M` | 3.380 | 0.129639 | 81.900% |
| `qwen3:4b-instruct-2507-q8_0` | 3.590 | 0.195740 | 76.675% |
| `qwen3:4b-q8_0` | 3.400 | 0.175878 | 29.300% |

This is sensitivity to a quality-dependent energy denominator—not independent
evidence of quality, validated energy per usable answer, or a universal best tag.

## Dispositions and remaining limits

| Dimension or interpretation | Disposition |
|---|---|
| Original scenario/judge/threshold arms | Retained exactly; 15-arm replay byte-identical |
| Conditional versus unconditional quality | Computed for the explicitly defined consensus completion proxy; actual usability remains unvalidated |
| Energy-metric sensitivity | Computed at raw consensus threshold 3 with failure-inclusive energy and explicit infinite costs |
| Served-failure-policy selection sensitivity | **NOT IDENTIFIABLE**: 173 screened, 152 selected for the full study, **21 excluded with zero comparable full-run rows** |
| New judge × proxy × energy crossproduct | Not computed; bounded extension is consensus-only, not every combination |
| Weight-population, causal architecture/training, operational safety or usability conclusions | Not established; no claim promotion |

The served screen records canary outcomes, not a comparable 20-scenario,
five-repetition quality/energy grid for excluded candidates. Their membership
and the boundary validation appear in `served_failure_disposition.json`.
Assigning them quality failures or energy values would invent evidence.
Estimating their selection effects requires separately authorized new
measurements, which were not performed.

All reported ranges are central **scenario-resampling descriptions**, not
confidence bounds over independent weights, random SRE incidents or operational
validity. Completion conditioning can select easier outcomes. Actual usable
completion, human instrument validation, additional hardware evidence and
publication readiness remain unresolved.

## Reproduction and verification

```bash
deep-dive/.venv/bin/python deep-dive/test_selection_sensitivity.py
deep-dive/.venv/bin/python deep-dive/test_selection_stability.py
deep-dive/.venv/bin/python deep-dive/test_analysis_repairs.py
deep-dive/.venv/bin/python deep-dive/selection_sensitivity.py --out <NEW-unused-directory>
```

The computation requires a new directory and fails closed on errors or hash
mismatches. It first replays and verifies the original 15 arms, then emits the
additional tables. The extension does not require raw bundles or live data:
it consumes the retained portable snapshots and hash-bound core outputs.

- **19 new + 18 existing selection + 24 core tests PASS**; real join and five
  corruption cases PASS. Parent owns test/config wiring.
- Configured `gates/checks.sh` PASS with only terminal-injected Git overrides
  removed in the test subprocess; no validation disabled or dependency installed.
- Independent full r5 replay: **17 computation files byte-identical**, including
  both receipts and all baseline/new outputs.
- Bounded implementation reviews: **GPT PASS; Claude PASS**. No mathematical
  blockers. Scoped privacy: **30 files, zero findings**; documentation links,
  whitespace and fresh audit-packet validation PASS.
- [r5 receipt](../../deep-dive/out/selection-sensitivity-152-20260909-r5/receipt.json)
  SHA-256: `052368fc4b18f02b8d3acbd4a6aa0ec27e7c85d8921a58843c2dcbb8bf0a9ed6`.
- Original r4 selection/base receipt SHA-256:
  `4b929c382f69c7e8d07a75d4e4be2b49540b43cc6d90b08e90708ac372d70fd2`.
- The r5 receipt binds all consumed sources/helpers, new code/tests and computed
  outputs. Supplemental gate evidence is recorded in
  [verification.json](../../deep-dive/out/selection-sensitivity-152-20260909-r5/verification.json);
  this later gate record is not part of the immutable computation receipt.
- Parent final check: all 61 scientific tests PASS, 32 extension hash bindings
  verified, and a separate execution reproduced all 17 computation files exactly.
  The [parent receipt](../../deep-dive/out/selection-sensitivity-152-20260909-r5/parent-verification.json)
  and final independent GPT/Claude PASS accept the retained computation scope,
  not human instrument validity or claim promotion.

**Implemented in this response:** the three bounded arms, denominator/missingness
handling, served-screen disposition, fixtures and r5 evidence. **Not started:**
new labels, inference, hardware collection or publication work. **Next
recommended evidence gate:** independent human instrument validation; scientific
claim locking, hardware scope and publication retain their separate gates.
