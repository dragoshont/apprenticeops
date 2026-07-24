# SDD: Browser-Delivered CEOps Experiments With User-Owned Runners

Status: proposed; research complete, implementation not started
Date: 2026-07-14
Public console: `https://experiment.ceops.org`
Execution boundary: user-owned loopback runner

## 1. User-Visible Outcome

After this change, a user can open `experiment.ceops.org`, explicitly pair it
with a CEOps Runner installed on their computer, run a versioned benchmark on
models and hardware they control, inspect all completed and failed attempts, and
export a portable evidence bundle without creating a CEOps account or exposing
their home network to CEOps.

## 2. Non-Negotiable Boundaries

- The web UI is static and browser-delivered.
- CEOps hosts no experiment control plane, account database, job queue, model
  artifact store, or result store in the first generation.
- The runner binds only to `127.0.0.1` and `[::1]` by default.
- The browser never receives SSH keys, model-provider secrets, judge credentials,
  or arbitrary filesystem access.
- The public site cannot scan local ports or auto-pair silently.
- Pairing and every mutating action require runner authorization in addition to
  browser CORS/Local Network Access permission.
- A runner may coordinate explicitly configured LAN workers, but that is a
  runner-side capability. The browser talks only to its paired loopback runner.
- The current private Mission Control remains private and unchanged until this
  contract is independently implemented and reviewed.

## 3. Why Loopback First

Secure Contexts treats `127.0.0.0/8`, `::1`, and conforming `localhost` names as
potentially trustworthy. That classification alone does not guarantee that an
HTTPS public document can reach a plaintext loopback service. Mixed-content
handling, browser Local Network Access permission, CORS response sharing, and
CEOps pairing authorization are separate gates. Browser behavior differs.

Therefore the primary Chromium/Edge flow is:

```text
https://experiment.ceops.org
          |
          | explicit CORS + pairing token
          v
http://127.0.0.1:<fixed-port>  CEOps Runner
          |
          +-- local Ollama / llama.cpp / engine adapters
          +-- optional configured LAN workers
          +-- local artifacts and telemetry
```

Direct browser-to-arbitrary-LAN-runner communication is not a baseline feature.
It may be revisited when Local Network Access behavior is sufficiently portable
and its permission UX can be tested across supported browsers.

### 3.1 Browser support tiers

| Browser family | Public `experiment.ceops.org` -> loopback runner | Required product path |
|---|---|---|
| Chromium / Edge | Candidate primary path. Chrome launched the Local Network Access permission in 142; exact Edge version and enterprise-policy behavior still require real testing. | Public console plus native LNA permission plus runner pairing; local UI remains available for recovery. |
| Firefox | Provisional until a real stable-browser spike proves public-to-loopback behavior and permission UX. | Public console only when proven; otherwise local UI. |
| Safari / WebKit | Not a portable public-to-HTTP-loopback path in the current compatibility evidence. | Runner-served local UI is the supported path. |

The runner-served local UI is a first-class product, not a degraded error page.
It provides the same setup, prepare, monitor, results, and export workflows from
a same-origin loopback document. The public site detects an unsupported or
blocked path and offers **Open local CEOps Runner** plus browser-specific
instructions. The local UI bundle and runner API advertise compatible versions.

The protocol spike uses a genuinely public HTTPS origin and real GUI browsers;
hosts-file mappings, headless-only tests, and localhost-hosted copies do not close
the permission/compatibility gate.

## 4. Current System And Reuse Map

The current Mission Control is:

```text
browser -> FastAPI -> SSH home -> scripts/pipeline-status.py
                              -> SSH ai -> run.py / runtime
```

Its backend is explicitly a single-operator LAN tool. It can optionally trust an
Authentik forward-auth header, but otherwise has no auth. It resolves a
server-owned `data/run-matrix.json`, starts detached processes over SSH, and
polls status from repository/run files.

### 4.1 Reuse largely as-is

- `run.py` inference, watchdog, output, and deterministic-check machinery;
- judge and result reconciliation logic, after credentials become runner-local;
- scenario, model-set, memory-context, and inference-strategy concepts;
- frontend visualization components for progress, pipeline stages, attempts,
  Pareto, scores, sessions, and artifacts;
- current Storybook fixture approach;
- completed-run promotion and privacy concepts.

### 4.2 Adapt behind a new contract

- frontend API client: absolute paired-runner origin instead of same-origin
  `/api/*`;
- `Status` and `RunMatrix` types: add API version, capabilities, immutable
  identities, unsupported reasons, and local-runner state;
- run controls: preflight capabilities and exact condition before enabling Start;
- polling: runner-local run/event API with resumable cursors;
- experiment definitions: signed or digest-pinned pack manifests rather than
  server paths alone;
