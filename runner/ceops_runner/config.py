"""Runtime configuration for the CEOps runner.

All values come from the environment so the same package is portable across a
laptop (loopback only) and an opt-in LAN bind on a workstation. The runner
refuses to bind a non-private address (fail-closed), and derives the exact
`Host` authority allowlist and CORS origin allowlist that the security layer
enforces on every request.
"""

from __future__ import annotations

import ipaddress
import os
import secrets
from dataclasses import dataclass


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def is_private_bind(host: str) -> bool:
    """True if `host` is loopback, RFC1918 private, or link-local.

    The runner will not bind anything else. `0.0.0.0`/`::` are rejected on
    purpose: a wildcard bind hides which interface is actually exposed.
    """
    if host in ("127.0.0.1", "::1", "localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if ip.is_unspecified:  # 0.0.0.0 / ::
        return False
    return ip.is_loopback or ip.is_private or ip.is_link_local


def _authority(host: str, port: int) -> str:
    # IPv6 hosts use bracketed authority form in the Host header.
    if ":" in host and not host.startswith("["):
        return f"[{host}]:{port}"
    return f"{host}:{port}"


@dataclass(frozen=True)
class RunnerConfig:
    bind_host: str
    port: int
    ollama_url: str
    allowed_origins: frozenset[str]
    local_origins: frozenset[str]
    host_allowlist: frozenset[str]
    instance_id: str
    lan_bound: bool
    api_version: str = "0.1.0"
    runner_version: str = "0.1.0"
    pairing_ttl_seconds: int = 120
    token_ttl_seconds: int = 12 * 3600
    inference_timeout_seconds: float = 300.0
    local_admin_token: str | None = None
    local_admin_file: str = ""

    @staticmethod
    def from_env(env: dict[str, str] | None = None) -> "RunnerConfig":
        env = dict(os.environ if env is None else env)
        bind_host = env.get("CEOPS_RUNNER_BIND", "127.0.0.1").strip()
        port = int(env.get("CEOPS_RUNNER_PORT", "8799"))

        if not is_private_bind(bind_host):
            raise SystemExit(
                f"CEOps runner refuses to bind non-private address {bind_host!r}. "
                "Bind loopback (127.0.0.1) or a specific private/link-local LAN "
                "address only."
            )

        ollama_url = env.get("CEOPS_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")

        lan_bound = bind_host not in ("127.0.0.1", "::1", "localhost")

        # Exact Host authorities the runner will answer to. Loopback authorities
        # are always accepted (the local approval curl uses them); the LAN
        # authority is added only when explicitly LAN-bound.
        authorities = {f"127.0.0.1:{port}", f"[::1]:{port}"}
        if lan_bound:
            authorities.add(_authority(bind_host, port))
        for extra in _parse_csv(env.get("CEOPS_RUNNER_HOST_ALLOW", "")):
            authorities.add(extra)

        # Same-origin local-UI origins (the runner-served console). These are the
        # only origins allowed to reach the local approval endpoint.
        local_origins = {f"http://127.0.0.1:{port}"}
        if lan_bound:
            local_origins.add(f"http://{bind_host}:{port}")

        # Public console origins allowed via CORS. Local-UI origins are added so
        # the same console works whether it is served by the runner or hosted.
        public_origins = _parse_csv(
            env.get("CEOPS_ALLOWED_ORIGINS", "https://experiment.ceops.org")
        )
        allowed_origins = set(public_origins) | local_origins

        instance_id = env.get("CEOPS_RUNNER_INSTANCE_ID") or secrets.token_hex(8)
        local_admin_token = env.get("CEOPS_LOCAL_ADMIN_TOKEN") or None
        local_admin_file = env.get("CEOPS_LOCAL_ADMIN_FILE") or os.path.join(
            os.path.expanduser("~"), ".ceops-runner", "local-admin.token"
        )

        return RunnerConfig(
            bind_host=bind_host,
            port=port,
            ollama_url=ollama_url,
            allowed_origins=frozenset(allowed_origins),
            local_origins=frozenset(local_origins),
            host_allowlist=frozenset(authorities),
            instance_id=instance_id,
            lan_bound=lan_bound,
            local_admin_token=local_admin_token,
            local_admin_file=local_admin_file,
        )
