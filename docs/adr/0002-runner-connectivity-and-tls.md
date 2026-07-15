# ADR 0002: Runner connectivity and TLS — certless v1, central minting deferred

- Status: Accepted
- Date: 2026-07-15
- Related: `docs/sdd/ceops-browser-runner.md` (§3, §6.7, §15, §17); ADR 0001 (Cloudflare Pages)

## Context

The CEOps experiment runner is browser-delivered and **user-owned**: a person runs
the runner on their own machine/LAN and the hosted console at
`experiment.ceops.org` connects to it. A recurring question is whether those local
connections need a browser-trusted TLS certificate, and — for third-party users —
whether CEOps should mint one for each runner.

Two constraints frame the decision:

- **Browser reachability (SDD §3.2).** From a hosted HTTPS page, reaching the
  runner is: `http://localhost` — allowed in Chrome/Edge/Firefox as a secure
  context (Chrome adds a one-time Local Network Access prompt), **blocked in
  Safari**; `http://<lan-ip>` — Chromium-only (LNA), blocked in Firefox/Safari.
  The runner-served console navigated directly at `http://127.0.0.1:<port>` (or a
  private LAN address) is a same-origin HTTP document that **every browser** accepts.
- **The DNS-token-on-the-box problem.** For a LAN-only box the only ACME path is
  DNS-01, which needs a zone-wide DNS-edit token. If each runner obtains its own
  certificate, that token is persisted on the runner — an unacceptable blast radius
  for a third-party (or even the operator's own) machine.

The operator prefers any TLS to be branded under `ceops.org`, and accepts running
**without a certificate** provided the flow works from `experiment.ceops.org`.

## Decision

1. **v1 ships certless.** The runner serves its own console at
   `http://127.0.0.1:<port>/` (and, opt-in, a private LAN address). This
   same-origin HTTP surface works in **every browser** and is the supported path.
   The hosted `experiment.ceops.org` console additionally connects to
   `http://localhost:<port>` for Chrome/Edge/Firefox; **Safari users use the
   runner's own `localhost` console.** No per-user certificate is issued, no central
   cert service is run, and **no DNS credential is placed on any runner.**

2. **If a runner ever terminates TLS** (e.g. the operator's own cross-LAN box) the
   certificate is minted so that (a) the runner **generates its own private key** and
   CEOps only *signs* it — CEOps never holds a runner's private key — and (b) the
   DNS-01 challenge is answered by a **central** holder of the `ceops.org` DNS
   credential, never by a token on the runner.

3. **Central `*.run.ceops.org` minting is deferred (documented, not built).** The
   Plex-style model — the runner generates a keypair, a central CEOps service runs
   Let's Encrypt DNS-01 for an opaque `<hash>.run.ceops.org` name and returns the
   signed cert — is the future path to close the two v1 gaps (Safari on the
   hosted→localhost path, and the cross-LAN-machine case) with all-browser valid
   HTTPS. It is **not** in v1 because it requires central infrastructure (an issuing
   service, an account/identity system, the central DNS credential, Let's Encrypt
   rate-limit management), which contradicts the SDD zero-central principle (§2/§15)
   and must be a deliberate, separate decision.

## Consequences

- **Works in v1, no certs:** run-on-my-laptop (the dominant case) in
  Chrome/Edge/Firefox via the hosted console; **every** browser including Safari via
  the runner's own `localhost` console; opt-in cross-machine LAN via the
  runner-served console navigated directly (plain HTTP, non-secure-context — no
  Service Workers / `crypto.subtle`).
- **Does not work in v1:** Safari driving the *hosted* `experiment.ceops.org` console
  down to `localhost`; and an all-browser hosted-console → LAN-IP runner. Both wait
  on the deferred central minting.
- **The sec note is avoided by construction:** with no runner-issued certificate
  there is no DNS token on any runner. The operator's current `home-ai.hont.ro`
  acme.sh certificate is a **local development convenience, not the product path**;
  it can be removed and the box falls back to the certless `localhost` console.
- When central minting is later adopted, it also retires the operator's own
  token-on-the-box, because `home-ai` becomes just another runner that receives a
  centrally-minted, runner-keyed certificate.

## Alternatives considered and rejected

- **Per-runner DNS-01 with the token on the box** — the original sec note; rejected
  (a zone-wide credential on every user's machine).
- **CEOps generates and ships private keys** — rejected; a central compromise would
  impersonate every runner and keys would transit the network.
- **User brings their own domain/certificate** — rejected as a default for third
  parties (unreasonable setup friction); remains available for advanced
  self-hosters.
- **Self-signed / private CA on the runner** — rejected as a product default; trusted
  only where the root is installed, so it breaks the hosted-console experience.
