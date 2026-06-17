#!/usr/bin/env bash
# run-experiment.sh — autonomous full ApprenticeOps eval pipeline.
#
# Launch DETACHED on the node:   nohup ./run-experiment.sh >driver.out 2>&1 &
#
# It runs the whole experiment hands-off and logs everything with timestamps:
#   1. waits for any in-flight run (the temp-0 det pass) to finish — never two at once;
#   2. locks the node into the reproducible power state (node-power.sh setup:
#      governor=performance, turbo OFF, clock pinned to base, fan control on,
#      Wi-Fi/Bluetooth off);
#   3. measures the hardware ceilings (calibrate.py: peak DRAM bw, disk, peak
#      tok/s, idle, telemetry observer overhead);
#   4. runs the FULL VARIANCE PASS — 25 models x 19 scenarios x R=5 at temp 0.7,
#      shuffled order, with ALL telemetry on (RAPL energy + core/uncore/dram,
#      perf memory-bandwidth + per-requestor split, perf CPU microarch/IPC,
#      iGPU, Ollama internals/MoE, per-model quiesce with fan-max + cache/swap
#      reset). This is the multi-day run;
#   5. restores the node (node-power.sh teardown) on ANY exit (trap).
#
# Monitor with:  tail -f experiment.log   and   wc -l results.var.jsonl
set -uo pipefail
cd "$(dirname "$0")"
LOG="$PWD/experiment.log"
ts() { date -uIs; }
log() { echo "[$(ts)] $*" | tee -a "$LOG"; }

# Always restore the node power state, however we exit (normal / error / crash).
trap 'log "EXIT: restoring node power state"; ./node-power.sh teardown >>"$LOG" 2>&1 || true' EXIT

log "=== experiment driver START (pid $$, host $(hostname)) ==="
log "disk: $(df -h . | awk 'NR==2{print $4\" free\"}')  mem: $(free -h | awk '/Mem/{print $7\" avail\"}')"

# 1) Wait for any in-flight eval run so we never contend. (This driver is a bash
#    script, so it never matches "run.py --models" itself.)
while pgrep -f "run.py --models" >/dev/null 2>&1; do
  log "waiting for an in-flight run to finish ($(wc -l < /tmp/sme/results.det.jsonl 2>/dev/null || echo 0) det rows) ..."
  sleep 120
done
log "node is free of eval runs"

# 2) Lock the node into the reproducible power state.
log "--- node-power.sh setup (lock clocks/fans/radios) ---"
./node-power.sh setup >>"$LOG" 2>&1 || log "WARN: node-power setup had issues (continuing best-effort)"

# 3) Measure the hardware ceilings on the now-quiet, locked box.
log "--- calibrate.py (hardware ceilings) ---"
if RAPL_DOMAIN=package-0 PERF_MEMBW=1 timeout 900 python3 calibrate.py --out calibration.json >>"$LOG" 2>&1; then
  log "calibration: $(tr -d '\n' < calibration.json)"
else
  log "WARN: calibrate.py failed/timed out (MBU columns will be blank)"
fi

# Adaptive cooldown target: idle temp + 7C (so quiesce forces a real settle
# without forever hitting the cap). Fallback 58C.
IDLE_T=$(python3 -c "import json;print(int(json.load(open('calibration.json')).get('idle_temp_c') or 50))" 2>/dev/null || echo 50)
COOL_T=$(( IDLE_T + 7 )); [ "$COOL_T" -lt 50 ] && COOL_T=58
log "cooldown target COOL_TEMP_C=${COOL_T}C (idle ${IDLE_T}C + 7)"

# 4) THE EXPERIMENT — full variance pass, all telemetry, locked + quiesced.
log "--- variance run: 25 models x 19 scenarios x R=5, all telemetry (this takes DAYS) ---"
QUIESCE=1 FAN_MAX=1 COOL_TEMP_C="${COOL_T}" COOL_MAX_S=120 DROP_CACHES=1 RESET_SWAP=1 \
SAMPLE_INTERVAL=0.5 PERF_MEMBW=1 PERF_CORE=1 RAPL_DOMAIN=package-0 \
python3 run.py --models models.txt --shuffle --order-seed 1 \
  --temp 0.7 --repeats 5 --seed-base 1 --out results.var.jsonl >>"$LOG" 2>&1
rc=$?
log "variance run exited rc=${rc}; rows=$(wc -l < results.var.jsonl 2>/dev/null || echo 0)"

# 5) Non-LLM baselines (cheap, no model) so 'LLM helps' is earned.
log "--- baselines.py ---"
python3 baselines.py --out results.baselines.jsonl >>"$LOG" 2>&1 || log "WARN: baselines.py failed"

log "=== experiment driver DONE (rows: var=$(wc -l < results.var.jsonl 2>/dev/null || echo 0)) ==="
# node-power.sh teardown runs via the EXIT trap.
