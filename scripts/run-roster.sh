#!/usr/bin/env bash
# run-roster.sh — node-side LOCKED full-roster run (runs ON home-ai). Deterministic:
# locks the power state, refuses to start unless the node matches the frozen manifest,
# runs every model in data/models.txt under per-model quiesce + reset-state
# evidence (in the rows), and captures the ollama server log + CPU-library choice.
# Resumable: --rm-after + append-to-file; re-run continues, dedup later.
#
# Driven by scripts/run-from-homelab.sh, or standalone on the node:
#   ./scripts/run-roster.sh              # full roster
#   LIMIT=2 ./scripts/run-roster.sh      # stop-and-audit batch (2 models), then audit
#
# Data convention (collectable by run-from-homelab.sh):
#   results.<RUN_ID>.jsonl          one row per (model,scenario,rep), env.* + reset.* stamped
#   outputs/<model>__<scenario>__rN.txt
#   logs/<RUN_ID>/{driver,run,preflight}.log, ollama-server.log, ollama-list.txt,
#                 ollama.meta, ollama-cpu-library.txt, node-power-status.txt, calibration.json
set -uo pipefail
cd "$(dirname "$0")/.."
RUN_ID="${RUN_ID:-roster-$(date -u +%Y%m%d-%H%M)}"
MODELS="${MODELS:-data/models.txt}"
MODEL_SET="${MODEL_SET:-manual}"
SCENARIOS="${SCENARIOS:-data/scenarios.json}"
SCENARIO_SET="${SCENARIO_SET:-all}"
MEMORY_CONTEXT="${MEMORY_CONTEXT:-none}"
MEMORY_CONTEXT_FILE="${MEMORY_CONTEXT_FILE:-}"
OUT="${OUT:-results.${RUN_ID}.jsonl}"
LOGDIR="${LOGDIR:-logs/${RUN_ID}}"
mkdir -p "$LOGDIR" outputs
ts() { date -uIs; }
log() { echo "[$(ts)] $*" | tee -a "$LOGDIR/driver.log"; }

cleanup() {
  log "EXIT: restoring node power state"
  ./scripts/node-power.sh teardown >>"$LOGDIR/driver.log" 2>&1 || true
  [ -n "${OLLAMA_LOG_PID:-}" ] && kill "$OLLAMA_LOG_PID" 2>/dev/null || true
}
trap cleanup EXIT

log "=== ROSTER RUN $RUN_ID START (host $(hostname)) models=$MODELS scenarios=$SCENARIOS out=$OUT ==="
[ -f "$MODELS" ] || { log "FATAL: $MODELS not found"; exit 1; }
[ -f "$SCENARIOS" ] || { log "FATAL: $SCENARIOS not found"; exit 1; }
if [ -n "$MEMORY_CONTEXT_FILE" ]; then
  [ -f "$MEMORY_CONTEXT_FILE" ] || { log "FATAL: $MEMORY_CONTEXT_FILE not found"; exit 1; }
fi

# 0) never contend with another eval
while pgrep -f "run.py --models" >/dev/null 2>&1; do log "waiting for in-flight run.py ..."; sleep 120; done

# 1) LOCK the node (turbo off, governor performance, perf_event_paranoid=1, fans)
log "--- node-power.sh setup ---"
./scripts/node-power.sh setup  >>"$LOGDIR/driver.log" 2>&1 || log "WARN: node-power setup had issues"
./scripts/node-power.sh status >"$LOGDIR/node-power-status.txt" 2>&1 || true

# 2) capture ollama identity + digests + a continuous server log + CPU library
OLLAMA_VER="$(ollama --version 2>/dev/null || true)"; log "ollama: $OLLAMA_VER"
{ echo "# ollama version: $OLLAMA_VER"; echo "# captured: $(ts)"; echo "# OLLAMA_LLM_LIBRARY=${OLLAMA_LLM_LIBRARY:-auto}"; } >"$LOGDIR/ollama.meta"
ollama list >"$LOGDIR/ollama-list.txt" 2>&1 || true     # name/size/DIGEST of present models
if systemctl is-active --quiet ollama 2>/dev/null; then
  journalctl -u ollama -f --since "now" --no-pager >"$LOGDIR/ollama-server.log" 2>&1 &
  OLLAMA_LOG_PID=$!
  log "ollama log -> $LOGDIR/ollama-server.log (journalctl, pid $OLLAMA_LOG_PID)"
