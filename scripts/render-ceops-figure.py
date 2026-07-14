#!/usr/bin/env python3
"""Render the CEOps controlled-selection scatter as an accessible inline SVG.

Reads the locked machine-readable exports (data/site/controlled_models.csv and
data/site/summary.json) and writes docs/analysis/_ceops-pareto.svg, a partial
that the Overview and Selection pages include. The SVG mirrors the CSV exactly
the way the on-page table does; it is shell chrome, not a paper figure, and it
does not touch docs/analysis/figures/ or any notebook output.

Encoding (bound to axes the locked data actually has -- no invented latency):
  x = energy (mWh per answer), lower is cheaper
  y = judged quality (%), higher is better
  bubble area = safety/refusal (%), larger is safer
  ring + label + teal = on the three-axis (quality x safety x energy) front
The three-axis front is deliberately NOT connected by a 2-D polyline, which
would misrepresent a three-axis frontier as a two-axis curve.

Deterministic: the same inputs always produce byte-identical output.
"""
from __future__ import annotations

import csv
import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "site" / "controlled_models.csv"
SUMMARY_PATH = ROOT / "data" / "site" / "summary.json"
# A Markdown partial so `{{< include >}}` splices the raw SVG into the page.
OUT_PATH = ROOT / "docs" / "analysis" / "_ceops-pareto.md"

# viewBox geometry (scales to column width via CSS width:100%).
W, H = 760.0, 470.0
M = {"top": 24.0, "right": 118.0, "bottom": 58.0, "left": 62.0}
PW = W - M["left"] - M["right"]
PH = H - M["top"] - M["bottom"]

X_MAX_MWH = 170.0            # energy ceiling (max observed ~155 mWh)
Y_MIN, Y_MAX = 25.0, 75.0   # quality percent window


def x_px(mwh: float) -> float:
    return M["left"] + (mwh / X_MAX_MWH) * PW


def y_px(q_pct: float) -> float:
    return M["top"] + (1 - (q_pct - Y_MIN) / (Y_MAX - Y_MIN)) * PH


def r_safety(safety_frac: float) -> float:
    # Bubble AREA encodes safety: radius grows with sqrt so area is linear.
    return 5.0 + math.sqrt(max(0.0, safety_frac - 0.55)) * 24.0


def short_label(model: str) -> str:
    # Drop the registry prefix and keep the recognisable tag.
    tag = model.split("/")[-1]
    return tag


def as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "t"}


def fmt(value: float, places: int = 0) -> str:
    return f"{value:.{places}f}"


def load_rows() -> list[dict]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    parsed = []
    for row in rows:
        quality = float(row["judge_score_fraction"]) * 100
        safety = float(row["safety_fraction"]) * 100
        energy = float(row["mean_energy_wh_per_answer"]) * 1000  # Wh -> mWh
        parsed.append(
            {
                "model": row["model"],
                "bracket": row.get("legacy_footprint_bracket", "") or "n/a",
                "quality": quality,
                "safety": safety,
                "safety_frac": float(row["safety_fraction"]),
                "energy": energy,
                "front": as_bool(row.get("three_axis_pareto", "")),
            }
        )
    # Draw dominated first, front last (front sits on top).
    parsed.sort(key=lambda r: (r["front"], r["quality"]))
    return parsed


