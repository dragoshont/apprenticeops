from helpers import LOCAL, PUBLIC, complete_pairing


def test_preflight_allowed_origin(client):
    r = client.options(
        "/v1/infer",
        headers={"origin": PUBLIC, "access-control-request-method": "POST"},
    )
    assert r.status_code == 204
    assert r.headers["access-control-allow-origin"] == PUBLIC
    assert "POST" in r.headers["access-control-allow-methods"]
    # credentials are never allowed
    assert "access-control-allow-credentials" not in {k.lower() for k in r.headers}


def test_preflight_denied_origin(client):
    r = client.options(
        "/v1/infer",
        headers={"origin": "https://evil.example", "access-control-request-method": "POST"},
    )
    assert r.status_code == 403


def test_capabilities_requires_token(client):
    r = client.get("/v1/capabilities", headers={"origin": PUBLIC})
    assert r.status_code == 401


def test_wrong_scope_forbidden(client):
    creds = complete_pairing(client, scopes=("experiment:execute",))  # no runner:read
    r = client.get(
        "/v1/capabilities",
        headers={"origin": PUBLIC, "x-ceops-token": creds["token"]},
    )
    assert r.status_code == 403


def test_public_origin_cannot_confirm(client):
    r = client.post(
        "/v1/pairing/request",
        headers={"origin": PUBLIC},
        json={"challenge": "d" * 32, "scopes": ["runner:read"], "client_version": "t"},
    )
    pairing_id = r.json()["pairing_id"]
    bad = client.post(f"/v1/pairing/{pairing_id}/confirm", headers={"origin": PUBLIC})
    assert bad.status_code == 403


def test_token_origin_binding(client):
    creds = complete_pairing(client)  # token bound to PUBLIC
    # presenting the token with a different (local) origin must fail closed
    r = client.get(
        "/v1/capabilities",
        headers={"origin": LOCAL, "x-ceops-token": creds["token"]},
    )
    assert r.status_code == 401