- artifacts: portable content-addressed bundle rather than a Git branch as the
  product boundary.

### 4.3 Replace

- FastAPI's SSH transport and hard-coded `HOME_SSH`, `AI_SSH`, `REPO_DIR`, and
  `AI_REPO` topology;
- Authentik-header trust as product authentication;
- detached `pgrep`/marker-file process control as the browser contract;
- GitHub/Copilot credentials and per-model Git commits as runner requirements;
- LAN-wide unauthenticated binding;
- fixed homelab node/power assumptions as universal requirements.

## 5. Tournament Of Architecture Options

| Option | Benefits | Costs / risk | Verdict |
|---|---|---|---|
| Hosted CEOps control plane with polling runners | Easy multi-device scheduling and central history | Creates accounts, secrets, result custody, home-network trust, uptime, abuse, and privacy obligations | Reject for first generation |
| Public browser directly controls arbitrary LAN runners | No local bridge process beyond runner | Browser permission fragmentation, DNS/mixed-content complexity, larger attack surface, cross-network confusion | Reject as baseline |
| Public static browser pairs to loopback runner | Browser-only UI, user-owned execution/data, no inbound home access, clear local authorization boundary | Requires local install and careful pairing/CORS design | **Selected** |
| Runner serves the entire UI locally | Simplest same-origin security and best browser compatibility | Loses canonical web-delivered UI/update experience | Required compatibility fallback, not primary |
| Native desktop application | Strong local integration | Packaging and update burden; violates browser-only product goal | Reject |

## 6. Pairing And Authorization Contract

### 6.1 Runner installation and setup

- Publish signed/notarized installers or packages for each supported OS and
  architecture, with checksum and provenance verification.
- Install one user-scoped background service plus a local status/approval UI;
  do not require the browser to start or repair an OS service.
- Setup verifies runner version, API compatibility, loopback port ownership,
  runtime adapters, model storage, telemetry permissions, judge-egress choice,
  and available disk before pairing.
- Provide native start, stop, status, upgrade, revoke-all-pairings, and uninstall
  commands plus a diagnostics bundle that excludes secrets.
- A port collision fails closed and names the owning process when permitted. The
  runner never scans for or silently moves to another port.

### 6.2 Runner discovery

- Use one documented fixed loopback port in the prototype; do not scan a range.
- The console performs only a read-only `GET /v1/health` after the user selects
  **Connect local runner**.
- A missing runner produces install/start instructions, not repeated probing.
- Canonical public targets are `http://127.0.0.1:<port>` and, after a separate
  listener test, `http://[::1]:<port>`. The prototype does not use `localhost` or
  `*.localhost`, avoiding resolver ambiguity. The `Host` authority is exact,
  including the bracketed IPv6 form.
- `GET /v1/health` is minimal, side-effect-free, unauthenticated, non-cacheable,
  and returns only runner/API version, runner instance ID, and pairing readiness.

### 6.3 Pairing ceremony

1. User starts the runner locally.
2. Console requests `POST /v1/pairing/request` with a random, single-use browser
   challenge, requested scopes, console origin, and client API version.
3. Runner displays the requesting origin, requested scopes, short confirmation
   phrase, pairing ID, and expiration in its own local UI/terminal.
4. User confirms locally.
5. The console polls the pairing-status resource using only the single-use
   challenge. Confirmation makes one high-entropy, origin-bound token available
   once; a second read fails.
6. Browser keeps the token in memory. It is never placed in a URL, log, cookie,
   Web Storage, IndexedDB, Cache Storage, BroadcastChannel, or cross-tab message.
7. Pairing requests have a maximum 120-second approval window, rate limits, a
   bounded number of failed reads, explicit denial/cancel states, and replay
   rejection.
8. The token expires no later than 12 hours and no later than the runner process
   lifetime. A browser reload, runner restart, explicit revoke, origin mismatch,
   or expiry requires re-pairing. Long experiments continue in the runner; the
   user re-pairs only to observe or control them.

The runner must not treat browser Local Network Access permission as
authorization.

`POST /v1/pairing/confirm` is not an HTTP endpoint exposed to the public console.
Confirmation occurs through the runner's local UI/terminal and its private
in-process control channel. A hostile local process remains outside the web
threat boundary; the runner does not claim to defend a fully compromised user
account.

The 120-second value is a default, not an inaccessible hard timeout. The local
approval UI offers **Extend by 5 minutes** before expiry and an untimed manual
pairing command that prints the same origin/scopes for users who need more time.
The browser announces remaining time without moving focus. Protocol tests cover
extension, expiry, and the untimed equivalent path under WCAG 2.2 SC 2.2.1.

### 6.4 Public-console request mediation