else
  cp "$HOME/.ollama/logs/server.log" "$LOGDIR/ollama-server.log" 2>/dev/null \
    && log "ollama log copied from ~/.ollama/logs/server.log" \
    || log "WARN: ollama not systemd + no ~/.ollama/logs/server.log — start 'ollama serve' with logging"
fi
# record which CPU LLM library ollama selected (cpu_avx2/avx/cpu) — a reproducibility fact
( sleep 45; grep -m1 -iE "dynamic llm librar|cpu_avx|llm library|system memory" "$LOGDIR/ollama-server.log" 2>/dev/null \
    >"$LOGDIR/ollama-cpu-library.txt" || true ) &

# 3) calibration (peak DRAM bandwidth for MBU); reuse if present
if [ ! -f calibration.json ]; then
  log "--- calibrate.py (peak DRAM bw / idle / ceilings) ---"
  RAPL_DOMAIN=package-0 PERF_MEMBW=1 timeout 900 python3 calibrate.py --out calibration.json \
    >>"$LOGDIR/driver.log" 2>&1 || log "WARN: calibrate failed (MBU peak will be approximate)"
fi
cp -f calibration.json "$LOGDIR/" 2>/dev/null || true
IDLE_T=$(python3 -c "import json;print(int(json.load(open('calibration.json')).get('idle_temp_c') or 50))" 2>/dev/null || echo 50)
COOL_T=$(( IDLE_T + 7 )); [ "$COOL_T" -lt 50 ] && COOL_T=58
log "cooldown target COOL_TEMP_C=${COOL_T}C"

# 4) PREFLIGHT — refuse to run unless the node matches data/run-manifest.json
log "--- preflight (must pass) ---"
if ! RAPL_DOMAIN=package-0 PERF_MEMBW=1 PERF_CORE=1 SCENARIO_SET="$SCENARIO_SET" python3 run.py --preflight-only \
  --scenarios "$SCENARIOS" --temp 0.7 --repeats 5 --seed-base 1 >"$LOGDIR/preflight.log" 2>&1; then
  log "FATAL: preflight FAILED:"; sed 's/^/    /' "$LOGDIR/preflight.log" | tee -a "$LOGDIR/driver.log"
  exit 3
fi
log "preflight OK"

# 5) THE LOCKED ROSTER RUN — per-model quiesce + reset-state evidence, all telemetry
NMODELS=$(grep -cvE '^[[:space:]]*(#|$)' "$MODELS")
NSCEN=$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))['scenarios']))" "$SCENARIOS" 2>/dev/null || echo '?')
log "--- roster run: ${NMODELS} models x ${NSCEN} scenarios x R=5, all telemetry, --rm-after ---"
QUIESCE=1 FAN_MAX=1 COOL_TEMP_C="${COOL_T}" COOL_MAX_S=120 DROP_CACHES=1 RESET_SWAP=1 \
SAMPLE_INTERVAL=0.5 PERF_MEMBW=1 PERF_CORE=1 RAPL_DOMAIN=package-0 SCENARIO_SET="$SCENARIO_SET" MEMORY_CONTEXT="$MEMORY_CONTEXT" \
python3 run.py --models "$MODELS" --scenarios "$SCENARIOS" --shuffle --order-seed 1 \
  --memory-context "$MEMORY_CONTEXT" \
  ${MEMORY_CONTEXT_FILE:+--memory-context-file "$MEMORY_CONTEXT_FILE"} \
  --temp 0.7 --repeats 5 --seed-base 1 --rm-after ${LIMIT:+--limit "$LIMIT"} \
  --out "$OUT" >>"$LOGDIR/run.log" 2>&1
rc=$?

# 6) quick reset-state health summary (proves identical-start across models)
python3 - "$OUT" >>"$LOGDIR/driver.log" 2>&1 <<'PY' || true
import json,sys,collections
ok=bad=0; warns=collections.Counter()
for ln in open(sys.argv[1]):
    ln=ln.strip()
    if not ln: continue
    try: r=json.loads(ln)
    except: continue
    if "reset.ok" in r:
        if r["reset.ok"]: ok+=1
        else: bad+=1; warns[r.get("reset.warnings")]+=1
print(f"reset-state: {ok} rows ok, {bad} flagged. top warnings: {dict(warns.most_common(5))}")
PY

log "=== ROSTER RUN $RUN_ID DONE rc=$rc rows=$(wc -l <"$OUT" 2>/dev/null || echo 0) ==="
log "audit:  python3 scripts/audit-run.py $OUT"
# node-power.sh teardown runs via the EXIT trap.
exit "$rc"
