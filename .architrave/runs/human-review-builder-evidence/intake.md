# Intake

## Understanding

Build a tiny stdlib loopback one-answer form, not an application stack.
Knowledge profile; no UI/backend/IaC/ops lane. User-approved scope.

## Acceptance Criteria

1. Default ten-item operator pilot; complete frozen context/question/answer.
2. Native unselected yes/no/unsure responsive and usable; endorses_destructive
   only for guard/secure scenario classes. Notes optional.
3. Skip/return, back/next, pause/resume; durable save before movement; errors block.
4. Explicit local routes; Host/Origin/CSRF/body validation; no repository serving.
5. Packet/protocol/input/answer hashes; separate reviewer progress; CAS saves;
   corrupt/mismatched data and failed writes refuse silently resetting.
6. Review/export with identity and formula-safe CSV, no machine scoring.
7. Synthetic tests only; no actual pilot labels, canonical edits, inference or publication.

## Grounding Sources

architrave.config.json; human_eval.py; scripts/test-human-eval.py;
deep-dive/human_validation_packet.py; run.py:prompt_capture_fields/output_capture_fields;
locked bundle contract/scenarios.json and raw/results.jsonl.gz;
original checkout docs/sdd/152-analysis-closure.md (read-only);
knowledge/yagni.md; knowledge/learning-loop.md;
.github/instructions/paper-voice.instructions.md.

## Assumptions and questions

Operator has seen machine material: provenance remains non-independent pilot
regardless of self-reported exposure. Bundle already local, no network fetch.
No blocking questions. Parent owns browser acceptance, final reviews, integration,
and durable server launch.

## Operations UX refinement

Within the existing Phase 1 scope: preserve literal thought tags and original
answer self-identification; verified empty answers remain rateable, missing full
evidence refuses. Add debounced note autosave through the existing revisioned
endpoint, retain drafts through errors and in-flight edits, show last confirmed
save timestamp and local progress folder. Back remains draft-preserving; partial
exports include explicit counts. Safety means endorsement, not word occurrence.
No parent-owned Edge/final-review or real-label interaction is authorized here.

## Persistent-storage correction

The user explicitly authorizes one narrow .gitignore addition:
`data/human-review-local/`. Real packets and human-authored progress now default
there, not disposable .tmp. Existing legacy default data is moved atomically on
the first default launch after integration, with packet/reviewer identities and
all bytes preserved. Active servers or corrupt progress block migration.
Normal launch never generates a missing packet; existing --prepare-only is the
explicit preparation action. Automated fixtures remain in .tmp or OS temporary
directories. Parent integration installs the ignore rule before real data moves.
