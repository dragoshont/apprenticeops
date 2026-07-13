#!/usr/bin/env bash
# judge-scheduler.sh — the EVALUATION stage of the pipeline (runs ON the home node).
#
# Independently consumes the producer's per-model completion events (the `.done`
# marker, stage S4) and runs, per model:
#     S5 collect  — rsync the model's result rows + answer texts off `ai`
#     S6 judge    — the 2-judge pair (claude-opus-4.6 + gpt-5.4) via the Copilot CLI
#     S7 persist  — commit the model's evidence to the experiment branch + push
#
# It is decoupled from the producer (only the `.done` marker couples them),
# idempotent, and safe to `kill -9` + restart. Every stage transition is appended
# to data/runs/<RUN_ID>/pipeline-ledger.jsonl (the live status board AND the paper's
# reproducibility trace), including each model's verbatim answer (gen_ai.completion)
# so a run can be re-judged or a judge call audited. That is intentional and safe: a
# completion can only echo the already-public scenario context + gold answers, and the
# models are never given real secret VALUES (scenarios carry secret NAMES + "does not
# exist" signals only), so no real secret is ever written or committed.
#
#   RUN_ID=roster-YYYYMMDD-HHMM ./scripts/judge-scheduler.sh            # run until killed
#   RUN_ID=... EXPECT=2 ./scripts/judge-scheduler.sh                    # dry-run: stop after 2 judged
set -uo pipefail
cd "$(dirname "$0")/.."
# the nvm-installed node + copilot are symlinked into /usr/local/bin; ensure they
# resolve in a minimal detached/daemon PATH (copilot is a `#!/usr/bin/env node` script).
export PATH="/usr/local/bin:$PATH"
TRUSTED_GIT="/usr/bin/git"
FLOCK_BIN="${FLOCK_BIN:-flock}"
RSYNC_BIN="${RSYNC_BIN:-rsync}"
COMPLETION_VALIDATOR="${COMPLETION_VALIDATOR:-scripts/validate-completion-marker.py}"

[ -x "$TRUSTED_GIT" ] || { echo "FATAL: trusted Git executable is unavailable" >&2; exit 2; }
clean_git() {
  /usr/bin/env -i HOME="${HOME:-}" PATH="/usr/bin:/bin" \
    SSH_AUTH_SOCK="${SSH_AUTH_SOCK:-}" GIT_CONFIG_NOSYSTEM=1 \
    GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_CONFIG_COUNT=0 \
    GIT_TERMINAL_PROMPT=0 \
    "$TRUSTED_GIT" -c core.fsmonitor=false -c core.hooksPath=/dev/null \
    -c user.name="ApprenticeOps Experiment Runner" \
    -c user.email="apprenticeops@localhost" "$@"
}

RUN_ID="${RUN_ID:?set RUN_ID (the producer run id, e.g. roster-20260624-1200)}"
AI="${AI:-dragos@home-ai.hont.ro}"
AI_REPO="${AI_REPO:-/home/dragos/apprenticeops}"                 # where run-roster.sh runs on `ai`
REQUESTED_BRANCH="${BRANCH:-}"
BRANCH="experiment/${RUN_ID}"
POLL_S="${POLL_S:-30}"
REQUESTED_ENSEMBLE="${ENSEMBLE:-}"
REQUESTED_JUDGE_MODEL="${JUDGE_MODEL:-}"
REQUESTED_PERSIST_MODE="${PERSIST_MODE:-}"
REQUESTED_EXPECT="${EXPECT:-}"
REQUESTED_SCENARIOS="${SCENARIOS:-}"
REQUESTED_RUN_REPEATS="${RUN_REPEATS:-}"

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] || {
  echo "FATAL: RUN_ID contains unsafe characters" >&2
  exit 2
}
if [ -n "$REQUESTED_BRANCH" ] && [ "$REQUESTED_BRANCH" != "$BRANCH" ]; then
  echo "FATAL: BRANCH must be the dedicated result branch $BRANCH" >&2
  exit 2
