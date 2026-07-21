# Recommended Plan

## Summary

Create a reusable literature-radar skill and deterministic evidence ledger, then
populate its first dated scan from recent primary/company sources and separately
logged practitioner signals.

## Implementation Sequence

1. Reconcile existing catalog and define immutable work/version/claim/scan IDs.
2. Run the fixed topic/company/source-family scan and retain negative searches.
3. Write schemas, validator/tests, protocol README, skill, and dated synthesis.
4. Run configured deterministic checks and independent semantic review.

## Test Strategy

- Schema/type/enum/unique-ID and lineage attack tests.
- Coverage and zero-result enforcement.
- Report heading/source-reference and social-corroboration gates.
- Canon-clean, privacy, documentation-link, compile, and diff checks.

## Rollback / Recovery

All artifacts are additive. Remove the radar directory, skill, validator/tests,
and config entries; canonical catalog/paper files remain unchanged.

## Human Approval Needed

Any promotion into `references.bib`, `literature-catalog.md`, or paper prose is a
separate human-approved task. No promotion is in this run.

## Paper-Impact Extension

After preserving the radar, compare its immutable source versions with the
current manuscript and reviewer guidance. Produce a promotion packet, not canon
edits, that separates:

1. prose/citation changes worth adding now;
2. analyses blocked on the active timeout run;
3. experiments that belong in a separate paper;
4. monitor and reject evidence.

The packet must keep causal and observational claims distinct, name exact source
version IDs in every decision-bearing disposition, and pass independent GPT- and
Claude-family review.
