#!/usr/bin/env bash
# Export the paper to Word (.docx) for collaborators or reviewers who prefer it.
# Uses the COMMITTED figures (docs/analysis/figures/) and references.bib, so it
# needs only Quarto (pandoc is bundled) — no Python, no kernel.
#
#   ./scripts/make-paper-docx.sh   ->   docs/analysis/paper.docx
set -euo pipefail
cd "$(dirname "$0")/.."
quarto render docs/analysis/paper.qmd --to docx
cp -f docs/analysis/_site/paper.docx docs/analysis/paper.docx
echo "wrote docs/analysis/paper.docx (Word)"
