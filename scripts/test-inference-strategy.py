#!/usr/bin/env python3
"""Regression tests for inference_strategy execution helpers."""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import run  # noqa: E402


class Sampler:
    abort_reason = None


def fake_tel(text: str, seed: int, finish: str = "stop") -> dict:
    return {
        "gen_ai.request.model": "fake-model",
        "gen_ai.operation.name": "chat",
        "gen_ai.request.max_tokens": 64,
        "gen_ai.request.temperature": 0.7,
        "gen_ai.request.seed": seed,
        "gen_ai.usage.input_tokens": 10,
        "gen_ai.usage.output_tokens": max(1, len(text.split())),
        "gen_ai.usage.output_chars": len(text),
        "gen_ai.response.finish_reasons": [finish],
        "gen_ai.server.time_to_first_token_s": 0.1,
        "phase.prefill_s": 0.1,
        "phase.decode_s": 0.2,
        "prefill_tok_s": 100.0,
        "decode_tok_s": 10.0,
        "wall_s": 1.0,
        "dnf": finish.startswith("DNF"),
        "progress_trace": [[0.1, len(text)]],
        "_text": text,
        "_think": "",
    }


def patch_run_chat(responses):
    calls = []
    original = run.run_chat

    def fake_run_chat(model, system, user, *, max_tokens, timeout_s, stall_s, think, sampler, temperature=0, seed=None):
        index = len(calls)
        calls.append({"seed": seed, "user": user})
        return fake_tel(responses[index], seed or 0)

    run.run_chat = fake_run_chat
    return original, calls


def restore_run_chat(original):
    run.run_chat = original


def scenario():
    return {
        "id": "s1",
        "context": "A pod needs a safe restart plan.",
        "question": "What should the operator do?",
        "deterministic_checks": [
            {"type": "any_include", "patterns": ["restart safely"], "desc": "safe restart"},
            {"type": "any_include", "patterns": ["verify"], "desc": "verify"},
        ],
    }


def policy():
    return {"max_tokens": 64, "timeout_s": 30, "stall_s": 10, "timeout_policy_id": "test", "policy_reasons": ["test"]}


def test_best_of_3_detcheck_selects_best_candidate():
    original, calls = patch_run_chat([
        "restart",
        "restart safely",
        "restart safely and verify",
    ])
    try:
        tel, candidates = run.run_strategy(
            "fake", scenario(), "PROMPT", memory_context="", memory_context_id="none",
            strategy_id="best_of_3_detcheck", strategy_prompt="", policy=policy(),
            think=False, sampler=Sampler(), temperature=0.7, seed=1,
        )
    finally:
        restore_run_chat(original)
    assert len(calls) == 3, calls
    assert tel["strategy.id"] == "best_of_3_detcheck"
    assert tel["strategy.candidate_count"] == 3
    assert tel["strategy.selected_candidate"] == 2
    assert tel["strategy.extra_calls"] == 2
    assert tel["_text"] == "restart safely and verify"
    assert candidates[2]["selected"] is True
    assert candidates[2]["det_passed"] == 2
    assert candidates[2]["completion"] == "restart safely and verify"


def test_single_call_tournament_brief_injects_strategy_prompt():
    original, calls = patch_run_chat(["restart safely and verify"])
    try:
        tel, candidates = run.run_strategy(
            "fake", scenario(), "PROMPT", memory_context="", memory_context_id="none",
            strategy_id="single_call_tournament_brief", strategy_prompt="consider options", policy=policy(),
            think=False, sampler=Sampler(), temperature=0.7, seed=2,
        )
    finally:
        restore_run_chat(original)
    assert len(calls) == 1
    assert "--- RESPONSE STRATEGY ---" in calls[0]["user"]
    assert "consider options" in calls[0]["user"]
    assert tel["strategy.id"] == "single_call_tournament_brief"
    assert candidates[0]["selected"] is True


def test_prompt_policy_metadata_helpers():
    s = scenario()
    prompt = run.build_prompt(s, "abc")
    diag = run.prompt_diagnostics(s, "abc", prompt)
    assert diag["prompt.memory_char_count"] == 3
    assert diag["prompt.estimated_tokens"] > 0
    resolved = run.resolve_policy(s, model="qwen3:4b-instruct-2507-q4_K_M", memory_context_id="homelab-okf-v1", strategy_id="best_of_3_detcheck")
    assert resolved["timeout_s"] > run.DEFAULT_TIMEOUT_S
    assert "memory_context" in resolved["policy_reasons"]
    assert "known_slow_model" in resolved["policy_reasons"]


def main() -> None:
    test_best_of_3_detcheck_selects_best_candidate()
    test_single_call_tournament_brief_injects_strategy_prompt()
    test_prompt_policy_metadata_helpers()
    print("inference strategy tests passed")


if __name__ == "__main__":
    main()
