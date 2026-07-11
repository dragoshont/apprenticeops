# Data Rights and Reuse

ApprenticeOps code, repository-authored documentation, scenarios, schemas, and
analysis code are released under the repository's Apache-2.0 license.

The frozen benchmark dataset also contains generated answers from third-party
model deployments. Those deployments span permissive, custom, and
noncommercial model-family terms. ApprenticeOps does not redistribute model
weights and does not grant rights beyond the applicable upstream terms. The
canonical per-model rights ledger is [`models.lock.jsonl`](models.lock.jsonl);
its `license`, `license_class`, and `license_url` fields identify the policy used
for each deployment.

The Croissant metadata therefore declares mixed rights: Apache-2.0 for the
repository-authored material plus every upstream model-license URL represented
in the frozen 94-model population. Before redistributing or commercially using
model-generated answers, review the terms for each contributing model family.
The metadata intentionally does not claim that all generated content is
Apache-2.0 or CC-BY.

The scenarios use synthetic or scrubbed operational material as documented in
[`raw/README.md`](raw/README.md) and [`../docs/PRIVACY_AND_EGRESS.md`](../docs/PRIVACY_AND_EGRESS.md).
No model weights, real credentials, or private incident records are included.