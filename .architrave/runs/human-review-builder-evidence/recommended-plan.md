# Recommended plan

One bounded candidate implementation phase after proposal gate; parent integration,
browser acceptance, and final semantic gate are separate.

## Implementation Sequence

Verify full-source contract; implement immutable packet preparation and revisioned
storage; implement fixed local endpoints and native one-item view; synthetic tests;
unlabeled real pilot preparation; hand candidate to parent for browser/final gates.

## Reuse boundary

Reuse the existing responsive/usable/endorses_destructive meanings and authoritative
guard/secure class scope. Reuse run.py UTF-8 SHA256 capture conventions. Do not call
old make helpers: human_eval.make exposes gold/rubrics and uses a five-point scale;
deep-dive packet is enriched, exposed, and clipped. No agreement scoring. New sidecar
is entirely separate under data/human-review-local, never old key.json or scores.csv.
The source bundle is artifact-locked but claim-provisional; do not require or change
paper-final claim status to run an explicitly non-independent qualitative pilot.

## Data / state contract

Default batch size is exactly n=10 (explicit user requirement). The frozen
reviewer-visible item payload is exactly: opaque id, full original system
instructions, full original user prompt (including all memory/context and question),
full raw answer, and safety_applicable boolean. No display truncation, answer
normalization, gold, rubric, machine scores, model identity, or source keys.
Progress/reviewer metadata is a separate response, not mixed into item text.
Packet: immutable schema/protocol/hash-bound full text, opaque UUID item IDs.
Private sidecar: exact source keys, hashes and deterministic sample recipe.
Browser: allowlisted item text, safety applicability, no gold, model metadata or keys.
State: protocol/packet/reviewer identity, revision, cursor, per-item status
(pending/skipped/reviewed), responses (yes/no/unsure/null), optional note.
Nonapplicable safety response is null plus explicit applicability=false, never no.
Reviewed requires all applicable responses; skipped may retain partial responses.
Exports: identities and hashes, applicability, status, each response, note;
formula-risk text cells prefixed with apostrophe. No machine scoring.

## Persistence and routes

Exclusive server process lock for the packet; per-session revisions prevent stale
tab overwrites; atomic replace + fsync; fail-closed on missing/corrupt/mismatched
existing sessions and packets. No silent repair/reset or automatic recovery.
CSRF uses secrets.token_urlsafe(32), memory-only server-bound, checked on every POST.
Exact Host and Origin checks; body/content type limits; no generic static root.
Export is an allowlist, never private sidecar paths or source item keys.

## Form and verification

Initial alias/exposure explanation then essentials; native fieldset/legend radios,
natural keyboard order; aria-live save/error status; focus item heading after
navigation, error on failure. No timed navigation.

## Test Strategy

Run scripts/test-review-human-eval.py explicitly in addition to gates/checks.sh and
unchanged scripts/test-human-eval.py. Parent decides standing config.test promotion;
worker does not edit config (outside delegated files). Tests cover complete text,
missing/corrupt bundle, key leakage, unknown item injection, no preselection,
unsure/applicability, immutable pilot provenance, disk failure/reload/CAS and exports.

Rollback: remove new code only; preserve user-owned packet/session directory.

Operations UX refinement: notes debounce through the same save endpoint; in-flight
edits stay local/dirty, manual navigation waits for the outstanding revision, and
failed autosaves stop navigation. Display server saved_at and the progress-folder
path (path excluded from exports). Exports add reviewed/skipped/pending/unsure-item
counts. Literal original text, including thought tags/self-ID, remains unchanged.
Parent owns the next independent implementation/browser gate.

Durability correction: default real storage is data/human-review-local with the
single user-authorized .gitignore entry. The exact earlier default pilot is
verified and process-locked before an atomic directory move; every stored
reviewer state must validate. Never overwrite an existing destination. Normal
launch refuses a missing packet rather than preparing one; --prepare-only remains
explicit. Fixtures are temporary-only. Test default paths, ignore scope, migration
byte equality/reviewer preservation, active-lock/corruption/move failures, and
repeat launches with preparation disabled. Guide includes private full-directory
backup as well as portable exports; no Git-backup or data-loss-immunity claim.
