# Privacy And Egress

Status: active publication-safety note, created 2026-07-03.

## Boundary

ApprenticeOps has two separate data-flow claims:

1. **System-under-test inference is local.** During graded inference, the tested
   model calls local Ollama only. It does not call Claude, GPT, GitHub Models,
   Azure AI, web search, or any external model API.
2. **Judging is eval-time egress.** `judge.py` sends scenario text and model
   answers to an off-node frontier judge. This is grading scaffolding, not a
   runtime dependency, but it is still data egress and must be disclosed.

Do not collapse these into a single "offline" claim. The deployed apprentice is
locally sovereign; the evaluation judge is not.

## What May Be Public

The repository intentionally contains scrubbed or synthetic operational shapes:

- scenario contexts, gold answers, deterministic checks, and judge rubrics;
- public examples of homelab-style systems such as Kubernetes, Flux, Traefik,
  Cloudflare, and Azure Key Vault;
- synthetic sentinel strings such as `EXAMPLE_BEARER_TOKEN_DO_NOT_USE`.

These are not automatically secrets, but they are publication disclosures. They
should stay documented and should not be expanded with raw private logs.

## What Must Not Be Public

- real API keys, OAuth tokens, bearer tokens, cookies, private keys, SSH keys;
- raw medical/personal/journal data;
- unpublished credentials, account identifiers, or secret material;
- raw private logs copied from live services without sanitization;
- model outputs that include any of the above.

## Gate

Run before sharing, release, or submission:

```bash
python3 scripts/privacy-scan.py
```

The scan fails on live-looking secret patterns and reports disclosure counts for
known infrastructure terms. It streams every released `data/raw` and locked
`data/completed-runs` plain, gzip, and tar text artifact without extracting
archives. An unreadable or corrupt released archive fails the scan rather than
being skipped. Ellipsis-only PEM examples
(`BEGIN ...`, `...`, `END ...`) are treated as synthetic placeholders; any
non-placeholder private-key body fails. To inspect examples:

```bash
python3 scripts/privacy-scan.py --show-disclosures
```

Disclosure findings are not automatic failures because this benchmark is about a
real homelab. They are prompts for human review: decide whether the term is
intentional public context, should be generalized, or should be removed.

## Current Known Disclosure Classes

- `*.home.domain` and related local hostnames in historical scenario text;
- `*.hont.ro` service names in operational docs or session history;
- private RFC1918 IP examples;
- Azure Key Vault and Cloudflare references.

These should be reviewed before a public thesis package. The right outcome may be
"intentionally public and documented," not always redaction.