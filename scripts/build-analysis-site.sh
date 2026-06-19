#!/usr/bin/env bash
# Rebuild the analysis outputs and render the static site.
#   - executes wave_analysis.ipynb (repopulates figures + data/site/ exports)
#   - renders a standalone HTML page
#   - renders the multi-page Quarto site if Quarto is installed
# Usage: scripts/build-analysis-site.sh   (run from anywhere; cd's to repo root)
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-.venv/bin/python}"
JUPYTER="${JUPYTER:-.venv/bin/jupyter}"
NB="docs/analysis/wave_analysis.ipynb"

if [ ! -x "$JUPYTER" ]; then
  echo "error: $JUPYTER not found. Create the venv and install deps first:" >&2
  echo "  python3 -m venv .venv && .venv/bin/pip install pandas numpy matplotlib nbconvert ipykernel" >&2
  exit 1
fi

echo "[1/3] executing $NB (repopulates figures + data/site/ exports)"
"$JUPYTER" nbconvert --to notebook --execute --inplace "$NB" \
  --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=600

echo "[2/3] standalone HTML  ->  docs/analysis/wave_analysis.html"
"$JUPYTER" nbconvert --to html --embed-images "$NB" >/dev/null

if command -v quarto >/dev/null 2>&1; then
  echo "[3/3] quarto site     ->  docs/analysis/_site/"
  quarto render docs/analysis
else
  echo "[3/3] quarto not installed — skipped the multi-page site"
  echo "      install with:  brew install --cask quarto"
fi

echo "done."
echo "  data exports : data/site/"
echo "  HTML page    : docs/analysis/wave_analysis.html"
