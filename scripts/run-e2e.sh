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
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/usr/local/bin:$PATH"            # node + copilot (nvm-symlinked) in daemon PATH

RUN_ID="${RUN_ID:-e2e-$(date -u +%Y%m%d-%H%M)}"
ACTION="${1:-run}"
MODELS="${MODELS:-data/models.dryrun.txt}"
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
PERSIST_MODE="${PERSIST_MODE:-git-push}"
TIMEOUT_POLICY_ID="${TIMEOUT_POLICY_ID:-ceops-v2-zero-stall-retry}"
JUDGE_MODEL="${JUDGE_MODEL:-claude-opus-4.6}"
ENSEMBLE="${ENSEMBLE:-copilot:gpt-5.4}"
STRATEGY_PROMPT_FILE="${STRATEGY_PROMPT_FILE:-}"
SYNC_MODE="${SYNC_MODE:-origin}"
AI="${AI:-dragos@home-ai.hont.ro}"
AI_REPO="${AI_REPO:-$PWD}"
POLL_S="${POLL_S:-15}"
JUDGE_SCHEDULER="${JUDGE_SCHEDULER:-./scripts/judge-scheduler.sh}"
PRODUCER_SCRIPT="${PRODUCER_SCRIPT:-./scripts/run-from-homelab.sh}"
SETSID_BIN="${SETSID_BIN:-setsid}"
[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] || {
  echo "FATAL: RUN_ID contains unsafe characters" >&2
  exit 2
}

env MODELS="$MODELS" MODEL_SET="$MODEL_SET" SCENARIOS="$SCENARIOS" \
  SCENARIO_SET="$SCENARIO_SET" RUN_MANIFEST="$RUN_MANIFEST" \
  MODEL_ARTIFACT_LOCK="$MODEL_ARTIFACT_LOCK" TIMEOUT_POLICY_ID="$TIMEOUT_POLICY_ID" \
  MEMORY_CONTEXT="$MEMORY_CONTEXT" MEMORY_CONTEXT_FILE="$MEMORY_CONTEXT_FILE" \
  INFERENCE_STRATEGY="$INFERENCE_STRATEGY" INFERENCE_RUNTIME="$INFERENCE_RUNTIME" \
  MAX_TOKENS_CAP="$MAX_TOKENS_CAP" RUN_REPEATS="$RUN_REPEATS" RUN_TEMP="$RUN_TEMP" \
  RUN_ALLOW_UNLOCKED="$RUN_ALLOW_UNLOCKED" JUDGE_MODEL="$JUDGE_MODEL" ENSEMBLE="$ENSEMBLE" \
  SYNC_MODE="$SYNC_MODE" PERSIST_MODE="$PERSIST_MODE" \
  /usr/bin/python3 -I recovery_profile.py --scope orchestration >/dev/null || exit 2

WORK="data/runs/${RUN_ID}"
LOG="${WORK}/e2e.log"
AUTHORITY="${WORK}/.run-authority"

[ ! -L data ] && { [ ! -e data/runs ] || [ ! -L data/runs ]; } && { [ ! -e "$WORK" ] || [ ! -L "$WORK" ]; } || {
  echo "FATAL: run path contains a symlink" >&2
  exit 2
}

if [[ "$ACTION" =~ ^(progress|status|watch)$ && ! -f "$WORK/run.meta" ]]; then
  echo "FATAL: unknown run $RUN_ID; run.meta is missing" >&2
  exit 2
fi
if [ -e "$WORK/run.meta" ] && [ -L "$WORK/run.meta" ]; then
  echo "FATAL: run.meta must not be symlinked" >&2
  exit 2
fi
if [ -e "$AUTHORITY" ] && [ -L "$AUTHORITY" ]; then
  echo "FATAL: run authority marker must not be symlinked" >&2
  exit 2