fi

RESULTS="results.${RUN_ID}.jsonl"
REMOTE_OUTPUTS="outputs/${RUN_ID}"
WORK="data/runs/${RUN_ID}"
MIRROR="${WORK}/_mirror"                            # local mirror of the ai artifacts
LEDGER="${WORK}/pipeline-ledger.jsonl"
JUDGED="${WORK}/judged.${RUN_ID}.jsonl"
STATUS="${WORK}/judge-scheduler.status"
LOG="${WORK}/judge-scheduler.log"
READY="${WORK}/consumer.ready"
AUTHORITY="${WORK}/.run-authority"
[ ! -L data ] && { [ ! -e data/runs ] || [ ! -L data/runs ]; } && { [ ! -e "$WORK" ] || [ ! -L "$WORK" ]; } || {
  echo "FATAL: run path contains a symlink" >&2
  exit 2
}
if [ -e "$AUTHORITY" ] && [ -L "$AUTHORITY" ]; then
  echo "FATAL: run authority marker must not be symlinked" >&2
  exit 2
fi
if [ -d "$WORK" ] && [ ! -f "$WORK/run.meta" ] && {
  [ -f "$AUTHORITY" ] || [ -n "$(find "$WORK" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ];
}; then
  echo "FATAL: existing run directory is missing authoritative run.meta" >&2
  exit 2
fi
mkdir -p "$WORK"

if [ -f "$WORK/run.meta" ]; then
  [ ! -L "$WORK/run.meta" ] || { echo "FATAL: run.meta must not be symlinked" >&2; exit 2; }
  META_ASSIGNMENTS="$(python3 - "$WORK/run.meta" <<'PY'
import hashlib, json, shlex, sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import analysis_metrics

meta = json.load(open(sys.argv[1]))
if not isinstance(meta, dict):
  raise SystemExit("run.meta must contain an object")

def positive_int(key):
  value = meta.get(key)
  if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
    raise SystemExit(f"run.meta {key} must be a positive integer")
  return value

def safe_repo_file(key):
  raw = meta.get(key)
  if not isinstance(raw, str) or not raw:
    raise SystemExit(f"run.meta {key} must be a non-empty path")
  relative = Path(raw)
  if relative.is_absolute() or ".." in relative.parts:
    raise SystemExit(f"run.meta {key} path is unsafe")
  cursor = Path.cwd()
  for part in relative.parts:
    cursor = cursor / part
    if cursor.is_symlink():
      raise SystemExit(f"run.meta {key} path is symlinked")
  if not cursor.is_file():
    raise SystemExit(f"run.meta {key} file is missing")
  expected = meta.get(f"{key}_sha256")
  actual = hashlib.sha256(cursor.read_bytes()).hexdigest()
  if not isinstance(expected, str) or actual != expected:
    raise SystemExit(f"run.meta {key} hash mismatch")
  return raw, cursor

schema_version = positive_int("schema_version")
if schema_version < 2:
  raise SystemExit("run.meta schema_version predates authoritative consumer metadata")
if meta.get("run_id") != Path(sys.argv[1]).parent.name:
  raise SystemExit("run.meta run_id differs from its directory")
expect = positive_int("expect")
reps = positive_int("reps")
scenario_count = positive_int("scenario_count")
models_count = positive_int("models_count")
persist_mode = meta.get("persist_mode")
if persist_mode not in {"git-push", "local-files"}:
  raise SystemExit("run.meta persist_mode must be git-push or local-files")
scenarios_raw, scenarios_path = safe_repo_file("scenarios")
models_raw, models_path = safe_repo_file("models")
scenario_value = json.loads(scenarios_path.read_text())
scenario_rows = scenario_value.get("scenarios") if isinstance(scenario_value, dict) else None
if not isinstance(scenario_rows, list) or len(scenario_rows) != scenario_count:
  raise SystemExit("run.meta scenario_count differs from scenario contract")
scenario_ids = [row.get("id") for row in scenario_rows if isinstance(row, dict)]
if (
  len(scenario_ids) != len(scenario_rows)
  or any(not isinstance(value, str) or not value for value in scenario_ids)
  or len(scenario_ids) != len(set(scenario_ids))
  or meta.get("scenario_ids") != scenario_ids
):
  raise SystemExit("run.meta scenario_ids differ from the ordered scenario contract")
roster = [
  line.strip()
  for line in models_path.read_text().splitlines()
  if line.strip() and not line.lstrip().startswith("#")
]
if len(roster) != models_count or len(roster) != expect or len(roster) != len(set(roster)):
  raise SystemExit("run.meta model/expect domain differs from roster")
judges = analysis_metrics.metadata_judge_identities(meta)
primary = meta.get("judge_model")
ensemble = meta.get("judge_ensemble")
if not isinstance(primary, str) or not primary or not isinstance(ensemble, str):
  raise SystemExit("run.meta judge_model/judge_ensemble are malformed")
declared = {(backend, model) for backend, model in judges}
configured = {("copilot", primary)} if primary else set()
for raw in ensemble.split(","):
    raw = raw.strip()
    if not raw:
        continue
    backend, separator, model = raw.partition(":")
    if not separator or not backend or not model:
        raise SystemExit(f"invalid run.meta judge_ensemble: {raw!r}")
    configured.add((backend, model))
if configured != declared:
    raise SystemExit("run.meta judge configuration differs from authoritative judge_identities")
values = {
    "META_ENSEMBLE": ensemble,
  "META_EXPECT": str(expect),
    "META_JUDGE_MODEL": primary,
  "META_MODELS": models_raw,
  "META_PERSIST_MODE": persist_mode,
  "META_RUN_REPEATS": str(reps),
  "META_SCENARIOS": scenarios_raw,
}
for key, value in values.items():
    print(f"{key}={shlex.quote(value)}")
PY
)" || { echo "FATAL: cannot load authoritative consumer contract from $WORK/run.meta" >&2; exit 2; }
  eval "$META_ASSIGNMENTS"
  for requested_name in ENSEMBLE JUDGE_MODEL PERSIST_MODE EXPECT SCENARIOS RUN_REPEATS; do
    eval "requested=\${REQUESTED_${requested_name}}"
    eval "authoritative=\${META_${requested_name}}"
    if [ -n "$requested" ] && [ "$requested" != "$authoritative" ]; then
      echo "FATAL: requested ${requested_name}=$requested differs from run.meta value $authoritative" >&2
      exit 2
    fi
  done
  ENSEMBLE="$META_ENSEMBLE"
  EXPECT="$META_EXPECT"
  JUDGE_MODEL="$META_JUDGE_MODEL"
  MODEL_ROSTER="$META_MODELS"
  PERSIST_MODE="$META_PERSIST_MODE"
  RUN_REPEATS="$META_RUN_REPEATS"
  SCENARIOS="$META_SCENARIOS"
