#!/usr/bin/env python3
"""Export the per-answer 2-judge score pairs to a committed CSV so the judge
agreement (kappa, Bland-Altman, confusion) reproduces from the repo WITHOUT the
raw, gitignored judge logs.

Source: .tmp/judge/judged.var.{claude,gpt55}.jsonl (R=5 variance pass; gitignored,
author-only). Output: data/site/judge_pairs.csv (committed), columns
model,scenario,rep,claude,gpt. Run by the author whenever the variance judges
change; the CSV is the shareable artifact.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE = ROOT / ".tmp/judge/judged.var.claude.jsonl"
GPT = ROOT / ".tmp/judge/judged.var.gpt55.jsonl"
OUT = ROOT / "data/site/judge_pairs.csv"


def load(path):
    rows = {}
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        s = o.get("score")
        if s is None:
            continue
        rows[(o["model"], o["scenario"], str(o.get("rep")))] = int(round(float(s)))
    return rows


if not CLAUDE.exists() or not GPT.exists():
    sys.exit(f"raw judge logs not found ({CLAUDE}, {GPT}) — author-only; CSV left as-is")

claude = load(CLAUDE)
gpt = load(GPT)
keys = sorted(set(claude) & set(gpt))
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w") as f:
    f.write("model,scenario,rep,claude,gpt\n")
    for model, scenario, rep in keys:
        f.write(f"{model},{scenario},{rep},{claude[(model, scenario, rep)]},{gpt[(model, scenario, rep)]}\n")
print(f"wrote {OUT} — {len(keys)} judge pairs")
