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
TRUSTED_PYTHON="/usr/bin/python3"
TRUSTED_GIT="/usr/bin/git"
[[ -x "$TRUSTED_PYTHON" && -x "$TRUSTED_GIT" ]] || {
  echo "FATAL: trusted Python or Git executable is unavailable" >&2
  exit 2
}
SCRIPT_PATH="$("$TRUSTED_PYTHON" -I - "${BASH_SOURCE[0]}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1]).resolve(strict=True)
if path.stat().st_nlink != 1:
  raise SystemExit("orchestrator entrypoint must have exactly one hard link")
print(path)
PY
)" || { echo "FATAL: cannot resolve physical orchestrator path" >&2; exit 2; }
SCRIPT_DIR="${SCRIPT_PATH%/*}"
SCRIPT_DIR="$(cd "$SCRIPT_DIR" && pwd -P)"
CANDIDATE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
for override in \
  GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR \
  GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES \
  GIT_CEILING_DIRECTORIES GIT_DISCOVERY_ACROSS_FILESYSTEM \
  GIT_CONFIG_COUNT GIT_CONFIG_GLOBAL GIT_CONFIG_SYSTEM; do
  [[ -z "${!override-}" ]] || {
    echo "FATAL: ambient Git repository override is not allowed: $override" >&2
    exit 2
  }
done
while IFS='=' read -r override _value; do
  case "$override" in
    GIT_CONFIG_KEY_*|GIT_CONFIG_VALUE_*)
      echo "FATAL: ambient Git repository override is not allowed: $override" >&2
      exit 2
      ;;
  esac
done < <(/usr/bin/env)
[[ -x /usr/bin/git && -e "$CANDIDATE_ROOT/.git" && ! -L "$CANDIDATE_ROOT/.git" ]] || {
  echo "FATAL: canonical Git executable or repository metadata is unavailable" >&2
  exit 2
}
clean_git_at() {
  local work_tree="$1"
  shift
  /usr/bin/env -i HOME="${HOME:-}" PATH="/usr/bin:/bin" GIT_CONFIG_NOSYSTEM=1 \
    GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_CONFIG_COUNT=0 \
    "$TRUSTED_GIT" -c core.fsmonitor=false -c core.hooksPath=/dev/null \
    -C "$work_tree" "$@"
}
trusted_git() {
  clean_git_at "$CANDIDATE_ROOT" "$@"
}
REPO_ROOT="$(trusted_git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "FATAL: orchestrator is not inside a Git worktree" >&2
  exit 2
}
REPO_ROOT="$(cd "$REPO_ROOT" && pwd -P)"
[[ "$SCRIPT_PATH" == "$SCRIPT_DIR/run-from-homelab.sh" ]] || {
  echo "FATAL: resolved orchestrator path is unexpected: $SCRIPT_PATH" >&2
  exit 2
}
[[ "$SCRIPT_PATH" == "$REPO_ROOT/scripts/run-from-homelab.sh" ]] || {
  echo "FATAL: orchestrator is not the canonical repository script" >&2
  exit 2
}
for trusted_path in \
  "scripts/run-from-homelab.sh" \
  "recovery_profile.py" \
  "scripts/validate-local-commit-checkout.py"; do
  trusted_git ls-files --error-unmatch -- "$trusted_path" >/dev/null 2>&1 || {
    echo "FATAL: required orchestrator file is not tracked: $trusted_path" >&2
    exit 2
  }
  [[ -f "$REPO_ROOT/$trusted_path" && ! -L "$REPO_ROOT/$trusted_path" ]] || {
    echo "FATAL: required orchestrator file is not a regular non-symlink: $trusted_path" >&2
    exit 2
  }
  tracked_blob="$(trusted_git rev-parse ":$trusted_path")" || exit 2
  working_blob="$(trusted_git hash-object --no-filters -- "$trusted_path")" || exit 2
  [[ "$tracked_blob" == "$working_blob" ]] || {
    echo "FATAL: required orchestrator file differs from the Git index: $trusted_path" >&2
    exit 2
  }
