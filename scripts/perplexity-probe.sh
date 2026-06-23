#!/usr/bin/env bash
# perplexity-probe.sh — OPTIONAL judge-free quality signal via llama.cpp, computed
# on the SAME GGUF blobs ollama already pulled (identical weights/quant). It is
# DECOUPLED from the locked ollama sweep:
#   - it adds ZERO time to the 15k-run main sweep (run it AFTER, or on idle time);
#   - per model it is a forward pass over a FIXED corpus (no generation), so it is
#     fast — seconds-to-minutes each, ~1-3h for the whole 158-tag roster on CPU;
#   - run it under scripts/node-power.sh setup for a clean clock if you want the
#     timing too (the PPL value itself is weight-determined, not clock-sensitive).
#
# Why bother: perplexity is the STANDARD quantization-quality metric (llama.cpp's
# own quant tables + Dettmers' 4-bit paper use it). With our q4/q8/fp16 variants it
# gives a clean quant-degradation curve that det-checks + the LLM judge are too
# coarse to see, plus a judge-INDEPENDENT quality axis (cross-checks the judge's
# known verbosity bias) and a calibration signal.
#
#   ./scripts/perplexity-probe.sh CORPUS.txt [models.txt] [out.jsonl]
#
# CORPUS = a HELD-OUT ops text file (NOT data/scenarios.json — keep it out-of-sample
# so PPL isn't circular). Join to the main results on `model` / `ollama.digest`.
# Needs llama.cpp's `llama-perplexity` on PATH (build: github.com/ggml-org/llama.cpp).
set -uo pipefail
CORPUS="${1:?usage: perplexity-probe.sh CORPUS.txt [models.txt] [out.jsonl]}"
MODELS="${2:-data/models.txt}"
OUT="${3:-results.perplexity.jsonl}"
CTX="${PPL_CTX:-2048}"

command -v llama-perplexity >/dev/null 2>&1 || { echo "FATAL: llama-perplexity not on PATH (build llama.cpp)"; exit 1; }
[ -f "$CORPUS" ] || { echo "FATAL: corpus $CORPUS not found"; exit 1; }
[ -f "$MODELS" ] || { echo "FATAL: model list $MODELS not found"; exit 1; }

# Resolve a tag -> its on-disk GGUF blob (the FROM line of the ollama Modelfile).
blob_of() { ollama show --modelfile "$1" 2>/dev/null | awk '/^FROM \//{print $2; exit}'; }

n=0
grep -vE '^[[:space:]]*(#|$)' "$MODELS" | while read -r tag; do
  [ -n "$tag" ] || continue
  n=$((n+1))
  if ! ollama show "$tag" >/dev/null 2>&1; then
    ollama pull "$tag" >/dev/null 2>&1 || { echo "skip (cannot fetch): $tag"; continue; }
  fi
  blob="$(blob_of "$tag")"
  [ -n "$blob" ] && [ -f "$blob" ] || { echo "skip (no GGUF blob): $tag"; continue; }
  # llama-perplexity prints e.g. "Final estimate: PPL = 6.1234 +/- 0.04567"
  ppl="$(llama-perplexity -m "$blob" -f "$CORPUS" -c "$CTX" 2>/dev/null \
          | awk -F'PPL = ' '/PPL = /{split($2,a," "); print a[1]; exit}')"
  ts="$(date -u +%FT%TZ)"
  printf '{"ts":"%s","model":"%s","blob":"%s","ppl":%s,"ctx":%s,"corpus":"%s"}\n' \
    "$ts" "$tag" "$(basename "$blob")" "${ppl:-null}" "$CTX" "$(basename "$CORPUS")" \
    | tee -a "$OUT"
done
echo "== perplexity probe done -> $OUT =="