- Validate exact `Host` and exact `Origin` on every request.
- Allow only `https://experiment.ceops.org` plus explicit development origins.
- Return exact-origin CORS and `Vary: Origin`; never wildcard CORS.
- Use `credentials: omit`; do not use cookies or URL credentials.
- The client uses `redirect: "error"` and `cache: "no-store"`; API responses use
  `Cache-Control: no-store`.
- Reject missing, absent, or `null` Origin. Explicitly allow only the required
  methods and headers in CORS; do not reflect arbitrary request values.
- Mutating requests carry the scoped bearer token in a custom header and use
  JSON, intentionally requiring CORS preflight.
- Reject missing or stale token, wrong origin, wrong host, redirect, simple form
  submissions, and unknown methods.
- Token scopes are `runner:read`, `experiment:prepare`, `experiment:execute`,
  `experiment:control`, `experiment:cancel`, `artifact:export`,
  `artifact:import`, `artifact:verify`, and `artifact:delete`. Unknown scopes are
  rejected; adding a scope requires an API-version change and threat review.
- Cancel and destructive cleanup are separately mediated and auditable.

### 6.5 Runner-served local-UI profile

- The local UI and API are same-origin loopback resources served by the same
  runner build. It has a separate local pairing session and token; the
  public-origin token cannot authorize the local origin.
- The local UI begins in setup-only mode. The user approves a local session in
  the runner terminal/native approval surface. The token is origin-bound,
  in-memory, expires/revokes under the same rules as the public token, and is
  required for every non-health endpoint.
- Same-origin GET requests may omit `Origin`; the runner still validates exact
  `Host` and local-session authorization. Unsafe methods require exact local
  `Origin`, JSON, a custom authorization header, and CSRF-resistant non-simple
  requests. Drive-by form and `no-cors` submissions fail.
- The local UI uses the same operation, condition, attempt, and bundle schemas as
  the public console. It is not a separate simplified product.
- No public-origin CORS is required for local-only confirmation endpoints.
- The local UI has a direct launch URL printed by the runner and is the Safari
  and permission-recovery path.

### 6.6 Complete mediation matrix

Routes are denied unless the exact profile, method, scope, and object owner below
match. Every preparation, run, operation, imported candidate, bundle record,
deletion preparation, and pairing stores its creating `pairing_id`. An
object-bearing request succeeds only for that same pairing or for an explicit,
locally confirmed administrative recovery grant naming the object and allowed
action. Object IDs and digests are unguessable identifiers, not authorization.

| Route family | Method/profile | Required authorization and ownership |
|---|---|---|
| `/v1/health` | GET, public or local | None; minimal non-sensitive fields only. |
| `/v1/pairing/request` | POST, public | LNA/CORS plus single-use challenge; rate-limited. |
| `/v1/pairing/{id}` | GET, public | Challenge in `X-CEOps-Pairing-Challenge`; never URL, log, or browser storage. Pairing ID and challenge must match; single-use bounded reads. |
| Local approval/session | local UI/terminal only | Physical/local user confirmation; not public CORS. |
| Capabilities, runner/workers, packs, models | GET, public or local | `runner:read`; runner-wide read data is filtered to non-secret capability fields. |
| Runs, run events, run artifacts | GET, public or local | `runner:read` plus same `pairing_id` as the run, or object-specific recovery grant. |
| Prepare | POST, public or local | `experiment:prepare`; resulting preparation is owned by the current pairing. |
| Start | POST, public or local | `experiment:execute`, matching unexpired preparation owned by the same pairing, and idempotency key. |
| Pause/resume | POST, public or local | `experiment:control`; adapter capability and same-pairing run ownership. |
| Cancel | POST, public or local | `experiment:cancel`; same-pairing run ownership, impact preflight, and idempotency key. |
| Export | POST, public or local | `artifact:export`; same-pairing run ownership. |
| Import | POST, public or local | `artifact:import`; resulting candidate/bundle record is owned by the current pairing; idempotency key required. |
| Verify | POST, public or local | `artifact:verify` plus same-pairing candidate/bundle ownership or object-specific recovery grant. |
| Delete run/bundle | POST, public or local | `artifact:delete`; target run/bundle ownership, target-specific deletion preparation owned by the same pairing, and confirmation. |
| Revoke pairing | POST, public or local | Current pairing token or local administrative confirmation. |
| Operation status/events | GET, public or local | Scope corresponding to the operation plus same-pairing operation ownership or object-specific recovery grant. |

The server rejects every unlisted route/method/header/profile combination. The
test matrix includes guessed or cross-pairing pairing IDs, preparation IDs, run
IDs, operation IDs, deletion IDs, candidate IDs, and bundle digests, plus
wrong/missing scopes for every endpoint family.

## 7. Minimal Runner API

### Read-only

