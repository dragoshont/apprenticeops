# Deterministic Gates

## checks

- `gates/checks.sh --quick`: PASS after knowledge-profile bootstrap.
- Architrave v0.10.3 JSON schema validation: PASS.
- `harness/validate-run.sh .architrave/runs/timeout-recovery-20260712`: PASS after substantive artifact population; one active phase.
- `gates/checks.sh`: PASS. Shell syntax, Python compilation, analyzer/run/report/privacy/promoter tests, document links, and `git diff --check` all passed.

## backend-checks

Not applicable (`kind: knowledge`; no backend/IaC lane).

## reconcile

Not applicable (`kind: knowledge`; no UI/token lane).

## other

- Parent bundle verify: PASS, bundle `dd262a5c...`, `claim_status=provisional`.
- Parent strict report: PASS, 15,200 results, 30,400 canonical from 30,441 attempts, 41 retries.
- Parent privacy scan: PASS, zero secret hits.
- Proposal semantic gate: initial Claude 4.8 PASS; initial GPT-5.6 Sol REVISE; repaired P0 re-judgement pending after deterministic PASS.

### Phase 3 implementation matrix

- `test-analyze-completed-run-failures.py`: PASS.
- `test-run-env-static.py`: PASS.
- `test-report-run-quality.py`: PASS.
- `test-privacy-scan.py`: PASS.
- `test-lock-completed-run.py`: PASS, 26 tests.
- Real parent strict report: PASS, zero missing/extra/competing canonical judge keys.
- Real bundle verification: PASS.
- Full privacy scan: PASS, 21,130 files/archive members, zero secret hits.
- Shell syntax and Python compilation: PASS.
- Documentation links: PASS, 119 files / 174 links.
- `git diff --check`: PASS.
- VS Code diagnostics: zero errors in touched Python files.
- Anti-scaffold diff scan: zero findings.

### Phase 3 revise loop 1

- GPT-5.6 Sol found same-cardinality explicit judge substitution could override modern `run.meta.judge_identities`; verdict REVISE.
- Reporter now treats metadata identities as authoritative and emits `judge-domain-conflict` when explicit identities differ.
- Promoter metadata validation now rejects requested identities that differ from authoritative metadata.
- Added matching and same-count substitution negatives for reporter and promoter.
- `test-report-run-quality.py`: PASS after repair.
- `test-lock-completed-run.py`: PASS, 27 tests after repair.
- Full `gates/checks.sh`, Architrave run validation, real strict parent report, bundle verify, privacy, and diagnostics: PASS after repair.

### Phase 3 revise loop 2

- Added strict shared modern judge metadata parser; only field absence is legacy.
- Added malformed/null/empty/duplicate/cardinality attacks for reporter/promoter and future producer-shape assertions.
- Bound real authoritative-domain engagement and substitution rejection into P4/P5.
- `gates/checks.sh`: PASS; promoter tests: 28.
- Architrave validation, real explicit-legacy parent report, bundle verify, privacy 21,130/0, diagnostics, and lesson-count audit: PASS after bookkeeping repair.

### Phase 3 semantic loop 3 — stopped

- Claude Opus 4.8: PASS.
- GPT-5.6 Sol: REVISE on lenient/unstructured `judges` count coercion.
- Deterministic gates before review were green, but the semantic gate is not PASS.
- Per the three-loop stopping condition, Phase 3 is blocked and no further repair was attempted without human approval.

### Human-approved bounded loop 4

- Shared strict positive-integer `metadata_judge_count` implemented; no `int(...)` trust-boundary coercion.
- Reporter/promoter tests cover valid positive integer and invalid fractional, numeric string, arbitrary string, object, list, boolean, zero, negative, null, and missing values.
- Focused reporter/promoter suites: PASS; promoter tests: 29.
- Full `gates/checks.sh`: PASS.
- Architrave run validation, diagnostics, `git diff --check`, phase-state audit, and anti-scaffold scan: PASS.
- Post-repair real parent strict report: PASS, 15,200 results / 30,400 canonical from 30,441 attempts / 41 retries / zero strict failures.
- Post-repair bundle verification: PASS.
- Post-repair privacy scan: PASS, 21,130 files/archive members / zero secret hits.
- GPT-5.6 Sol final human-approved review: PASS.
- Claude Opus 4.8 final human-approved review: code PASS, formal REVISE only on stale pending bookkeeping; confirmation pending after synchronization.

