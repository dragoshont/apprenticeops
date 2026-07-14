"""Authorization state and helpers for the runner.

Implements the real controls the SDD requires as the authorization boundary:

* an in-memory, single-use **pairing** ceremony (no persistence, no browser
  storage) that mints an origin-bound, scoped bearer **token** only after a
  local confirmation on the runner host;
* single-retrieval token delivery (a second read returns nothing);
* exact `Host` authority checks (DNS-rebinding defense) and exact `Origin`
  allow-listing.

All state is process-local and lost on restart, which is the intended
"re-pair after a runner restart" behavior.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field

KNOWN_SCOPES: frozenset[str] = frozenset(
    {
        "runner:read",
        "experiment:prepare",
        "experiment:execute",
        "experiment:control",
        "experiment:cancel",
        "artifact:export",
        "artifact:import",
        "artifact:verify",
        "artifact:delete",
    }
)

_PHRASE_ADJECTIVES = (
    "amber", "brisk", "cobalt", "dawn", "ember", "fern",
    "granite", "harbor", "ivory", "juniper", "kelp", "larch",
)
_PHRASE_NOUNS = (
    "otter", "cedar", "quartz", "meadow", "falcon", "harbor",
    "willow", "cobble", "lantern", "beacon", "thistle", "marlin",
)


def make_confirm_phrase() -> str:
    a = secrets.choice(_PHRASE_ADJECTIVES)
    n = secrets.choice(_PHRASE_NOUNS)
    num = secrets.randbelow(90) + 10
    return f"{a}-{n}-{num}"


def validate_scopes(scopes: list[str]) -> list[str]:
    """Return the requested scopes if all are known; raise otherwise."""
    unknown = [s for s in scopes if s not in KNOWN_SCOPES]
    if unknown:
        raise ValueError(f"unknown scopes: {', '.join(sorted(unknown))}")
    if not scopes:
        raise ValueError("at least one scope is required")
    return scopes


class PairingLimitError(RuntimeError):
    """Raised when too many pending pairings exist (rate/DoS guard)."""


@dataclass
class Token:
    value: str
    origin: str
    scopes: tuple[str, ...]
    pairing_id: str
    expires_at: float

    def active(self, now: float | None = None) -> bool:
        return (now or time.time()) < self.expires_at


@dataclass
class Pairing:
    pairing_id: str
    challenge: str
    origin: str
    scopes: tuple[str, ...]
    confirm_phrase: str
    created_at: float
    expires_at: float
    status: str = "pending"  # pending | confirmed | denied | expired
    token: Token | None = None
    token_retrieved: bool = False
    failed_reads: int = 0

    def expired(self, now: float | None = None) -> bool:
        return (now or time.time()) >= self.expires_at


class AuthStore:
    """Thread-safe in-memory pairing/token store (single runner process)."""

    MAX_PENDING_PAIRINGS = 64
    MAX_FAILED_READS = 10
    RETENTION_SECONDS = 60

    def __init__(self, pairing_ttl: int, token_ttl: int) -> None:
        self._pairing_ttl = pairing_ttl
        self._token_ttl = token_ttl
        self._pairings: dict[str, Pairing] = {}
        self._tokens: dict[str, Token] = {}
        self._lock = threading.Lock()

    def _evict_locked(self, now: float) -> None:
        """Delete terminal/expired pairings past the retention window and dead
        tokens, so an unauthenticated caller cannot grow memory without bound."""
        drop = [
            pid
            for pid, p in self._pairings.items()
            if (p.expired(now) or p.status in ("denied", "expired", "confirmed"))
            and now - p.created_at > self.RETENTION_SECONDS
        ]
        for pid in drop:
            self._pairings.pop(pid, None)
        for value in [v for v, t in self._tokens.items() if not t.active(now)]:
            self._tokens.pop(value, None)

    # -- pairing ---------------------------------------------------------
    def create_pairing(self, challenge: str, origin: str, scopes: list[str]) -> Pairing:
        validate_scopes(scopes)
        if not challenge or len(challenge) < 16:
            raise ValueError("challenge must be a high-entropy string (>= 16 chars)")
        now = time.time()
        pairing = Pairing(
            pairing_id=secrets.token_urlsafe(12),
            challenge=challenge,
            origin=origin,
            scopes=tuple(scopes),
            confirm_phrase=make_confirm_phrase(),
            created_at=now,
            expires_at=now + self._pairing_ttl,
        )
        with self._lock:
            self._evict_locked(now)
            pending = sum(
                1 for p in self._pairings.values() if p.status == "pending" and not p.expired(now)
            )
            if pending >= self.MAX_PENDING_PAIRINGS:
                raise PairingLimitError("too many pending pairings; try again later")
            self._pairings[pairing.pairing_id] = pairing
        return pairing

    def get_pairing(self, pairing_id: str) -> Pairing | None:
        with self._lock:
            return self._pairings.get(pairing_id)

    def confirm_pairing(self, pairing_id: str) -> Pairing:
        """Locally confirm a pending pairing and mint its token."""
        now = time.time()
        with self._lock:
            pairing = self._pairings.get(pairing_id)
            if pairing is None:
                raise KeyError("unknown pairing")
            if pairing.status == "denied":
                raise ValueError("pairing already denied")
            if pairing.expired(now):
                pairing.status = "expired"
                raise ValueError("pairing expired")
            if pairing.status == "confirmed":
                return pairing
            token = Token(
                value=secrets.token_urlsafe(32),
                origin=pairing.origin,
                scopes=pairing.scopes,
                pairing_id=pairing.pairing_id,
                expires_at=now + self._token_ttl,
            )
            pairing.status = "confirmed"
            pairing.token = token
            self._tokens[token.value] = token
            return pairing

    def deny_pairing(self, pairing_id: str) -> None:
        with self._lock:
            pairing = self._pairings.get(pairing_id)
            if pairing is not None and pairing.status == "pending":
                pairing.status = "denied"

    def extend_pairing(self, pairing_id: str, seconds: int) -> Pairing:
        with self._lock:
            pairing = self._pairings.get(pairing_id)
            if pairing is None:
                raise KeyError("unknown pairing")
            if pairing.status != "pending":
                raise ValueError("only a pending pairing can be extended")
            pairing.expires_at = time.time() + seconds
            return pairing

    def retrieve_token(self, pairing_id: str, challenge: str) -> Token:
        """Return the minted token exactly once, gated by the challenge."""
        now = time.time()
        with self._lock:
            pairing = self._pairings.get(pairing_id)
            if pairing is None:
                raise KeyError("unknown pairing")
            if not secrets.compare_digest(pairing.challenge, challenge):
                pairing.failed_reads += 1
                if pairing.failed_reads >= self.MAX_FAILED_READS:
                    pairing.status = "denied"
                raise PermissionError("challenge mismatch")
            if pairing.status != "confirmed" or pairing.token is None:
                raise LookupError(pairing.status)
            if pairing.token_retrieved:
                raise LookupError("already_retrieved")
            if not pairing.token.active(now):
                raise LookupError("expired")
            pairing.token_retrieved = True
            return pairing.token

    # -- tokens ----------------------------------------------------------
    def validate_token(self, value: str | None, origin: str | None) -> Token | None:
        if not value:
            return None
        now = time.time()
        with self._lock:
            token = self._tokens.get(value)
            if token is None or not token.active(now):
                return None
            # Origin binding: a public request must present the origin the token
            # was paired with. (Same-origin GETs may omit Origin; callers that
            # require an origin enforce presence separately.)
            if origin is not None and not secrets.compare_digest(token.origin, origin):
                return None
            return token

    def revoke_token(self, value: str) -> bool:
        with self._lock:
            existed = value in self._tokens
            self._tokens.pop(value, None)
            for p in self._pairings.values():
                if p.token is not None and p.token.value == value:
                    p.status = "denied"
            return existed

    def purge_expired(self) -> None:
        now = time.time()
        with self._lock:
            for value in [v for v, t in self._tokens.items() if not t.active(now)]:
                self._tokens.pop(value, None)
            for pid in [
                p.pairing_id
                for p in self._pairings.values()
                if p.expired(now) and p.status == "pending"
            ]:
                self._pairings[pid].status = "expired"

    def pending_pairings(self) -> list["Pairing"]:
        """Pending, unexpired pairings for the runner-host local approval surface."""
        now = time.time()
        with self._lock:
            return [
                p
                for p in self._pairings.values()
                if p.status == "pending" and not p.expired(now)
            ]


def host_authority_allowed(host_header: str | None, allowlist: frozenset[str]) -> bool:
    """Exact `Host` authority match. Missing/foreign Host is rejected."""
    if not host_header:
        return False
    return host_header in allowlist
