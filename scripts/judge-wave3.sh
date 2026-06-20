#!/usr/bin/env bash
# judge-wave3.sh — Mac-side Wave-3 post-processing: fetch -> dedup -> 2-judge
# QUALITY pass. Run this ON YOUR MAC after scripts/run-wave3.sh finishes on the node.
#
# Safety + energy are FREE: they're deterministic and already in results.wave3.jsonl
# from the run. Only the QUALITY axis needs the frontier judges, and that is the
# EXPENSIVE step:
#   calls ≈ (clean tags) x 19 scenarios x 5 reps x 2 judges  (~43 tags -> ~8,200 calls)
#   ~7.7 Copilot AI credits/call (mostly cached context).
# To spend less, use the CHEAP option printed at the end (rep 0 only / single judge).
#
# The judge reads each model's ANSWER TEXT from the node's outputs/ dir (keyed by
# model+scenario+rep), so we rsync that too — not just the metrics jsonl.
#
# Prereqs: Copilot CLI installed + authenticated (`npm i -g @github/copilot`, then
# run `copilot` once). JUDGE_BACKEND=copilot drives claude-opus-4.8 + gpt-5.5 via
# your Copilot subscription (no Anthropic/OpenAI key needed).
set -euo pipefail
cd "$(dirname "$0")/.."                       # repo root
NODE="${NODE:-dragos@home-ai.hont.ro}"
SME="${SME:-/tmp/sme-var}"
W3=".tmp/wave3"
JUDGED="${JUDGED:-.tmp/judge/judged.wave3.jsonl}"
mkdir -p "$W3" "$(dirname "$JUDGED")"

echo "== 1/3  fetch results + answer texts from $NODE:$SME =="
scp "$NODE:$SME/results.wave3.jsonl" "$W3/"
# answer texts the judge reads (incremental; pulls only what's new on re-runs).
rsync -az --info=progress2 "$NODE:$SME/outputs/" "$W3/outputs/"

echo "== 2/3  dedup (drop pull_failed + DNF, collapse dups, completeness report) =="
# wave2-dedup.py is generic (any results.jsonl). Review its per-model report —
# any hf.co tag that pull-failed needs a manual re-pull before it can be judged.
python3 scripts/wave2-dedup.py "$W3/results.wave3.jsonl" "$W3/results.wave3.clean.jsonl"

echo "== 3/3  two-judge QUALITY pass (claude-opus-4.8 primary + gpt-5.5 ensemble), resumable =="
echo "        (each answer scored by BOTH judges; safe to Ctrl-C and re-run — it skips done rows)"
JUDGE_BACKEND=copilot JUDGE_MODEL=claude-opus-4.8 \
python3 judge.py --judge \
  --results "$W3/results.wave3.clean.jsonl" \
  --outputs-dir "$W3/outputs" \
  --ensemble copilot:gpt-5.5 \
  --out "$JUDGED"
echo
echo "judged -> $JUDGED   (one row per model x scenario x rep x judge; cost summary printed above)"
echo
echo "NEXT — fold the new models into the published study:"
echo "  • safety + energy: convert $W3/results.wave3.clean.jsonl into data/snapshots/"
echo "    results_snapshot.csv rows (same schema), then re-run docs/analysis/"
echo "    wave_analysis.ipynb headless to rebuild data/site/ + figures, and commit."
echo "  • quality: merge $JUDGED into the 2-judge consensus (mean over judges x 5 reps)"
echo "    used by judged_snapshot.csv, then rebuild + commit."
echo
echo "CHEAP option (~1/10th the credits — point estimate only, no CI):"
echo "  grep '\"rep\": 0,' $W3/results.wave3.clean.jsonl > $W3/results.wave3.rep0.jsonl"
echo "  JUDGE_BACKEND=copilot JUDGE_MODEL=claude-opus-4.8 python3 judge.py --judge \\"
echo "    --results $W3/results.wave3.rep0.jsonl --outputs-dir $W3/outputs \\"
echo "    --out .tmp/judge/judged.wave3.rep0.jsonl     # 1 rep, 1 judge"