### Phase 4 launch readiness

- `local-commit` sync now materializes the exact detached commit in a temporary clean clone and mirrors the complete committed tree; tracked evidence is not excluded.
- `run.py` telemetry sampler no longer shadows `threading.Thread._stop`; focused start/stop/join regression PASS and real-node calibration completed without the prior `TypeError`.
- Final clean branchless snapshot: `e35ef3f25a1c089eb2de482a1057ba5784547948`; exact commit observed on both `home.hont.ro` and `home-ai.hont.ro`.
- Production preflight `timeout-sensitivity-preflight6-20260712`: PASS on `home-ai`, Ollama 0.30.8, locked CPU/RAPL environment, exact recovery roster/scenario/manifest/artifact hashes.
- Zero-execution proof: `result_rows=0`, `output_files=0`, no `run.py` or judge-scheduler process, consumer not launched, and node power state restored.
- Modern evaluator metadata: exactly `copilot:claude-opus-4.8` and `copilot:gpt-5.6-sol`, `judges=2`; matching explicit domain accepted and same-cardinality `gpt-5.4` substitution emitted `judge-domain-conflict`.
- Read-only Ollama artifact observation: 21 locked affected models, none currently installed; therefore no installed affected-model mismatch. Post-pull digest enforcement remains the Phase 5 per-model gate.
- Recovery analysis manifest source hashes match current analyzer, shared metrics, and promoter; tracked output hashes match the installed launch contracts.
- Final `gates/checks.sh`: PASS, including build, analyzer tests, source/provenance tests, reporter tests, privacy tests, 29 promoter tests, 119-file/174-link documentation audit, and `git diff --check`.
- Claude Opus 4.8 Phase 4 semantic verdict: PASS, no blocker.
- GPT-5.6 Sol Phase 4 semantic verdict: PASS after bookkeeping confirmation; no implementation/provenance blocker.

### Phase 5 no-push launch candidate

- Initial `local-files` implementation: dual-family REVISE before inference. Findings included restart fallback to Git push, producer-before-consumer ordering, incomplete receipt durability, optional receipt promotion, incomplete candidate/retry domains, and insufficient command-level tests.
- Repaired `run.meta.persist_mode` authority: direct scheduler restart adopts metadata and rejects any explicit conflict before a Git-capable branch.
- Consumer safety: mandatory `flock`, committed-receipt revalidation, atomic readiness receipt, and producer launch only after readiness contract verification.
- Local evidence: deterministic/fsynced result gzip, candidate tar, and structured receipt; exact scenario x repetition domain; exact result x judge domain; exactly one successful judgement per key; only classified parse retries; foreign candidate rows rejected; source result and judge attempts hash-bound.
- Promotion: `local-files` requires exact receipt/result/candidate inventories for every roster model, re-opens and hash/domain-verifies every receipt, and includes receipts in source hashes and immutable bundle payload.
- Command-level gates: no-Git restart PASS; mode conflict PASS; lock contention PASS; tampered committed receipt blocks readiness; failed consumer never launches producer; unknown status is read-only; parse-failed judge attempts remain retryable.
- Focused persistence/promoter suites PASS; promoter suite now 31 tests.
- Regenerated parent failure analysis: four launch contracts byte-identical; only source-bound promoter hash changed and was refreshed in the tracked analysis manifest.
- Final `gates/checks.sh`: PASS, including all new command-level tests; `harness/validate-run.sh`: PASS; diagnostics: zero errors.
- Final dual-family semantic re-review: pending. No Phase 5 inference has launched.

### Phase 5 semantic re-review loop 2