fi
if [[ ! "$ACTION" =~ ^(progress|status|watch)$ && -d "$WORK" && ! -f "$WORK/run.meta" ]]; then
  if [ -f "$AUTHORITY" ] || [ -n "$(find "$WORK" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
    echo "FATAL: existing run directory is missing authoritative run.meta" >&2
    exit 2
  fi
fi
if [[ ! "$ACTION" =~ ^(progress|status|watch)$ ]]; then
  mkdir -p "$WORK"
fi

if [[ "$ACTION" =~ ^(progress|status|watch)$ && -f "$WORK/run.meta" ]]; then
  eval "$(python3 - "$WORK/run.meta" <<'PY'
import json, shlex, sys
meta = json.load(open(sys.argv[1]))
mapping = {
  "MODELS": "models",
  "MODEL_SET": "model_set",
  "SCENARIOS": "scenarios",
  "SCENARIO_SET": "scenario_set",
  "RUN_MANIFEST": "run_manifest",
  "MODEL_ARTIFACT_LOCK": "model_artifact_lock",
  "TIMEOUT_POLICY_ID": "timeout_policy_id",
  "JUDGE_MODEL": "judge_model",
  "ENSEMBLE": "judge_ensemble",
  "MEMORY_CONTEXT": "memory_context",
  "MEMORY_CONTEXT_FILE": "memory_context_file",
  "INFERENCE_STRATEGY": "inference_strategy",
  "INFERENCE_RUNTIME": "inference_runtime",
  "LLAMA_CPP_MODEL_MAP": "llama_cpp_model_map",
  "LLAMA_CPP_ARTIFACTS": "llama_cpp_artifacts",
  "LLAMA_CPP_EXTRA_ARGS": "llama_cpp_extra_args",
  "STRATEGY_PROMPT_FILE": "strategy_prompt_file",
  "SYNC_MODE": "sync_mode",
  "PERSIST_MODE": "persist_mode",
}
for env_key, meta_key in mapping.items():
  value = meta.get(meta_key)
  if value is None:
    value = ""
  print(f"{env_key}={shlex.quote(str(value))}")
for env_key, meta_key in (("MAX_TOKENS_CAP", "max_tokens_cap"), ("RUN_REPEATS", "run_repeats_override"), ("RUN_TEMP", "run_temp_override")):
  value = meta.get(meta_key)
  print(f"{env_key}={shlex.quote('' if value is None else str(value))}")
print(f"RUN_ALLOW_UNLOCKED={'1' if meta.get('run_allow_unlocked') else ''}")
print(f"EXPECT={int(meta.get('expect') or 0)}")
PY
)"
fi
# consumer exits cleanly once EXPECT models are judged; default = model count in MODELS
EXPECT="${EXPECT:-$(grep -cvE '^[[:space:]]*(#|$)' "$MODELS" 2>/dev/null || echo 0)}"
export RUN_ID MODELS MODEL_SET SCENARIOS SCENARIO_SET RUN_MANIFEST MODEL_ARTIFACT_LOCK TIMEOUT_POLICY_ID JUDGE_MODEL ENSEMBLE MEMORY_CONTEXT MEMORY_CONTEXT_FILE INFERENCE_STRATEGY INFERENCE_RUNTIME LLAMA_CPP_MODEL_MAP LLAMA_CPP_ARTIFACTS LLAMA_CPP_EXTRA_ARGS MAX_TOKENS_CAP RUN_REPEATS RUN_TEMP RUN_ALLOW_UNLOCKED PREFLIGHT_ONLY PERSIST_MODE STRATEGY_PROMPT_FILE RUN_USER EXPECT
if [ ! -f "$WORK/run.meta" ]; then
python3 - "$AUTHORITY" "$RUN_ID" "$PERSIST_MODE" <<'PY'
import json, os, sys, tempfile
from pathlib import Path

path = Path(sys.argv[1])
payload = {"run_id": sys.argv[2], "persist_mode": sys.argv[3], "schema_version": 1}
fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
temporary = Path(name)
try:
  with os.fdopen(fd, "w") as handle:
    json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())
  os.replace(temporary, path)
  directory = os.open(path.parent, os.O_RDONLY)
  try:
    os.fsync(directory)
  finally:
    os.close(directory)
except Exception:
  temporary.unlink(missing_ok=True)
  raise
PY
python3 - "$WORK/run.meta" <<'PY'
import json, os, sys, tempfile
from collections import Counter
from pathlib import Path

