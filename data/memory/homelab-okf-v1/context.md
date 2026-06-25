---
type: Memory Context
title: Homelab OKF memory v1
description: Compact, secret-free homelab operations briefing for memory-conditioned ApprenticeOps runs.
tags: [apprenticeops, homelab, memory]
timestamp: 2026-06-25T00:00:00Z
---

# Scope

This is the static memory context for `memory_context=homelab-okf-v1`. It is a
compact LLM-wiki / OKF-style briefing generated from the homelab repository and
repo audit. It is not vector RAG and it does not contain live secrets. Scenario
context remains authoritative for incident-specific facts.

# Topology

- The homelab is a single-node MicroK8s cluster on `home.hont.ro` /
	`192.168.1.201`, managed from the `homelab` repo by Flux and Kustomize.
- `home-ai.hont.ro` / `192.168.1.200` is a separate Ansible-managed CPU inference
	node. It is not part of the Kubernetes cluster.
- The NAS exports `nas.hont.ro:/complete`. The host mount `/media/nas` is for ops
	tools; Kubernetes workloads should use `nas-complete-pvc`, not `hostPath:
	/media/nas`.

# GitOps And Change Control

- Durable cluster changes go through git under `clusters/home/` and app manifests
	under `apps/`; Flux reconciles the `main` branch.
- Avoid manual `kubectl apply`, `edit`, or live deployment patches for permanent
	fixes. They create drift and can be reverted by Flux.
- Default-deny NetworkPolicy is expected. If DNS resolves but pod-to-pod traffic
	times out, suspect a missing allow policy under `clusters/home/policies/`.

# Ingress, DNS, And TLS

- Web UIs use Traefik with `*.hont.ro` hostnames and Let's Encrypt DNS-01 via
	Cloudflare. Public-facing apps can go through the Cloudflare Tunnel to Traefik.
- Internal media apps are often exposed by NodePort/LAN patterns. Do not assume a
	public ingress exists unless the manifest and route show it.
- A stale Cloudflare A record or split-horizon DNS mismatch can make a service work
	on LAN but fail from mobile/WAN while pods and Traefik remain healthy.

# Secrets And Identity

- Secret values must not be committed or printed. Safe references include secret
	names, paths, and the vault name `homelabkvp5jwiq`; unsafe material includes
	actual tokens, passwords, age private keys, Cloudflare API tokens, and OIDC
	client secrets.
- The intended secret path is SOPS/age plus Azure Key Vault and External Secrets
	Operator. Some host-local `.env` material exists as legacy configuration and
	should be treated as a redaction boundary.
- Authentik is the identity hub for user-facing apps. Forward-auth cutovers must
	be staged carefully and verified with an interactive sign-in.

# Storage And Backup

- Local app config and scratch live under `/mnt/internal_drive/{config,downloads,
	transcode}`. Media content lives under `/media/external_drive/complete` and is
	generally treated as replaceable media, not fully backed up.
- Restic backs up important host/app data; a backup is trustworthy only after a
	restore drill proves the right host, path, snapshot, and repository integrity.
- MicroK8s hostpath storage does not imply online expansion. High PVC usage should
	be handled with retention reduction, migration, or a storage-class change rather
	than assuming a live size bump will work.

# Observability And Operations

- Grafana, Loki, OTel collector, Netdata/node metrics, and Kubernetes status are
	the primary observation surfaces. CPU/pod health alone is necessary but not
	sufficient; prefer app-specific request/latency/log evidence when available.
- Homelab MCP tools are preferred over raw SSH when an equivalent read-only tool
	exists. The MCP server is read-only by default; mutating tools require explicit
	operator intent and auditability.
- Common high-signal failure patterns: CrashLoop/OOMKilled, ExternalSecret remote
	key missing while the store validates, SourceNotReady from a Flux GitRepository,
	stale DNS/A-record drift, missing NetworkPolicy, oversized recorder/history DBs,
	and container memory limits that are mistaken for node pressure.

# AI Node

- `home-ai.hont.ro` runs Ollama 0.30.8 on CPU-only hardware. The benchmark locks
	power/thermal state before canonical runs and stamps node/environment evidence
	into every result row.
- Current small-agent model guidance favors fast tool-reliable models such as
	`granite4:tiny-h` and fallback `granite4:micro`; large local models are not
	assumed to be better on this CPU node.

# Citations

[1] `/Users/dragoshont/Repo/homelab/copilot-instructions.md`
[2] `/Users/dragoshont/Repo/homelab/vault/knowledge/rules.md`
[3] `/Users/dragoshont/Repo/homelab/vault/knowledge/patterns.md`
[4] Read-only homelab repository audit, 2026-06-25.
