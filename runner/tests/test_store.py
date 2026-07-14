import time

import pytest

from ceops_runner.security import AuthStore


def _pair(store, origin="https://experiment.ceops.org", scopes=("runner:read",)):
    return store.create_pairing("x" * 20, origin, list(scopes))


def test_confirm_and_single_retrieval():
    store = AuthStore(120, 3600)
    pairing = _pair(store)
    assert pairing.status == "pending"
    store.confirm_pairing(pairing.pairing_id)
    token = store.retrieve_token(pairing.pairing_id, "x" * 20)
    assert token.origin == "https://experiment.ceops.org"
    with pytest.raises(LookupError):  # second read never returns the token
        store.retrieve_token(pairing.pairing_id, "x" * 20)


def test_challenge_mismatch_is_rejected():
    store = AuthStore(120, 3600)
    pairing = _pair(store)
    store.confirm_pairing(pairing.pairing_id)
    with pytest.raises(PermissionError):
        store.retrieve_token(pairing.pairing_id, "y" * 20)


def test_pairing_expiry_blocks_confirm():
    store = AuthStore(0, 3600)  # immediate expiry
    pairing = _pair(store)
    time.sleep(0.02)
    with pytest.raises(ValueError):
        store.confirm_pairing(pairing.pairing_id)


def test_token_validation_and_origin_binding():
    store = AuthStore(120, 3600)
    pairing = _pair(store)
    store.confirm_pairing(pairing.pairing_id)
    token = store.retrieve_token(pairing.pairing_id, "x" * 20)
    assert store.validate_token(token.value, "https://experiment.ceops.org") is not None
    assert store.validate_token(token.value, "https://other.example") is None
    assert store.validate_token("not-a-token", "https://experiment.ceops.org") is None
    store.revoke_token(token.value)
    assert store.validate_token(token.value, "https://experiment.ceops.org") is None


def test_unknown_scope_rejected():
    store = AuthStore(120, 3600)
    with pytest.raises(ValueError):
        store.create_pairing("x" * 20, "https://o.example", ["bogus:scope"])


def test_failed_challenge_reads_deny_pairing():
    store = AuthStore(120, 3600)
    pairing = _pair(store)
    store.confirm_pairing(pairing.pairing_id)
    for _ in range(AuthStore.MAX_FAILED_READS):
        with pytest.raises(PermissionError):
            store.retrieve_token(pairing.pairing_id, "wrong-challenge-value")
    # the pairing is now denied; even the correct challenge yields no token
    assert store.get_pairing(pairing.pairing_id).status == "denied"
    with pytest.raises(LookupError):
        store.retrieve_token(pairing.pairing_id, "x" * 20)


def test_short_challenge_rejected():
    store = AuthStore(120, 3600)
    with pytest.raises(ValueError):
        store.create_pairing("short", "https://o.example", ["runner:read"])