path = Path(sys.argv[1])
models_path = Path(os.environ.get("MODELS", "data/models.dryrun.txt"))
scenarios_path = Path(os.environ.get("SCENARIOS", "data/scenarios.json"))
manifest_path = Path(os.environ.get("RUN_MANIFEST", "data/run-manifest.json"))
artifact_lock_path = Path(os.environ["MODEL_ARTIFACT_LOCK"]) if os.environ.get("MODEL_ARTIFACT_LOCK") else None
memory_path = Path(os.environ["MEMORY_CONTEXT_FILE"]) if os.environ.get("MEMORY_CONTEXT_FILE") else None
strategy_path = Path(os.environ["STRATEGY_PROMPT_FILE"]) if os.environ.get("STRATEGY_PROMPT_FILE") else None
llama_cpp_model_map = Path(os.environ["LLAMA_CPP_MODEL_MAP"]) if os.environ.get("LLAMA_CPP_MODEL_MAP") else None
llama_cpp_artifacts = Path(os.environ["LLAMA_CPP_ARTIFACTS"]) if os.environ.get("LLAMA_CPP_ARTIFACTS") else None

def sha256(p):
  import hashlib
  return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

def model_count(p):
  try:
    return sum(1 for line in p.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#"))
  except OSError:
    return 0

def scenarios(p):
  try:
    return json.loads(p.read_text()).get("scenarios", [])
  except Exception:
    return []

def strategy_candidate_count(strategy_id):
  try:
    matrix = json.loads(Path("data/run-matrix.json").read_text())
    for item in matrix.get("inference_strategies", []):
      if item.get("id") == strategy_id:
        return int(item.get("candidate_count") or 1)
  except Exception:
    pass
  return 1

def judge_identities():
  values = [("copilot", os.environ.get("JUDGE_MODEL", "claude-opus-4.6"))]
  for raw in os.environ.get("ENSEMBLE", "copilot:gpt-5.4").split(","):
    raw = raw.strip()
    if not raw:
      continue
    backend, separator, model = raw.partition(":")
    if not separator or not backend or not model:
      raise SystemExit(f"invalid ENSEMBLE judge identity: {raw!r}")
    values.append((backend, model))
  return [
    {"judge_backend": backend, "judge_model": model}
    for backend, model in sorted(set(values))
  ]

items = scenarios(scenarios_path)
strategy_id = os.environ.get("INFERENCE_STRATEGY", "baseline")
obj = {
  "schema_version": 2,
  "run_id": os.environ.get("RUN_ID"),
  "model_set": os.environ.get("MODEL_SET", "manual"),
  "models": str(models_path),
  "models_sha256": sha256(models_path),
  "models_count": model_count(models_path),
  "scenario_set": os.environ.get("SCENARIO_SET", "all"),
  "scenarios": str(scenarios_path),
  "scenarios_sha256": sha256(scenarios_path),
  "run_manifest": str(manifest_path),
  "run_manifest_sha256": sha256(manifest_path),
  "model_artifact_lock": str(artifact_lock_path) if artifact_lock_path else None,
  "model_artifact_lock_sha256": sha256(artifact_lock_path) if artifact_lock_path else None,
  "memory_context": os.environ.get("MEMORY_CONTEXT", "none"),
  "memory_context_file": str(memory_path) if memory_path else None,
  "memory_context_sha256": sha256(memory_path) if memory_path else None,
  "inference_strategy": strategy_id,
  "inference_runtime": os.environ.get("INFERENCE_RUNTIME", "ollama"),
  "sync_mode": os.environ.get("SYNC_MODE", "origin"),
  "persist_mode": os.environ.get("PERSIST_MODE", "git-push"),
  "llama_cpp_model_map": str(llama_cpp_model_map) if llama_cpp_model_map else None,
  "llama_cpp_model_map_sha256": sha256(llama_cpp_model_map) if llama_cpp_model_map else None,
  "llama_cpp_artifacts": str(llama_cpp_artifacts) if llama_cpp_artifacts else None,
  "llama_cpp_artifacts_sha256": sha256(llama_cpp_artifacts) if llama_cpp_artifacts else None,
  "llama_cpp_extra_args": os.environ.get("LLAMA_CPP_EXTRA_ARGS") or None,
  "max_tokens_cap": int(os.environ["MAX_TOKENS_CAP"]) if os.environ.get("MAX_TOKENS_CAP") else None,
  "run_repeats_override": int(os.environ["RUN_REPEATS"]) if os.environ.get("RUN_REPEATS") else None,
  "run_temp_override": float(os.environ["RUN_TEMP"]) if os.environ.get("RUN_TEMP") else None,
  "run_allow_unlocked": os.environ.get("RUN_ALLOW_UNLOCKED") == "1",
  "preflight_only": os.environ.get("PREFLIGHT_ONLY") == "1",
  "strategy_candidate_count": strategy_candidate_count(strategy_id),
  "strategy_prompt_file": str(strategy_path) if strategy_path else None,
  "strategy_prompt_sha256": sha256(strategy_path) if strategy_path else None,
  "timeout_policy_id": os.environ.get("TIMEOUT_POLICY_ID", "ceops-v2-zero-stall-retry"),
  "judge_model": os.environ.get("JUDGE_MODEL", "claude-opus-4.6"),
  "judge_ensemble": os.environ.get("ENSEMBLE", "copilot:gpt-5.4"),
  "scenario_count": len(items),
  "scenario_ids": [s.get("id") for s in items if isinstance(s, dict) and s.get("id")],
  "class_counts": dict(Counter(s.get("class") or "unknown" for s in items if isinstance(s, dict))),
  "difficulty_counts": dict(Counter(s.get("difficulty") or "unknown" for s in items if isinstance(s, dict))),
  "grounding_counts": dict(Counter(s.get("grounding") or "unknown" for s in items if isinstance(s, dict))),
  "reps": int(os.environ.get("RUN_REPEATS") or os.environ.get("REPS", "5")),
  "judge_identities": judge_identities(),
  "judges": len(judge_identities()),
  "expect": int(os.environ.get("EXPECT", "0") or "0"),
  "user": os.environ.get("RUN_USER", "user"),
  "started_at": int(__import__("time").time()),
}
path.parent.mkdir(parents=True, exist_ok=True)
fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
with os.fdopen(fd, "w") as fh:
  json.dump(obj, fh, separators=(",", ":"))
  fh.write("\n")
  fh.flush()
  os.fsync(fh.fileno())
os.replace(tmp, path)
directory = os.open(path.parent, os.O_RDONLY)
try:
  os.fsync(directory)
finally:
  os.close(directory)
json.loads(path.read_text())
PY
else
python3 - "$WORK/run.meta" "$MODELS" "$SCENARIOS" "$MEMORY_CONTEXT" "$MEMORY_CONTEXT_FILE" "$INFERENCE_STRATEGY" "$STRATEGY_PROMPT_FILE" "$INFERENCE_RUNTIME" "$LLAMA_CPP_MODEL_MAP" "$LLAMA_CPP_ARTIFACTS" "$LLAMA_CPP_EXTRA_ARGS" "$MAX_TOKENS_CAP" "$RUN_REPEATS" "$RUN_TEMP" "$RUN_ALLOW_UNLOCKED" "$RUN_MANIFEST" "$TIMEOUT_POLICY_ID" "$MODEL_ARTIFACT_LOCK" <<'PY'
import hashlib, json, os, sys
from pathlib import Path
meta = json.loads(Path(sys.argv[1]).read_text())
if int(meta.get("schema_version") or 0) < 2:
  raise SystemExit("run.meta predates run-matrix metadata; start a new run")
for key, value in (("models", sys.argv[2]), ("scenarios", sys.argv[3])):
  if meta.get(key) != value:
    raise SystemExit(f"run.meta {key}={meta.get(key)!r} does not match launch {value!r}")
scenario_path = Path(sys.argv[3])
models_path = Path(sys.argv[2])
if models_path.exists():
  got = hashlib.sha256(models_path.read_bytes()).hexdigest()
  if meta.get("models_sha256") and meta["models_sha256"] != got:
    raise SystemExit("run.meta model hash mismatch; start a new run")
if scenario_path.exists():
  got = hashlib.sha256(scenario_path.read_bytes()).hexdigest()
  if meta.get("scenarios_sha256") and meta["scenarios_sha256"] != got:
    raise SystemExit("run.meta scenario hash mismatch; start a new run")
memory_context = sys.argv[4]
memory_file = sys.argv[5]
inference_strategy = sys.argv[6]
strategy_file = sys.argv[7]
inference_runtime = sys.argv[8]
llama_cpp_model_map = sys.argv[9]
llama_cpp_artifacts = sys.argv[10]
llama_cpp_extra_args = sys.argv[11]
max_tokens_cap = sys.argv[12]
run_repeats = sys.argv[13]
run_temp = sys.argv[14]
run_allow_unlocked = sys.argv[15]
run_manifest = sys.argv[16]
timeout_policy_id = sys.argv[17]
model_artifact_lock = sys.argv[18]
sync_mode = os.environ.get("SYNC_MODE", "origin")
persist_mode = os.environ.get("PERSIST_MODE", "git-push")
if meta.get("memory_context", "none") != memory_context:
  raise SystemExit(f"run.meta memory_context={meta.get('memory_context')!r} does not match launch {memory_context!r}")
if (meta.get("memory_context_file") or "") != memory_file:
  raise SystemExit("run.meta memory context file mismatch; start a new run")
if memory_file:
  memory_path = Path(memory_file)
  got = hashlib.sha256(memory_path.read_bytes()).hexdigest()
  if meta.get("memory_context_sha256") and meta["memory_context_sha256"] != got:
    raise SystemExit("run.meta memory context hash mismatch; start a new run")
if (meta.get("inference_strategy") or "baseline") != inference_strategy:
  raise SystemExit(f"run.meta inference_strategy={meta.get('inference_strategy')!r} does not match launch {inference_strategy!r}")
if (meta.get("inference_runtime") or "ollama") != inference_runtime:
  raise SystemExit(f"run.meta inference_runtime={meta.get('inference_runtime')!r} does not match launch {inference_runtime!r}")
if (meta.get("sync_mode") or "origin") != sync_mode:
  raise SystemExit(f"run.meta sync_mode={meta.get('sync_mode')!r} does not match launch {sync_mode!r}")
if (meta.get("persist_mode") or "git-push") != persist_mode:
  raise SystemExit(f"run.meta persist_mode={meta.get('persist_mode')!r} does not match launch {persist_mode!r}")
if (meta.get("llama_cpp_model_map") or "") != llama_cpp_model_map:
  raise SystemExit("run.meta llama.cpp model map mismatch; start a new run")
if llama_cpp_model_map:
  map_path = Path(llama_cpp_model_map)
  got = hashlib.sha256(map_path.read_bytes()).hexdigest()
  if meta.get("llama_cpp_model_map_sha256") and meta["llama_cpp_model_map_sha256"] != got:
    raise SystemExit("run.meta llama.cpp model map hash mismatch; start a new run")
if (meta.get("llama_cpp_artifacts") or "") != llama_cpp_artifacts:
  raise SystemExit("run.meta llama.cpp artifacts mismatch; start a new run")
if llama_cpp_artifacts:
  artifact_path = Path(llama_cpp_artifacts)
  got = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
  if meta.get("llama_cpp_artifacts_sha256") and meta["llama_cpp_artifacts_sha256"] != got:
    raise SystemExit("run.meta llama.cpp artifacts hash mismatch; start a new run")
if (meta.get("llama_cpp_extra_args") or "") != llama_cpp_extra_args:
  raise SystemExit("run.meta llama.cpp extra args mismatch; start a new run")
if str(meta.get("max_tokens_cap") or "") != max_tokens_cap:
  raise SystemExit("run.meta max token cap mismatch; start a new run")
if run_repeats and int(meta.get("reps") or 0) != int(run_repeats):
  raise SystemExit("run.meta repeat override mismatch; start a new run")
if str(meta.get("run_temp_override") or "") != run_temp:
  raise SystemExit("run.meta temperature override mismatch; start a new run")
if ("1" if meta.get("run_allow_unlocked") else "") != run_allow_unlocked:
  raise SystemExit("run.meta unlocked-run flag mismatch; start a new run")
if (meta.get("run_manifest") or "data/run-manifest.json") != run_manifest:
  raise SystemExit("run.meta manifest path mismatch; start a new run")
manifest_path = Path(run_manifest)
if manifest_path.exists():
  got = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
  if meta.get("run_manifest_sha256") and meta["run_manifest_sha256"] != got:
    raise SystemExit("run.meta manifest hash mismatch; start a new run")
if (meta.get("timeout_policy_id") or "ceops-v2-zero-stall-retry") != timeout_policy_id:
  raise SystemExit("run.meta timeout policy mismatch; start a new run")
if (meta.get("judge_model") or "claude-opus-4.6") != os.environ.get("JUDGE_MODEL", "claude-opus-4.6"):
  raise SystemExit("run.meta primary judge mismatch; start a new run")
if (meta.get("judge_ensemble") or "copilot:gpt-5.4") != os.environ.get("ENSEMBLE", "copilot:gpt-5.4"):
  raise SystemExit("run.meta judge ensemble mismatch; start a new run")
if (meta.get("model_artifact_lock") or "") != model_artifact_lock:
  raise SystemExit("run.meta model artifact lock mismatch; start a new run")
if model_artifact_lock:
  artifact_path = Path(model_artifact_lock)
  got = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
  if meta.get("model_artifact_lock_sha256") and meta["model_artifact_lock_sha256"] != got:
    raise SystemExit("run.meta model artifact lock hash mismatch; start a new run")
if (meta.get("strategy_prompt_file") or "") != strategy_file:
  raise SystemExit("run.meta strategy prompt file mismatch; start a new run")
if strategy_file:
  strategy_path = Path(strategy_file)
  got = hashlib.sha256(strategy_path.read_bytes()).hexdigest()
  if meta.get("strategy_prompt_sha256") and meta["strategy_prompt_sha256"] != got:
    raise SystemExit("run.meta strategy prompt hash mismatch; start a new run")
PY
fi

if [ "$PERSIST_MODE" = "local-files" ]; then
  [ -f "$AUTHORITY" ] && [ ! -L "$AUTHORITY" ] || {
    echo "FATAL: local-files run requires a regular authority marker" >&2
    exit 2
  }
  python3 - "$AUTHORITY" "$RUN_ID" "$PERSIST_MODE" <<'PY'
import json, sys
value = json.load(open(sys.argv[1]))
if value != {"persist_mode": sys.argv[3], "run_id": sys.argv[2], "schema_version": 1}:
  raise SystemExit("run authority marker differs from launch contract")
PY
fi
ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
elog() { echo "[$(ts)] $*" | tee -a "$LOG"; }

shell_env() {
  python3 - "$@" <<'PY'
import shlex, sys
print(" ".join(f"{item.split('=', 1)[0]}={shlex.quote(item.split('=', 1)[1])}" for item in sys.argv[1:]))
PY
}

shell_quote() {
  python3 - "$1" <<'PY'
import shlex, sys
print(shlex.quote(sys.argv[1]))
PY
}

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
  echo "  judged: $(cat "${WORK}/judged.${RUN_ID}.jsonl" 2>/dev/null | wc -l | tr -d ' ') rows; models: $(jq -r .model "${WORK}/judged.${RUN_ID}.jsonl" 2>/dev/null | sort -u | tr '\n' ' ')/ target ${EXPECT}"
  tail -n 5 "${WORK}/pipeline-ledger.jsonl" 2>/dev/null | sed 's/^/  ledger: /'
  git log --oneline "experiment/${RUN_ID}" 2>/dev/null | head -3 | sed 's/^/  commit: /'
  echo "  consumer alive: $(pgrep -fc '[j]udge-scheduler' || echo 0)"
}

