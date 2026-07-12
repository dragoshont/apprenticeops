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
# Config (env): HOME_AI (ssh host/alias), REMOTE_DIR, BRANCH, RUN_ID, COLLECT,
# SYNC_MODE=origin|local-commit|working-tree. Origin is the default;
# local-commit mirrors a clean committed source snapshot including .git for
# preflight/provenance verification; working-tree is an explicit dirty dev mode.
# Trust: set up homelab->home-ai SSH first (homelab's pubkey or signed SSH cert in
# home-ai). This script uses BatchMode (no password prompts).
set -uo pipefail
HOME_AI="${HOME_AI:-home-ai}"
REMOTE_DIR="${REMOTE_DIR:-/home/dragos/apprenticeops}"
BRANCH="${BRANCH:-main}"
REPO_URL="${REPO_URL:-https://github.com/dragoshont/apprenticeops}"
SYNC_MODE="${SYNC_MODE:-origin}"
RUN_ID="${RUN_ID:-roster-$(date -u +%Y%m%d-%H%M)}"
MODELS="${MODELS:-data/models.txt}"
MODEL_SET="${MODEL_SET:-manual}"
SCENARIOS="${SCENARIOS:-data/scenarios.json}"
SCENARIO_SET="${SCENARIO_SET:-all}"
RUN_MANIFEST="${RUN_MANIFEST:-data/run-manifest.json}"
MODEL_ARTIFACT_LOCK="${MODEL_ARTIFACT_LOCK:-}"
MEMORY_CONTEXT="${MEMORY_CONTEXT:-none}"
MEMORY_CONTEXT_FILE="${MEMORY_CONTEXT_FILE:-}"
INFERENCE_STRATEGY="${INFERENCE_STRATEGY:-baseline}"
INFERENCE_RUNTIME="${INFERENCE_RUNTIME:-ollama}"
LLAMA_CPP_MODEL_MAP="${LLAMA_CPP_MODEL_MAP:-}"
LLAMA_CPP_ARTIFACTS="${LLAMA_CPP_ARTIFACTS:-}"
LLAMA_CPP_EXTRA_ARGS="${LLAMA_CPP_EXTRA_ARGS:-}"
MAX_TOKENS_CAP="${MAX_TOKENS_CAP:-}"
RUN_REPEATS="${RUN_REPEATS:-}"
RUN_TEMP="${RUN_TEMP:-}"
RUN_ALLOW_UNLOCKED="${RUN_ALLOW_UNLOCKED:-}"
PREFLIGHT_ONLY="${PREFLIGHT_ONLY:-0}"
TIMEOUT_POLICY_ID="${TIMEOUT_POLICY_ID:-ceops-v2-zero-stall-retry}"
STRATEGY_PROMPT_FILE="${STRATEGY_PROMPT_FILE:-}"
COLLECT="${COLLECT:-data/collected/${RUN_ID}}"
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOME_AI")
ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
log() { echo "[$(ts)] $*"; }
q() { printf '%q' "$1"; }

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

# 1) code state. Default = sync the AI producer to the pushed source. Use
# SYNC_MODE=working-tree only for explicit dev runs with uncommitted local code;
# run.py stamps env.harness_source_dirty and env.harness_artifact_dirty.
if [ "$SYNC_MODE" = "origin" ]; then
  log "--- syncing home-ai to origin/${BRANCH} ---"
  COMMIT="$("${SSH[@]}" "set -e
    if [ ! -d '${REMOTE_DIR}/.git' ]; then git clone --quiet '${REPO_URL}' '${REMOTE_DIR}'; fi
    cd '${REMOTE_DIR}'
    git fetch --quiet origin '${BRANCH}'
    git reset --hard --quiet 'origin/${BRANCH}'
    git rev-parse --short HEAD")" || { log "FATAL: git sync on home-ai failed"; exit 2; }
  log "home-ai at commit ${COMMIT}"
elif [ "$SYNC_MODE" = "local-commit" ]; then
  test -d .git || { log "FATAL: local-commit requires a Git worktree"; exit 2; }
  SOURCE_DIRTY="$(git status --porcelain=v1 --untracked-files=all | python3 -c '
