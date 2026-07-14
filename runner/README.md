# CEOps runner

A loopback-first, user-owned experiment runner. A browser-delivered console pairs
with it (token + exact-`Host` + exact-`Origin` CORS) and executes **real** model
inference against a locally reachable Ollama. No central account, no hosted result
custody, no mock inference path.

This is the Phase-2/3 spike of `docs/sdd/ceops-browser-runner.md` — a genuinely
working vertical slice (health, capabilities, pairing ceremony, single-retrieval
tokens, real `/v1/infer`), not the full product surface.

## Install

```bash
cd runner
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
```

## Run

Loopback (default, same machine):

```bash
ceops-runner                      # binds 127.0.0.1:8799, talks to http://127.0.0.1:11434
```

Opt-in LAN bind (drive from another machine on the same LAN — prints an exposure
warning; requires the same pairing token):

```bash
ceops-runner --bind 192.168.1.200 --allow-origin https://experiment.ceops.org
```

The runner **refuses to bind** anything that is not loopback or a private /
link-local address (fail closed). `0.0.0.0` is rejected on purpose.

## Pairing (how a console gets a token)

1. The console `POST`s `/v1/pairing/request` (its origin must be allow-listed).
2. The runner prints the pairing id + confirmation phrase on **its own host**.
3. A person approves on the runner host — `POST /v1/pairing/{id}/confirm`
   (loopback / local-UI origin only; the public console can never self-approve).
4. The console retrieves the origin-bound token **once** via a
   challenge-authenticated `GET /v1/pairing/{id}`.
5. The token lives in browser memory only and is required (with the right scope)
   on every non-health route. A runner restart invalidates all tokens.

## API

| Route | Auth |
|---|---|
| `GET /v1/health` | none (minimal fields) |
| `GET /v1/capabilities`, `GET /v1/models` | token `runner:read` |
| `POST /v1/pairing/request` | allow-listed public origin |
| `GET /v1/pairing/{id}` | challenge header, single token retrieval |
| `POST /v1/pairing/{id}/confirm` \| `/deny` | local origin / loopback only |
| `GET /v1/pairing/pending/list` | local origin / loopback only |
| `POST /v1/infer` | token `experiment:execute` (real Ollama generation) |
| `POST /v1/pairings/current/revoke` | current token |

The runner also serves its own console at `/` (the all-browser, Safari/offline
path). The same `static/` console is what deploys to `experiment.ceops.org`.

## Test

```bash
pip install -e '.[dev]'
pytest                                            # unit tests: no Ollama needed

# real inference against a live Ollama (no mocks):
CEOPS_IT_OLLAMA_URL=http://192.168.1.200:11434 \
CEOPS_IT_MODEL=qwen3:4b-instruct-2507-q4_K_M \
pytest tests/test_integration_ollama.py -v
```

## Configuration

| Env | Default | Meaning |
|---|---|---|
| `CEOPS_RUNNER_BIND` | `127.0.0.1` | bind address (loopback or private only) |
| `CEOPS_RUNNER_PORT` | `8799` | listen port |
| `CEOPS_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama backend |
| `CEOPS_ALLOWED_ORIGINS` | `https://experiment.ceops.org` | comma-separated console origins |
| `CEOPS_RUNNER_HOST_ALLOW` | — | extra exact `Host` authorities |
| `CEOPS_RUNNER_INSTANCE_ID` | random | stable id across restarts if set |
