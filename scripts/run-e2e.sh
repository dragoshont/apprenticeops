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
MODELS="${MODELS:-data/models.dryrun.txt}"
MODEL_SET="${MODEL_SET:-manual}"
SCENARIOS="${SCENARIOS:-data/scenarios.json}"
SCENARIO_SET="${SCENARIO_SET:-all}"
AI="${AI:-dragos@home-ai.hont.ro}"
AI_REPO="${AI_REPO:-/home/dragos/apprenticeops}"
POLL_S="${POLL_S:-15}"
WORK="data/runs/${RUN_ID}"
LOG="${WORK}/e2e.log"
mkdir -p "$WORK"
# consumer exits cleanly once EXPECT models are judged; default = model count in MODELS
EXPECT="${EXPECT:-$(grep -cvE '^[[:space:]]*(#|$)' "$MODELS" 2>/dev/null || echo 0)}"
export RUN_ID MODELS MODEL_SET SCENARIOS SCENARIO_SET RUN_USER EXPECT
if [ ! -f "$WORK/run.meta" ]; then
python3 - "$WORK/run.meta" <<'PY'
import json, os, sys, tempfile
from collections import Counter
from pathlib import Path

path = Path(sys.argv[1])
models_path = Path(os.environ.get("MODELS", "data/models.dryrun.txt"))
scenarios_path = Path(os.environ.get("SCENARIOS", "data/scenarios.json"))

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

items = scenarios(scenarios_path)
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
  "scenario_count": len(items),
  "scenario_ids": [s.get("id") for s in items if isinstance(s, dict) and s.get("id")],
  "class_counts": dict(Counter(s.get("class") or "unknown" for s in items if isinstance(s, dict))),
  "difficulty_counts": dict(Counter(s.get("difficulty") or "unknown" for s in items if isinstance(s, dict))),
  "grounding_counts": dict(Counter(s.get("grounding") or "unknown" for s in items if isinstance(s, dict))),
  "reps": int(os.environ.get("REPS", "5")),
  "judges": int(os.environ.get("NJUDGES", "2")),
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
json.loads(path.read_text())
PY
else
python3 - "$WORK/run.meta" "$MODELS" "$SCENARIOS" <<'PY'
import hashlib, json, sys
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
PY
fi
ts() { date -uIs; }
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

case "${1:-run}" in
  progress|status) progress; exit 0 ;;
  watch) while true; do clear; progress; sleep 20; done ;;
esac

elog "=== E2E LAUNCH  RUN_ID=$RUN_ID  models=$MODELS  scenarios=$SCENARIOS  expect=$EXPECT ==="
elog "launching PRODUCER on ai (detached) ..."
PROD_ENV=$(shell_env "RUN_ID=$RUN_ID" "MODELS=$MODELS" "MODEL_SET=$MODEL_SET" "SCENARIOS=$SCENARIOS" "SCENARIO_SET=$SCENARIO_SET" "HOME_AI=$AI" "REMOTE_DIR=$AI_REPO")
setsid bash -c "$PROD_ENV ./scripts/run-from-homelab.sh >>$(shell_quote "$LOG") 2>&1" </dev/null &
elog "launching CONSUMER on home (detached, flock-guarded) ..."
RUN_ID="$RUN_ID" AI="$AI" AI_REPO="$AI_REPO" EXPECT="$EXPECT" POLL_S="$POLL_S" SCENARIOS="$SCENARIOS" SCENARIO_SET="$SCENARIO_SET" \
  setsid nohup ./scripts/judge-scheduler.sh >>"${WORK}/judge-scheduler.out" 2>&1 </dev/null &
elog "both launched autonomously. watch with:  RUN_ID=$RUN_ID ./scripts/run-e2e.sh progress"
progress | tee -a "$LOG"
