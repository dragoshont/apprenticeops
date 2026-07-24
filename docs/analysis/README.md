# Analysis & figures

Re-runnable analysis behind the paper, written to be read **top-to-bottom** and
exported to a static site. The notebooks are the data + figures;
[`paper.qmd`](paper.qmd) is the submission manuscript, while
[`../PAPER.md`](../PAPER.md) remains the design, pre-registration, and analysis
plan that the manuscript cites.

## Notebooks

- **[`wave_analysis.ipynb`](wave_analysis.ipynb)** — the canonical analysis
  generator. It reports 94-model quality/safety breadth and a controlled
  24-model quality/safety/energy selection; all systems cells enforce the
  base-clock, Turbo-off, `package-0` scope.
- **[`judge_comparison.ipynb`](judge_comparison.ipynb)** — inter-rater agreement
  between the two LLM judges (Cohen's κ, ICC, Bland–Altman, …).
- **[`reviewer.ipynb`](reviewer.ipynb)** — twelve editable reviewer queries.
  Energy/speed/roofline/MCDA queries can access controlled rows only.

The public portal keeps narrative discovery separate from executable evidence:
Home, Paper, Review, and Research Updates are searchable; the three code-heavy
notebooks remain directly navigable but are excluded from the site search index.
[`research-updates.qmd`](research-updates.qmd) summarizes candidate radar evidence
without promoting it into the paper or bibliography.

## Machine-readable exports → [`../../data/site/`](../../data/site)

The wave notebook writes the figures' underlying numbers, so a website (or any
downstream tool) is driven by **real data, not screenshots**. Regenerated in
place on every run.

| File | Contents |
|---|---|
| `summary.json` | Exact breadth/controlled populations, paired contrasts, fronts, and `energy_cross_batch_comparison_allowed=false`. |
| `models.csv` · `models.json` | 94-model quality/safety breadth; intentionally no energy field. |
| `controlled_models.csv` | 24-model controlled quality/safety/energy table with batch/regime/source fields. |
| `pareto.csv` | Controlled three-axis front (7 models). |
| `quality_safety_pareto.csv` | 94-model breadth quality/safety front (2 models). |
| `axis_quality.csv` | Judged percentage of ceiling by historical group (scenario-cluster interval). |
| `axis_safety_bracket.csv` · `axis_safety_arm.csv` | Deterministic refusal per instruct bracket / per training-type arm. |
| `axis_energy.csv` | Controlled energy-per-answer and decode-tokens/s-per-watt by historical group. |

## Rebuild / view

```bash
# Explicitly refresh notebooks, exports, figures, site, and PDF.
scripts/build-analysis-site.sh --update

# Re-execute all public notebooks in temporary outputs and compare everything.
scripts/build-analysis-site.sh --verify

# Stamp the rendered site with canonical evidence + commit provenance.
python3 scripts/write-portal-build.py --site-dir docs/analysis/_site

# Fail on stale claims, wrong commit identity, or notebook search leakage.
python3 scripts/verify-portal.py \
  --site-dir docs/analysis/_site \
  --expected-commit "$(git rev-parse HEAD)"
```

Exact notebook-output and PNG comparison is **reference-platform verification**:
the correction-lock artifacts were generated on macOS arm64, and the Pages
workflow pins that gate to GitHub's `macos-15` arm64 runner. Schema, claim, link,
privacy, and portal-truth audits are platform-independent. Native Linux arm64
reproduces notebook outputs and tabular exports but not identical PNG pixels;
Ubuntu x64 can also differ at floating ordering/serialization boundaries. Those
platform differences are not accepted silently or hidden by wider tolerances.

> **Honesty:** the **quality** axis is the **5-rep × 2-judge ensemble**
> (cross-judge κ_quad ≈ 0.91); **safety** is judge-free. **Energy and systems
> rankings are controlled-first-batch only.** Everything is one commodity node
> (n = 1). The former 12-of-94 pooled-energy front is withdrawn.
> Render artifacts (`_site/`, `*.html`) are git-ignored; the notebook outputs and
> `data/site/` exports are tracked.

**Accessibility.** Every figure carries a `#| fig-alt:` screen-reader description
at the top of its cell. Quarto applies these as `<img alt="…">` on `quarto render`
(the accessible build). The plain `nbconvert` HTML preview does **not** carry them
(nbconvert doesn't read Quarto cell directives) — use the Quarto site for the
accessible version.
