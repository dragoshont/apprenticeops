# Archival Dataset Release

Status: metadata and deterministic package tooling ready; external publication
requires operator approval. **DOI status: not reserved.**

Croissant `datePublished=2026-06-21` records the first Git publication of the
complete Wave-1 + Wave-2 raw dataset (commit `36fc989`, author date checked by
`scripts/audit-release-metadata.py`); `dateModified=2026-07-11`
records the correction-lock metadata update. It does not imply a Zenodo record
or DOI.

## Decision

Use a manual **Zenodo dataset record** for the citable frozen dataset. Keep the
GitHub repository as the executable code and documentation source. Do not use
the paper DOI for the dataset, and do not rely on the GitHub-to-Zenodo software
integration as the dataset record.

Why Zenodo:

- it issues a dataset DOI and supports reserving it before publication;
- one upload can contain up to 100 files and 50 GB, comfortably above this
  artifact's size;
- it supports multiple standard or custom licenses, which this mixed-rights
  benchmark requires;
- immutable versions and a persistent landing page fit the correction-lock
  workflow.

The most recent published Datasets & Benchmarks guidance available during this
preparation also expects reviewer-accessible data/code and a Croissant file at
submission. Re-check the selected conference year's live author kit before
submission; a dedicated ML-host mirror may still be required in addition to the
Zenodo archive.

## Prepared Artifacts

- `data/croissant.json`: Croissant 1.0 metadata, generated from the locked
  analysis manifest and validated with `mlcroissant==1.0.22`.
- `data/DATA_RIGHTS.md`: mixed-rights statement. Repository-authored material is
  Apache-2.0; model-generated outputs remain subject to the represented model
  family terms.
- `.python-version` and `requirements-lock.txt`: exact Python 3.14.5 plus the
  universal hash-locked analysis/release graph. `uv` regenerates the lock;
  standard pip installs it with `--require-hashes`.
- `data/tool-license-policy.json` and `scripts/audit-tool-licenses.py`: sourced
  license policy for the added uv (MIT OR Apache-2.0), Pillow (MIT-CMU), and
  mlcroissant (Apache-2.0) tools plus all active locked dependencies.
- `scripts/build-release-package.py`: deterministic package builder under
  `.tmp/release/`, containing every frozen source plus citation, rights,
  privacy, reproduction, inventory, and the public blind scoring sheet. The
  private `key.json` is excluded until human scoring and agreement are complete.
- `scripts/audit-release-metadata.py`: citation, rights, Croissant, and release
  plan gate.

## Validate Locally

```bash
python3 scripts/build-croissant.py --check
python3 scripts/validate-croissant.py

python3.14 -m venv .tmp/release-venv
.tmp/release-venv/bin/python -m pip install --require-hashes -r requirements-lock.txt
.tmp/release-venv/bin/python scripts/validate-analysis-environment.py
.tmp/release-venv/bin/python scripts/audit-tool-licenses.py
.tmp/release-venv/bin/python scripts/validate-croissant.py --official

python3 scripts/build-release-package.py
python3 scripts/audit-release-metadata.py
```

Croissant `contentUrl` values are relative to `data/croissant.json`. They work
from a checkout, from the raw GitHub metadata URL, and after extracting the
deterministic release archive because the `data/` layout is preserved.

## Zenodo Operator Gate

Do these steps only after the correction-lock commit and final release review:

1. Create a new Zenodo upload with resource type **Dataset**.
2. Use the title and creator from `data/croissant.json`; link the GitHub
   repository as the related software resource.
3. Declare Apache-2.0 plus the custom/noncommercial model-family rights listed
   in `data/DATA_RIGHTS.md`. Do not accept Zenodo's default CC-BY as the only
   license.
4. Upload the deterministic `.tmp/release/*.tar.gz` package and its SHA-256.
5. Reserve the dataset DOI only when the files and metadata are final. A deleted
   draft loses its reserved DOI; publication registers it.
6. Add the reserved DOI to `CITATION.cff`, Croissant `identifier`/`sameAs`, and
   the manuscript, rebuild the package, and rerun all release gates.
7. Preview the public record, verify download without authentication, then
   publish. Record the version DOI and use the concept DOI for project-level
   citations after Zenodo creates it.

No DOI, upload, or public record is created by repository scripts.