- `GET /v1/health`
- `GET /v1/capabilities`
- `GET /v1/runners/current`
- `GET /v1/workers`
- `GET /v1/packs`
- `GET /v1/models`
- `GET /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/events?after=<cursor>`
- `GET /v1/runs/{run_id}/artifacts`

### Pairing and control

- `POST /v1/pairing/request`
- `GET /v1/pairing/{pairing_id}` (challenge-authenticated, bounded, no token
  replay)
- local UI/terminal pairing confirmation (not a public-console HTTP route)
- `POST /v1/pairings/current/revoke`
- `POST /v1/experiments/prepare`
- `POST /v1/experiments/start`
- `POST /v1/runs/{run_id}/pause`
- `POST /v1/runs/{run_id}/resume`
- `POST /v1/runs/{run_id}/cancel`
- `POST /v1/runs/{run_id}/export`
- `POST /v1/bundles/import`
- `POST /v1/bundles/{bundle_digest}/verify`
- `POST /v1/deletions/prepare`
- `POST /v1/deletions/{deletion_id}/confirm`
- `GET /v1/operations/{operation_id}`
- `GET /v1/operations/{operation_id}/events?after=<cursor>`

The prepare response is load-bearing: it resolves the full immutable condition,
checks capabilities, estimates work/storage, and returns blocking incompatibility
reasons before execution.

Every mutating endpoint returns `202 Accepted` with a durable `operation_id`,
never a claim that the action completed. Start/export/cancel/import/verify/delete
accept an idempotency key. Retrying the same key returns the same operation;
reusing it with a different request fails.

## 8. Capability Contract

`GET /v1/capabilities` must include:

- runner API, implementation, and bundle-schema versions;
- OS, architecture, CPU/GPU/NPU inventory, RAM, disk, and isolation support;
- available runtime adapters and exact versions/builds;
- installed model artifact digests and supported acquisition methods;
- telemetry providers, domains, units, sampling, privileges, and quality flags;
- supported DNF signals and resource limits;
- maximum concurrency and current reservations;
- judge adapters without exposing credentials;
- supported pack/schema versions;
- pairing origin, scopes, expiry, and revocation state.

Runner and worker inventory rows include stable ID/fingerprint, role, endpoint
scope, supported actions, prerequisites, current reservation, source,
`observed_at`, `stale_after`, readiness, health, and an explicit unsupported or
unavailable reason. Optional LAN workers are discovered and mediated only by the
paired loopback runner; the browser never discovers or calls them.

The judge capability is explicit:

- `none`: deterministic checks only;
- `local`: runner-local judge with model/runtime/artifact identity;
- `remote`: named provider/model plus egress class, credential availability,
  redaction policy, and operator confirmation requirement.

The prepared condition and UI repeat that choice. The exported bundle records
whether judging was absent, local, or remote; remote judge egress is never
implied by the word "offline."

Missing capability data is explicit. It does not become a default value.

### 8.1 Prepared condition

The prepare response includes `preparation_id`, condition digest, expiry,
resolved pack/model/runtime/strategy/judge/hardware identities, blockers,
warnings, planned downloads and mutations, disk and work estimates, reservation
conflicts, privacy/egress classes, telemetry quality, pause/resume capability,
comparison eligibility, and the source/confidence of every estimate. Start
requires an unexpired preparation and returns its digest in the operation
receipt.

## 9. Experiment And Attempt State

### Run state

`draft -> prepared -> ready -> queued -> running -> pausing -> paused -> resuming -> canceling -> completed | canceled | failed | partial | unknown`

### Attempt execution state

- `completed`
- `timeout`
- `oom`
- `runtime_unavailable`
- `model_load_failed`
- `process_crash`
- `canceled`

Attempt records separate:

- `execution_status` and `finish_reason` / `dnf_reason`;
- partial-output digest and bytes/tokens produced;
- deterministic verification status: `pending | passed | failed | error |
  unavailable`;
- judge status per declared judge: `pending | succeeded | parse_failed | error |
  skipped | unavailable`;
- nullable score and explicit unavailable reason;
- retry/parent lineage and canonical-success selection;
- source, observed time, scope, and stale policy.

Execution state is separate from verification and semantic score. A verifier
error is unjudged infrastructure failure, not a model failure. DNF is a preserved
reliability outcome and can still have partial output and judge evidence. Retries
never replace prior attempts silently. Progress separately reports planned
canonical completions, raw attempts, retries, DNF, verifier states, judge states,
and a stable denominator.

### 9.1 Operation state

Every long-running mutation is an operation:

`queued -> waiting -> running -> blocked | canceling -> canceled | succeeded | failed | partial | unknown`