case "$ACTION" in
  progress|status) progress; exit 0 ;;
  watch) while true; do clear; progress; sleep 20; done ;;
esac

elog "=== E2E LAUNCH  RUN_ID=$RUN_ID  models=$MODELS  scenarios=$SCENARIOS manifest=$RUN_MANIFEST artifact_lock=${MODEL_ARTIFACT_LOCK:-none} timeout_policy=$TIMEOUT_POLICY_ID memory=$MEMORY_CONTEXT strategy=$INFERENCE_STRATEGY runtime=$INFERENCE_RUNTIME sync=$SYNC_MODE persist=$PERSIST_MODE expect=$EXPECT preflight_only=$PREFLIGHT_ONLY ==="
PROD_ENV=$(shell_env "RUN_ID=$RUN_ID" "MODELS=$MODELS" "MODEL_SET=$MODEL_SET" "SCENARIOS=$SCENARIOS" "SCENARIO_SET=$SCENARIO_SET" "RUN_MANIFEST=$RUN_MANIFEST" "MODEL_ARTIFACT_LOCK=$MODEL_ARTIFACT_LOCK" "TIMEOUT_POLICY_ID=$TIMEOUT_POLICY_ID" "MEMORY_CONTEXT=$MEMORY_CONTEXT" "MEMORY_CONTEXT_FILE=$MEMORY_CONTEXT_FILE" "INFERENCE_STRATEGY=$INFERENCE_STRATEGY" "INFERENCE_RUNTIME=$INFERENCE_RUNTIME" "LLAMA_CPP_MODEL_MAP=$LLAMA_CPP_MODEL_MAP" "LLAMA_CPP_ARTIFACTS=$LLAMA_CPP_ARTIFACTS" "LLAMA_CPP_EXTRA_ARGS=$LLAMA_CPP_EXTRA_ARGS" "MAX_TOKENS_CAP=$MAX_TOKENS_CAP" "RUN_REPEATS=$RUN_REPEATS" "RUN_TEMP=$RUN_TEMP" "RUN_ALLOW_UNLOCKED=$RUN_ALLOW_UNLOCKED" "PREFLIGHT_ONLY=$PREFLIGHT_ONLY" "STRATEGY_PROMPT_FILE=$STRATEGY_PROMPT_FILE" "SYNC_MODE=$SYNC_MODE" "HOME_AI=$AI" "REMOTE_DIR=$AI_REPO")
if [ "$PREFLIGHT_ONLY" = "1" ]; then
  elog "launching PRODUCER preflight-only on ai (inline; consumer disabled) ..."
  if ! bash -c "$PROD_ENV $(shell_quote "$PRODUCER_SCRIPT") >>$(shell_quote "$LOG") 2>&1"; then
    elog "FATAL: producer preflight-only path failed; consumer was not launched"
    exit 3
  fi
  elog "PREFLIGHT_ONLY: PASS; producer emitted zero rows/files and consumer was not launched"
  exit 0
