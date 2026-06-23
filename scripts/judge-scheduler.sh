#!/usr/bin/env bash
# judge-scheduler.sh — the EVALUATION stage of the pipeline (runs ON the home node).
#
# Independently consumes the producer's per-model completion events (the `.done`
# marker, stage S4) and runs, per model:
#     S5 collect  — rsync the model's result rows + answer texts off `ai`
#     S6 judge    — the 2-judge pair (claude-opus-4.8 + gpt-5.5) via the Copilot CLI
#     S7 persist  — commit the model's evidence to the experiment branch + push
#
# It is decoupled from the producer (only the `.done` marker couples them),
# idempotent, and safe to `kill -9` + restart. Every stage transition is appended
# to data/runs/<RUN_ID>/pipeline-ledger.jsonl (the live status board AND the paper's
# reproducibility trace). No secrets are ever written or committed.
#
#   RUN_ID=roster-YYYYMMDD-HHMM ./scripts/judge-scheduler.sh            # run until killed
#   RUN_ID=... EXPECT=2 ./scripts/judge-scheduler.sh                    # dry-run: stop after 2 judged
set -uo pipefail
cd "$(dirname "$0")/.."

RUN_ID="${RUN_ID:?set RUN_ID (the producer run id, e.g. roster-20260624-1200)}"
AI="${AI:-dragos@home-ai.hont.ro}"
AI_REPO="${AI_REPO:-/home/dragos/apprenticeops}"                 # where run-roster.sh runs on `ai`
BRANCH="${BRANCH:-experiment/${RUN_ID}}"
POLL_S="${POLL_S:-30}"
ENSEMBLE="${ENSEMBLE:-copilot:gpt-5.5}"
JUDGE_MODEL="${JUDGE_MODEL:-claude-opus-4.8}"
EXPECT="${EXPECT:-0}"                               # >0 = exit once this many models are judged

RESULTS="results.${RUN_ID}.jsonl"
WORK="data/runs/${RUN_ID}"
MIRROR="${WORK}/_mirror"                            # local mirror of the ai artifacts
LEDGER="${WORK}/pipeline-ledger.jsonl"
JUDGED="${WORK}/judged.${RUN_ID}.jsonl"
STATUS="${WORK}/judge-scheduler.status"
LOG="${WORK}/judge-scheduler.log"
mkdir -p "$WORK" "$MIRROR/outputs"

SSH="ssh -o BatchMode=yes -o ConnectTimeout=10"
ts() { date -uIs; }
log() { echo "[$(ts)] $*" | tee -a "$LOG" >&2; }
status() { echo "[$(ts)] $*" >"$STATUS"; log "$*"; }
ledger() {  # model stage ok [detail]
  printf '{"model":"%s","stage":"%s","ts":%s,"ok":%s,"detail":"%s"}\n' \
    "$1" "$2" "$(date +%s)" "$3" "${4:-}" >>"$LEDGER"
}
judged_models() { [ -f "$JUDGED" ] && jq -r '.model' "$JUDGED" 2>/dev/null | sort -u; }

log "consumer up: RUN_ID=$RUN_ID branch=$BRANCH ai=$AI expect=${EXPECT:-inf}"
# experiment branch: create from current HEAD if missing, then track it on origin
git rev-parse --verify "$BRANCH" >/dev/null 2>&1 || git branch "$BRANCH"
git checkout "$BRANCH" >/dev/null 2>&1 || { log "FATAL: cannot checkout $BRANCH"; exit 1; }
git push -q -u origin "$BRANCH" 2>/dev/null || true

while true; do
  # ---- S5 collect (bulk mirror of the producer's artifacts) ----------------
  rsync -az -e "$SSH" "$AI:$AI_REPO/$RESULTS"      "$MIRROR/"          2>/dev/null || true
  rsync -az -e "$SSH" "$AI:$AI_REPO/$RESULTS.done" "$MIRROR/"          2>/dev/null || true
  rsync -az -e "$SSH" "$AI:$AI_REPO/outputs/"      "$MIRROR/outputs/"  2>/dev/null || true

  completed=()
  [ -f "$MIRROR/$RESULTS.done" ] && \
    mapfile -t completed < <(jq -r '.model' "$MIRROR/$RESULTS.done" 2>/dev/null | sort -u)
  already="$(judged_models)"

  for m in "${completed[@]}"; do
    [ -z "$m" ] && continue
    grep -qxF "$m" <<<"$already" 2>/dev/null && continue      # already judged -> skip
    msafe="${m//\//_}"; msafe="${msafe//:/_}"

    status "model $m -> S5 collect"; ledger "$m" collect 1
    jq -c --arg m "$m" 'select(.model==$m)' "$MIRROR/$RESULTS" \
      >"$WORK/$msafe.results.jsonl" 2>/dev/null || true
    if [ ! -s "$WORK/$msafe.results.jsonl" ]; then
      ledger "$m" collect 0 "no rows yet"; status "model $m: no rows yet, retry next poll"; continue
    fi

    status "model $m -> S6 judge"; ledger "$m" judge 1
    if JUDGE_BACKEND=copilot JUDGE_MODEL="$JUDGE_MODEL" \
         python3 judge.py --judge --results "$WORK/$msafe.results.jsonl" \
           --outputs-dir "$MIRROR/outputs" --ensemble "$ENSEMBLE" \
           --out "$JUDGED" >>"$WORK/judge.log" 2>&1; then
      ledger "$m" judge 1 "done"
    else
      ledger "$m" judge 0 "judge.py failed"; status "model $m: S6 judge FAILED (see judge.log)"; continue
    fi

    status "model $m -> S7 persist"
    gzip -kf "$WORK/$msafe.results.jsonl"
    git add "$WORK/$msafe.results.jsonl.gz" "$JUDGED" "$LEDGER" "$STATUS" 2>/dev/null || true
    if git commit -q -m "experiment($RUN_ID): judged $m"; then
      if git push -q origin "$BRANCH" 2>/dev/null; then
        ledger "$m" persist 1 "$(git rev-parse --short HEAD)"
      else
        ledger "$m" persist 0 "push failed (committed locally)"
      fi
    else
      ledger "$m" persist 0 "nothing to commit"
    fi
    status "model $m -> done (committed)"
  done

  njudged="$(judged_models | grep -c . 2>/dev/null || echo 0)"
  if [ "${EXPECT:-0}" -gt 0 ] && [ "${njudged:-0}" -ge "$EXPECT" ]; then
    status "EXPECT=$EXPECT reached ($njudged judged) — consumer exiting cleanly"
    break
  fi
  sleep "$POLL_S"
done
