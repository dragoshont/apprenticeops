from helpers import PUBLIC


def test_pairing_request_is_capped(client):
    """An unauthenticated flood of pairing requests must be bounded (DoS guard)."""
    last = None
    for i in range(70):  # AuthStore.MAX_PENDING_PAIRINGS == 64
        last = client.post(
            "/v1/pairing/request",
            headers={"origin": PUBLIC},
            json={"challenge": f"{i:032d}", "scopes": ["runner:read"], "client_version": "t"},
        )
    assert last.status_code == 429