fi
READY="$WORK/consumer.ready"
rm -f "$READY"
elog "launching CONSUMER on home (detached, flock-guarded) ..."
RUN_ID="$RUN_ID" AI="$AI" AI_REPO="$AI_REPO" EXPECT="$EXPECT" POLL_S="$POLL_S" SCENARIOS="$SCENARIOS" SCENARIO_SET="$SCENARIO_SET" JUDGE_MODEL="$JUDGE_MODEL" ENSEMBLE="$ENSEMBLE" PERSIST_MODE="$PERSIST_MODE" \
  "$SETSID_BIN" nohup "$JUDGE_SCHEDULER" >>"${WORK}/judge-scheduler.out" 2>&1 </dev/null &
CONSUMER_PID=$!
for _attempt in $(seq 1 60); do
  [ -f "$READY" ] && break
  if ! kill -0 "$CONSUMER_PID" 2>/dev/null; then
    wait "$CONSUMER_PID" || true
    elog "FATAL: consumer exited before readiness; producer was not launched"
    exit 4
  fi
  sleep 1
done
if [ ! -f "$READY" ]; then
  kill "$CONSUMER_PID" 2>/dev/null || true
  elog "FATAL: consumer readiness timed out; producer was not launched"
  exit 4
fi
python3 - "$READY" "$RUN_ID" "$PERSIST_MODE" "$CONSUMER_PID" <<'PY' || {
import json, sys
value = json.load(open(sys.argv[1]))
if (
  value.get("run_id") != sys.argv[2]
  or value.get("persist_mode") != sys.argv[3]
  or value.get("pid") != int(sys.argv[4])
):
    raise SystemExit("consumer readiness contract mismatch")
PY
  kill "$CONSUMER_PID" 2>/dev/null || true
  elog "FATAL: consumer readiness contract mismatch; producer was not launched"
  exit 4
}
if ! kill -0 "$CONSUMER_PID" 2>/dev/null; then
  wait "$CONSUMER_PID" || true
  elog "FATAL: consumer exited after readiness; producer was not launched"
  exit 4
fi
elog "consumer ready; launching PRODUCER on ai (detached) ..."
"$SETSID_BIN" bash -c "$PROD_ENV $(shell_quote "$PRODUCER_SCRIPT") >>$(shell_quote "$LOG") 2>&1" </dev/null &
elog "consumer and producer launched autonomously. watch with:  RUN_ID=$RUN_ID ./scripts/run-e2e.sh progress"
progress | tee -a "$LOG"
