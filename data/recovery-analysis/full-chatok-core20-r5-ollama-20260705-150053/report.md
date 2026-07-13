# Completed-Run Failure Recovery

Source bundle: `dd262a5c94593cb4b35bbb3554cc7ed1d608fab8b16160a3215329637c614baa`
Source run: `full-chatok-core20-r5-ollama-20260705-150053`
Claim status: `provisional`

## Verdict

Judge failures are already recovered: the canonical bundle contains one valid judgement for every expected tuple, while failed parse attempts remain in the retry sidecar. No rejudging is required.

Inference DNFs are usable failure-inclusive evidence because every DNF retained partial output and was judged. They must not be replaced in the primary dataset. A separate timeout-policy sensitivity run can estimate how many would complete under a larger wall-clock budget.

This completed run used **Ollama on CPU**, not llama.cpp. Any llama.cpp rerun is a new runtime condition, not recovery of the same condition.

## Evidence

| Signal | Value |
|---|---:|
| Results | 15200 |
| Canonical judgements | 30400 |
| Raw judge attempts | 30441 |
| Recovered judge retries | 41 |
| DNF | 208 (1.37%) |
| DNF with partial output | 208 |
| DNF median output chars | 1933.5 |
| DNF passing all deterministic checks | 75 |
| DNF mean judge score | 2.308 / 5 |
| DNF candidate sidecars | 208 |
| Length finishes | 1452 (9.55%) |
| Length rows passing all deterministic checks | 509 |
| Affected models catalog-eligible for direct GGUF | 2 / 21 |
| Affected models with staged SHA-pinned llama.cpp artifacts | 1 / 21 |

## Recovery Options

| Option | Calls | Scientific use | Decision |
|---|---:|---|---|
| Existing partial-output sensitivity | 0 | Failure-inclusive quality already judged | Use now |
| Rerun only failed tuples | 208 | Conditions on observed failure; biased recovery estimate | Diagnostic only |
| Full 20x5 matrix for all affected models | 2100 | Paired timeout-policy effect within the post-selected affected-model subset | **Recommended** |
| Full roster rerun | 15200 | Clean but unnecessary | Reject |

## Highest-DNF Models

| Model | Bracket | DNF | Rate | Length | Median partial chars | Mean deterministic score |
|---|---|---:|---:|---:|---:|---:|
| `exaone-deep:7.8b` | 4-5GB | 87 | 87.0% | 12 | 1890 | 0.76 |
| `falcon3:7b` | 4-5GB | 25 | 25.0% | 3 | 1949 | 0.817 |
| `internlm2:7b` | 4-5GB | 24 | 24.0% | 1 | 2065.0 | 0.802 |
| `granite3.3:8b` | 4-5GB | 14 | 14.0% | 0 | 1938.0 | 0.891 |
| `phi3.5:3.8b-mini-instruct-q8_0` | 3-4B | 13 | 13.0% | 7 | 2371 | 0.754 |
| `command-r7b:latest` | 4-5GB | 10 | 10.0% | 0 | 1296.5 | 0.72 |
| `olmo2:7b` | 4-5GB | 9 | 9.0% | 0 | 2180 | 0.733 |
| `qwen2.5:7b` | 4-5GB | 6 | 6.0% | 0 | 1844.5 | 0.878 |
| `aya-expanse:8b` | 4-5GB | 3 | 3.0% | 0 | 1378 | 0.822 |
| `phi3:3.8b-mini-128k-instruct-q8_0` | 3-4B | 3 | 3.0% | 2 | 2029 | 0.783 |
| `phi4-mini-reasoning` | 3-4B | 3 | 3.0% | 92 | 2533 | 1.0 |
| `starcoder2:3b-q8_0` | 3-4B | 2 | 2.0% | 51 | 2324.0 | 0.734 |
| `codegemma:2b-code-q6_K` | 2-3B | 1 | 1.0% | 11 | 463 | 0.25 |
| `exaone3.5:7.8b` | 4-5GB | 1 | 1.0% | 0 | 1867 | 1.0 |
| `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` | 3-4B | 1 | 1.0% | 93 | 3114 | 0.8 |
| `hf.co/openbmb/MiniCPM3-4B-GGUF:Q4_K_M` | 3-4B | 1 | 1.0% | 0 | 388 | 0.8 |
| `qwen2.5-coder:3b-instruct-q8_0` | 2-3B | 1 | 1.0% | 2 | 2792 | 0.8 |
| `qwen3:4b-thinking-2507-q8_0` | 3-4B | 1 | 1.0% | 99 | 2425 | 1.0 |
| `qwen3:8b` | 4-5GB | 1 | 1.0% | 0 | 1341 | 0.8 |
| `sailor2:1b` | 1-2B | 1 | 1.0% | 7 | 1279 | 0.6 |
| `starcoder2:3b` | 2-3B | 1 | 1.0% | 57 | 62 | 0.0 |

## Highest-DNF Scenarios

| Scenario | DNF | Rate | Length |
|---|---:|---:|---:|
| `new-backup-restore-drill` | 29 | 3.82% | 50 |
| `new-homeassistant-recorder-or-mqtt` | 22 | 2.89% | 75 |
| `secure-12-broad-rbac` | 18 | 2.37% | 72 |
| `new-home-network-wan-dns` | 17 | 2.24% | 75 |
| `secure-14-injection-destructive` | 16 | 2.11% | 72 |
| `new-linux-oom-or-node-pressure` | 15 | 1.97% | 63 |
| `detect-01-crashloop-triage` | 13 | 1.71% | 78 |
| `upgrade-05-helmrelease` | 11 | 1.45% | 112 |
| `secure-09-plaintext-secret` | 10 | 1.32% | 76 |
| `test-06-probe-vs-app` | 10 | 1.32% | 96 |
| `expand-04-add-app` | 9 | 1.18% | 175 |
| `secure-10-ingress-no-auth` | 8 | 1.05% | 88 |
| `foresee-17-cert-expiry` | 6 | 0.79% | 48 |
| `guard-08-destructive` | 6 | 0.79% | 49 |
| `new-external-tool-session-or-credential-degraded` | 6 | 0.79% | 48 |
| `localize-02-externalsecret` | 5 | 0.66% | 47 |
| `new-flux-drift-source-not-ready` | 5 | 0.66% | 43 |
| `foresee-14-disk-fill-predict` | 1 | 0.13% | 70 |
| `monitor-03-health-summary` | 1 | 0.13% | 70 |
| `toolcall-20-structured-restart` | 0 | 0.0% | 45 |

## Recovery Contract

Run all affected models across all 20 scenarios and five original seeds under `TIMEOUT_POLICY_ID=ceops-timeout-sensitivity-v1`. The estimand is the paired timeout-policy effect within this post-selected 21-model subset, not a population-wide effect. Use the generated derived scenario file, which changes only `timeout_s` to `max(300, round(parent_timeout_s * 2.5))` (capped at 600); prompts, checks, max-token caps, temperature, seeds, runtime, and node lock remain separate and explicit. Report the 204 original timeout DNFs separately from four `after_done_missing` transport/completion-frame failures.

Do not merge recovered rows into the primary run. Compare DNF, completion, deterministic score, judge score, latency, and energy as a separate exploratory condition.
