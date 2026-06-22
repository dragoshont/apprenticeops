# Analysis & figures

Re-runnable analysis behind the paper, written to be read **top-to-bottom** and
exported to a static site. The notebooks are the data + figures; the paper
([`../PAPER.md`](../PAPER.md)) is the prose.

## Notebooks

- **[`wave_analysis.ipynb`](wave_analysis.ipynb)** — *the sovereign selection.*
  Quality → Safety → Energy → the **quality × safety × energy Pareto** → systems
  context (cost, deterministic precision, the bracket value gate, roofline
  transfer) → conclusions. GitHub renders it with figures; or build the site below.
- **[`judge_comparison.ipynb`](judge_comparison.ipynb)** — inter-rater agreement
  between the two LLM judges (Cohen's κ, ICC, Bland–Altman, …).

## Machine-readable exports → [`../../data/site/`](../../data/site)

The wave notebook writes the figures' underlying numbers, so a website (or any
downstream tool) is driven by **real data, not screenshots**. Regenerated in
place on every run.

| File | Contents |
|---|---|
| `summary.json` | Headline numbers: model/Pareto counts, the 3–4B knee, instruct-vs-reasoning safety, the sovereign pick. |
| `models.csv` · `models.json` | Per-model 3-axis table — `model, bracket, quality, safety, energy_wh, mWh, pareto`. |
| `pareto.csv` | The Pareto-optimal short-list (non-dominated on quality ↑, safety ↑, energy ↓). |
| `axis_quality.csv` | Judged %-of-frontier per bracket (mean + 95 % CI). |
| `axis_safety_bracket.csv` · `axis_safety_arm.csv` | Deterministic refusal per instruct bracket / per training-type arm. |
| `axis_energy.csv` | Energy-per-answer + tok/s-per-watt per bracket. |

## Rebuild / view

```bash
# one command: re-run the notebook, write data/site exports, render HTML (+ Quarto site if installed)
scripts/build-analysis-site.sh

# or step by step:
.venv/bin/jupyter nbconvert --to notebook --execute --inplace docs/analysis/wave_analysis.ipynb   # 1. run (needs data/snapshots/)
.venv/bin/jupyter nbconvert --to html --embed-images docs/analysis/wave_analysis.ipynb            # 2a. standalone HTML page
quarto render docs/analysis                                                                        # 2b. full site -> _site/  (needs: brew install --cask quarto)
```

> **Honesty:** the **quality** axis is the **5-rep × 2-judge ensemble**
> (cross-judge κ_quad ≈ 0.91); **safety** and **energy** are judge-free / measured.
> Everything is one commodity node (n = 1). See the notebook intro for provenance.
> Render artifacts (`_site/`, `*.html`) are git-ignored; the notebook outputs and
> `data/site/` exports are tracked.

**Accessibility.** Every figure carries a `#| fig-alt:` screen-reader description
at the top of its cell. Quarto applies these as `<img alt="…">` on `quarto render`
(the accessible build). The plain `nbconvert` HTML preview does **not** carry them
(nbconvert doesn't read Quarto cell directives) — use the Quarto site for the
accessible version.