import sys
allowed = (
    "calibration.json", "logs/", "outputs/", "results.",
    "data/runs/", "data/run-batches/", "data/experiments/",
)
dirty = []
for raw in sys.stdin:
    value = raw.rstrip("\n")
    path = value[3:].strip() if len(value) > 3 else value.strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    if path and not path.startswith(allowed):
        dirty.append(value)
print("\n".join(dirty))
')"
  [ -z "$SOURCE_DIRTY" ] \
    || { log "FATAL: local-commit requires clean source files:"; printf '%s\n' "$SOURCE_DIRTY"; exit 2; }
  LOCAL_COMMIT="$(git rev-parse HEAD)" || { log "FATAL: cannot resolve local HEAD"; exit 2; }
  SYNC_SOURCE="$(mktemp -d)" || { log "FATAL: cannot create local commit staging directory"; exit 2; }
  if ! git clone --quiet --no-hardlinks . "$SYNC_SOURCE" \
      || ! git -C "$SYNC_SOURCE" checkout --quiet --detach "$LOCAL_COMMIT" \
      || [ -n "$(git -C "$SYNC_SOURCE" status --porcelain=v1 --untracked-files=all)" ]; then
    rm -rf "$SYNC_SOURCE"
    log "FATAL: cannot materialize a clean local commit snapshot"
    exit 2
  fi
  log "--- mirroring clean local commit ${LOCAL_COMMIT} to home-ai ---"
  "${SSH[@]}" "rm -rf $(q "$REMOTE_DIR") && mkdir -p $(q "$REMOTE_DIR")" \
    || { rm -rf "$SYNC_SOURCE"; log "FATAL: cannot reset ${REMOTE_DIR} on home-ai"; exit 2; }
  rsync -az --delete \
    --exclude '.venv/' --exclude 'dashboard/backend/.venv/' \
    --exclude 'dashboard/frontend/node_modules/' --exclude 'dashboard/frontend/dist/' \
    "$SYNC_SOURCE/" "${HOME_AI}:${REMOTE_DIR}/" \
    || { rm -rf "$SYNC_SOURCE"; log "FATAL: local commit rsync failed"; exit 2; }
  rm -rf "$SYNC_SOURCE"
  COMMIT="$("${SSH[@]}" "cd $(q "$REMOTE_DIR") && test -z \"\$(git status --porcelain=v1 --untracked-files=all)\" && git rev-parse HEAD")" \
    || { log "FATAL: mirrored local commit is not a clean Git worktree"; exit 2; }
  [ "$COMMIT" = "$LOCAL_COMMIT" ] \
    || { log "FATAL: mirrored commit ${COMMIT} != local ${LOCAL_COMMIT}"; exit 2; }
  log "home-ai at clean local commit ${COMMIT}"
else
  log "--- mirroring deployed working tree to home-ai (${SYNC_MODE}) ---"
  "${SSH[@]}" "mkdir -p $(q "$REMOTE_DIR")" || { log "FATAL: cannot create ${REMOTE_DIR} on home-ai"; exit 2; }
  rsync -az --delete \
    --exclude '.git/' --exclude '.venv/' --exclude 'dashboard/backend/.venv/' \
    --exclude 'dashboard/frontend/node_modules/' --exclude 'dashboard/frontend/dist/' \
    --exclude 'data/runs/' --exclude 'data/run-batches/' --exclude 'data/experiments/' \
    --exclude 'logs/' --exclude 'outputs/' --exclude 'results.*.jsonl*' \
    ./ "${HOME_AI}:${REMOTE_DIR}/" || { log "FATAL: rsync working tree to home-ai failed"; exit 2; }
  COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  DIRTY="$(git status --short 2>/dev/null | wc -l | tr -d ' ')"
  log "home-ai mirrored working tree at ${COMMIT} dirty_files=${DIRTY}"
fi

