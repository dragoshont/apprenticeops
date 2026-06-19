#!/usr/bin/env python3
"""render_scenarios.py — render data/scenarios.json into a human-readable
scenario book (data/SCENARIOS.md).

Unlike MODEL-PROMPTS.md (which shows only the prompt text a model receives),
this view includes the **gold answer, deterministic checks, and judge rubric**
for every scenario — i.e. everything a human reviewer needs to read the
benchmark. The JSON remains the source of truth; regenerate after any edit:

    python3 render_scenarios.py
"""
from __future__ import annotations

import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "data", "scenarios.json")
OUT = os.path.join(ROOT, "data", "SCENARIOS.md")


def render_check(c) -> str:
    """Render one deterministic check as a bullet, tolerating any check shape."""
    if not isinstance(c, dict):
        return f"- `{c}`"
    desc = c.get("desc") or c.get("description") or ""
    ctype = c.get("type", "?")
    extras = {k: v for k, v in c.items() if k not in ("type", "desc", "description")}
    payload = "; ".join(
        f"{k}=[{', '.join(map(str, v))}]" if isinstance(v, list) else f"{k}={v}"
        for k, v in extras.items()
    )
    head = f"- **{desc}**" if desc else "- (check)"
    return head + f" — `{ctype}`" + (f": {payload}" if payload else "")


def render_scenario(s: dict) -> str:
    sid = s.get("id", "?")
    badges = " · ".join(
        f"**{k}**&nbsp;`{s[k]}`"
        for k in ("class", "aiopslab_task", "difficulty", "grounding")
        if s.get(k)
    )
    out = [f"## {sid}", "", badges, ""]
    if s.get("context"):
        out += ["### Context", "", "```text", str(s["context"]).rstrip(), "```", ""]
    if s.get("question"):
        out += ["### Task", "", str(s["question"]).rstrip(), ""]
    if s.get("gold_answer"):
        out += ["### Gold answer", "", str(s["gold_answer"]).rstrip(), ""]
    checks = s.get("deterministic_checks") or []
    if checks:
        out += ["### Deterministic checks (judge-free)", ""]
        out += [render_check(c) for c in checks]
        out += [""]
    if s.get("judge_rubric"):
        out += ["### Judge rubric", "", str(s["judge_rubric"]).rstrip(), ""]
    limits = [f"{k}=`{s[k]}`" for k in ("max_tokens", "timeout_s") if s.get(k)]
    if limits:
        out += [f"*Limits: {' · '.join(limits)}*", ""]
    out += ["---", ""]
    return "\n".join(out)


def main() -> None:
    data = json.load(open(SRC, encoding="utf-8"))
    scen = data["scenarios"]
    by = lambda key: ", ".join(  # noqa: E731
        f"{k} {v}" for k, v in sorted(Counter(s.get(key, "?") for s in scen).items())
    )

    head = [
        "# ApprenticeOps — scenario book (human-readable)",
        "",
        "> **Auto-generated** from [`scenarios.json`](scenarios.json) by",
        "> [`render_scenarios.py`](../render_scenarios.py) — do **not** edit by hand.",
        "> Regenerate after any scenario change:",
        ">",
        "> ```bash",
        "> python3 render_scenarios.py",
        "> ```",
        ">",
        "> The JSON is the source of truth. This view adds the **gold answers,",
        "> deterministic checks, and judge rubric** that `MODEL-PROMPTS.md`",
        "> (prompt text only) omits — it is the file a human reviewer reads.",
        "",
        f"**{len(scen)} scenarios.** By class: {by('class')}. "
        f"By difficulty: {by('difficulty')}. By grounding: {by('grounding')}.",
        "",
        "| # | id | class | difficulty | grounding |",
        "|---|----|-------|-----------|-----------|",
    ]
    for i, s in enumerate(scen, 1):
        anchor = str(s.get("id", "")).lower()
        head.append(
            f"| {i} | [`{s.get('id', '?')}`](#{anchor}) | {s.get('class', '')} "
            f"| {s.get('difficulty', '')} | {s.get('grounding', '')} |"
        )
    head += ["", "---", ""]

    body = [render_scenario(s) for s in scen]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(head) + "\n" + "\n".join(body))
    print(f"wrote {OUT}: {len(scen)} scenarios "
          f"({os.path.getsize(OUT)} bytes)")


if __name__ == "__main__":
    main()
