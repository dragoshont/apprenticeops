#!/usr/bin/env bash
# run-e2e.sh — ONE-SHOT autonomous end-to-end pipeline launcher (runs ON the home
# node). A single command launches BOTH schedulers and returns; they then run to
# completion with NO further intervention, each logging to home so progress is
# always visible:
#   producer (inference)    -> detached on the ai node  (scripts/run-from-homelab.sh)
#   consumer (judge+commit)  -> detached on home, flock-guarded (scripts/judge-scheduler.sh)
#
# Usage (on home, from ~/apprenticeops):
#   RUN_ID=e2e-1 MODELS=data/models.dryrun.txt ./scripts/run-e2e.sh     # launch both, return
#   RUN_ID=e2e-1 ./scripts/run-e2e.sh progress                          # snapshot progress
#   RUN_ID=e2e-1 ./scripts/run-e2e.sh watch                             # live (refresh 20s)
#
# Logs on home (all under data/runs/<RUN_ID>/):
#   e2e.log               launch trace + the snapshot at launch
#   judge-scheduler.log   every consumer line (collect/judge/persist)
#   judge.log             judge.py per-answer scoring output
#   pipeline-ledger.jsonl one line per stage transition per model (the S1->S7 trace)
#   judge-scheduler.status current consumer status (single line)
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="/usr/local/bin:$PATH"            # node + copilot (nvm-symlinked) in daemon PATH

RUN_ID="${RUN_ID:-e2e-$(date -u +%Y%m%d-%H%M)}"
MODELS="${MODELS:-data/models.dryrun.txt}"
AI="${AI:-dragos@home-ai.hont.ro}"
AI_REPO="${AI_REPO:-/home/dragos/apprenticeops}"
POLL_S="${POLL_S:-15}"
WORK="data/runs/${RUN_ID}"
LOG="${WORK}/e2e.log"
mkdir -p "$WORK"
# consumer exits cleanly once EXPECT models are judged; default = model count in MODELS
EXPECT="${EXPECT:-$(grep -cvE '^[[:space:]]*(#|$)' "$MODELS" 2>/dev/null || echo 0)}"
ts() { date -uIs; }
elog() { echo "[$(ts)] $*" | tee -a "$LOG"; }

progress() {
  echo "===== E2E PROGRESS  RUN_ID=$RUN_ID  $(ts) ====="
  echo "-- PRODUCER (ai, inference) --"
  ssh -o BatchMode=yes -o ConnectTimeout=8 "$AI" \
    "cd '$AI_REPO'; echo rows=\$(wc -l < results.${RUN_ID}.jsonl 2>/dev/null); \
     echo emitted=\$(grep -c . results.${RUN_ID}.jsonl.done 2>/dev/null); \
     echo run.py_alive=\$(pgrep -fc '[r]un.py --models' || echo 0); \
     tail -n 2 logs/${RUN_ID}/driver.log 2>/dev/null" 2>/dev/null | sed 's/^/  /' \
    || echo "  (ai unreachable)"
  echo "-- CONSUMER (home, judge+commit) --"
  echo "  status: $(cat "${WORK}/judge-scheduler.status" 2>/dev/null || echo '(none yet)')"
  echo "  judged: $(wc -l < "${WORK}/judged.${RUN_ID}.jsonl" 2>/dev/null || echo 0) rows; models: $(jq -r .model "${WORK}/judged.${RUN_ID}.jsonl" 2>/dev/null | sort -u | tr '\n' ' ')/ target ${EXPECT}"
  tail -n 5 "${WORK}/pipeline-ledger.jsonl" 2>/dev/null | sed 's/^/  ledger: /'
  git log --oneline "experiment/${RUN_ID}" 2>/dev/null | head -3 | sed 's/^/  commit: /'
  echo "  consumer alive: $(pgrep -fc '[j]udge-scheduler' || echo 0)"
}

case "${1:-run}" in
  progress|status) progress; exit 0 ;;
  watch) while true; do clear; progress; sleep 20; done ;;
esac

elog "=== E2E LAUNCH  RUN_ID=$RUN_ID  models=$MODELS  expect=$EXPECT ==="
elog "launching PRODUCER on ai (detached) ..."
RUN_ID="$RUN_ID" MODELS="$MODELS" HOME_AI="$AI" REMOTE_DIR="$AI_REPO" \
  ./scripts/run-from-homelab.sh >>"$LOG" 2>&1 || elog "WARN: producer launch returned non-zero"
elog "launching CONSUMER on home (detached, flock-guarded) ..."
RUN_ID="$RUN_ID" AI="$AI" AI_REPO="$AI_REPO" EXPECT="$EXPECT" POLL_S="$POLL_S" \
  setsid nohup ./scripts/judge-scheduler.sh >>"${WORK}/judge-scheduler.out" 2>&1 </dev/null &
elog "both launched autonomously. watch with:  RUN_ID=$RUN_ID ./scripts/run-e2e.sh progress"
progress | tee -a "$LOG"
