# README Update Plan

Status: active P0 correction plan, created 2026-07-03.

## Canonical Project Definition

Use this wording for the current thesis track:

> ApprenticeOps evaluates open-weight small language models up to **5B
> parameters** under CPU-only commodity-laptop constraints, measuring quality,
> safety, latency, memory, and energy trade-offs for local operational reasoning.

Use `GB` only for artifact size, quantized footprint, disk usage, RAM behavior,
or resident memory. Do not use `<=5 GB` as the research boundary.

## Snapshot Language

The committed 94-model result remains useful but must be labeled correctly:

> The current committed result snapshot is a legacy footprint-bounded 94-model
> study that includes some models above 5B parameters. It is reproducible and
> remains the paper-era evidence, but it is not the final <=5B-parameter thesis
> roster.

## Current Model-Universe Status

`data/models.lock.jsonl` currently represents all 173 tags in `data/models.txt`.
The model-lock validator reports 155 included `thesis_5b_candidate` rows and 18
excluded `above_5b_parameters` rows. Therefore the 150+ model, <=5B thesis roster
count gate is complete; provenance metadata remains incomplete.

## README Rewrite Acceptance Criteria

1. The first screen says `<=5B parameters`, not `<=5 GB` or `<=8B`, as the current
   thesis boundary.
2. Legacy snapshot claims stay, but are explicitly scoped as the 94-model
   footprint-bounded snapshot.
3. Scenario counts are tabled: paper-era 19, current corpus 33, Core current 20,
   external v1 dev 9.
4. Grounded mode is described as oracle/context upper bound, not a measured RAG
   deployment.
5. Verification claims point to concrete scripts and committed snapshots, or are
   softened until `scripts/audit-paper-data.py` exists.