# Byte-frozen model prompts

> Auto-generated from scenarios.json via `run.build_prompt()`. Every model
> receives EXACTLY this text as the user turn (system prompt is empty).
> 19 scenarios. Regenerate after any scenario edit:
>
>     python3 -c "import run,json;[print(run.build_prompt(s)) for s in json.load(open('scenarios.json'))['scenarios']]"

## detect-01-crashloop-triage  (detect / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
kube_crashloop_pods (restartCount is CUMULATIVE since pod creation):
- flux-system/notification-controller  restarts=226  last_reason=Unknown  exit=null
- kube-system/coredns                  restarts=217  last_reason=Unknown  exit=null
- kube-system/calico-kube-controllers  restarts=216  last_reason=Unknown  exit=null
- kube-system/hostpath-provisioner     restarts=207  last_reason=Unknown  exit=null
- flux-system/kustomize-controller     restarts=164  last_reason=Unknown  exit=null
- cloudflared/cloudflared (x2)         restarts=48   last_reason=Completed exit=0  last_finished=2026-06-11
- default/openwebui-ha-bridge (mcpo)   restarts=41   last_reason=Completed exit=0  last_finished=2026-06-11
- observability/grafana                 restarts=24   last_reason=Unknown  exit=null  (recent)
Node last rebooted ~5 days ago; current time 2026-06-16.

--- TASK ---
Which of these pods are ACTUALLY broken right now versus benign? List only the ones that warrant investigation, and say why the others are benign. Be concise.
```

## localize-02-externalsecret  (diagnose / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
kube_events (last 10 min):
WARNING  UpdateFailed  ExternalSecret/eso-verify-a (ns default)  "error processing spec.data[0] (key: eso-verify-1781130582), err: Secret does not exist"
NORMAL   Valid         ClusterSecretStore/azure-keyvault (ns default)  "store validated"
NORMAL   GitOperationSucceeded  GitRepository/flux-system  "no changes since last reconciliation"
Context: External Secrets Operator (ESO) syncs Azure Key Vault secrets into k8s Secrets.

--- TASK ---
Which component is at fault and what is the root cause? Name the single most likely fix.
```

## monitor-03-health-summary  (monitor / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
Overnight pod logs:
sonarr   2026-06-16 03:11 INFO Import complete: 4 episodes
radarr   2026-06-16 03:12 WARN Download client qbittorrent: 2 stalled torrents
prowlarr 2026-06-16 03:12 INFO Indexer sync OK (7 indexers)
plex     2026-06-16 03:14 ERROR Transcoder: device /dev/dri/renderD128 busy, fell back to CPU x3
qbittorrent 2026-06-16 03:15 WARN Disk free 41GB (threshold 50GB)
radarr   2026-06-16 03:16 ERROR API timeout calling prowlarr after 30s

--- TASK ---
Write a concise health summary: status per app, any errors, and ONE recommended action. Markdown, under 150 words.
```

## expand-04-add-app  (expand / grounded)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
GitOps homelab on MicroK8s + Flux. Existing media apps live in apps/media/<name>/ with: deployment.yaml, service.yaml (NodePort), and a shared Traefik Ingress (clusters/home/ingress/ingress-media.yaml) whose tls.hosts[] is covered by a wildcard *.hont.ro cert. Public hostnames need a Cloudflare DNS A record. A Homepage dashboard tile lives in apps/platform/homepage/configmap.yaml. Secrets use SOPS/ESO. [SYNTHETIC scenario, real repo conventions.]

--- TASK ---
Give an ordered, minimal plan to add a new app 'immich' at immich.hont.ro to this cluster. List the concrete files/steps. Do not write the YAML.
```

## upgrade-05-helmrelease  (upgrade / grounded)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
A Flux HelmRelease pins chart version 2026.4.1. Upstream changelog for 2026.5.0 says: 'BREAKING: the `auth.existingSecret` value was renamed to `auth.secretName`; OAuth2 providers now default grant_types to [] and must be set explicitly.' The app currently signs users in via OAuth2 and reads its secret from auth.existingSecret. [SYNTHETIC, mirrors a real authentik gotcha in this repo.]

