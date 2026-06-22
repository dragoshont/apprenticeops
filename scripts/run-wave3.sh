#!/usr/bin/env bash
# run-wave3.sh — node-side Wave-3 sweep (the "missed models" expansion roster).
#
# Mirrors run-experiment.sh's locked + quiesced power state and full telemetry
# (so Wave-3 energy is directly comparable to the Wave-1 variance pass), but it
# points at data/models.wave3.txt, APPENDS to results.wave3.jsonl, and adds
# --rm-after (Wave 3 pulls ~43 models incl. the 4-5 GB tier and many hf.co GGUFs
# — --rm-after bounds disk by removing each model THIS run pulled once its
# scenarios finish; models already on disk are KEPT, never deleted).
#
# SAFE TO LAUNCH NOW: step 1 waits for any in-flight `run.py --models` (i.e. the
# Wave-2 sweep) to finish before it starts — so you can stage it today and it
# kicks off the moment Wave 2 wraps.
#
# ── FROM YOUR MAC (one-time sync, then launch detached on the node) ──────────
#   scp data/models.wave3.txt dragos@home-ai.hont.ro:/tmp/sme-var/data/
#   scp scripts/run-wave3.sh   dragos@home-ai.hont.ro:/tmp/sme-var/scripts/
#   ssh dragos@home-ai.hont.ro \
#     'cd /tmp/sme-var && nohup ./scripts/run-wave3.sh >wave3.driver.out 2>&1 &'
#
# ── MONITOR ──────────────────────────────────────────────────────────────────
#   ssh dragos@home-ai.hont.ro 'tail -f /tmp/sme-var/wave3.log'
#   ssh dragos@home-ai.hont.ro 'wc -l /tmp/sme-var/results.wave3.jsonl'
#
# When it finishes, run scripts/judge-wave3.sh ON YOUR MAC (fetch + dedup + the
# 2-judge quality pass). Safety + energy are already in results.wave3.jsonl.
set -uo pipefail
SME="${SME:-/tmp/sme-var}"
cd "$SME"
LOG="$PWD/wave3.log"
MODELS="${MODELS:-data/models.wave3.txt}"
OUT="${OUT:-results.wave3.jsonl}"
ts() { date -uIs; }
log() { echo "[$(ts)] $*" | tee -a "$LOG"; }
n_active() { grep -cvE '^[[:space:]]*(#|$)' "$1" 2>/dev/null || echo '?'; }

# Always restore the node power state, however we exit (normal / error / crash).
trap 'log "EXIT: restoring node power state"; ./scripts/node-power.sh teardown >>"$LOG" 2>&1 || true' EXIT

log "=== WAVE-3 driver START (pid $$, host $(hostname), dir $PWD) ==="
[ -f "$MODELS" ] || { log "FATAL: manifest $MODELS not found — scp it to $SME/data/ first"; exit 1; }
[ -f run.py ]   || { log "FATAL: run.py not in $SME (sync the repo files here first)"; exit 1; }
log "manifest: $MODELS ($(n_active "$MODELS") active tags; commented-out tags are skipped)"
log "disk: $(df -h . | awk 'NR==2{print $4\" free\"}')  mem: $(free -h | awk '/Mem/{print $7\" avail\"}')"

# 1) Never contend: wait for the Wave-2 (or any) run.py to finish first.
while pgrep -f "run.py --models" >/dev/null 2>&1; do
  log "waiting for an in-flight run to finish ($(wc -l < "$OUT" 2>/dev/null || echo 0) wave-3 rows so far) ..."
  sleep 120
done
log "node is free of eval runs — starting Wave 3"

# 2) Lock the reproducible power state (identical to Wave 1/2 so energy compares).
log "--- node-power.sh setup (lock clocks/fans/radios) ---"
./scripts/node-power.sh setup >>"$LOG" 2>&1 || log "WARN: node-power setup had issues (continuing best-effort)"

# 3) Reuse the existing hardware calibration — do NOT re-measure (keep the MBU
#    ceilings identical to Wave 1/2).
if [ -f calibration.json ]; then
  log "reusing calibration.json: $(tr -d '\n' < calibration.json)"
else
  log "WARN: no calibration.json in $SME — MBU columns will be blank (run calibrate.py if you want them)"
fi
IDLE_T=$(python3 -c "import json;print(int(json.load(open('calibration.json')).get('idle_temp_c') or 50))" 2>/dev/null || echo 50)
COOL_T=$(( IDLE_T + 7 )); [ "$COOL_T" -lt 50 ] && COOL_T=58
log "cooldown target COOL_TEMP_C=${COOL_T}C (idle ${IDLE_T}C + 7)"

# 4) THE WAVE-3 SWEEP — same temp / reps / telemetry as the powered Wave-1
#    variance pass; --rm-after to bound disk; APPEND to results.wave3.jsonl
#    (dedup later on the Mac). Thinking models run WITHOUT --think here, exactly
#    as in the committed Wave-1 variance pass (run-experiment.sh); if you want a
#    separate think:true profile for the reasoning tags, see the note at the end.
log "--- wave-3 run: $(n_active "$MODELS") models x 19 scenarios x R=5, temp 0.7, all telemetry, --rm-after ---"
QUIESCE=1 FAN_MAX=1 COOL_TEMP_C="${COOL_T}" COOL_MAX_S=120 DROP_CACHES=1 RESET_SWAP=1 \
SAMPLE_INTERVAL=0.5 PERF_MEMBW=1 PERF_CORE=1 RAPL_DOMAIN=package-0 \
python3 run.py --models "$MODELS" --shuffle --order-seed 1 \
  --temp 0.7 --repeats 5 --seed-base 1 --rm-after --out "$OUT" >>"$LOG" 2>&1
rc=$?
log "=== WAVE-3 driver DONE rc=${rc}; rows=$(wc -l < "$OUT" 2>/dev/null || echo 0) ==="
# node-power.sh teardown runs via the EXIT trap.
#
# NEXT (on your Mac):  scripts/judge-wave3.sh   (fetch + dedup + 2-judge quality).
#
# Optional separate think:true profile for the reasoning tags only (qwen3-thinking,
# deepseek-r1, cogito, smallthinker, SmolLM3) — run AFTER the main sweep and write
# to a distinct file so it's labelled, e.g.:
#   printf '# bracket: 3-4B\nqwen3:4b-thinking-2507-q4_K_M\ncogito:3b\nsmallthinker:3b-preview-q4_K_M\n' > data/models.wave3.think.txt
#   QUIESCE=1 ... python3 run.py --models data/models.wave3.think.txt --think \
#     --temp 0.7 --repeats 5 --rm-after --out results.wave3.think.jsonl