An operation records actor/pairing, targets, ordered stages, timestamps,
heartbeat, source, idempotency key, terminal error/correlation ID, retry and
cancel eligibility, retained/deleted artifact counts, logs/artifacts, impact,
recovery guidance, and a durable receipt. The UI never equates button click or
HTTP acceptance with completion.

Pause is adapter-specific. Capabilities and prepare identify safe pause point,
checkpoint granularity, expected discarded work, and resume preflight. If an
adapter cannot prove resumability, Pause is disabled with a reason; Stop/Cancel
preserves completed and partial attempts and reports exact impact.

The UI must expose disconnected, permission-required, pairing-pending,
pairing-expired/revoked, capability-stale/mismatch, preparing, queued, running,
stalled, pausing, paused, resuming, canceling, partially judged, resumable,
exporting, import collision, verifier error, privacy-failed, and integrity-failed
states. Every health/progress/result state shows source, observation time, scope,
and stale status.

## 10. Evidence Bundle

Adopt OCI Image Layout and ORAS conventions for local content-addressed bundles.
The root descriptor digest is the bundle identity. CEOps defines benchmark media
types and a canonical run manifest containing:

- experiment/scenario/model/runtime/hardware identities;
- prompts, checks, judge and strategy hashes;
- all attempts and retry lineage;
- DNF and verifier outcomes;
- telemetry series and measurement provenance;
- logs, outputs, sidecars, and analysis exports;
- privacy/redaction report;
- software/build provenance and checksums.

Digest integrity is not source authenticity by itself. Bundle signing and
attestation are a later phase after the local bundle contract is stable.

### 10.1 Bundle lifecycle

Bundle schemas are versioned independently from the runner API. Import first
creates an isolated candidate record and verifies descriptor/blob digests,
schema support, condition completeness, source/build identity, attempt lineage,
judge reconciliation, privacy/redaction status, and required media types before
anything becomes comparison-eligible.

Verification outcomes are `verified`, `verified_with_warnings`, `incomplete`,
`privacy_failed`, `integrity_failed`, `unsupported_schema`, and `untrusted`.
Only policy-eligible verified bundles enter comparisons. Import collisions are
resolved by digest identity; bytes are never overwritten by a matching label.
The UI can reopen a verified bundle entirely offline and shows import source,
verification time, claim status, comparison eligibility/reason, correction or
supersession lineage, and unavailable fields.

Export, import, verify, and delete are durable operations. An interrupted export
is resumed or discarded by temporary-object identity; it never publishes a
partial bundle under the final digest. Deletion shows active dependencies,
retained versus deleted artifacts, recovery implications, and a terminal audit
receipt.

### 10.2 Destructive deletion contract

Deletion always targets exactly one immutable run bundle digest or imported
bundle digest. A run ID or label alone is not a valid target. Runs and imported
bundles are distinct target types even when they reference the same blobs.

`POST /v1/deletions/prepare` requires `artifact:delete` and returns a
`deletion_id`, target type/digest, immutable condition/run identities, active
operation and comparison dependencies, shared/unique blob counts and bytes,
retained versus removed records, whether bytes can be recovered or re-imported,
irreversible effects, blockers, and expiry. Active runs or operations block
deletion unless they reach a terminal state; deletion never becomes an implicit
cancel.

The confirmation UI displays the exact digest and impact, requires a deliberate
target-digest confirmation, focuses the safe Cancel action first, and provides
no bulk wildcard. `POST /v1/deletions/{deletion_id}/confirm` requires the same
pairing, `artifact:delete`, an unexpired preparation, and an idempotency key.

Deletion is journaled by immutable blob/object steps. Shared blobs remain.
Interrupted deletion reconciles completed and pending steps on restart; retries
with the same idempotency key continue the same operation. Terminal outcomes are
`succeeded`, `partial`, or `failed`, never ambiguous success. The audit receipt
records actor, target, preparation digest, removed/retained objects and bytes,
dependencies, timestamps, errors, recovery/re-import instructions, and final
verification that retained bundles still resolve.

## 11. OSS Candidates And Adoption Gates

No single existing framework supplies the product boundary.

