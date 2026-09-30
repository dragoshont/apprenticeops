# Runtime evidence

Parent owns Edge acceptance and durable loopback launch. Worker only runs isolated
synthetic HTTP tests; no model execution, deployment, or real human labels.

Real pilot preparation (not browser interaction):
`.tmp/human-review/operator-pilot-10-v1` in the original checkout.
Packet ID: `573e2253b61a4328b70573b5a83fbb10`.
Packet SHA256: `1f9ec883cd913b3b82c233099d08602d0674ce4a894473fedda22f168b2b9b2e`.
Protocol SHA256: `71ed09bb7efb1641344a54fb5b80cb43ab7ed698b8bfae91480a98a352635c4d`.
Ten items, two safety-scoped; zero sessions or labels. Exact source keys remain
private-sidecar only. Prompt lengths 306–719 and answer lengths 50–2479 characters,
unmodified (not display caps); full-source equality also tested with longer fixtures.

Persistent-storage correction: the location above is historical/current before
integration. The candidate now defaults to data/human-review-local/operator-pilot-10-v1
and migrates that exact legacy directory on first default launch, preserving
packet/progress bytes. Parent must integrate the authorized .gitignore entry
before that launch. Migration tests used only synthetic temporary fixtures.
