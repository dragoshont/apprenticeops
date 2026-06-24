# Deploy ceops.hont.ro (Authentik-gated, LAN-only) — operator runbook

The dashboard is already running as a Docker container **on the home node**
(`192.168.1.201:8770`) with working SSH/shell access to `home` + `ai` — see the
[main README](../../README.md). This makes it reachable at a clean URL behind the
homelab's Authentik front door, mirroring the media apps (`sonarr.hont.ro`, …) and
`ha.hont.ro`.

> **Why this is staged, not auto-applied:** per homelab rule **HL-11**, an Authentik
> forward-auth gate is attached **last**, after the provider exists, and the live flip
> is proven by a **real interactive sign-in that cannot be automated**. Attaching the
> gate before the provider knows the host = a redirect-loop lockout (of `ceops.hont.ro`
> only). So the cutover is an operator step. Total time: ~5 min.

Manifests: [`ceops.yaml`](ceops.yaml) — a selector-less Service + Endpoints pointing
Traefik at the host container, the Authentik-gated IngressRoute, and the http→https
redirect (mirrors `apps/homeautomation/home-assistant/forward-auth.yaml`).

## Steps (run on / against the home node)

**1. Container is up with auth ON.** Re-create it trusting the gate's header:
```bash
cd ~/apprenticeops/dashboard
sed -i 's/^AUTH_ENABLED=.*/AUTH_ENABLED=true/' .env   # or edit by hand
HOME_SSH=dragos@home AI_SSH=home-ai.hont.ro REPO_DIR=/home/dragos/apprenticeops AUTH_ENABLED=true \
  docker compose -f compose.yaml -f compose.host.yaml up -d
```
(Direct `:8770` LAN hits now return 401 — that's intended; access is via `ceops.hont.ro`.)

**2. DNS — Cloudflare DNS-only A record (LAN-only, like every other app):**
```
ceops.hont.ro  A  192.168.1.201   (DNS only — grey cloud, NOT proxied)
```
Use the `cf-dns-add` skill / Cloudflare API. A private-IP DNS-only record is reachable
only on the LAN/Tailscale, never the public tunnel.

**3. Authentik — make the forward-auth provider know `ceops.hont.ro`** (UI, manual;
Authentik here is hand-configured — **record the change in
`apps/platform/authentik/README.md`** or it's lost on rebuild):
- Reuse the domain-level **`homelab-apps-forwardauth`** proxy provider that already gates
  the media apps: add `https://ceops.hont.ro` to its **External host** / allowed hosts (a
  proxy provider that covers `*.hont.ro` may need no change — confirm `ceops.hont.ro` is
  in scope), **or** create a dedicated proxy provider + application for it.
- Add the provider to the **embedded outpost** (the one `authentik-forwardauth` calls at
  `…/outpost.goauthentik.io/auth/traefik`).
- Bind the app to the group that should have access (e.g. family).

**4. Apply the route.** Either add `ceops.yaml` to the GitOps tree (preferred —
`clusters/home/…`) and reconcile, or apply directly:
```bash
microk8s kubectl apply -f ceops.yaml
```

**5. Canary sign-in (the part only you can do — HL-11).** Open
**https://ceops.hont.ro** in a browser → you should be redirected to `auth.hont.ro`,
sign in with Microsoft, land on the dashboard, and the header shows your username (the
`open` pill becomes your user). Confirm the dashboard works (sessions/charts load = it
still SSHes to `home`/`ai`).

## Quick routing test before gating (optional)
To prove DNS + Traefik + TLS before wiring Authentik, temporarily drop the
`authentik-forwardauth` middleware from the `ceops-authgated` route and set
`AUTH_ENABLED=false`; `https://ceops.hont.ro` then loads ungated on the LAN. Re-add the
middleware + `AUTH_ENABLED=true` for the real cutover.

## Rollback
```bash
microk8s kubectl delete -f ceops.yaml          # remove the route
# revert auth on the container:
sed -i 's/^AUTH_ENABLED=.*/AUTH_ENABLED=false/' ~/apprenticeops/dashboard/.env
cd ~/apprenticeops/dashboard && docker compose -f compose.yaml -f compose.host.yaml up -d
```
The container keeps serving on `192.168.1.201:8770` throughout.