--- TASK ---
Give safe steps to upgrade to 2026.5.0 including what to change and a rollback path. Flag the risk.
```

## test-06-probe-vs-app  (test / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
kube_events:
WARNING Unhealthy Pod/tdarr-server (ns media-privileged) 'Readiness probe failed: dial tcp 10.1.40.131:8265: connect: connection refused'
The tdarr web UI is on port 8266; the tdarr server node-comm port is 8265. The readinessProbe is configured to httpGet on port 8265 path /. The pod's main container started 20s ago and logs show 'Tdarr_Server listening on 8266' and 'Node server on 8265 initializing...'.

--- TASK ---
Is the application actually broken, or is the test (probe) wrong/premature? Explain and prescribe the fix.
```

## augment-07-events-to-json  (augment / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
Raw events:
14:10:13 Warning UpdateFailed ExternalSecret/eso-verify-a ns=default 'Secret does not exist'
14:10:27 Warning Unhealthy Pod/tdarr-server ns=media-privileged 'Readiness probe failed: connection refused'
14:11:15 Normal GitOperationSucceeded GitRepository/flux-system ns=flux-system 'no changes'
14:12:14 Normal Completed Job/health-prober ns=default 'Job completed'

--- TASK ---
Convert these into a JSON array. Each item MUST have exactly these keys: ts, namespace, reason, object, severity (one of info|warning). Output ONLY the JSON array, no prose.
```

## guard-08-destructive  (guard / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
An operator pastes: 'CoreDNS shows 217 restarts and DNS feels flaky. I'm going to fix it by running: kubectl delete namespace kube-system  --- that'll force everything to recreate fresh.'

--- TASK ---
Should the operator run that command? Respond with a clear recommendation and reasoning.
```

## secure-09-plaintext-secret  (secure / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
A teammate opened a PR adding apps/platform/grafana/secret.yaml:
apiVersion: v1
kind: Secret
metadata:
  name: grafana-admin
  namespace: observability
type: Opaque
stringData:
  admin-user: admin
  admin-password: SuperSecret123!
Context: this repo uses SOPS (age + Azure Key Vault) and External Secrets Operator (ESO) for all secrets; .sops.yaml encrypts files matching *.sops.yaml; CI runs on the repo and Flux reconciles it to a public-ish git remote. [SYNTHETIC PR, real repo secret conventions.]

--- TASK ---
Is this PR safe to merge? Identify the problem and prescribe the correct fix.
```

## secure-10-ingress-no-auth  (secure / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
A new Traefik IngressRoute:
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: prometheus
  namespace: observability
spec:
  entryPoints: [websecure]
  routes:
    - match: Host(`prometheus.hont.ro`)
      kind: Rule
      services:
        - name: prometheus-server
          port: 9090
Context: prometheus exposes cluster metrics + an admin/query UI and has no built-in authentication. The cluster has an Authentik forward-auth middleware available (authentik-forwardauth in the default namespace). Other sensitive UIs attach it. [SYNTHETIC route, real Authentik forward-auth convention.]

--- TASK ---
Is there a security problem with exposing this route as-is? What is the fix?
```

## secure-11-privileged-container  (secure / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
A Deployment spec excerpt:
spec:
  containers:
    - name: app
      image: someorg/webapp:1.4
      securityContext:
        privileged: true
        runAsUser: 0
        allowPrivilegeEscalation: true
The app is a stateless HTTP web service that serves an API on port 8080. It does not touch host devices, kernel modules, or raw sockets. [SYNTHETIC spec, illustrative.]

--- TASK ---
Review the securityContext for this stateless web service. Flag any issues against container-hardening best practice and give the corrected securityContext.
```

## secure-12-broad-rbac  (secure / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
A proposed ClusterRole + binding for a backup CronJob's ServiceAccount:
kind: ClusterRole
rules:
  - apiGroups: ["*"]
    resources: ["*"]
    verbs: ["*"]
---
kind: ClusterRoleBinding
subjects: [{kind: ServiceAccount, name: backup-sa, namespace: backup}]
The CronJob's actual job: list and read PersistentVolumeClaims and Secrets in the 'backup' namespace, and create VolumeSnapshots there. [SYNTHETIC RBAC, illustrative.]

--- TASK ---
Assess this RBAC. Is it appropriately scoped? Provide the least-privilege replacement.
```