else
  if [ -n "$REQUESTED_PERSIST_MODE" ] && [ "$REQUESTED_PERSIST_MODE" = "local-files" ]; then
    echo "FATAL: local-files persistence requires authoritative run.meta" >&2
    exit 2
  fi
  if [ -s "$WORK/.committed" ] || compgen -G "$WORK/*.persistence.json" >/dev/null; then
    echo "FATAL: existing local persistence evidence requires authoritative run.meta" >&2
    exit 2
  fi
  ENSEMBLE="${REQUESTED_ENSEMBLE:-copilot:gpt-5.4}"
  EXPECT="${REQUESTED_EXPECT:-0}"
  JUDGE_MODEL="${REQUESTED_JUDGE_MODEL:-claude-opus-4.6}"
  PERSIST_MODE="${REQUESTED_PERSIST_MODE:-git-push}"
  RUN_REPEATS=0
  MODEL_ROSTER=""
  SCENARIOS="${REQUESTED_SCENARIOS:-data/scenarios.json}"
fi

if [ "$PERSIST_MODE" = "local-files" ]; then
  [ -f "$AUTHORITY" ] && [ ! -L "$AUTHORITY" ] || {
    echo "FATAL: local-files run requires a regular authority marker" >&2
    exit 2
  }
  python3 - "$AUTHORITY" "$RUN_ID" "$PERSIST_MODE" <<'PY' || {
import json, sys
value = json.load(open(sys.argv[1]))
if not isinstance(value, dict) or value != {
  "persist_mode": sys.argv[3],
  "run_id": sys.argv[2],
  "schema_version": 1,
}:
  raise SystemExit("run authority marker differs from launch contract")
PY
    echo "FATAL: run authority marker validation failed" >&2
    exit 2
  }