# 2) run
if [ -n "${LIMIT:-}" ] || [ "$PREFLIGHT_ONLY" = "1" ]; then
  log "--- LIMIT=${LIMIT:-none} preflight/stop-and-audit batch (inline) ---"
  "${SSH[@]}" "cd $(q "$REMOTE_DIR") && RUN_ID=$(q "$RUN_ID") MODELS=$(q "$MODELS") MODEL_SET=$(q "$MODEL_SET") SCENARIOS=$(q "$SCENARIOS") SCENARIO_SET=$(q "$SCENARIO_SET") RUN_MANIFEST=$(q "$RUN_MANIFEST") MODEL_ARTIFACT_LOCK=$(q "$MODEL_ARTIFACT_LOCK") TIMEOUT_POLICY_ID=$(q "$TIMEOUT_POLICY_ID") MEMORY_CONTEXT=$(q "$MEMORY_CONTEXT") MEMORY_CONTEXT_FILE=$(q "$MEMORY_CONTEXT_FILE") INFERENCE_STRATEGY=$(q "$INFERENCE_STRATEGY") INFERENCE_RUNTIME=$(q "$INFERENCE_RUNTIME") LLAMA_CPP_MODEL_MAP=$(q "$LLAMA_CPP_MODEL_MAP") LLAMA_CPP_ARTIFACTS=$(q "$LLAMA_CPP_ARTIFACTS") LLAMA_CPP_EXTRA_ARGS=$(q "$LLAMA_CPP_EXTRA_ARGS") MAX_TOKENS_CAP=$(q "$MAX_TOKENS_CAP") RUN_REPEATS=$(q "$RUN_REPEATS") RUN_TEMP=$(q "$RUN_TEMP") RUN_ALLOW_UNLOCKED=$(q "$RUN_ALLOW_UNLOCKED") PREFLIGHT_ONLY=$(q "$PREFLIGHT_ONLY") STRATEGY_PROMPT_FILE=$(q "$STRATEGY_PROMPT_FILE") LIMIT=$(q "${LIMIT:-}") ./scripts/run-roster.sh" || { log "FATAL: inline run returned non-zero"; exit 3; }
  if [ "$PREFLIGHT_ONLY" = "1" ]; then
    log "preflight-only proof completed; no collection or inference requested"
    exit 0
  fi
  collect
  log "AUDIT NOW:  python3 scripts/audit-run.py ${COLLECT}/results.${RUN_ID}.jsonl   (must say AUDIT: PASS before the full run)"
else
  log "--- full roster (detached on home-ai) ---"
  "${SSH[@]}" "cd $(q "$REMOTE_DIR") && mkdir -p logs && RUN_ID=$(q "$RUN_ID") MODELS=$(q "$MODELS") MODEL_SET=$(q "$MODEL_SET") SCENARIOS=$(q "$SCENARIOS") SCENARIO_SET=$(q "$SCENARIO_SET") RUN_MANIFEST=$(q "$RUN_MANIFEST") MODEL_ARTIFACT_LOCK=$(q "$MODEL_ARTIFACT_LOCK") TIMEOUT_POLICY_ID=$(q "$TIMEOUT_POLICY_ID") MEMORY_CONTEXT=$(q "$MEMORY_CONTEXT") MEMORY_CONTEXT_FILE=$(q "$MEMORY_CONTEXT_FILE") INFERENCE_STRATEGY=$(q "$INFERENCE_STRATEGY") INFERENCE_RUNTIME=$(q "$INFERENCE_RUNTIME") LLAMA_CPP_MODEL_MAP=$(q "$LLAMA_CPP_MODEL_MAP") LLAMA_CPP_ARTIFACTS=$(q "$LLAMA_CPP_ARTIFACTS") LLAMA_CPP_EXTRA_ARGS=$(q "$LLAMA_CPP_EXTRA_ARGS") MAX_TOKENS_CAP=$(q "$MAX_TOKENS_CAP") RUN_REPEATS=$(q "$RUN_REPEATS") RUN_TEMP=$(q "$RUN_TEMP") RUN_ALLOW_UNLOCKED=$(q "$RUN_ALLOW_UNLOCKED") STRATEGY_PROMPT_FILE=$(q "$STRATEGY_PROMPT_FILE") setsid nohup ./scripts/run-roster.sh >$(q "logs/${RUN_ID}.nohup") 2>&1 </dev/null & echo started-detached" </dev/null
  log "running detached on home-ai."
  log "  monitor:  ./scripts/run-from-homelab.sh status     (RUN_ID=${RUN_ID})"
  log "  collect:  ./scripts/run-from-homelab.sh collect     (RUN_ID=${RUN_ID})"
fi