- Claude Opus 4.8: PASS with minor fail-closed concerns; authorized a fresh snapshot contingent on companion PASS and fresh gates.
- GPT-5.6 Sol: REVISE. Launch denied on permissive modern metadata defaults/coercion, coordinated receipt/archive contradiction, repetition coercion, readiness liveness race, committed-domain validation, judge torn-tail durability, and unsafe run-path handling.
- Strict modern metadata now requires schema v2, explicit `persist_mode`, positive non-boolean integer counts, hash-matched safe non-symlinked roster/scenario files, exact model/expect/scenario domains, and explicit repetition agreement before Git.
- `RUN_ID` and run-path components are constrained and checked before directory/lock/log creation; symlinked run evidence paths fail closed.
- `.committed` must be unique and a roster subset before receipt validation/readiness.
- Receipt verification independently recomputes strict integer tuple domains, canonical result payload, external scenario/judge contracts, success/retry counts, current result/judged bytes, and current candidate sidecars; candidates are semantically cross-bound to each result row's `strategy.candidates`.
- Coordinated result/archive/receipt, candidate/archive/receipt, receipt-count, source-result, source-judge, foreign-row, and fractional-repetition attacks are covered.
- Judge attempt JSONL uses fsynced append, truncates only a torn final fragment, rejects malformed interior rows, and resumes only structurally successful judgements; invalid non-null scores remain retryable.
- Launcher rechecks consumer liveness after parsing the PID-bound readiness receipt. A fake consumer that writes readiness then exits cannot launch the producer.
- Full focused suites and `gates/checks.sh` PASS after repair; Architrave run validation PASS. No inference launched.
- Parent failure-analysis regeneration: all treatment outputs remain byte-identical; source-bound promoter hash refreshed to `8a5b91f...`.

### Phase 5 semantic loop 3 — stopped

- Final deterministic state before review: `gates/checks.sh` PASS; `harness/validate-run.sh` PASS; promoter tests 31; documentation 119 files / 174 links; diagnostics zero.
- Claude Opus 4.8: PASS.
- GPT-5.6 Sol: REVISE on persistence-mode downgrade after missing metadata, coercive promoter counts, and nested-path / late terminal-marker mediation.
- Semantic loop cap reached. Phase 5 is blocked; no production snapshot, preflight, or inference launch followed this verdict.

### Human-approved bounded Phase 5 loop 4

- Human approval received to repair only the three recorded GPT blockers: metadata-loss persistence downgrade, strict promoter counts, and nested-path/late-terminal-marker mediation.
- Added fsynced `.run-authority` before `run.meta`; existing/nonempty runs without metadata fail before consumer or producer launch, including before the first receipt. Local launches and restarts require the exact authority marker.
- Promotion now requires explicit `--persist-mode` matching `run.meta`; operator docs and CLI tests are synchronized.
- Replaced promoter metadata/repetition/done-unit coercion with strict non-boolean integer validation. Added malformed float/string/bool/null/missing/count/override/tuple/unit attacks.
- Scheduler validates exact ordered unique scenario IDs, authority, committed roster domain, and every nested run-tree entry before lock/log/status creation and around each rsync.
- Promotion output/state/staging directories, lock, and ledger use no-follow mediation; symlink attacks cover state, staging, lock, ledger, mirror, outputs, lock/log/status evidence.
- `.paused`/`.canceled` are checked at intake, source-hash checks, validation, immediately before idempotent acceptance, and immediately before final rename. Late-marker tests refuse final lock.
- Focused suites PASS: scheduler/readiness, strict persistence, judge resume, and promoter 39 tests.
- Full configured gate and run validation PASS before final path hardening; final full rerun pending after provenance update.
- Final post-provenance `gates/checks.sh`: PASS; promoter suite 39 tests; documentation audit 119 files / 174 links.
- Final `harness/validate-run.sh`: PASS; exactly one active phase.
- VS Code diagnostics: zero errors across launcher, scheduler, promoter, and focused tests.
- `git diff --check`: PASS. Anti-scaffold scan found no scaffold marker; its only match was the intentional privacy constant `EXACT_SECRET_PLACEHOLDERS`.
- Parent failure-analysis regeneration: all four treatment outputs byte-identical; source-bound promoter hash refreshed to `8b9c6e6f...`.
- Final human-approved dual-family review pending. No inference, push, parent mutation, or claim change.

### Human-approved loop 4 semantic result — stopped

- Claude Opus 4.8: PASS.
- GPT-5.6 Sol: REVISE on independent authority control, direct `validate`/`lock` mode enforcement, and pre-write staging mediation.
- The one explicitly approved extra loop is exhausted. Phase 5 is blocked; no fresh production snapshot, preflight, or inference followed this verdict.

### Phase 5A simplification and launch