def build_svg(rows: list[dict], pick: str) -> str:
    x_ticks = [0, 25, 50, 75, 100, 125, 150]
    y_ticks = [25, 35, 45, 55, 65, 75]
    parts: list[str] = []
    parts.append(
        '<svg class="ceops-pareto" viewBox="0 0 {w:.0f} {h:.0f}" '
        'role="img" aria-labelledby="ceops-pareto-title ceops-pareto-desc">'.format(w=W, h=H)
    )
    parts.append(
        '<title id="ceops-pareto-title">Controlled selection: judged quality '
        "versus energy per answer, bubble area for safety.</title>"
    )
    parts.append(
        '<desc id="ceops-pareto-desc">Twenty-four controlled models under one '
        "power regime. Seven are on the three-axis quality, safety and energy "
        "front and are ringed and labelled. The complete data table follows "
        "this chart.</desc>"
    )

    # Grid + Y ticks
    for t in y_ticks:
        yy = y_px(t)
        parts.append(f'<line class="grid-line" x1="{x_px(0):.1f}" y1="{yy:.1f}" x2="{M["left"]+PW:.1f}" y2="{yy:.1f}"/>')
        parts.append(f'<text class="tick" x="{M["left"]-8:.1f}" y="{yy+4:.1f}" text-anchor="end">{t}</text>')
    # X ticks
    for t in x_ticks:
        parts.append(f'<text class="tick" x="{x_px(t):.1f}" y="{M["top"]+PH+20:.1f}" text-anchor="middle">{t}</text>')

    # Axes
    parts.append(f'<line class="axis-line" x1="{M["left"]:.1f}" y1="{M["top"]+PH:.1f}" x2="{M["left"]+PW:.1f}" y2="{M["top"]+PH:.1f}"/>')
    parts.append(f'<line class="axis-line" x1="{M["left"]:.1f}" y1="{M["top"]:.1f}" x2="{M["left"]:.1f}" y2="{M["top"]+PH:.1f}"/>')
    parts.append(f'<text class="axis-label" x="{M["left"]+PW/2:.1f}" y="{H-12:.1f}" text-anchor="middle">Energy (mWh per answer) \u2014 lower is cheaper</text>')
    parts.append(f'<text class="axis-label" transform="translate(16 {M["top"]+PH/2:.1f}) rotate(-90)" text-anchor="middle">Judged quality (%)</text>')

    for row in rows:
        cx, cy = x_px(row["energy"]), y_px(row["quality"])
        r = r_safety(row["safety_frac"])
        is_pick = row["model"] == pick
        on_front = row["front"]
        if on_front:
            stroke = "var(--chart-front)"
            fill = "var(--chart-front-fill)"
        else:
            stroke = "var(--chart-dominated)"
            fill = "var(--chart-dominated-fill)"
        aria = (
            f'{short_label(row["model"])}. Quality {fmt(row["quality"],1)} percent. '
            f'Safety {fmt(row["safety"],1)} percent. Energy {fmt(row["energy"])} milliwatt hours per answer. '
            f'{"On the three-axis front" if on_front else "Dominated"}'
            f'{". Balanced recommendation." if is_pick else "."}'
        )
        parts.append(f'<g class="pt-group" tabindex="0" role="img" aria-label="{html.escape(aria)}">')
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
            f'style="fill:{fill};stroke:{stroke};stroke-width:{2 if on_front else 1.4}"/>'
        )
        if is_pick:
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r+4:.1f}" '
                f'style="fill:none;stroke:var(--rec-line);stroke-width:1.5;stroke-dasharray:2 2"/>'
            )
        if on_front:
            label_right = cx < M["left"] + PW * 0.62
            lx = cx + r + 6 if label_right else cx - r - 6
            anchor = "start" if label_right else "end"
            label = short_label(row["model"]) + (" \u00b7 pick" if is_pick else "")
            parts.append(f'<text class="pt-label" x="{lx:.1f}" y="{cy-r-4:.1f}" text-anchor="{anchor}">{html.escape(label)}</text>')
        parts.append(f'<circle class="pt-focus-ring" cx="{cx:.1f}" cy="{cy:.1f}" r="{r+5:.1f}"/>')
        parts.append("</g>")

    parts.append("</svg>")
    return "\n".join(parts)


def build_table(rows: list[dict], pick: str) -> str:
    ordered = sorted(rows, key=lambda r: r["quality"], reverse=True)
    out: list[str] = ['<div class="ceops-table-wrap">']
    out.append('<table class="ceops-table">')
    out.append(
        "<caption class=\"u-vh\">Controlled selection: 24 models under one power "
        "regime, ranked by judged quality. All rows are verified analysis v1 "
        "evidence; standing marks the seven on the three-axis front.</caption>"
    )
    out.append(
        "<thead><tr><th scope=\"col\">Model</th><th scope=\"col\">Footprint</th>"
        "<th scope=\"col\">Quality %</th><th scope=\"col\">Safety %</th>"
        "<th scope=\"col\">Energy mWh</th><th scope=\"col\">Standing</th></tr></thead>"
    )
    out.append("<tbody>")
    for row in ordered:
        classes = []
        if row["front"]:
            classes.append("is-front")
        if row["model"] == pick:
            classes.append("is-pick")
        cls = f' class="{" ".join(classes)}"' if classes else ""
        if row["front"]:
            label = "On front · pick" if row["model"] == pick else "On front"
            standing = f'<span class="ceops-badge ceops-badge--verified">{label}</span>'
        else:
            standing = '<span class="ceops-table__na">Dominated</span>'
        out.append(
            f"<tr{cls}><th scope=\"row\"><code>{html.escape(row['model'])}</code></th>"
            f"<td>{html.escape(row['bracket'])}</td>"
            f"<td class=\"u-tnum\">{fmt(row['quality'],1)}</td>"
            f"<td class=\"u-tnum\">{fmt(row['safety'],1)}</td>"
            f"<td class=\"u-tnum\">{fmt(row['energy'])}</td>"
            f"<td>{standing}</td></tr>"
        )
    out.append("</tbody></table></div>")
    return "\n".join(out)


def main() -> None:
    rows = load_rows()
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    pick = summary.get("controlled_three_axis_pick", "")
    front = sum(1 for r in rows if r["front"])
    total = len(rows)
    svg = build_svg(rows, pick)
    legend = (
        '<div class="ceops-chartlegend" aria-hidden="true">'
        '<span><span class="swatch"></span>On the three-axis front</span>'
        '<span><span class="swatch dominated"></span>Dominated</span>'
        "<span>Bubble area = safety (refusal rate)</span>"
        "</div>"
    )
    banner = (
        f"<!-- generated by scripts/render-ceops-figure.py from "
        f"data/site/controlled_models.csv; {front} of {total} on the three-axis "
        f"front; do not edit by hand -->\n"
    )
    OUT_PATH.write_text(banner + svg + "\n" + legend + "\n", encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(ROOT)} ({front} of {total} front points, pick={pick})")

    table_path = ROOT / "docs" / "analysis" / "_ceops-table.md"
    table_banner = (
        "<!-- generated by scripts/render-ceops-figure.py from "
        "data/site/controlled_models.csv; do not edit by hand -->\n"
    )
    table_path.write_text(table_banner + build_table(rows, pick) + "\n", encoding="utf-8")
    print(f"wrote {table_path.relative_to(ROOT)} ({total} rows)")


if __name__ == "__main__":
    main()
