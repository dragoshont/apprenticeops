# ApprenticeOps Concept Nodes (`data/concepts/`) — P4 knowledge capture

Owned, structured operations knowledge that otherwise lives only in prose gold-answers and cited-but-not-embedded SRE/DORA books. Ported from the uoeo-msc ITS knowledge-capture layer (see that repo's `docs/its-research-and-knowledge-capture.md`).

> **Not the same as the top-level `knowledge/` directory.** `knowledge/` holds **Architrave's framework packs** (agent guidance — apple/backend/web/operations-ux/…, declared `kind: knowledge` in `architrave.config.json`). This `data/concepts/` directory holds the **ApprenticeOps domain model**: the ops facts the benchmark tests. They are deliberately separate — do not merge domain data into the Architrave packs.

Each node in `nodes/` is one teachable ops concept/algorithm/technique/pitfall. It:
- cites an **owned in-repo source** (`data/memory/homelab-okf-v1/`, `docs/TAXONOMY.md`, `docs/PROTOCOL.md`) — not a book;
- links to the **scenarios** it underpins (a reverse map, so `data/scenarios.json` is not edited);
- carries constraints + misconceptions (the reasoning the gold answers encode);
- is `verified: true` only after a human checked it against the source.

## Why (benchmark benefit)

The **grounded** experimental condition currently feeds a model a flat ~3 KB OKF brief. With structured nodes, grounding can retrieve the *specific* nodes relevant to a scenario, giving a cleaner measure of grounding-faithfulness and letting results report **which ops concepts** small local models get wrong.

## Node → scenario map (this batch)

| Node | Scenarios |
|------|-----------|
| `ops.crashloop-cumulative-vs-active` | detect-01-crashloop-triage |
| `ops.rca-layer-isolation` | localize-02-externalsecret, diagnose-26-sideport-installed-apps-rca, new-flux-drift-source-not-ready |
| `ops.destructive-action-guard` | guard-08-destructive, secure-14-injection-destructive, secure-16-injection-approval, toolcall-20-structured-restart |
| `ops.capacity-forecast` | foresee-14-disk-fill-predict, foresee-15-pvc-pressure, foresee-16-smart-prefail, new-linux-oom-or-node-pressure |
| `ops.least-privilege-default-deny` | secure-10-ingress-no-auth, secure-11-privileged-container, secure-12-broad-rbac, secure-13-latest-tag |

## Validate (stdlib only)

```bash
python3 data/concepts/validate.py
```

Checks required fields, provenance (every source artifact exists on disk), scenario-id existence against `data/scenarios.json`, and prerequisite-graph integrity.

## Authoring a new node

Copy an existing node in `nodes/`, cite an owned source, list the scenarios it underpins, set `verified: false`, fill the content from the source, then flip `verified: true` after a human check. Keep JSON (this repo is JSON-native).
