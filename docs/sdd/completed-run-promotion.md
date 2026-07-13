# SDD: Completed-Run Promotion Into Analysis v1

Status: live promotion completed; exploratory failure-recovery analysis staged
Date: 2026-07-12
Scope: post-run normalization, completion validation, evidence locking, and analysis eligibility

## 1. User-Visible Outcome

After this change, an operator can run one command against a completed experiment directory and receive either:

- an immutable, SHA-256-bound `source_kind=completed_run` evidence bundle that is eligible for analysis schema v1; or
- a fail-closed report naming every missing, ambiguous, incomplete, or unpersisted unit.

The command refused the run while it was partial, then promoted the exact completed evidence after collection, judging, and persistence reached their declared domains.

Live outcome:

- bundle ID: `dd262a5c94593cb4b35bbb3554cc7ed1d608fab8b16160a3215329637c614baa`;
- 15,200 canonical results and 30,400 canonical judgements;
- 41 failed judge parse attempts preserved separately as retries;
- 152 completed and committed models, 152 result archives, 152 candidate archives, and zero pending pushes;
- bundle verification and repository privacy scan pass;
- `claim_status=provisional`; the frozen 94-model claim source remains unchanged.

## 2. Scope Honesty

This change does not:

- alter `run.py`, prompts, scenarios, samplers, judges, model outputs, or the active run;
- rejudge or reinterpret an answer;
- create analysis schema v2 or a parallel metric implementation;
- promote any partial-run value into public prose;
- replace the locked 94-model paper manifest;
- emit Croissant, RO-Crate, or a BagIt package in the first implementation.

The evidence lock is not a claim lock. A completed-run bundle starts with `claim_status=provisional`. Public claims still require a separate, reviewed analysis lock.

## 3. Tournament Of Options

Three independent, read-only candidates were generated and ranked by a fourth independent judge.

| Candidate | Shape | Outcome fit | Simplicity | Crash safety | Live evidence compatibility | Verdict |
|---|---|---:|---:|---:|---:|---|
| A | Atomic command plus BagIt, RO-Crate, Croissant, and new capture fields | 1/5 | 1/5 | 3/5 | 0/5 | Rejected |
| B | Staged normalize -> validate -> lock, with one-command `promote` wrapper | 5/5 | 3/5 | 5/5 | 5/5 | **Winner** |
| C | Thin in-place completed-run package and immediate global-manifest switch | 3/5 | 5/5 | 4/5 | 4/5 | Rejected |

Independent tournament result: `WINNER: B`.

### Why B won

B can lock the already-running experiment after completion without changing its producer. It derives condition identity from existing result rows plus an explicit requested judge policy, preserves raw append order as attempt identity, separates normalization from validation, and does not mutate the global paper claim manifest.

### Salvaged ideas

- From A: expose one ergonomic `promote` command and use named ledger stages.
- From C: keep the first implementation to a thin SHA-256 manifest; reserve BagIt for archival transfer and require explicit absence checks for pause, cancellation, and pending pushes.

### Rejected details

- A requires `model_attempt_index`, `inference_tuple_sha256`, and output hashes that the live run did not capture. Retrofitting them would change the experiment and make its current evidence permanently ineligible.
- C would replace `data/analysis-manifest.json` during evidence promotion. Evidence completion must not silently replace the current public claim source.

## 4. Standards And Build-Vs-Adopt Decision

### Thin manifest now

Build a small repository-native promoter because the differentiating capability is semantic validation of ApprenticeOps rows, retries, conditions, and persistence. Existing general-purpose packaging tools do not provide these gates.

### BagIt later, as export only

RFC 8493 defines a reliable storage/transfer envelope with a `data/` payload, payload manifests, optional tag manifests, and checksum validation. It treats payload bytes as opaque and does not define experiment-row semantics. A future archival export may wrap a locked bundle as a valid BagIt 1.0 bag; BagIt is not the in-repo promotion state machine.

### RO-Crate and Croissant later

RO-Crate is useful for rich research-object metadata. Croissant 1.0 is useful for published dataset discovery, loading, record sets, and file checksums. Neither governs append-only judge retries or completed-run lifecycle transitions. Add them only at archival/publication time, after the locked row contract is stable.

## 5. Inputs

The promoter reads one run directory without modifying it:

```text
data/runs/<RUN_ID>/
  run.meta
  _mirror/results.<RUN_ID>.jsonl
  _mirror/results.<RUN_ID>.jsonl.done
  judged.<RUN_ID>.jsonl
  pipeline-ledger.jsonl
  *.results.jsonl.gz        # optional per-model compressed result archives
  *.candidates.tar.gz       # optional per-model candidate traces
  *.log                     # optional operational logs
  .committed
  .push-pending
  .paused                    # optional blocker
  .canceled                  # optional blocker
```

It also reads the roster and scenario files named by `run.meta`, resolved beneath a caller-supplied repository root.

### Artifact-scope tournament

| Option | Evidence coverage | Storage/complexity | Verdict |
|---|---:|---:|---|
| Copy every run file, including uncompressed per-model duplicates and transient locks | High but noisy | Captures hundreds of MB of duplicate and mutable transport state | Rejected |
| Copy only aggregate results, judgements, and fixed metadata | Misses operational logs and sidecar provenance | Smallest | Rejected |
| Hash and copy aggregate evidence plus compressed per-model results, candidate archives, and logs | Complete durable evidence without byte-duplicate uncompressed files | Hundreds of MB, bounded to durable evidence | **Selected** |

The selected scope excludes uncompressed `*.results.jsonl` because each is the
byte-equivalent source of its included `*.results.jsonl.gz` counterpart. It also
excludes transient lock files. Sidecar filenames and bytes are fixed at intake;
membership drift fails promotion. When per-model archive classes are present,
their filenames must exactly match the producer's sanitized roster-derived set;
sanitization collisions fail closed.

The current live run predates `analysis_condition_key_sha256` and `evaluation_policy` in result/judge rows. Promotion therefore requires the requested judge identities explicitly when row-level policy metadata is absent, for example:

```bash
--judge copilot:claude-opus-4.6 \
--judge copilot:gpt-5.4
```

The promoter derives the canonical v1 condition hash from each inference row and this requested policy. It never infers the requested ensemble from whichever judge calls survived.

## 6. Outputs

Default output root: `data/completed-runs/`.

```text
data/completed-runs/
  .staging/                         # ignored, crash-recoverable
  .state/<RUN_ID>/promotion-ledger.jsonl
  <RUN_ID>-<BUNDLE_ID>/
    bundle-manifest.json
    gate-report.json
    normalization-metadata.json
    promotion-ledger.jsonl
    contract/
      roster.txt
      scenarios.json
    raw/
      run.meta
      results.jsonl.gz
      results.done
      judged.attempts.jsonl.gz
      pipeline-ledger.jsonl
      committed-models.txt
      push-pending.txt
      model-results/*.results.jsonl.gz
      candidates/*.candidates.tar.gz
      logs/*.log
    canonical/
      results.jsonl.gz
      judged.jsonl.gz
      judge-retries.jsonl.gz
```

`BUNDLE_ID` is the SHA-256 of the canonical source-hash map. A byte-identical rerun resolves to the same bundle ID.

The manifest uses the existing analysis contract:

```json
{
  "analysis_schema_version": 1,
  "source_kind": "completed_run",
  "source_id": "<RUN_ID>",
  "claim_status": "provisional",
  "source_sha256": {}
}
```

Additional fields may record bundle state, expected/observed counts, judge identities, condition-key-set hash, roster/scenario hashes, and tool version. They do not create a new analysis schema.

## 7. Normalization Contract

### 7.1 Inference rows

1. Parse every non-empty JSONL line; any parse error fails promotion.
2. Require one unique `(model, scenario, rep)` tuple.
3. Require exact roster, scenario, and repetition domains from `run.meta`.
4. Derive `analysis_condition_key_sha256` with `analysis_metrics.analysis_condition()` and the explicit evaluation policy.
5. When a row records only temperature/think and delegates the remaining sampler
  settings to a pinned runtime version, add an explicit normalized
  `analysis.sampler_policy={kind: runtime_defaults, ...}` marker to the
  canonical copy. The raw row remains unchanged.
6. When `ollama.digest` is absent but `ollama.ps.before` identifies exactly one
  matching loaded model with a 64-character digest, add an explicit
  `analysis.artifact_identity=ollama-ps-sha256:<digest>` marker to the canonical
  copy. Ambiguous or missing snapshots still fail closed.
7. Reject any remaining incomplete condition identity.
8. Add only canonical provenance fields; preserve all original fields.
9. Preserve the hash-bound raw append order. Identical source bytes therefore
  produce identical canonical bytes without retaining the large result payload
  in memory.

DNF, timeout, length, blank, and deterministic no-answer outcomes are valid completed evidence. Missing tuples are not.

### 7.2 Judge attempts