| Capability | Candidate disposition before spike | Required adoption evidence |
|---|---|---|
| General evaluation engine | Spike EvalScope and Inspect AI as adapters; no default chosen. | Active maintenance and compatible license; local/Ollama/llama.cpp path; repeated-attempt retention; deterministic seeds; typed failures; no forced cloud custody; adapter emits CEOps condition and attempt fixtures without loss. |
| Existing benchmark imports | Defer an lm-evaluation-harness adapter until native CEOps fixtures pass. | Stable task import boundary, license/provenance retention, and explicit translation loss report. |
| Isolated task/verifier environments | Spike Harbor on Linux only. | Deterministic environment digest, verifier/error separation, resource limits, offline operation, and portable artifact export. |
| Performance load generation | Optional MLPerf LoadGen adapter after semantic runner. | Profile/seed fidelity, local runtime integration, and telemetry boundary that does not redefine CEOps task correctness. |
| Linux process/resource isolation | Spike BenchExec on supported Linux runners. | cgroup/process-tree enforcement, timeout/OOM distinction, privilege disclosure, and no silent fallback. |
| Cross-platform energy/resource sampling | Spike EnergiBridge behind a telemetry-quality adapter. | Current maintenance/license review; supported hardware matrix; direct/estimated distinction; units, boundary, sampling, baseline, and missing-data quality. |
| Immutable local bundles | Adopt OCI Image Layout semantics; spike ORAS transport separately. | Offline local layout and digest verification first; media-type/schema fixtures; no registry dependency; provenance and privacy metadata preserved. |
| Browser pairing, CEOps condition identity, DNF model, operation model, and evidence viewer | Build. | No evaluated project supplies this boundary; it is the product-specific differentiator. |

The first implementation should keep the current native ApprenticeOps engine as
one runner adapter rather than block on choosing a universal engine. All other
tool choices remain provisional until a scored spike records feature fit,
maintenance/currentness, license, supply-chain posture, coupling cost, and a
rejected-alternative rationale.

## 12. Security Threats And Controls

| Threat | Required control |
|---|---|
| Malicious public site drives localhost runner | Exact origin/host checks, user-confirmed pairing, scoped token, non-simple preflighted mutations. |
| DNS rebinding or cross-network confusion | Loopback binding only; reject non-loopback Host/address; no wildcard DNS or arbitrary LAN discovery. |
| Stolen token | In-memory, short-lived, origin-bound token; explicit revoke; no URL/cookie storage. |
| Runner command injection | Browser submits typed IDs and manifests; runner resolves adapters/paths and never executes raw shell from the client. |
| Malicious experiment pack | Digest pinning, schema validation, declared capabilities, sandbox policy, no source-provided command execution by default. |
| Secret disclosure | Runner-local credential adapters; capability response reports availability only; logs/artifacts pass redaction. |
| Result tampering | Content-addressed artifacts, canonical manifest, immutable attempts, verification before comparison/export. |
| Browser disconnect | Runner owns execution; event cursors and resumable status; page lifecycle never owns the process. |
| Runner process crash or host reboot | Write-ahead run/operation/attempt journal; fsync at declared boundaries; preserve partial output and telemetry; reconcile adapters and reservations on restart; mark uncertain work `unknown` until inspected; resume only from a proven checkpoint. |
| Event loss or background throttling | Monotonic event IDs, one in-flight poll, deduplication, retention window, cursor-expired snapshot reconciliation, bounded backoff, immediate refresh on visibility return, and explicit stale state. |
| Local hostile process occupies the fixed port | Bind fails closed; show collision diagnostics locally; never scan or move ports; pairing proves only the responding runner identity and does not claim protection from a compromised user account. |

### 12.1 Recovery matrix

| Failure | Durable state | User-visible outcome | Recovery |
|---|---|---|---|
| Browser closes/reloads | Runner run and operation journal continue; pairing token is lost. | Run shows unavailable until re-pair; no claim that the page stopped it. | Re-pair, fetch snapshot, resume events from current cursor. |
| Runner process restarts | Prepared condition, operations, attempts, outputs, and cursors survive locally. | `reconciling` then running/paused/partial/unknown with source and timestamp. | Reconcile child processes and artifacts; resume only at adapter-declared checkpoint. |
| Host reboots | Same journal plus service restart policy; active child process is presumed gone. | Run becomes `unknown` or `partial` until artifact reconciliation. | Preflight hardware/runtime again; resume remaining work or close with preserved DNF/partial attempts. |
| Judge unavailable | Inference and deterministic evidence remain; declared judge states are pending/error. | `partially judged`; quality result is not complete. | Retry the same declared judge identity with attempt lineage; never substitute silently. |
| Export interrupted | Temporary export operation and completed blobs remain; no final digest is published. | Export operation failed/partial with retained bytes. | Resume or discard temporary export, then verify final layout. |
| Deletion interrupted | Deletion journal preserves removed, retained, and pending object steps; shared blobs remain. | `partial` delete operation with exact impact, not a vanished row or success toast. | Reconcile on restart, continue with the same idempotency key, or stop and use receipt/re-import guidance where recovery is possible. |
| Runner/browser API mismatch | No mutation starts. | Compatibility blocker names both versions and supported remedy. | Upgrade runner or use its bundled local UI. |
| Event cursor expired | Authoritative snapshot remains. | History gap is named; stale stream is not treated as complete. | Fetch snapshot and resume from returned current cursor. |

## 13. Realistic Gap From Current Mission Control

