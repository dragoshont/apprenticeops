"""Real end-to-end inference test against a live Ollama.

Skipped unless ``CEOPS_IT_OLLAMA_URL`` is set. There is no mock: this drives the
full pairing ceremony and a genuine ``/v1/infer`` generation.

    CEOPS_IT_OLLAMA_URL=http://192.168.1.200:11434 \
    CEOPS_IT_MODEL=qwen3:4b-instruct-2507-q4_K_M \
    pytest tests/test_integration_ollama.py -v
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from ceops_runner.app import create_app
from ceops_runner.config import RunnerConfig

from helpers import BASE_URL, PUBLIC, complete_pairing

OLLAMA_URL = os.environ.get("CEOPS_IT_OLLAMA_URL")
MODEL = os.environ.get("CEOPS_IT_MODEL", "qwen3:4b-instruct-2507-q4_K_M")


@pytest.mark.skipif(
    not OLLAMA_URL,
    reason="set CEOPS_IT_OLLAMA_URL to run the real inference integration test",
)
def test_real_inference_end_to_end():
    cfg = RunnerConfig.from_env(
        {
            "CEOPS_RUNNER_BIND": "127.0.0.1",
            "CEOPS_RUNNER_PORT": "8799",
            "CEOPS_OLLAMA_URL": OLLAMA_URL,
            "CEOPS_ALLOWED_ORIGINS": PUBLIC,
            "CEOPS_RUNNER_INSTANCE_ID": "integration",
        }
    )
    client = TestClient(create_app(cfg), base_url=BASE_URL)

    creds = complete_pairing(client)
    r = client.post(
        "/v1/infer",
        headers={"origin": PUBLIC, "x-ceops-token": creds["token"]},
        json={
            "model": MODEL,
            "prompt": "Reply with exactly the single word: pong",
            "options": {"num_predict": 16},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["response"].strip(), "expected a non-empty model response"
    assert body["eval_count"] and body["eval_count"] > 0