done
cd "$REPO_ROOT"
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
JUDGE_MODEL="${JUDGE_MODEL:-claude-opus-4.6}"
ENSEMBLE="${ENSEMBLE:-copilot:gpt-5.4}"
PERSIST_MODE="${PERSIST_MODE:-git-push}"
STRATEGY_PROMPT_FILE="${STRATEGY_PROMPT_FILE:-}"
COLLECT="${COLLECT:-data/collected/${RUN_ID}}"
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOME_AI")
ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
log() { echo "[$(ts)] $*"; }
q() { printf '%q' "$1"; }

cleanup_sync_source() {
  "$TRUSTED_PYTHON" -I - "$1" <<'PY'
import shutil, sys, tempfile
from pathlib import Path

path = Path(sys.argv[1]).resolve()
temp_root = Path(tempfile.gettempdir()).resolve()
if path.parent != temp_root or not path.name.startswith("tmp."):
    raise SystemExit(f"refusing to remove non-bootstrap temporary path: {path}")
shutil.rmtree(path)
PY
}

env MODELS="$MODELS" MODEL_SET="$MODEL_SET" SCENARIOS="$SCENARIOS" \
  SCENARIO_SET="$SCENARIO_SET" RUN_MANIFEST="$RUN_MANIFEST" \
  MODEL_ARTIFACT_LOCK="$MODEL_ARTIFACT_LOCK" TIMEOUT_POLICY_ID="$TIMEOUT_POLICY_ID" \
  MEMORY_CONTEXT="$MEMORY_CONTEXT" MEMORY_CONTEXT_FILE="$MEMORY_CONTEXT_FILE" \
  INFERENCE_STRATEGY="$INFERENCE_STRATEGY" INFERENCE_RUNTIME="$INFERENCE_RUNTIME" \
  MAX_TOKENS_CAP="$MAX_TOKENS_CAP" RUN_REPEATS="$RUN_REPEATS" RUN_TEMP="$RUN_TEMP" \
  RUN_ALLOW_UNLOCKED="$RUN_ALLOW_UNLOCKED" JUDGE_MODEL="$JUDGE_MODEL" \
  ENSEMBLE="$ENSEMBLE" SYNC_MODE="$SYNC_MODE" PERSIST_MODE="$PERSIST_MODE" \
  "$TRUSTED_PYTHON" -I "$REPO_ROOT/recovery_profile.py" --repo-root "$REPO_ROOT" --scope orchestration >/dev/null || exit 2

require_ssh() {
  "${SSH[@]}" true 2>/dev/null || {
    log "FATAL: cannot SSH to '$HOME_AI' in BatchMode. Set up the trusted homelab->home-ai"
    log "       key/cert first (homelab pubkey or CA-signed SSH cert in home-ai)."
    exit 2
  }
}

require_remote_idle() {
  "${SSH[@]}" "target=$(q "$REMOTE_DIR"); for link in /proc/[0-9]*/cwd; do current=\$(readlink \"\$link\" 2>/dev/null || true); case \"\$current\" in \"\$target\"|\"\$target\"/*) echo \"active process uses \$target: \$link -> \$current\" >&2; exit 1;; esac; done" \
    || { log "FATAL: refusing to synchronize an active remote checkout: $REMOTE_DIR"; exit 2; }
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
case "$SYNC_MODE" in
  origin|local-commit|working-tree) ;;
  *) log "FATAL: SYNC_MODE must be origin, local-commit, or working-tree"; exit 2 ;;
esac
require_remote_idle

# 1) code state. Default = sync the AI producer to the pushed source. Use
# SYNC_MODE=working-tree only for explicit dev runs with uncommitted local code;
# run.py stamps env.harness_source_dirty and env.harness_artifact_dirty.
case "$SYNC_MODE" in
origin)
  log "--- syncing home-ai to origin/${BRANCH} ---"
  COMMIT="$("${SSH[@]}" "set -e
    if [ ! -d '${REMOTE_DIR}/.git' ]; then git clone --quiet '${REPO_URL}' '${REMOTE_DIR}'; fi
    cd '${REMOTE_DIR}'
    git fetch --quiet origin '${BRANCH}'
    git reset --hard --quiet 'origin/${BRANCH}'
    git rev-parse --short HEAD")" || { log "FATAL: git sync on home-ai failed"; exit 2; }
  log "home-ai at commit ${COMMIT}"
  ;;
