# Submission Checklist

Status: preparation started; venue-specific formatting and external publication
remain open.

Target family: arXiv preprint followed by a Datasets & Benchmarks venue. The
latest accessible NeurIPS Datasets & Benchmarks call used for this preparation
is the 2025 call; re-check the live call, author kit, page limit, deadlines,
OpenReview fields, and checklist for the actual submission year.

## Evidence And Claims

- [x] One canonical analysis schema (`v1`) and locked frozen manifest.
- [x] Every current public numeric surface passes the claim audit.
- [x] Quality/safety breadth and controlled systems scopes are separated.
- [x] Invalid pooled-energy result is withdrawn everywhere.
- [x] Limitations and non-claims are explicit.
- [ ] Human scores and judge-human agreement artifact are complete.
- [x] Fresh detached-checkout reproduction with fresh declared dependencies is
  recorded and leaves no tracked mutation.
- [ ] A second human operator records independent reproduction sign-off.

## Dataset And Code

- [x] Code, scenarios, snapshots, raw evidence, and reproduction commands exist.
- [x] Croissant 1.0 metadata validates locally and with the official parser.
- [x] Deterministic archive package tooling and SHA-256 verification exist.
- [x] Python 3.14.5 and the full universal transitive environment are
  hash-locked; active dependency licenses pass the explicit tool policy.
- [x] Mixed model-output rights are explicit; no Apache-only data claim.
- [ ] Zenodo dataset DOI is reserved, embedded, and published.
- [ ] Confirm whether the selected venue year requires a dedicated ML-host
  mirror (Hugging Face, OpenML, Dataverse, or Kaggle) in addition to Zenodo.
- [ ] Reviewer access is tested without authentication or a request to the PI.

## Manuscript Package

- [x] Quarto HTML and Typst PDF render from one source.
- [x] Reproducibility, ethics, privacy/egress, and compute scope are documented.
- [ ] Apply the selected venue's current template without changing claims.
- [ ] Verify page limits, references/appendix policy, anonymization choice, and
  supplemental-material policy against the live author kit.
- [ ] Complete the venue's reproducibility, compute, ethics, and dataset
  documentation checklist.
- [ ] Run a final citation, attribution, accessibility, and link sweep.

## Final Release Gate

```bash
python3 scripts/audit-paper-data.py
python3 scripts/audit-paper-claims.py
python3 scripts/audit-release-metadata.py
scripts/build-analysis-site.sh --verify
python3 scripts/privacy-scan.py
```

Do not mark submission-ready while any unchecked item above affects reviewer
access, human validation, licensing, or the selected venue's mandatory policy.