The gap is **large but still not a rewrite of the benchmark engine**. The
portable product replaces the transport, authorization, durable operation,
packaging, and evidence lifecycle around reusable inference/evaluation concepts.

### Reuse estimate

- Inference, checking, judging, telemetry concepts, and artifact generation:
  approximately 70-85% conceptually reusable.
- React presentation primitives and experiment-selection interactions:
  approximately 50-70% reusable after type/API, accessibility, mobile, and stale
  state changes. Existing Pareto calculations and labels are not reused as
  public evidence semantics.
- Current FastAPI transport/control backend: approximately 20-35% reusable; SSH,
  fixed topology, marker/process control, and auth assumptions are not portable.
- Deployment/auth configuration: not reusable as the public product boundary.

### Delivery slices

| Slice | Outcome | Rough effort | Risk |
|---|---|---:|---|
| 0. Protocol spike | Real GUI Edge/Firefox/Safari/Technology Preview matrix for public HTTPS -> loopback; full local-UI fallback; fake runner only | 1-2 weeks | High, retire browser uncertainty first |
| 1. Canonical schemas | Pairing, runner/worker inventory, prepared condition, operations, run/attempt/verifier/judge/evidence, and bundle manifests | 1.5-2.5 weeks | High/contract |
| 2. Runner shell | Loopback/local UI server, pairing/auth, operation and event journal, restart reconciliation, fake adapter | 2-3 weeks | High/security/recovery |
| 3. Native ApprenticeOps adapter | Wrap `run.py`, checks, judges, telemetry, capability-specific pause/resume/cancel, artifacts | 2-3 weeks | Medium-high |
| 4. Browser and local console | Setup center, pairing, inventory, capability preflight, run builder, operation monitor, attempts/results, recovery/audit | 3-5 weeks | High/UX/accessibility |
| 5. Bundle and reproduction | OCI layout, import/export/verify/delete, offline re-open, collision/recovery, docs | 1.5-2.5 weeks | Medium-high |
| 6. Cross-platform hardening | Signed Linux/macOS/Windows packaging, service lifecycle, browser matrix, security, privacy, and recovery tests | 4-7 weeks | High |

A credible one-platform technical preview is approximately **8-12 engineer
weeks** after the protocol spike. A supported Linux/macOS/Windows product is more
realistically **16-24 engineer weeks** for one engineer, with packaging,
security, recovery, and browser compatibility on the critical path. This excludes
a hosted service because none is planned.

## 14. Phases And Gates

| Phase | Win | Gate | Rollback |
|---:|---|---|---|
| 0 | Pairing feasibility established with fake runner | Real browser matrix; exact origin/host/token attacks; no arbitrary LAN access | Delete spike; current Mission Control unchanged |
| 1 | Versioned schemas and reference fixtures | JSON Schema and adversarial fixtures; dual-family design PASS | Revert additive schemas/docs |
| 2 | Loopback runner with fake adapter | Pair/revoke/expiry/CORS/DNS-rebind tests; restart/reconnect behavior | Remove runner package |
| 3 | Real local experiment adapter | Existing experiment regression suite plus condition/artifact gates | Keep fake runner; revert adapter |
| 4 | Browser experiment preview | Storybook states and live desktop/mobile preview; user sign-off | No production domain binding |
| 5 | Evidence bundle | Export/import/verify/offline reopen pass | Keep local native artifacts |
| 6 | Production beta | Cross-platform installers, browser matrix, security review, signed release | Keep current private Mission Control |

### 14.1 Required protocol-spike matrix

Use a genuinely public HTTPS console and real GUI browsers. Minimum platforms:
macOS Safari stable and Technology Preview, Edge, and Firefox; Windows 11 Edge
and Firefox. Add Chrome when available. Headless automation supplements but does
not replace the native permission UX.

