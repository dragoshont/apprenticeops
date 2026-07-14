"""Shared test helpers and constants."""

from __future__ import annotations

from ceops_runner.config import RunnerConfig

PORT = 8799
PUBLIC = "https://experiment.ceops.org"
LOCAL = f"http://127.0.0.1:{PORT}"
BASE_URL = f"http://127.0.0.1:{PORT}"


def make_config(**env_over: str) -> RunnerConfig:
    env = {
        "CEOPS_RUNNER_BIND": "127.0.0.1",
        "CEOPS_RUNNER_PORT": str(PORT),
        # deliberately unreachable in unit tests; only the real integration test
        # points this at a live Ollama.
        "CEOPS_OLLAMA_URL": "http://127.0.0.1:59999",
        "CEOPS_ALLOWED_ORIGINS": PUBLIC,
        "CEOPS_RUNNER_INSTANCE_ID": "test-instance",
    }
    env.update(env_over)
    return RunnerConfig.from_env(env)


def complete_pairing(client, scopes=("runner:read", "experiment:execute")) -> dict:
    """Drive the real pairing ceremony end to end and return the issued token."""
    challenge = "c" * 32
    r = client.post(
        "/v1/pairing/request",
        headers={"origin": PUBLIC},
        json={"challenge": challenge, "scopes": list(scopes), "client_version": "test"},
    )
    assert r.status_code == 201, r.text
    pairing_id = r.json()["pairing_id"]
    # local-host approval (no Origin header == loopback caller)
    confirm = client.post(f"/v1/pairing/{pairing_id}/confirm")
    assert confirm.status_code == 200, confirm.text
    poll = client.get(
        f"/v1/pairing/{pairing_id}",
        headers={"X-CEOps-Pairing-Challenge": challenge},
    )
    assert poll.status_code == 200 and poll.json()["status"] == "confirmed", poll.text
    return {"token": poll.json()["token"], "challenge": challenge, "pairing_id": pairing_id}
