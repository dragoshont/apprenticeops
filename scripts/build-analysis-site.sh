#!/usr/bin/env bash
# Rebuild or verify the analysis outputs.
#   --update: executes all public notebooks in place and renders the site.
#   --verify: copies manifest-bound evidence into an isolated workspace, executes
#             notebook copies there, and compares cached outputs plus tracked
#             scientific artifacts without writing to the working tree.
# Usage: scripts/build-analysis-site.sh [--update|--verify]
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-.venv/bin/python}"
NOTEBOOKS=(
  "docs/analysis/wave_analysis.ipynb"
  "docs/analysis/judge_comparison.ipynb"
  "docs/analysis/reviewer.ipynb"
)
PRIMARY_NOTEBOOK="${NOTEBOOKS[0]}"
SITE="data/site"
FIGURES="docs/analysis/figures"
NOTEBOOK_COMPARATOR="scripts/compare-notebook-outputs.py"
MODE="${1:---update}"

if [[ "$MODE" != "--update" && "$MODE" != "--verify" ]]; then
  echo "usage: $0 [--update|--verify]" >&2
  exit 1
fi

if [[ "$PY" == */* ]]; then
  if [[ "$PY" == /* ]]; then
    resolved_py="$PY"
  else
    resolved_py="$PWD/$PY"
  fi
else
  resolved_py="$(command -v "$PY" 2>/dev/null || true)"
fi
if [ -z "$resolved_py" ] || [ ! -x "$resolved_py" ]; then
  echo "error: $PY not found. Create the venv and install dependencies first:" >&2
  echo "  python3.14 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements-lock.txt" >&2
  exit 1
fi
PY="$resolved_py"

if ! "$PY" -m jupyter nbconvert --version >/dev/null 2>&1; then
  echo "error: nbconvert is unavailable from $PY; install requirements-lock.txt" >&2
  exit 1
fi
"$PY" scripts/validate-analysis-environment.py
"$PY" scripts/audit-tool-licenses.py

if [[ "$MODE" == "--verify" ]]; then
  for path in "${NOTEBOOKS[@]}" "$SITE" "$FIGURES" "$NOTEBOOK_COMPARATOR"; do
    if [ ! -e "$path" ]; then
      echo "error: required analysis artifact missing: $path" >&2
      exit 1
    fi
  done

  tmp_dir="$(mktemp -d)"
  verify_root="$tmp_dir/repo"
  mkdir -p "$verify_root/data" "$verify_root/docs/analysis" "$verify_root/scripts"

  copy_path() {
    source_path="$1"
    destination="$verify_root/$source_path"
    mkdir -p "$(dirname "$destination")"
    cp -R "$source_path" "$destination"
  }

  copy_path "analysis_metrics.py"
  copy_path "data/analysis.schema.json"
  copy_path "data/analysis-manifest.json"
  copy_path "data/scenarios.json"
  copy_path "data/snapshots"
  mkdir -p "$verify_root/$SITE" "$verify_root/$FIGURES"
  copy_path "scripts/validate-analysis-schema.py"
  copy_path "scripts/make-paper-figures.py"
  copy_path "$NOTEBOOK_COMPARATOR"
  for notebook in "${NOTEBOOKS[@]}"; do
    copy_path "$notebook"
  done

  while IFS= read -r source_path; do
    copy_path "$source_path"
  done < <("$PY" -c 'import json; print("\n".join(json.load(open("data/analysis-manifest.json"))["source_sha256"]))')

  cleanup() {
    exit_code=$?
    rm -rf "$tmp_dir"
    exit "$exit_code"
  }
  trap cleanup EXIT

  echo "[1/4] executing notebooks in an isolated evidence workspace"
  for notebook in "${NOTEBOOKS[@]}"; do
    stem="$(basename "$notebook" .ipynb)"
    (
      cd "$verify_root"
      "$PY" -m jupyter nbconvert --to notebook --execute "$notebook" \
        --output "$stem.executed.ipynb" --output-dir "$tmp_dir" \
        --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=600
    )
  done

  echo "[2/4] validating schema v1 and regenerating paper figures"
  (
    cd "$verify_root"
    "$PY" scripts/validate-analysis-schema.py
    "$PY" scripts/make-paper-figures.py
  )

  echo "[3/4] comparing cached notebook outputs"
  mismatch=0
  for notebook in "${NOTEBOOKS[@]}"; do
    stem="$(basename "$notebook" .ipynb)"
    if ! "$PY" "$verify_root/$NOTEBOOK_COMPARATOR" \
      "$notebook" "$tmp_dir/$stem.executed.ipynb" "$verify_root"; then
      mismatch=1
    fi
  done

  echo "[4/4] comparing canonical exports and figures"
  if ! diff -qr "$SITE" "$verify_root/$SITE"; then
    echo "error: regenerated $SITE differs from the committed bundle" >&2
    mismatch=1
  fi
  if ! diff -qr "$FIGURES" "$verify_root/$FIGURES"; then
    echo "error: regenerated $FIGURES differs from the committed bundle" >&2
    mismatch=1
  fi
  if [[ "$mismatch" -ne 0 ]]; then
    echo "run '$0 --update' only as an explicit correction-lock refresh" >&2
    exit 1
  fi

  echo "analysis v1 verification passed; tracked notebook and outputs are unchanged"
  exit 0
fi

echo "[1/5] executing public notebooks in place"
for notebook in "${NOTEBOOKS[@]}"; do
  echo "      $notebook"
  "$PY" -m jupyter nbconvert --to notebook --execute --inplace "$notebook" \
    --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=600
done

echo "[2/5] validating canonical analysis schema v1"
"$PY" scripts/validate-analysis-schema.py

echo "[3/5] regenerating committed paper figures"
"$PY" scripts/make-paper-figures.py

echo "[4/5] standalone HTML  ->  docs/analysis/wave_analysis.html"
"$PY" -m jupyter nbconvert --to html --embed-images "$PRIMARY_NOTEBOOK" >/dev/null

if command -v quarto >/dev/null 2>&1; then
  echo "[5/5] quarto site     ->  docs/analysis/_site/"
  quarto render docs/analysis
else
  echo "[5/5] quarto not installed — skipped the multi-page site"
  echo "      install with:  brew install --cask quarto"
fi

echo "done."
echo "  data exports : data/site/"
echo "  HTML page    : docs/analysis/wave_analysis.html"