| Area | Required cases and pass condition |
|---|---|
| Address/request | `127.0.0.1`, `[::1]`, `localhost`, `*.localhost`; health GET, JSON pairing POST, token-header mutation; record prompt/preflight/request order. Only the documented target succeeds. |
| Permission | Grant, deny, reset, restart, private mode, managed-policy denial, top-level versus iframe. No mutation occurs before both browser permission and runner pairing. |
| CORS/authority | Allowed, wrong, absent, and null origins; canonical/wrong Host; raw form and `no-cors`; LAN address; DNS name resolving to loopback. Only the exact contract succeeds. |
| Redirect/cache | 301/302/307/308 to another port, LAN, and public host; token never forwards; stale health/status/event responses are never reused. |
| Pairing/token | Replay, expiry, cancel, held-request timeout, rate limit, wrong scope/origin, revoke, runner restart, reload, multiple tabs, and browser-storage audit. |
| Command safety | Duplicate Start/Export/Cancel, lost response, retry with and without idempotency key. Exactly one intended operation exists. |
| Port/lifecycle | Occupied/fake port, separate IPv4/IPv6 listeners, install/start/stop/upgrade/uninstall, sleep/wake, multiple OS users. Fail closed without scanning. |
| Polling/recovery | Duplicate/gapped events, cursor expiry, retention loss, runner restart, network loss, hidden/discarded tab, visibility resume, and stale indicator. |
| Local UI | Public-path failure followed by complete same-origin setup/prepare/run/inspect/export flow; runner/public shell API mismatch and upgrade path. |
| Accessibility | Keyboard-only, VoiceOver/Safari, NVDA/Edge and Firefox, 200% resize, 320 CSS-pixel reflow, contrast/forced colors, target size, reduced motion, paused updates, and restrained status announcements. |
| WebSocket negative gate | The complete product works with WebSocket unavailable; no token appears in a URL or subprotocol. |

### 14.2 Accessibility and static-host floor

Both public and local UIs must conform to WCAG 2.2 Level AA: semantic HTML, complete keyboard
operation, visible/unobscured focus, text recovery messages, 4.5:1 text and 3:1
UI contrast, 24 CSS-pixel minimum targets with approximately 44 px touch
targets, 200% resize, 320 px reflow, non-color state cues,
`prefers-reduced-motion`, and programmatic status messages without moving focus.
The pairing phrase is a confirmation aid, not a memory/transcription test; the
local UI displays origin and scopes directly. Event logs are not live regions.

The static host and local UI use restrictive CSP with exact `connect-src`,
`frame-ancestors 'none'`, no third-party runtime scripts,
`Referrer-Policy: no-referrer`, and explicit resource integrity/provenance where
applicable. Runner responses are never service-worker cached. The paired surface
does not rely on a service worker in v1.

Production sign-off includes a criterion-by-criterion WCAG 2.2 A/AA audit of
both complete processes, not only representative components:

- public console: setup guidance -> browser permission -> public pairing ->
  prepare -> review -> start -> monitor -> inspect -> export;
- runner-served local UI: local setup/session approval -> prepare -> review ->
  start -> monitor -> inspect -> export, including the untimed pairing path.

The declared browser/assistive-technology matrix must have zero unresolved
Level A or AA failures across both complete processes. Automated checks are
supplementary; keyboard and screen-reader testing are required. Any inaccessible
step blocks production release even when an equivalent individual component
passes in isolation.

## 15. Explicit Deferrals

- central CEOps accounts, cloud queue, result upload, or hosted judging;
- browser-direct arbitrary LAN runner discovery/control;
- collaborative teams and remote administration;
- automatic public leaderboard submissions;
- model artifact hosting;
- persistent pairing before the in-memory flow is proven;
- Mission Control exposure on a public subdomain;
- DNS binding for `experiment.ceops.org` before preview sign-off.

## 16. Standards And Primary References

- W3C Secure Contexts: loopback origins are potentially trustworthy, while
  powerful network capabilities require authenticated delivery:
  <https://w3c.github.io/webappsec-secure-contexts/#is-origin-trustworthy>.
- WHATWG Fetch/CORS: cross-origin sharing is opt-in; mutating/custom-header
  requests preflight; credentials and wildcard origins are incompatible.
  <https://fetch.spec.whatwg.org/#http-cors-protocol>.
- WICG Local Network Access (Draft Community Group Report, 2026-06-18): public
  pages must not silently pivot into local or loopback services. The browser
  permission mediates network access but does not authorize CEOps actions:
  <https://wicg.github.io/local-network-access/>.
- Chrome's implementation guidance records LNA permission launch in Chrome 142
  and explicitly states that it replaced the paused PNA preflight approach:
  <https://developer.chrome.com/blog/local-network-access>.
- CEOps still uses ordinary Fetch/CORS preflight because its JSON and scoped
  token headers are not CORS-safelisted; it does not depend on obsolete
  `Access-Control-Allow-Private-Network` headers.
- WebSocket: widely available, but classic WebSocket lacks backpressure and local
  network restrictions are evolving; polling/event cursors are the portable
  baseline: <https://websockets.spec.whatwg.org/>.
- RFC 6454 and RFC 9110 govern exact origin and authority semantics:
  <https://www.rfc-editor.org/rfc/rfc6454#section-5> and
  <https://www.rfc-editor.org/rfc/rfc9110#section-7.4>.
- OCI Image Spec / ORAS define content-addressed local artifact layout and a
  candidate transport: <https://github.com/opencontainers/image-spec> and
  <https://github.com/oras-project/oras>.

These standards do not define the CEOps application protocol. The SDD uses their
security model rather than inventing a weaker one.