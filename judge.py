#!/usr/bin/env python3
"""
judge.py — frontier reference + LLM-as-judge (off-node, stdlib only).

Two backends (JUDGE_BACKEND):
  copilot    — the official GitHub Copilot CLI (`npm i -g @github/copilot`), the
               supported "Copilot SDK" path. Drives `claude-opus-4.8` (Claude
               4.8 Max, CONFIRMED live 2026-06-16) and gpt-5.5 etc. through the
               account's Copilot subscription — NO Anthropic key, NO GitHub
               Models. Auth is whatever the CLI already has (keychain). Note:
               batch judging consumes Copilot AI Credits (measured ~7.7/call for
               claude-opus-4.8 via the CLI, dominated by the cached system/tool
               context). judge.py now PARSES the footer's Tokens/AI-Credits line
               (cache read = 'cached', cache write = 'written') and records exact
               per-call billing into judged.jsonl + a cost summary.
  github     — GitHub Models, OpenAI-compatible (GITHUB_TOKEN, PAT models:read).
               VERIFIED 2026-06-16 via `gh models list`: GitHub Models hosts NO
               Anthropic/Claude models (only openai/meta/microsoft/mistral/
               cohere/deepseek), so the strongest judge here is openai/gpt-5 or
               o3 — NOT Claude.
  anthropic  — Anthropic API (ANTHROPIC_API_KEY) — alternative Claude path if you
               have a key instead of Copilot.

    # discover the EXACT judge model id for your backend, then exit:
    JUDGE_BACKEND=copilot   python3 judge.py --list-models     # finds claude-opus-4.8
    JUDGE_BACKEND=anthropic ANTHROPIC_API_KEY=... python3 judge.py --list-models
    JUDGE_BACKEND=github    GITHUB_TOKEN=...       python3 judge.py --list-models

    export JUDGE_BACKEND=copilot JUDGE_MODEL=claude-opus-4.8
    python3 judge.py --reference --scenarios scenarios.json --out reference.jsonl
    python3 judge.py --judge     --results results.jsonl   --out judged.jsonl
    # ensemble (bias control, 2nd family): adds a second judge per answer
    python3 judge.py --judge --ensemble copilot:gpt-5.5 --results r.jsonl --out judged.jsonl

The judge/reference is EVAL SCAFFOLDING — the small local model under test never
calls it. It runs on the Mac, never the node, so offline/breakglass purity holds.
Bias controls (MT-Bench/AlpacaEval, see MARKET.md): blind to author, must cite
evidence, grades vs frozen gold+rubric, 1-5; hand-validate a κ subset.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

GITHUB_ENDPOINT = os.environ.get("GITHUB_MODELS_ENDPOINT", "https://models.github.ai/inference")
GITHUB_CATALOG = os.environ.get("GITHUB_MODELS_CATALOG", "https://models.github.ai/catalog/models")
ANTHROPIC_ENDPOINT = os.environ.get("ANTHROPIC_ENDPOINT", "https://api.anthropic.com")
ANTHROPIC_VERSION = os.environ.get("ANTHROPIC_VERSION", "2023-06-01")
COPILOT_BIN = os.environ.get("COPILOT_BIN", "copilot")
# Defaults are env-overridable; confirm copilot ids via --list-models.
DEFAULT_MODEL = {"copilot": "claude-opus-4.8", "github": "openai/gpt-5",
                 "anthropic": "claude-opus-4-8"}
BACKENDS = ("copilot", "github", "anthropic")
_FOOTER_RE = re.compile(r"^(Changes|AI Credits|Tokens)\b")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _http_json(url, *, headers, data=None, timeout=180, method=None):
    req = urllib.request.Request(
        url, data=(json.dumps(data).encode() if data is not None else None),
        headers=headers, method=method or ("POST" if data is not None else "GET"))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


class Judge:
    """Backend-agnostic frontier client. backend in {github, anthropic}."""

    def __init__(self, backend=None, model=None):
        self.backend = (backend or os.environ.get("JUDGE_BACKEND", "copilot")).lower()
        if self.backend not in BACKENDS:
            sys.exit(f"unknown JUDGE_BACKEND={self.backend!r} (use one of {BACKENDS})")
        self.model = model or os.environ.get("JUDGE_MODEL") or DEFAULT_MODEL[self.backend]
        self._tok = None
        self.last_usage = None   # token / credit / cache billing of the most recent call
        if self.backend == "github":
            self._tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
            if not self._tok:
                sys.exit("set GITHUB_TOKEN (PAT with models:read). NOTE: GitHub Models has NO "
                         "Claude — use JUDGE_BACKEND=copilot for Claude 4.8.")
        elif self.backend == "anthropic":
            self._tok = os.environ.get("ANTHROPIC_API_KEY")
            if not self._tok:
                sys.exit("set ANTHROPIC_API_KEY for the Anthropic Claude judge.")
        else:  # copilot
            self._bin = shutil.which(COPILOT_BIN) or COPILOT_BIN
            if not shutil.which(COPILOT_BIN):
                sys.exit("Copilot CLI not found. Install: npm i -g @github/copilot, then `copilot` "
                         "once to authenticate.")

    def list_models(self):
        """Return [(id, label)] of judge models available on this backend."""
        if self.backend == "copilot":
            # the CLI caches the ids it has accepted under ~/.copilot; harvest them.
            ids = set()
            root = os.path.expanduser("~/.copilot")
            for dp, _, fns in os.walk(root):
                for fn in fns:
                    try:
                        with open(os.path.join(dp, fn), "rb") as fh:
                            blob = fh.read().decode("utf-8", "ignore")
                    except OSError:
                        continue
                    for m in re.findall(r'"model"\s*:\s*"([^"]+)"', blob):
                        ids.add(m)
            return sorted((i, "copilot") for i in ids)
        if self.backend == "github":
            data = _http_json(GITHUB_CATALOG, headers={
                "Authorization": f"Bearer {self._tok}", "Accept": "application/json"})
            items = data if isinstance(data, list) else data.get("data", data.get("models", []))
            return [(m.get("id") or m.get("name"),
                     m.get("publisher") or m.get("vendor") or "") for m in items]
        data = _http_json(f"{ANTHROPIC_ENDPOINT}/v1/models", headers={
            "x-api-key": self._tok, "anthropic-version": ANTHROPIC_VERSION})
        return [(m.get("id"), m.get("display_name", "")) for m in data.get("data", [])]

    @staticmethod
    def _strip_copilot_footer(out):
        lines = [_ANSI_RE.sub("", ln) for ln in (out or "").splitlines()]
        while lines and (not lines[-1].strip() or _FOOTER_RE.match(lines[-1].strip())):
            lines.pop()
        return "\n".join(lines).strip()

    @staticmethod
    def _parse_copilot_footer(out):
        """Billing from the Copilot CLI footer (the lines we otherwise drop), e.g.
            AI Credits 7.69 (6s)
            Tokens     ↑ 27.6k (16.7k cached, 11.0k written) • ↓ 4
        'cached' = prompt-cache READ (a hit), 'written' = cache CREATION (a miss)."""
        def _n(s):
            s = s.strip().lower().replace(",", "")
            mult = 1
            if s.endswith("k"):
                mult, s = 1000, s[:-1]
            elif s.endswith("m"):
                mult, s = 1_000_000, s[:-1]
            try:
                return int(float(s) * mult)
            except ValueError:
                return None
        u = {}
        for ln in (out or "").splitlines():
            ln = _ANSI_RE.sub("", ln).strip()
            m = re.match(r"AI Credits\s+([\d.]+)", ln)
            if m:
                u["ai_credits"] = float(m.group(1))
            if ln.startswith("Tokens"):
                for key, pat in (("tokens_in", r"\u2191\s*([\d.,km]+)"),
                                 ("tokens_out", r"\u2193\s*([\d.,km]+)"),
                                 ("cache_read", r"([\d.,km]+)\s*cached"),
                                 ("cache_write", r"([\d.,km]+)\s*written")):
                    mm = re.search(pat, ln, re.I)
                    if mm:
                        u[key] = _n(mm.group(1))
        return u or None

    @staticmethod
    def _norm_usage(u):
        """Normalize an OpenAI/Anthropic usage object to the same keys as the
        Copilot footer (tokens_in/out, cache_read/write). Anthropic splits cache
        read vs creation; OpenAI reports only cached (read)."""
        if not u:
            return None
        det = u.get("prompt_tokens_details") or {}
        out = {
            "tokens_in": u.get("prompt_tokens", u.get("input_tokens")),
            "tokens_out": u.get("completion_tokens", u.get("output_tokens")),
            "cache_read": u.get("cache_read_input_tokens", det.get("cached_tokens")),
            "cache_write": u.get("cache_creation_input_tokens"),
        }
        return {k: v for k, v in out.items() if v is not None} or None

    def complete(self, system, user, *, json_mode=False, temperature=0):
        if self.backend == "copilot":
            prompt = f"{system}\n\n{user}"
            env = {**os.environ, "COPILOT_ALLOW_ALL": "1"}
            p = subprocess.run(
                [self._bin, "--model", self.model, "--no-color", "--allow-all-tools",
                 "-p", prompt],
                capture_output=True, text=True, timeout=300, env=env)
            if p.returncode != 0 and not p.stdout.strip():
                raise RuntimeError(f"copilot CLI failed: {p.stderr.strip()[:200]}")
            self.last_usage = self._parse_copilot_footer(p.stdout)
            return self._strip_copilot_footer(p.stdout)
        if self.backend == "github":
            body = {"model": self.model, "temperature": temperature,
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": user}]}
            if json_mode:
                body["response_format"] = {"type": "json_object"}
            d = _http_json(f"{GITHUB_ENDPOINT}/chat/completions", headers={
                "Authorization": f"Bearer {self._tok}", "Content-Type": "application/json"}, data=body)
            self.last_usage = self._norm_usage(d.get("usage"))
            return d["choices"][0]["message"]["content"]
        # anthropic messages API (stdlib HTTP — no SDK dependency)
        body = {"model": self.model, "max_tokens": 1024, "temperature": temperature,
                "system": system, "messages": [{"role": "user", "content": user}]}
        d = _http_json(f"{ANTHROPIC_ENDPOINT}/v1/messages", headers={
            "x-api-key": self._tok, "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json"}, data=body)
        self.last_usage = self._norm_usage(d.get("usage"))
        return "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")


JUDGE_SYS = (
    "You are a strict, fair evaluator of homelab operations answers. "
    "You are given the CONTEXT an assistant saw, the TASK, a GOLD reference "
    "answer, a RUBRIC, and the assistant's ANSWER. Score the ANSWER 1-5:\n"
    "5=matches gold intent, correct + actionable + safe; 3=partially correct or "
    "missing a key point; 1=wrong, unsafe, or non-responsive.\n"
    "You MUST cite the specific evidence from CONTEXT that justifies your score. "
    "Judge correctness and safety, NOT verbosity or style. If the rubric names a "
    "HARD FAIL condition and the answer meets it, score 1.\n"
    'Reply as JSON: {"score": <1-5>, "evidence": "<quote/why>", "verdict": "<one line>", '
    '"criteria_met": ["<rubric points the answer satisfied>"], '
    '"criteria_missed": ["<rubric points the answer missed>"]}'
)


def judge_one(judge, scen, answer):
    user = (f"--- CONTEXT ---\n{scen['context']}\n\n--- TASK ---\n{scen['question']}\n\n"
            f"--- GOLD REFERENCE ---\n{scen['gold_answer']}\n\n"
            f"--- RUBRIC ---\n{scen['judge_rubric']}\n\n"
            f"--- ANSWER (author hidden) ---\n{answer}\n\n"
            "Score now as the specified JSON.")
    raw = judge.complete(JUDGE_SYS, user, json_mode=True)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        m = re.search(r"\{.*\}", raw or "", re.S)  # tolerate prose-wrapped JSON (anthropic)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return {"score": None, "evidence": "parse_error", "verdict": (raw or "")[:200]}


def reference_one(judge, scen):
    user = (f"--- CONTEXT ---\n{scen['context']}\n\n--- TASK ---\n{scen['question']}\n\n"
            "Answer as the ideal homelab operator would: correct, concise, actionable, safe.")
    return judge.complete("You are an expert homelab SRE.", user)


GOLD_REVIEW_SYS = (
    "You are an ADVERSARIAL reviewer of a benchmark's gold answers and scoring "
    "(option-C de-biasing). Given the CONTEXT, TASK, the PROPOSED GOLD answer, the "
    "RUBRIC, and the DETERMINISTIC CHECKS, find anything wrong: a gold that is "
    "factually wrong, incomplete, or over-specified; a rubric that rewards the wrong "
    "thing; or deterministic checks that are gameable, too loose, or too strict "
    "(would pass a wrong answer or fail a correct one). Be skeptical, specific, and "
    "concise. If the gold and scoring are sound, say so.\n"
    'Reply as JSON: {"agree": true|false, "severity": "none|minor|major", '
    '"issues": ["..."], "suggested_fix": "..."}'
)


def gold_review_one(judge, scen):
    checks = "\n".join(
        f"- {c['type']}: {c.get('desc', '')} "
        f"{c.get('patterns', c.get('value', c.get('allowed', '')))}"
        for c in scen.get("deterministic_checks", []))
    user = (f"--- CONTEXT ---\n{scen['context']}\n\n--- TASK ---\n{scen['question']}\n\n"
            f"--- PROPOSED GOLD ---\n{scen['gold_answer']}\n\n"
            f"--- RUBRIC ---\n{scen['judge_rubric']}\n\n"
            f"--- DETERMINISTIC CHECKS ---\n{checks}\n\nReview now as the specified JSON.")
    raw = judge.complete(GOLD_REVIEW_SYS, user, json_mode=True)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        m = re.search(r"\{.*\}", raw or "", re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return {"agree": None, "severity": "parse_error", "issues": [(raw or "")[:200]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default="data/scenarios.json")
    ap.add_argument("--results", default="results.jsonl")
    ap.add_argument("--out")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--reference", action="store_true")
    ap.add_argument("--gold-review", action="store_true",
                    help="frontier adversarially reviews every gold+rubric+checks "
                         "(option-C); writes a disagreement list to --out for you to adjudicate")
    ap.add_argument("--list-models", action="store_true",
                    help="list judge models on the selected backend (find the Claude id), then exit")
    ap.add_argument("--backend", help="copilot | github | anthropic (overrides JUDGE_BACKEND)")
    ap.add_argument("--model", help="judge model id (overrides JUDGE_MODEL)")
    ap.add_argument("--ensemble",
                    help="comma list of extra judges as backend:model for bias control, "
                         "e.g. 'copilot:gpt-5.5'. Each answer is scored by every judge.")
    ap.add_argument("--outputs-dir", default="outputs", help="where run.py wrote model answers")
    ap.add_argument("--workers", type=int, default=int(os.environ.get("JUDGE_WORKERS", "8")),
                    help="parallel judge calls (default 8 = the Copilot-CLI concurrency ceiling; "
                         "set 1 for serial). Each call is an independent Copilot agent.")
    args = ap.parse_args()
    primary = Judge(backend=args.backend, model=args.model)
    judges = [primary]
    if args.ensemble:
        for spec in args.ensemble.split(","):
            spec = spec.strip()
            if not spec:
                continue
            be, _, mo = spec.partition(":")
            judges.append(Judge(backend=be or None, model=mo or None))

    if args.list_models:
        for mid, who in sorted(primary.list_models(), key=lambda x: (x[0] or "")):
            tag = "   <-- CLAUDE" if "claude" in (mid or "").lower() else ""
            print(f"{mid}\t{who}{tag}")
        return

    scen_path = args.scenarios
    scen_sha = hashlib.sha256(open(scen_path, "rb").read()).hexdigest()
    scen = {s["id"]: s for s in json.load(open(scen_path))["scenarios"]}

    if args.reference:
        if not args.out:
            sys.exit("--reference needs --out")
        with open(args.out, "w") as f:
            for sid, s in scen.items():
                ans = reference_one(primary, s)
                f.write(json.dumps({"scenario": sid, "frontier_model": primary.model,
                                    "reference_answer": ans}) + "\n")
                sys.stderr.write(f"ref {sid} done\n")
        return

    if args.gold_review:
        if not args.out:
            sys.exit("--gold-review needs --out")
        flagged = 0
        with open(args.out, "w") as f:
            for sid, s in scen.items():
                r = gold_review_one(primary, s)
                bad = (r.get("agree") is False) or (r.get("severity") in ("minor", "major"))
                flagged += bool(bad)
                f.write(json.dumps({"scenario": sid, "judge_model": primary.model, **r}) + "\n")
                sys.stderr.write(f"review {sid}: agree={r.get('agree')} sev={r.get('severity')}\n")
        sys.stderr.write(f"\n{flagged}/{len(scen)} scenario(s) flagged for your "
                         f"adjudication. See {args.out}.\n")
        return

    if args.judge:
        if not args.out:
            sys.exit("--judge needs --out")
        memory_context_by_unit = {}
        # resume: skip (model, scenario, rep, memory_context, judge_model) already
        # written to --out, so paired no-memory/memory runs can be judged together
        # without one condition suppressing the other.
        # so a long ensemble run that dies (sleep/network) continues instead of
        # re-judging from scratch. Output is opened in APPEND mode.
        done = set()
        if os.path.exists(args.out):
            for line in open(args.out):
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                done.add((d.get("model"), d.get("scenario"), str(d.get("rep")),
                          d.get("memory_context") or "none", d.get("judge_model")))
            if done:
                sys.stderr.write(f"resume: {len(done)} judged rows already in {args.out}; skipping them\n")
        cost = {"calls": 0, "ai_credits": 0.0, "tokens_in": 0, "tokens_out": 0,
                "cache_read": 0, "cache_write": 0}
        # Build the task list (one per pending model x judge), then run them through a
        # bounded pool. 8 parallel Copilot agents is the historical ceiling before the
        # CLI rate-limits (docs/CONSOLIDATION-PLAN.md). Each task builds its OWN Judge
        # so the per-call `last_usage` is never shared across threads.
        specs = [(jg.backend, jg.model) for jg in judges]
        tasks = []
        for line in open(args.results):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue  # tolerate a partial last line (mid-rsync snapshot)
            sid = row.get("scenario")
            if not sid or sid not in scen:
                continue
            row_sha = row.get("env.scenarios_sha")
            if row_sha != scen_sha:
                sys.stderr.write(f"skip {row.get('model')} {sid}: result scenario hash {row_sha!r} != selected {scen_sha[:12]}…\n")
                continue
            rep = row.get("rep", 0)
            memory_context = row.get("env.memory_context") or "none"
            memory_context_by_unit[(row["model"], sid, str(rep), memory_context)] = memory_context
            if all((row["model"], sid, str(rep), memory_context, mo) in done for _, mo in specs):
                continue
            base = f"{row['model'].replace('/', '_').replace(':', '_')}__{sid}"
            answer = row.get("gen_ai.completion") or ""
            if not answer:
                # run.py suffixes __r{rep} only when repeats>1; try both. This is
                # legacy fallback only; embedded completions avoid filename
                # collisions when concatenating memory/no-memory twin runs.
                for cand in (f"{base}__r{rep}.txt", f"{base}.txt"):
                    fp = os.path.join(args.outputs_dir, cand)
                    if os.path.exists(fp):
                        answer = open(fp).read()
                        break
            for be, mo in specs:
                if (row["model"], sid, str(rep), memory_context, mo) in done:
                    continue
                tasks.append((row["model"], sid, rep, memory_context, answer, be, mo))

        def _judge_task(t):
            model, sid, rep, memory_context, answer, be, mo = t
            if not answer:
                return (model, sid, rep, memory_context, be, mo, {"score": 1, "verdict": "empty"}, None)
            jg = Judge(backend=be, model=mo)   # fresh per task -> thread-safe usage
            for attempt in range(4):
                try:
                    j = judge_one(jg, scen[sid], answer)
                    return (model, sid, rep, memory_context, be, mo, j, jg.last_usage)
                except Exception as e:  # noqa: BLE001
                    if attempt == 3:
                        sys.stderr.write(f"judge[{mo}] {model} {sid} r{rep} "
                                         f"SKIP after 4 tries: {str(e)[:120]}\n")
                    else:
                        time.sleep(5 * (attempt + 1))
            return None  # leave unjudged; a resume pass re-judges it

        workers = max(1, args.workers)
        sys.stderr.write(f"judging {len(tasks)} (answer x judge) calls, {workers}-wide\n")
        # single writer (the main thread) -> no lock needed; write as each completes.
        with open(args.out, "a") as f, cf.ThreadPoolExecutor(max_workers=workers) as ex:
            for fut in cf.as_completed([ex.submit(_judge_task, t) for t in tasks]):
                res = fut.result()
                if res is None:
                    continue
                model, sid, rep, memory_context, be, mo, j, u = res
                if u:
                    cost["calls"] += 1
                    for k in ("ai_credits", "tokens_in", "tokens_out", "cache_read", "cache_write"):
                        cost[k] += u.get(k) or 0
                memory_context = memory_context_by_unit.get((model, sid, str(rep), memory_context), memory_context)
                f.write(json.dumps({"model": model, "scenario": sid, "rep": rep,
                                    "memory_context": memory_context,
                                    "scenarios_path": scen_path,
                                    "scenarios_sha256": scen_sha,
                                    "judge_backend": be, "judge_model": mo,
                                    "usage": u, **j}) + "\n")
                f.flush()
                sys.stderr.write(f"judge[{mo}] {model} {sid} r{rep} -> {j.get('score')}\n")
        ci = cost["tokens_in"]
        hit = round(100 * cost["cache_read"] / ci, 1) if ci else None
        sys.stderr.write(
            f"\n== judge cost: {cost['calls']} calls · {cost['ai_credits']:.1f} AI credits · "
            f"in={ci} out={cost['tokens_out']} · cache_read={cost['cache_read']} "
            f"({hit}% of input cached) · cache_write={cost['cache_write']} ==\n")
        return

    sys.exit("pass --judge, --reference, or --list-models")


if __name__ == "__main__":
    main()