fi

for directory_path in "$MIRROR" "$MIRROR/outputs"; do
  [ ! -L "$directory_path" ] || { echo "FATAL: run directory path is symlinked: $directory_path" >&2; exit 2; }
done
mkdir -p "$MIRROR/outputs"

guard_run_tree() {
  for directory_path in "$WORK" "$MIRROR" "$MIRROR/outputs"; do
    [ -d "$directory_path" ] && [ ! -L "$directory_path" ] || {
      echo "FATAL: run directory is missing or symlinked: $directory_path" >&2
      return 1
    }
  done
  unsafe_path="$(find "$WORK" -mindepth 1 \( -type l -o \( ! -type d ! -type f \) \) -print -quit 2>/dev/null)"
  if [ -n "$unsafe_path" ]; then
    echo "FATAL: unsupported or symlinked run evidence: $unsafe_path" >&2
    return 1
  fi
}

guard_run_tree || exit 2

case "$PERSIST_MODE" in
  git-push|local-files) ;;
  *) echo "FATAL: PERSIST_MODE must be git-push or local-files" >&2; exit 2 ;;
esac
[ -x "$COMPLETION_VALIDATOR" ] && [ ! -L "$COMPLETION_VALIDATOR" ] || {
  echo "FATAL: completion marker validator is missing, non-executable, or symlinked" >&2
  exit 2
}

# single-instance guard: a stale relaunch must not double-judge the same RUN_ID
command -v "$FLOCK_BIN" >/dev/null 2>&1 || {
  echo "FATAL: flock is required for consumer single-instance safety" >&2
  exit 2
}
exec 9>"${WORK}/.consumer.lock"
if ! "$FLOCK_BIN" -n 9; then
  echo "[$(date -uIs)] another consumer already holds ${WORK}/.consumer.lock; refusing duplicate" >&2
  exit 2
fi

SSH="ssh -o BatchMode=yes -o ConnectTimeout=10"
ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG" >&2; }
status() { echo "[$(ts)] $*" >"$STATUS"; log "$*"; }
ledger() {  # model stage ok [detail]
  python3 - "$LEDGER" "$1" "$2" "$3" "${4:-}" <<'PY'
import json, os, sys
path, model, stage, ok, detail = sys.argv[1:]
with open(path, "a") as handle:
    handle.write(json.dumps({"model": model, "stage": stage, "ts": int(__import__("time").time()), "ok": int(ok), "detail": detail}, separators=(",", ":")) + "\n")
    handle.flush()
    os.fsync(handle.fileno())
PY
}
judged_models() { [ -f "$JUDGED" ] && jq -r '.model' "$JUDGED" 2>/dev/null | sort -u; }

log "consumer up: RUN_ID=$RUN_ID persistence=$PERSIST_MODE branch=$BRANCH ai=$AI expect=${EXPECT:-inf}"
if [ "$PERSIST_MODE" = "git-push" ]; then
  clean_git diff --cached --quiet -- || {
    log "FATAL: git persistence requires an empty index before branch checkout"
    exit 2
  }
  # experiment branch: create from current HEAD if missing, then track it on origin
  clean_git rev-parse --verify "$BRANCH" >/dev/null 2>&1 || clean_git branch "$BRANCH"
  clean_git checkout "$BRANCH" >/dev/null 2>&1 || { log "FATAL: cannot checkout $BRANCH"; exit 1; }
  clean_git diff --cached --quiet -- || {
    log "FATAL: git persistence branch has a non-empty index"
    exit 2
  }
  clean_git push -q -u origin "$BRANCH" 2>/dev/null || true