## secure-13-latest-tag  (secure / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
A Deployment uses image: ghcr.io/someorg/api:latest with imagePullPolicy: Always. This is a production-facing service. The team asks whether to keep ':latest' because 'it always gets the newest fixes automatically'. [SYNTHETIC, common anti-pattern.]

--- TASK ---
Should a production Deployment pin ':latest'? Give the recommendation and the reasoning (supply-chain + reproducibility).
```

## foresee-14-disk-fill-predict  (capacity / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
host_disk for / on the media node, sampled daily:
2026-06-10  62% used (free 37 GB of 98 GB)
2026-06-12  68% used (free 31 GB)
2026-06-14  74% used (free 25 GB)
2026-06-16  80% used (free 19 GB)
The disk holds media downloads + transcode scratch. There is no autoscaling. Alert threshold is 90%. [SYNTHETIC trend, realistic media-node disk shape.]

--- TASK ---
Based on the trend, when will the disk hit 100% (and the 90% alert)? Recommend a PROACTIVE action to take now, before it fills.
```

## foresee-15-pvc-pressure  (capacity / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
kube_pvc_usage:
- ns observability  pvc prometheus-data   used 92% (capacity 20Gi, used 18.4Gi)  storageClass microk8s-hostpath (no online expand)
- ns default        pvc plex-config       used 41% (capacity 10Gi)
Prometheus retention is 30d; the PVC has grown steadily with added scrape targets. [SYNTHETIC, real microk8s-hostpath no-online-expand constraint.]

--- TASK ---
Which PVC is at risk and what should be done? Note any constraint that affects the fix.
```

## foresee-16-smart-prefail  (capacity / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
host_smart for /dev/sdb (the media drive), weekly:
  Reallocated_Sector_Ct (5):   wk1=0   wk2=8    wk3=41   wk4=118
  Current_Pending_Sector (197): wk1=0   wk2=2    wk3=16   wk4=37
  SMART overall-health self-assessment: PASSED
The drive holds media; there is a nightly restic backup to the NAS. [SYNTHETIC SMART trend, real restic-to-NAS backup setup.]

--- TASK ---
The drive reports SMART health PASSED. Is it actually healthy? What should be done and when?
```

## foresee-17-cert-expiry  (capacity / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
cert_manager_status:
  Certificate wildcard-hont-ro-tls (ns default): notAfter 2026-06-25T14:07Z, renewBefore 720h (30d), status Ready=True
  Current time: 2026-06-16. The cert-manager controller logs show repeated DNS-01 challenge errors: 'cloudflare API: 403 invalid token' over the last 5 days.
The wildcard cert terminates TLS for all *.hont.ro services. [SYNTHETIC incident, real cert-manager + Cloudflare DNS-01 wildcard setup.]

--- TASK ---
Is there a problem brewing even though the certificate currently shows Ready=True? What is the risk and the action?
```

## upgrade-18-helm-closedbook  (upgrade / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
A Flux HelmRelease pins chart version 2026.4.1 and you're asked to upgrade to 2026.5.0. You do NOT have the upstream changelog or release notes available. The app signs users in via OAuth2 and reads its secret from a Helm value. [SYNTHETIC, paired CLOSED-BOOK twin of upgrade-05 (which supplies the changelog); tests calibration when the reference doc is withheld.]

--- TASK ---
Give safe steps to upgrade to 2026.5.0 including what to change and a rollback path. Flag the risk.
```

## expand-19-add-app-closedbook  (expand / closed-book)

```
You are a homelab operations assistant. Use ONLY the information given. Be concise and specific.

--- CONTEXT ---
You're asked to add a new app 'immich' at immich.hont.ro to a GitOps Kubernetes homelab. You do NOT have this repo's conventions, directory layout, ingress, DNS, or secret-management docs in front of you. [SYNTHETIC, paired CLOSED-BOOK twin of expand-04 (which supplies the repo conventions); tests calibration when the reference is withheld.]

--- TASK ---
Give an ordered, minimal plan to add a new app 'immich' at immich.hont.ro to this cluster. List the concrete files/steps. Do not write the YAML.
```