local-commit)
  test -d .git || { log "FATAL: local-commit requires a Git worktree"; exit 2; }
  SOURCE_DIRTY="$(trusted_git status --porcelain=v1 --untracked-files=all | "$TRUSTED_PYTHON" -I -c '
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
    LOCAL_COMMIT="$(trusted_git rev-parse HEAD)" || { log "FATAL: cannot resolve local HEAD"; exit 2; }
    SYNC_SOURCE="$(mktemp -d)" || { log "FATAL: cannot create local commit staging directory"; exit 2; }
    if ! clean_git_at "$CANDIDATE_ROOT" clone --quiet --no-hardlinks "$CANDIDATE_ROOT" "$SYNC_SOURCE" \
      || ! clean_git_at "$SYNC_SOURCE" checkout --quiet --detach "$LOCAL_COMMIT" \
      || [ -n "$(clean_git_at "$SYNC_SOURCE" status --porcelain=v1 --untracked-files=all)" ]; then
    cleanup_sync_source "$SYNC_SOURCE"
    log "FATAL: cannot materialize a clean local commit snapshot"
    exit 2
  fi
  log "--- mirroring clean local commit ${LOCAL_COMMIT} to home-ai ---"
  CHECKOUT_MARKER=".apprenticeops-local-commit-checkout"
    "${SSH[@]}" "/usr/bin/python3 -I - $(q "$REMOTE_DIR") $(q "$CHECKOUT_MARKER")" \
    <"$SCRIPT_DIR/validate-local-commit-checkout.py" \
    || { cleanup_sync_source "$SYNC_SOURCE"; log "FATAL: $REMOTE_DIR is not an isolated marker-bound local-commit checkout"; exit 2; }
  rsync -az --delete \
    --exclude '.apprenticeops-local-commit-checkout' \
    --exclude '.venv/' --exclude 'dashboard/backend/.venv/' \
    --exclude 'dashboard/frontend/node_modules/' --exclude 'dashboard/frontend/dist/' \
    --exclude 'calibration.json' --exclude 'data/runs/' --exclude 'data/run-batches/' \
    --exclude 'data/experiments/' --exclude 'logs/' --exclude 'outputs/' \
    --exclude 'results.*.jsonl*' \
    "$SYNC_SOURCE/" "${HOME_AI}:${REMOTE_DIR}/" \
    || { cleanup_sync_source "$SYNC_SOURCE"; log "FATAL: local commit rsync failed"; exit 2; }
  cleanup_sync_source "$SYNC_SOURCE"
  COMMIT="$("${SSH[@]}" "cd $(q "$REMOTE_DIR") && test \"\$(cat .apprenticeops-local-commit-checkout)\" = apprenticeops-local-commit-v1 && test -z \"\$(git status --porcelain=v1 --untracked-files=no)\" && git rev-parse HEAD")" \
    || { log "FATAL: mirrored local commit is not a clean Git worktree"; exit 2; }
  [ "$COMMIT" = "$LOCAL_COMMIT" ] \
    || { log "FATAL: mirrored commit ${COMMIT} != local ${LOCAL_COMMIT}"; exit 2; }
  log "home-ai at clean local commit ${COMMIT}"
  ;;
working-tree)
  log "--- mirroring deployed working tree to home-ai (${SYNC_MODE}) ---"
  "${SSH[@]}" "mkdir -p $(q "$REMOTE_DIR")" || { log "FATAL: cannot create ${REMOTE_DIR} on home-ai"; exit 2; }
  rsync -az --delete \
    --exclude '.git/' --exclude '.venv/' --exclude 'dashboard/backend/.venv/' \
    --exclude 'dashboard/frontend/node_modules/' --exclude 'dashboard/frontend/dist/' \
    --exclude 'data/runs/' --exclude 'data/run-batches/' --exclude 'data/experiments/' \
    --exclude 'logs/' --exclude 'outputs/' --exclude 'results.*.jsonl*' \
    ./ "${HOME_AI}:${REMOTE_DIR}/" || { log "FATAL: rsync working tree to home-ai failed"; exit 2; }
  COMMIT="$(trusted_git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  DIRTY="$(trusted_git status --short 2>/dev/null | wc -l | tr -d ' ')"
  log "home-ai mirrored working tree at ${COMMIT} dirty_files=${DIRTY}"
  ;;
esac

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
