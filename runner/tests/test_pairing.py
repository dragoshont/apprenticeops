from helpers import ADMIN_HEADER, PUBLIC


def _request(client, challenge, scopes=("runner:read", "experiment:execute")):
    return client.post(
        "/v1/pairing/request",
        headers={"origin": PUBLIC},
        json={"challenge": challenge, "scopes": list(scopes), "client_version": "t"},
    )


def test_full_pairing_ceremony(client):
    challenge = "e" * 32
    r = _request(client, challenge)
    assert r.status_code == 201
    body = r.json()
    pairing_id = body["pairing_id"]
    assert body["confirm_phrase"]

    pending = client.get(f"/v1/pairing/{pairing_id}", headers={"X-CEOps-Pairing-Challenge": challenge})
    assert pending.json()["status"] == "pending"

    confirm = client.post(f"/v1/pairing/{pairing_id}/confirm", headers=ADMIN_HEADER)
    assert confirm.status_code == 200

    got = client.get(f"/v1/pairing/{pairing_id}", headers={"X-CEOps-Pairing-Challenge": challenge})
    assert got.json()["status"] == "confirmed"
    assert got.json()["token"]

    again = client.get(f"/v1/pairing/{pairing_id}", headers={"X-CEOps-Pairing-Challenge": challenge})
    assert not again.json().get("token")  # single retrieval


def test_challenge_required_on_poll(client):
    r = _request(client, "f" * 32)
    pairing_id = r.json()["pairing_id"]
    bad = client.get(f"/v1/pairing/{pairing_id}", headers={"X-CEOps-Pairing-Challenge": "w" * 32})
    assert bad.status_code == 403


def test_unknown_pairing_id(client):
    r = client.get("/v1/pairing/does-not-exist", headers={"X-CEOps-Pairing-Challenge": "z" * 32})
    assert r.status_code == 404


def test_pairing_request_requires_public_origin(client):
    r = client.post(
        "/v1/pairing/request",
        json={"challenge": "g" * 32, "scopes": ["runner:read"], "client_version": "t"},
    )
    assert r.status_code == 403  # no Origin header


def test_pending_list_requires_admin_secret(client):
    _request(client, "h" * 32)
    denied = client.get("/v1/pairing/pending/list")  # no secret
    assert denied.status_code == 403
    ok = client.get("/v1/pairing/pending/list", headers=ADMIN_HEADER)
    assert ok.status_code == 200
    assert len(ok.json()["pending"]) >= 1