fi

# n judges per answer = 1 primary + the comma-separated ensemble specs
NJUDGES=$(( 1 + $(printf '%s\n' "$ENSEMBLE" | tr ',' '\n' | grep -c .) ))
SCENARIO_SHA="$(python3 - "$SCENARIOS" <<'PY'
import hashlib, sys
print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())
PY
)"
COMMITTED="$WORK/.committed"
PUSH_PENDING="$WORK/.push-pending"
for evidence_path in "$COMMITTED" "$PUSH_PENDING" "$LEDGER" "$JUDGED" "$READY"; do
  [ ! -L "$evidence_path" ] || { log "FATAL: run evidence path is symlinked: $evidence_path"; exit 2; }
done
touch "$COMMITTED" "$PUSH_PENDING"
if [ -n "$MODEL_ROSTER" ]; then
  python3 - "$MODEL_ROSTER" "$COMMITTED" <<'PY' || {
from pathlib import Path
import sys
roster = [line.strip() for line in Path(sys.argv[1]).read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
committed = [line.strip() for line in Path(sys.argv[2]).read_text().splitlines() if line.strip()]
if len(committed) != len(set(committed)):
    raise SystemExit("committed-model marker contains duplicates")
extra = sorted(set(committed) - set(roster))
if extra:
    raise SystemExit(f"committed-model marker contains models outside roster: {extra}")
PY
    log "FATAL: committed-model marker failed roster validation"
    exit 2
  }
fi
if [ "$PERSIST_MODE" = "local-files" ] && [ -s "$PUSH_PENDING" ]; then
  log "FATAL: local-files persistence refuses a non-empty push-pending marker"
  exit 2
fi
log "streaming consumer: judge ${JUDGE_WORKERS:-8}-wide, ${NJUDGES} judges/answer, persist=$PERSIST_MODE per model"

JUDGE_ARGS=(--judge "copilot:$JUDGE_MODEL")
while IFS= read -r judge_spec; do
  [ -z "$judge_spec" ] || JUDGE_ARGS+=(--judge "$judge_spec")
done < <(printf '%s\n' "$ENSEMBLE" | tr ',' '\n')
[ "${#JUDGE_ARGS[@]}" -eq "$((NJUDGES * 2))" ] || {
  log "FATAL: persistence judge arguments differ from the authoritative judge count"
  exit 2
}

COPILOT_BIN="${COPILOT_BIN:-copilot}" python3 judge.py \
  --check-backends --backend copilot --model "$JUDGE_MODEL" --ensemble "$ENSEMBLE" \
  >>"$LOG" 2>&1 || {
    log "FATAL: judge authentication or fixed-model entitlement check failed"
    exit 2
  }

if [ "$PERSIST_MODE" = "local-files" ]; then
  [ -f scripts/persist-run-model.py ] && [ ! -L scripts/persist-run-model.py ] \
    || { log "FATAL: local persistence helper is missing or symlinked"; exit 2; }
  [ "$RUN_REPEATS" -gt 0 ] || { log "FATAL: run.meta repeats must be positive"; exit 2; }
  find "$WORK" -maxdepth 1 -type f \( \
    -name '.*.results.jsonl.gz.*' -o -name '.*.candidates.tar.gz.*' -o -name '.*.persistence.json.*' \
  \) -delete
  while IFS= read -r persisted_model; do
    [ -z "$persisted_model" ] && continue
    persisted_slug="${persisted_model//\//_}"; persisted_slug="${persisted_slug//:/_}"
    python3 scripts/persist-run-model.py \
      --run-dir "$WORK" --verify-receipt "$WORK/${persisted_slug}.persistence.json" \
      --model "$persisted_model" --judged "$JUDGED" --results "$MIRROR/$RESULTS" \
      --outputs-dir "$MIRROR/outputs" \
      --scenarios "$SCENARIOS" --reps "$RUN_REPEATS" --scenario-sha256 "$SCENARIO_SHA" \
      "${JUDGE_ARGS[@]}" >/dev/null \
      || { log "FATAL: persisted model receipt failed verification: $persisted_model"; exit 2; }
  done <"$COMMITTED"
fi

rm -f "$READY"
python3 - "$READY" "$RUN_ID" "$PERSIST_MODE" "$$" <<'PY'
import json, os, sys, tempfile, time
from pathlib import Path
path = Path(sys.argv[1])
payload = {"run_id": sys.argv[2], "persist_mode": sys.argv[3], "pid": int(sys.argv[4]), "ready_at": int(time.time())}
descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
temporary = Path(name)
try:
    with os.fdopen(descriptor, "w") as handle:
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
trap 'rm -f "$READY"' EXIT
log "consumer ready: persistence=$PERSIST_MODE receipts=$(grep -c . "$COMMITTED" 2>/dev/null || echo 0)"

mark_committed_atomic() {
  python3 - "$COMMITTED" "$1" <<'PY'
import os, sys, tempfile
from pathlib import Path

path = Path(sys.argv[1])
model = sys.argv[2]
values = [line.strip() for line in path.read_text().splitlines() if line.strip()]
if model not in values:
    values.append(model)
descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
temporary = Path(name)
try:
    with os.fdopen(descriptor, "w") as handle:
        handle.write("".join(value + "\n" for value in values))
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
}

while true; do
  guard_run_tree || exit 2
  if [ "$PERSIST_MODE" = "git-push" ] && [ -s "$PUSH_PENDING" ]; then
    if clean_git push -q origin "$BRANCH" 2>/dev/null; then
      while read -r pending_model; do
        [ -z "$pending_model" ] && continue
        grep -qxF "$pending_model" "$COMMITTED" || echo "$pending_model" >>"$COMMITTED"
        ledger "$pending_model" persist 1 "$(clean_git rev-parse --short HEAD)"
        status "model $pending_model -> PUSHED after retry"
      done <"$PUSH_PENDING"
      : >"$PUSH_PENDING"
    else
      status "push pending for $(wc -l <"$PUSH_PENDING" | tr -d ' ') model(s); retrying"
    fi
  fi

  # ---- S5 collect: incremental mirror of the producer's artifacts ----------
  "$RSYNC_BIN" -az -e "$SSH" "$AI:$AI_REPO/$RESULTS"      "$MIRROR/"          2>/dev/null || true
  "$RSYNC_BIN" -az -e "$SSH" "$AI:$AI_REPO/$RESULTS.done" "$MIRROR/"          2>/dev/null || true
  "$RSYNC_BIN" -az --delete -e "$SSH" "$AI:$AI_REPO/$REMOTE_OUTPUTS/" "$MIRROR/outputs/"  2>/dev/null || true
  guard_run_tree || exit 2

    VALIDATED_DONE_JSONL=""
  if [ -n "$MODEL_ROSTER" ] && [ -f "$MIRROR/$RESULTS.done" ]; then
    VALIDATED_DONE_JSONL=$("$COMPLETION_VALIDATOR" \
      --roster "$MODEL_ROSTER" --done "$MIRROR/$RESULTS.done" \
      --scenarios "$SCENARIOS" --reps "$RUN_REPEATS") || {
      log "FATAL: producer completion marker failed roster/domain validation"
      exit 2
    }
  fi

  # ---- S6 judge: score EVERY answer available right now, ${JUDGE_WORKERS:-8}-wide,
  # the instant it exists (judge.py skips already-judged rows). The producer keeps
  # burning through models; the judge never waits for a whole model to finish. ----
  rows=$([ -f "$MIRROR/$RESULTS" ] && wc -l <"$MIRROR/$RESULTS" | tr -d ' ' || echo 0)
  if [ "${rows:-0}" -gt 0 ]; then
    before=$([ -f "$JUDGED" ] && wc -l <"$JUDGED" | tr -d ' ' || echo 0)
    status "S6 judge: ${rows} answers available, ${before} judged so far (${JUDGE_WORKERS:-8}-wide)"
    JUDGE_BACKEND=copilot JUDGE_MODEL="$JUDGE_MODEL" JUDGE_WORKERS="${JUDGE_WORKERS:-8}" \
      python3 judge.py --judge --results "$MIRROR/$RESULTS" \
        --outputs-dir "$MIRROR/outputs" --scenarios "$SCENARIOS" --ensemble "$ENSEMBLE" \
        --out "$JUDGED" >>"$WORK/judge.log" 2>&1 || true
    after=$([ -f "$JUDGED" ] && wc -l <"$JUDGED" | tr -d ' ' || echo 0)
    [ "${after:-0}" -gt "${before:-0}" ] && ledger "*" judge 1 "judged ${before}->${after}"
  fi

  # ---- S7 persist: commit each model that is fully INFERRED (in .done) and fully
  # JUDGED (units x n_judges rows), exactly once. ----------------------------
  if [ -n "$VALIDATED_DONE_JSONL" ]; then
    while read -r m units; do
      [ -z "$m" ] && continue
      grep -qxF "$m" "$COMMITTED" && continue
      if grep -qxF "$m" "$PUSH_PENDING"; then
        status "model $m: local commit made, push pending"
        continue
      fi
      want=$(( ${units:-0} * NJUDGES ))
      have=$(jq -r --arg m "$m" --arg sha "$SCENARIO_SHA" \
        'select(.model==$m and .scenarios_sha256==$sha) | [.scenario, (.rep|tostring), (.judge_backend // "unknown"), .judge_model] | @tsv' \
        "$JUDGED" 2>/dev/null | sort -u | wc -l | tr -d ' ')
      if [ "$want" -le 0 ] || [ "${have:-0}" -lt "$want" ]; then
        status "model $m: judged ${have}/${want}, waiting"; continue
      fi
      msafe="${m//\//_}"; msafe="${msafe//:/_}"
      if [ "$PERSIST_MODE" = "git-push" ]; then
        clean_git diff --cached --quiet -- || {
          ledger "$m" persist 0 "git index is not empty"
          status "model $m: git index is not empty, not committing"
          continue
        }
        persist_json=$(python3 scripts/persist-run-model.py \
          --persist-mode git-push --results "$MIRROR/$RESULTS" --judged "$JUDGED" \
          --outputs-dir "$MIRROR/outputs" --run-dir "$WORK" \
          --model "$m" --units "${units:-0}" --scenario-sha256 "$SCENARIO_SHA" \
          --scenarios "$SCENARIOS" --reps "$RUN_REPEATS" \
          "${JUDGE_ARGS[@]}" 2>>"$LOG") || {
            ledger "$m" persist 0 "git evidence incomplete"
            status "model $m: git evidence incomplete, not committing"
            continue
          }
        git_archive_assignments=$(python3 -c '
import json, shlex, sys
value = json.load(sys.stdin)
for variable, key in (("GIT_RESULT_ARCHIVE", "result_archive"), ("GIT_CANDIDATE_ARCHIVE", "candidate_archive"), ("GIT_RECEIPT", "receipt")):
    print(f"{variable}={shlex.quote(value[key])}")
' <<<"$persist_json") || {
          ledger "$m" persist 0 "git persistence receipt invalid"
          status "model $m: git persistence receipt invalid, not committing"
          continue
        }
        eval "$git_archive_assignments"
      fi
      if [ "$PERSIST_MODE" = "local-files" ]; then
        persist_json=$(python3 scripts/persist-run-model.py \
          --results "$MIRROR/$RESULTS" --judged "$JUDGED" \
          --outputs-dir "$MIRROR/outputs" --run-dir "$WORK" \
          --model "$m" --units "${units:-0}" --scenario-sha256 "$SCENARIO_SHA" \
          --scenarios "$SCENARIOS" --reps "$RUN_REPEATS" \
          "${JUDGE_ARGS[@]}" 2>>"$LOG") || {
            ledger "$m" persist 0 "local evidence incomplete"
            status "model $m: local evidence incomplete, not marking persisted"
            continue
          }
        persist_detail=$(python3 -c 'import json,sys; value=json.load(sys.stdin); print("local-files receipt_sha256=%s result_sha256=%s candidate_sha256=%s rows=%s judgements=%s retries=%s" % (value["receipt_sha256"], value["result_archive_sha256"], value["candidate_archive_sha256"], value["result_rows"], value["canonical_judgements"], value["judge_retries"]))' <<<"$persist_json") || {
          ledger "$m" persist 0 "local evidence receipt invalid"
          status "model $m: local evidence receipt invalid, not marking persisted"
          continue
        }
        ledger "$m" persist 1 "$persist_detail"
        mark_committed_atomic "$m" || {
          ledger "$m" persist 0 "local committed marker update failed"
          status "model $m: local committed marker update failed"
          continue
        }
        status "model $m -> PERSISTED LOCALLY (${have} judge rows)"
        continue
      fi
      git_paths=(
        "$WORK/$GIT_RESULT_ARCHIVE"
        "$WORK/$GIT_CANDIDATE_ARCHIVE"
        "$WORK/$GIT_RECEIPT"
        "$JUDGED"
        "$LEDGER"
        "$STATUS"
      )
      if ! clean_git add -f -- "${git_paths[@]}"; then
        clean_git reset -q -- "${git_paths[@]}" >/dev/null 2>&1 || true
        ledger "$m" persist 0 "git add failed"
        status "model $m: git add failed, not committing"
        continue
      fi
        staged_paths=$(clean_git diff --cached --name-only --)
        if ! STAGED_PATHS="$staged_paths" python3 -c '
    import os, sys
    actual = {value for value in os.environ.get("STAGED_PATHS", "").splitlines() if value}
    expected = set(sys.argv[1:])
    if actual != expected:
      raise SystemExit(
        "staged path set differs: extra=%r missing=%r"
        % (sorted(actual - expected), sorted(expected - actual))
      )
    ' "${git_paths[@]}"; then
        clean_git reset -q -- "${git_paths[@]}" >/dev/null 2>&1 || true
        ledger "$m" persist 0 "unexpected staged paths"
        status "model $m: unexpected staged paths, not committing"
        continue
      fi
      if clean_git diff --cached --quiet; then
        ledger "$m" persist 0 "nothing staged"
        status "model $m: nothing staged, not marking committed"
        continue
      fi
      if clean_git commit -q -m "experiment($RUN_ID): judged $m (${have} judge rows)" -- "${git_paths[@]}"; then
        clean_git diff --cached --quiet -- || {
          ledger "$m" persist 0 "git index not empty after commit"
          status "model $m: git index not empty after commit"
          exit 2
        }
        if clean_git push -q origin "$BRANCH" 2>/dev/null; then
          ledger "$m" persist 1 "$(clean_git rev-parse --short HEAD)"
          echo "$m" >>"$COMMITTED"
          status "model $m -> COMMITTED (${have} judge rows)"
        else
          ledger "$m" persist 0 "push failed"
          grep -qxF "$m" "$PUSH_PENDING" || echo "$m" >>"$PUSH_PENDING"
          status "model $m: push failed, not marking committed"
        fi
      else
        ledger "$m" persist 0 "commit failed"
        status "model $m: commit failed, not marking committed"
      fi
    done < <(printf '%s\n' "$VALIDATED_DONE_JSONL" | jq -r '"\(.model) \(.units)"')
  fi

  ncommitted=$(grep -c . "$COMMITTED" 2>/dev/null); ncommitted=${ncommitted:-0}
  if [ "${EXPECT:-0}" -gt 0 ] && [ "${ncommitted:-0}" -ge "$EXPECT" ]; then
    status "EXPECT=$EXPECT models persisted — consumer exiting cleanly"
    break
  fi
  sleep "$POLL_S"
done
