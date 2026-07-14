from helpers import PUBLIC, complete_pairing


def test_infer_requires_token(client):
    r = client.post("/v1/infer", headers={"origin": PUBLIC}, json={"model": "x", "prompt": "y"})
    assert r.status_code == 401


def test_infer_requires_execute_scope(client):
    creds = complete_pairing(client, scopes=("runner:read",))
    r = client.post(
        "/v1/infer",
        headers={"origin": PUBLIC, "x-ceops-token": creds["token"]},
        json={"model": "x", "prompt": "y"},
    )
    assert r.status_code == 403


def test_infer_validates_body(client):
    creds = complete_pairing(client)
    r = client.post(
        "/v1/infer",
        headers={"origin": PUBLIC, "x-ceops-token": creds["token"]},
        json={"model": "", "prompt": "y"},
    )
    assert r.status_code == 400


def test_infer_really_calls_backend(client):
    # A valid, scoped, well-formed request whose only failure is that the
    # configured Ollama is unreachable must return an honest 502. This proves
    # there is no mock/fake path: the runner genuinely attempted the inference.
    creds = complete_pairing(client)
    r = client.post(
        "/v1/infer",
        headers={"origin": PUBLIC, "x-ceops-token": creds["token"]},
        json={"model": "qwen3:4b", "prompt": "hello"},
    )
    assert r.status_code == 502
    assert "ollama_unreachable" in str(r.json().get("detail", ""))