Raw `judged.<RUN_ID>.jsonl` remains immutable; its bytes are preserved inside deterministic gzip framing in the bundle.

Each attempt is joined to exactly one result through the unique legacy tuple `(model, scenario, rep, memory_context, inference_strategy, runtime_adapter)`, then enriched with the derived condition hash and explicit evaluation policy.
Judge input is streamed; only the at-most-one successful candidate per expected
canonical key is retained in memory, bounded by the expected judgement count.

Canonical key:

```text
(condition_sha, scenario, rep, judge_backend, judge_model)
```

For every canonical key:

- exactly one structurally complete row with numeric `score` must exist;
- zero successful rows fails promotion;
- more than one successful row fails promotion, even when scores match;
- non-success attempts are preserved in `judge-retries.jsonl.gz` with source line and reason;
- the canonical row and retry rows together account for every raw attempt exactly once.

This rule resolves the current parse-failure-then-success pattern without hiding retries or choosing between competing successful verdicts.

## 8. Fail-Closed Gates

Expected counts are derived from the locked metadata, not hard-coded:

```text
expected_results = models_count * scenario_count * reps
expected_judgements = expected_results * expected_judge_count
```

For the active run these resolve to 15,200 and 30,400.

| Gate | Requirement |
|---|---|
| P0 Path safety | All input and output paths remain beneath approved roots; no symlink traversal. |
| P1 Terminal state | `.paused` and `.canceled` absent; `.push-pending` empty. |
| P2 Metadata | `run.meta` parses; roster/scenario paths and SHA-256 values match; counts equal file contents. |
| P3 Results | Exact result count, no duplicate tuple, exact model/scenario/rep domains, complete v1 condition identity. |
| P4 Judgements | Exact complete backend/model set for every result; no missing or multiple successful verdicts. |
| P5 Persistence | `results.done` and `.committed` contain each roster model exactly once; any present per-model result/candidate archive class exactly matches the roster-derived filename set. |
| P6 Provenance | One runtime/hardware/prompt/memory/strategy/sampler/scenario policy per declared deployment; all source hashes stable across the promotion read. |
| P7 Reconciliation | Canonical judgements plus retry sidecar account for every raw attempt. |
| P8 Privacy handoff | Bundle remains provisional until the repository privacy gate passes over it. |

No `--force`, `--allow-partial`, or `--allow-unlocked` escape hatch is permitted.

## 9. CLI And State Machine

```bash
python3 scripts/lock-completed-run.py normalize --run-dir ... --repo-root ... --persist-mode git-push --judge ...
python3 scripts/lock-completed-run.py validate  --run-dir ... --repo-root ... --persist-mode git-push --judge ...
python3 scripts/lock-completed-run.py lock      --run-dir ... --repo-root ... --persist-mode git-push --judge ...
python3 scripts/lock-completed-run.py promote   --run-dir ... --repo-root ... --persist-mode git-push --judge ...
python3 scripts/lock-completed-run.py verify    --bundle ...
python3 scripts/lock-completed-run.py status    --run-id ... --output-root ...
```

`promote` runs normalize -> validate -> lock and stops at the first failed gate.
The explicit persistence mode must match `run.meta`; `local-files` additionally
requires exact receipt/result/candidate inventories and receipt revalidation.

Ledger stages:

```text
promotion_started
normalize_started
normalize_passed | normalize_failed
validate_started
validate_passed | validate_failed
lock_started
lock_passed | lock_failed
promotion_eligible
```

Every ledger record includes UTC timestamp, run ID, stage, success flag, input digest, output digest when available, and a concise detail object.

The mutable operational ledger is copied into the bundle for review but is not
part of `source_sha256` or `BUNDLE_ID`; `verify` deliberately permits the ledger
and the necessarily self-describing manifest outside that hash map. Rerunning
an identical promotion appends new operational events without changing evidence
identity.

## 10. Atomicity, Idempotency, And Rollback

- A normalized staging directory is disposable and is never treated as a trust
  anchor. Public `validate` and direct `lock` rebuild it deterministically from
  the still-hash-bound source evidence under the promotion lock. `lock` carries
  one in-process payload hash map through manifest creation, rechecks it before
  rename, and verifies the final bundle; failed finalization removes the target.
- Build under `.staging/<RUN_ID>.<pid>/` on the same filesystem.
- Write temporary files, flush and `fsync`, then `os.replace` each completed file.
- Write `bundle-manifest.json` last.
- Re-read and hash all source files immediately before finalizing; any change fails the attempt.
- Atomically rename the completed staging directory to `<RUN_ID>-<BUNDLE_ID>`.
- If the target exists and verifies byte-identically, return success without rewriting it.
- If the target exists but differs, fail; never overwrite evidence.
- A crash before rename leaves no visible bundle. Under the exclusive same-run
  lock, the next run removes abandoned staging directories for that run and
  recomputes.
