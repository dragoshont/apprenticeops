#!/usr/bin/env bash
# run-from-homelab.sh — CONTROL-side orchestrator. Runs on the homelab control node
# and drives the home-ai experiment node over SSH (homelab's key/cert is trusted by
# home-ai). Deterministic + idempotent: home-ai mirrors the EXACT pinned commit, runs
# the locked roster (scripts/run-roster.sh), and artifacts are pulled back by convention.
#
#   ./scripts/run-from-homelab.sh                 # launch the full roster (detached on home-ai)
#   LIMIT=2 ./scripts/run-from-homelab.sh         # stop-and-audit batch (inline) + collect + audit
#   ./scripts/run-from-homelab.sh collect         # pull artifacts for $RUN_ID anytime
#   ./scripts/run-from-homelab.sh status          # tail the node-side driver log
#
# Config (env): HOME_AI (ssh host/alias), REMOTE_DIR, BRANCH, RUN_ID, COLLECT.
# Trust: set up homelab->home-ai SSH first (homelab's pubkey or signed SSH cert in
# home-ai). This script uses BatchMode (no password prompts).
set -uo pipefail
HOME_AI="${HOME_AI:-home-ai}"
REMOTE_DIR="${REMOTE_DIR:-/opt/apprenticeops}"
BRANCH="${BRANCH:-main}"
REPO_URL="${REPO_URL:-https://github.com/dragoshont/apprenticeops}"
RUN_ID="${RUN_ID:-roster-$(date -u +%Y%m%d-%H%M)}"
COLLECT="${COLLECT:-data/collected/${RUN_ID}}"
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOME_AI")
ts() { date -uIs; }
log() { echo "[$(ts)] $*"; }

require_ssh() {
  "${SSH[@]}" true 2>/dev/null || {
    log "FATAL: cannot SSH to '$HOME_AI' in BatchMode. Set up the trusted homelab->home-ai"
    log "       key/cert first (homelab pubkey or CA-signed SSH cert in home-ai)."
    exit 2
  }
}

collect() {
  mkdir -p "$COLLECT/logs"
  log "collecting $RUN_ID artifacts -> $COLLECT"
  rsync -az "${HOME_AI}:${REMOTE_DIR}/results.${RUN_ID}.jsonl" "$COLLECT/"      2>/dev/null || log "  (no results yet)"
  rsync -az "${HOME_AI}:${REMOTE_DIR}/logs/${RUN_ID}/"         "$COLLECT/logs/" 2>/dev/null || true
  rsync -az "${HOME_AI}:${REMOTE_DIR}/calibration.json"        "$COLLECT/"      2>/dev/null || true
  rsync -az "${HOME_AI}:${REMOTE_DIR}/outputs/"                "$COLLECT/outputs/" 2>/dev/null || true
  log "collected -> $COLLECT"
}

case "${1:-run}" in
  collect)
    require_ssh; collect; exit 0 ;;
  status)
    require_ssh
    "${SSH[@]}" "tail -n 40 '${REMOTE_DIR}/logs/${RUN_ID}/driver.log' 2>/dev/null || echo '(no driver log for ${RUN_ID})'"
    exit 0 ;;
esac

log "=== orchestrate $RUN_ID  control=$(hostname) -> experiment=${HOME_AI}:${REMOTE_DIR} ==="
require_ssh

# 1) deterministic code state: home-ai mirrors the EXACT pinned origin/$BRANCH.
#    (Only TRACKED files are reset; gitignored results/outputs/logs/calibration are kept.)
log "--- syncing home-ai to origin/${BRANCH} ---"
COMMIT="$("${SSH[@]}" "set -e
  if [ ! -d '${REMOTE_DIR}/.git' ]; then git clone --quiet '${REPO_URL}' '${REMOTE_DIR}'; fi
  cd '${REMOTE_DIR}'
  git fetch --quiet origin '${BRANCH}'
  git reset --hard --quiet 'origin/${BRANCH}'
  git rev-parse --short HEAD")" || { log "FATAL: git sync on home-ai failed"; exit 2; }
log "home-ai at commit ${COMMIT}"

# 2) run
if [ -n "${LIMIT:-}" ]; then
  log "--- LIMIT=${LIMIT} stop-and-audit batch (inline) ---"
  "${SSH[@]}" "cd '${REMOTE_DIR}' && RUN_ID='${RUN_ID}' LIMIT='${LIMIT}' ./scripts/run-roster.sh" || log "WARN: audit batch returned non-zero"
  collect
  log "AUDIT NOW:  python3 scripts/audit-run.py ${COLLECT}/results.${RUN_ID}.jsonl   (must say AUDIT: PASS before the full run)"
else
  log "--- full roster (detached on home-ai) ---"
  "${SSH[@]}" "cd '${REMOTE_DIR}' && RUN_ID='${RUN_ID}' nohup ./scripts/run-roster.sh >'logs/${RUN_ID}.nohup' 2>&1 & echo started pid \$!"
  log "running detached on home-ai."
  log "  monitor:  ./scripts/run-from-homelab.sh status     (RUN_ID=${RUN_ID})"
  log "  collect:  ./scripts/run-from-homelab.sh collect     (RUN_ID=${RUN_ID})"
fi
