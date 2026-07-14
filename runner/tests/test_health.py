from helpers import PUBLIC


def test_health_ok(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["instance_id"] == "test-instance"
    assert body["pairing_ready"] is True
    assert r.headers["cache-control"] == "no-store"


def test_health_rejects_foreign_host(client):
    r = client.get("/v1/health", headers={"host": "evil.example.com"})
    assert r.status_code == 421


def test_health_cors_for_allowed_origin(client):
    r = client.get("/v1/health", headers={"origin": PUBLIC})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == PUBLIC
    assert r.headers["vary"] == "Origin"


def test_console_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "CEOps experiment runner" in r.text
    assert "content-security-policy" in {k.lower() for k in r.headers}
