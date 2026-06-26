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

RUN_ID="${RUN_ID:?set RUN_ID (the producer run id, e.g. roster-20260624-1200)}"
AI="${AI:-dragos@home-ai.hont.ro}"
AI_REPO="${AI_REPO:-/home/dragos/apprenticeops}"                 # where run-roster.sh runs on `ai`
BRANCH="${BRANCH:-experiment/${RUN_ID}}"
POLL_S="${POLL_S:-30}"
ENSEMBLE="${ENSEMBLE:-copilot:gpt-5.4}"
JUDGE_MODEL="${JUDGE_MODEL:-claude-opus-4.6}"
EXPECT="${EXPECT:-0}"                               # >0 = exit once this many models are judged
SCENARIOS="${SCENARIOS:-data/scenarios.json}"

RESULTS="results.${RUN_ID}.jsonl"
WORK="data/runs/${RUN_ID}"
MIRROR="${WORK}/_mirror"                            # local mirror of the ai artifacts
LEDGER="${WORK}/pipeline-ledger.jsonl"
JUDGED="${WORK}/judged.${RUN_ID}.jsonl"
STATUS="${WORK}/judge-scheduler.status"
LOG="${WORK}/judge-scheduler.log"
mkdir -p "$WORK" "$MIRROR/outputs"

# single-instance guard: a stale relaunch must not double-judge the same RUN_ID
exec 9>"${WORK}/.consumer.lock"
if command -v flock >/dev/null 2>&1 && ! flock -n 9; then
  echo "[$(date -uIs)] another consumer already holds ${WORK}/.consumer.lock; exiting" >&2
  exit 0
fi

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

# n judges per answer = 1 primary + the comma-separated ensemble specs
NJUDGES=$(( 1 + $(printf '%s' "$ENSEMBLE" | tr ',' '\n' | grep -c .) ))
SCENARIO_SHA="$(python3 - "$SCENARIOS" <<'PY'
import hashlib, sys
print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())
PY
)"
COMMITTED="$WORK/.committed"; touch "$COMMITTED"
PUSH_PENDING="$WORK/.push-pending"; touch "$PUSH_PENDING"
log "streaming consumer: judge ${JUDGE_WORKERS:-8}-wide, ${NJUDGES} judges/answer, commit per model"

while true; do
  if [ -s "$PUSH_PENDING" ]; then
    if git push -q origin "$BRANCH" 2>/dev/null; then
      while read -r pending_model; do
        [ -z "$pending_model" ] && continue
        grep -qxF "$pending_model" "$COMMITTED" || echo "$pending_model" >>"$COMMITTED"
        ledger "$pending_model" persist 1 "$(git rev-parse --short HEAD)"
        status "model $pending_model -> PUSHED after retry"
      done <"$PUSH_PENDING"
      : >"$PUSH_PENDING"
    else
      status "push pending for $(wc -l <"$PUSH_PENDING" | tr -d ' ') model(s); retrying"
    fi
  fi

  # ---- S5 collect: incremental mirror of the producer's artifacts ----------
  rsync -az -e "$SSH" "$AI:$AI_REPO/$RESULTS"      "$MIRROR/"          2>/dev/null || true
  rsync -az -e "$SSH" "$AI:$AI_REPO/$RESULTS.done" "$MIRROR/"          2>/dev/null || true
  rsync -az -e "$SSH" "$AI:$AI_REPO/outputs/"      "$MIRROR/outputs/"  2>/dev/null || true

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
  if [ -f "$MIRROR/$RESULTS.done" ]; then
    while read -r m units; do
      [ -z "$m" ] && continue
      grep -qxF "$m" "$COMMITTED" && continue
      if grep -qxF "$m" "$PUSH_PENDING"; then
        status "model $m: local commit made, push pending"
        continue
      fi
      want=$(( ${units:-0} * NJUDGES ))
      have=$(jq -r --arg m "$m" --arg sha "$SCENARIO_SHA" \
        'select(.model==$m and .scenarios_sha256==$sha) | [.scenario, (.rep|tostring), .judge_model] | @tsv' \
        "$JUDGED" 2>/dev/null | sort -u | wc -l | tr -d ' ')
      if [ "$want" -le 0 ] || [ "${have:-0}" -lt "$want" ]; then
        status "model $m: judged ${have}/${want}, waiting"; continue
      fi
      msafe="${m//\//_}"; msafe="${msafe//:/_}"
      jq -c --arg m "$m" 'select(.model==$m)' "$MIRROR/$RESULTS" >"$WORK/$msafe.results.jsonl" 2>/dev/null
      gzip -kf "$WORK/$msafe.results.jsonl"
      git add -f "$WORK/$msafe.results.jsonl.gz" "$JUDGED" "$LEDGER" "$STATUS" 2>/dev/null || true
      if git diff --cached --quiet; then
        ledger "$m" persist 0 "nothing staged"
        status "model $m: nothing staged, not marking committed"
        continue
      fi
      if git commit -q -m "experiment($RUN_ID): judged $m (${have} judge rows)"; then
        if git push -q origin "$BRANCH" 2>/dev/null; then
          ledger "$m" persist 1 "$(git rev-parse --short HEAD)"
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
    done < <(jq -r '"\(.model) \(.units)"' "$MIRROR/$RESULTS.done" 2>/dev/null)
  fi

  ncommitted=$(grep -c . "$COMMITTED" 2>/dev/null || echo 0)
  if [ "${EXPECT:-0}" -gt 0 ] && [ "${ncommitted:-0}" -ge "$EXPECT" ]; then
    status "EXPECT=$EXPECT models committed — consumer exiting cleanly"
    break
  fi
  sleep "$POLL_S"
done