- Parent evidence preservation: second bundle copy on `home` independently verified; original operational run and remote experiment branch retained.
- Treatment source checkpoint: `e35ef3f...` focused launch/report/promoter tests PASS; source branch published separately from results.
- Full 21-model zero-row production preflight: PASS; zero inference rows/files and consumer disabled.
- Non-cohort smoke attempt 1: expected fail-closed on repeat mismatch, zero rows, power restored.
- Corrected smoke: 6/6 inference rows, reset-state 6/6, 12/12 canonical parent-judge rows, zero retries, strict report PASS, result branch synchronized with zero pending pushes.
- Smoke promotion: bundle `f683a54e...` locked/provisional and verification PASS; privacy scan PASS (`files_scanned=378`, `secret_hits=0`).
- Treatment launch: source/contract gates PASS; AI exact source `e35ef3f...`; Ollama 0.30.8; first model pull and digest verification PASS; producer and consumer alive; 2 rows observed.
- Live judge repair: focused `test-analysis-metrics.py` PASS (27 tests), `test-judge-row-schema.py` PASS, Python compilation and diff check PASS, actual Granite row normalized to complete condition `b0411b10...` with `runtime_defaults` sampler policy.
- Resume evidence: Qwen judge domain remained exactly 200; Granite advanced to 113; result branch synchronized at repair commit `bbcc8d9`; producer never stopped.
- Duplicate-judge recovery: actual incident journal audit found 1,790 attempts / 832 unique / 958 extras / 389 duplicate keys. Unified normalized identity regression PASS; actual copied Granite key is now recognized as done by both judges. Canonical baseline 200/200 unique; incident archive and baseline hashes verified; recovery commit `00891db` pushed.
- First post-recovery live check: 209 journal rows / 209 unique / zero duplicate extras; Qwen exactly 200; producer remained active.
- Mission Control status fix: focused timeout regression PASS; backend compilation/diff check PASS; container image `0.6.1` healthy; public and direct `/api/status` HTTP 200 with active run; no new `TimeoutExpired`/500 log entry.

### Paper reliability disclosure

- Final `gates/checks.sh`: PASS after all three paper-owner edits; configured
	build and all tests PASS, including 39 promoter tests.
- Documentation audit: PASS, 119 files / 179 local links. Paper claim audit:
	PASS, 10 surfaces. Scoped `git diff --check`: PASS.
- Submission manuscript renders: isolated Quarto HTML PASS and isolated Typst
	PDF PASS; both outputs non-empty and outside the working tree.
- Exact disposable analysis environment: Python 3.14.5, 79 active packages,
	complete hashes, self-consistent lock, and license audit PASS.
- `audit-paper-data.py` completed its environment, license, schema, snapshot,
	model, runtime, test, Croissant, release, and scenario gates, then exposed
	pre-existing orchestration drift: its archived schema-v2 run call omits the
	required explicit legacy judge identities. The same archived run passes the
	supported strict invocation with `copilot:claude-opus-4.6` and
	`copilot:gpt-5.4` (450/450 rows, 900/900 canonical, zero strict failures).
	The aggregate audit is therefore not recorded as PASS.
- Optional isolated notebook verification: `judge_comparison.ipynb` and
	`reviewer.ipynb` match fresh execution; cached `wave_analysis.ipynb` output
	differs from fresh execution. No notebook/output refresh was made because the
	drift predates and is outside this documentation slice. Configured checks,
	claim audit, source links, and both manuscript renders remain green.

### Pre-commit CEOps promotion hardening

- Exact-domain receipt persistence: PASS, 17 dynamically discovered tests,
	including same-tuple alternate condition, judge substitution, and coordinated
	duplicate row/receipt attacks.
- Strict schema-v2 reporting: PASS, 22 dynamically discovered tests including
	model/scenario/committed substitutions, metadata downgrade, malformed done
	JSON, boolean units, missing/invalid persistence mode, explicit legacy
	persistence opt-in, and unclassified retries.
- Completed-run promotion: PASS, 45 dynamically discovered attacks. Public
	validate/lock rebuild staging from source; stale/coordinated stage mutations
	are discarded; unsafe run IDs, unclassified judge failures, and non-domain
	final-verification or post-rename-fsync exceptions are rejected and cleaned up.
- Real evidence: external schema-v2 run PASS at 450/450 results and 900/900
	canonical judgements under explicit legacy persistence policy; parent bundle
	verifies with unchanged ID `dd262a5c...`.
- Exact locked-environment `audit-paper-data.py`: PASS end to end; the historical
	run's judge and persistence exception are now declared in the audit policy.
- Full configured `gates/checks.sh`: PASS; documentation links 120/178; paper
	claim audit 10 surfaces; diagnostics zero in repaired promotion files.
