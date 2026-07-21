# Handover — Ops knowledge capture (`data/concepts/`)

**For:** the ceops / apprenticeops review agent
**From:** uni-assistant (external ITS/knowledge-capture work, uoeo-msc)
**Branch:** `its-knowledge-capture` (commit `ea6fdc3`) — **not pushed**
**Date:** 2026-07-21
**Change type:** additive only (no existing files modified, no `scenarios.json` edit, no push)

---

## 1. TL;DR — what to review

A new directory `data/concepts/` captures ApprenticeOps **ops domain knowledge** as structured, sourced, verified nodes and links each to the scenarios it underpins. Please review it for: **correctness of the ops claims**, **fit with repo conventions**, and whether the **integration approach** (reverse scenario-link, no `scenarios.json` edit) is the one you want before merging.

```
data/concepts/
├── node.schema.json     # JSON Schema (draft 2020-12) for a concept node
├── validate.py          # stdlib-only validator (no pytest/pyyaml/jsonschema)
├── README.md            # what/why + node→scenario map + how to validate
└── nodes/
    ├── ops.crashloop-cumulative-vs-active.json
    ├── ops.rca-layer-isolation.json
    ├── ops.destructive-action-guard.json
    ├── ops.capacity-forecast.json
    └── ops.least-privilege-default-deny.json
```

Validate (from repo root):
```bash
python3 data/concepts/validate.py     # -> OK - 5 node(s) valid: fields + provenance + scenarios + graph.
```

---

## 2. Why this exists

ApprenticeOps' actual ops algorithms (cumulative-vs-active restart triage, RCA layer-isolation, destructive-action guarding, capacity forecasting, least-privilege/default-deny) currently live **only** inside prose `gold_answer`s, `deterministic_checks`, and cited-but-not-embedded SRE/DORA books. That knowledge is not queryable, not versioned as a unit, and not reusable as a grounding target.

This change captures it as an **owned domain model**: one node per concept, each citing an **owned in-repo source** (the OKF briefs + taxonomy — not a book), carrying the constraints and misconceptions the gold answers encode, and linked to the scenarios that exercise it.

**Benchmark payoff:** the *grounded* condition today injects a flat ~3 KB OKF brief. With structured nodes, grounding can retrieve the *specific* nodes relevant to a scenario — a cleaner measure of grounding-faithfulness, and it lets results report *which concepts* small local models get wrong. (This is a proposal/enabler; it is **not** wired into `run.py` yet — see §6.)

---

## 3. Node → scenario map (this batch)

| Node | Scenarios it underpins |
|------|------------------------|
| `ops.crashloop-cumulative-vs-active` | `detect-01-crashloop-triage` |
| `ops.rca-layer-isolation` | `localize-02-externalsecret`, `diagnose-26-sideport-installed-apps-rca`, `new-flux-drift-source-not-ready` |
| `ops.destructive-action-guard` | `guard-08-destructive`, `secure-14-injection-destructive`, `secure-16-injection-approval`, `toolcall-20-structured-restart` |
| `ops.capacity-forecast` | `foresee-14-disk-fill-predict`, `foresee-15-pvc-pressure`, `foresee-16-smart-prefail`, `new-linux-oom-or-node-pressure` |
| `ops.least-privilege-default-deny` | `secure-10-ingress-no-auth`, `secure-11-privileged-container`, `secure-12-broad-rbac`, `secure-13-latest-tag` |

The link is a **reverse map**: each node lists `scenarios: [...]`; `data/scenarios.json` is **not touched**. The validator checks every listed id exists.

---

## 4. Design decisions (and why)

1. **`data/concepts/`, not `knowledge/`.** The top-level `knowledge/` is Architrave's framework packs (`architrave.config.json` `kind: knowledge`). Domain data must not be merged into it. Named `data/concepts/` to be unambiguous. (First draft used `data/knowledge/`; renamed after review feedback.)
2. **JSON + stdlib only.** The repo is JSON-native and has no pytest (`requirements.txt`: "# pytest # if you add tests"). The validator uses only `json`/`pathlib`, so it runs anywhere with no new dependency.
3. **Reverse scenario link (no `scenarios.json` edit).** `main` is diverged (ahead 44 / behind 16) with untracked in-flight work; editing the 33-record data file risked conflicts. The node→scenario map achieves the same graph additively. If you'd prefer a **forward** `concepts: []` on each scenario (or inside the existing `lifecycle` block), that's an easy follow-up — flagged as an open question.
4. **Owned-source provenance + `verified` flag.** Every node cites a real in-repo artifact (`data/memory/homelab-okf-v1/context.md`, `docs/TAXONOMY.md`, `docs/PROTOCOL.md`) and is `verified: true` only after a human check. The validator fails if a cited source path doesn't exist.
5. **Isolated branch, not pushed.** Because `main` is diverged, the work is on `its-knowledge-capture` and was **not pushed**. Your `main` and working tree are untouched.

---

## 5. What to check (review checklist)

- [ ] **Ops accuracy:** do the 5 nodes' `one_line` / `worked_examples` / `constraints` / `misconceptions` match the corresponding `gold_answer`s and the OKF? (I authored them from the OKF + standard ops knowledge; please verify against your gold answers — especially the destructive-action / injection framing in `ops.destructive-action-guard`.)
- [ ] **Scenario mapping:** are the node→scenario links right? Any scenario that should map to a node but doesn't (or vice-versa)?
- [ ] **Naming/placement:** is `data/concepts/` the home you want? Node id scheme `ops.<slug>` OK?
- [ ] **Integration direction:** reverse map (current) vs a forward `concepts: []` on scenarios/lifecycle — which do you want to standardise on?
- [ ] **Provenance policy:** is citing the OKF/taxonomy as the "owned source" acceptable, or should nodes cite the underlying SRE/DORA refs too (with the OKF as the access artifact)?

---

## 6. Explicitly NOT done (scope + follow-ups)

- **No `run.py` / grounding-pipeline wiring.** Retrieving per-scenario nodes into the grounded condition is the logical next step but is not implemented here.
- **No forward `concepts[]` on `scenarios.json`** (chose the reverse map — see §4.3).
- **Only 5 concept clusters** (the highest-recurrence ones). Classes like `monitor`, `expand`, `upgrade`, `augment`, `test` are not yet captured.
- **No embeddings / semantic retrieval** (the uoeo-msc side ships lexical grounding; embeddings are a documented future seam).

---

## 7. How to land or discard

```bash
# review
git -C ~/Repo/apprenticeops checkout its-knowledge-capture
python3 data/concepts/validate.py

# land (after reconciling main): merge or cherry-pick, then push on your terms
git checkout main && git merge its-knowledge-capture

# or discard entirely
git branch -D its-knowledge-capture
```

Nothing here has been pushed. Everything is additive and reversible.

---

## 8. Context (origin of the approach)

This is Phase 4 of an ITS/knowledge-capture build done in `uoeo-msc` (a separate private repo). The full rationale — domain-model-as-knowledge-graph, provenance/verified gates, the 200:1 authoring-cost argument, spaced retrieval, grounding firewall — is in that repo's `docs/its-research-and-knowledge-capture.md`. This handover is self-contained; that doc is background only.