- Rollback removes or disregards the additive bundle. Raw `data/runs/` evidence is untouched.

Filesystem mode bits are not treated as immutability. Content addressing, no-overwrite behavior, source hashes, and Git history provide the enforceable boundary.

## 11. Analysis Eligibility

The first implementation proves bundle eligibility and does not generate claims.

`verify` establishes integrity and analysis eligibility; it does not certify
privacy. Existing analysis adapters may consume canonical bundle files only
after `verify` and `scripts/privacy-scan.py` both succeed. A later reviewed phase
will generate completed-run v1 exports in a separate output tree. It must not
replace `data/analysis-manifest.json` or current public paper artifacts
automatically.

## 12. Implementation Phases And Ledger

| Phase | Status | Scope | Gate | Rollback |
|---|---|---|---|---|
| 0. Tournament and decision | completed | Three candidates plus independent ranking | `WINNER: B` | Keep candidate records; no code changed |
| 1. Design contract | completed | This SDD, standards, gates, runtime ledger shape | Design adversarial review PASS | Delete this additive SDD |
| 2. Fixture-first core | completed | Normalization, validation, locking, verification, status CLI; synthetic fixtures | Focused tests PASS, including a full-shape 152×20×5×2 promotion; live partial run refused at P5 with exit 4, no source mutation, no bundle; all captured rows at the validation-v4 checkpoint (12,623) normalized to complete single-condition v1 identities | Revert new script/tests |
| 3. Repository integration | completed | Docs, artifact inventory, `.gitignore`, privacy and complete script suite | All script tests, `audit-paper-data.py`, claims, links, privacy, CLI, compile, and diff checks PASS | Revert integration edits |
| 4. Independent implementation review | completed | Repeated implementation and adversarial passes repaired exact-gap, full-ID, ledger, full-shape, sidecar, TOCTOU, symlink-tree, and archive-privacy findings. | Final v5 GPT implementation judge PASS (all dimensions >=4/5); Claude adversarial review PASS (no blocker/major); 26 focused tests and all repository gates PASS | Repair or revert |
| 5. Live completed-run promotion | completed | Promoted exact 15,200 results / 30,400 canonical judgements / 152 persisted models; retained 41 judge retries | Bundle `dd262a5c…` verifies; privacy PASS | Discard additive bundle only |
| 6. Completed-run analysis | completed: diagnosis only | Generated privacy-safe failure report and timeout-sensitivity contract; no public claims replaced | Bundle verify, privacy, deterministic report/analyzer tests PASS | Keep prior public paper lock |

This promotion ledger is closed. Timeout-sensitivity hardening, launch readiness,
execution, comparative analysis, and the policy decision are governed by
`docs/sdd/timeout-recovery-sensitivity.md` and its Architrave P0-P7 ledger.

## 13. Acceptance Checks

The implementation is complete only when executable tests prove:

1. A full-shape fixture (152 models × 20 scenarios × 5 repetitions × 2 judges) promotes and verifies.
2. The same fixture promotes idempotently to the same bundle ID.
3. A partial fixture is refused and creates no visible bundle.
4. Wrong roster/scenario hashes are refused.
5. Missing, extra, or duplicate result tuples are refused.
6. A parse-failure attempt followed by one success yields one canonical judgement plus one retry row.
7. Multiple successful rows for one judge key are refused.
8. A missing requested judge family is refused.
9. Canonical plus retry rows account for every raw attempt.
10. Incomplete analysis condition identity is refused.
11. Pending persistence, pause, and cancellation markers are refused.
12. Source mutation between normalize and lock is refused.
13. `verify` detects any changed byte in a locked bundle.
14. The actual live partial run, checked read-only, is refused without changing any file beneath its run directory.
15. The existing analysis and publication test suites remain green.

## 14. Security And Privacy

- Resolve paths and reject symlinks or traversal outside approved roots.
- Never execute content from the run directory.
- Never fetch URLs.
- Never place secrets in argv or the ledger.
- Use deterministic gzip metadata so hashes reproduce.
- Preserve raw model and judge text; do not print it in error messages.
- The final promotion gate reports tuple identifiers and field names, not completions or judge evidence.
- `scripts/privacy-scan.py` remains the release gate for any produced bundle.
