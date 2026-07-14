"""FastAPI application for the CEOps runner.

Security envelope enforced on every request (SDD 6.2/6.4/6.5/12):

* exact ``Host`` authority (rebinding defense) via middleware;
* exact ``Origin`` allow-listing with non-wildcard CORS and ``Vary: Origin``;
* preflight handled centrally; ``credentials`` are never allowed;
* ``Cache-Control: no-store`` on every response;
* pairing-token bearer auth with scope + origin binding on every non-health,
  non-pairing route;
* the local approval endpoints accept only same-origin local-UI or no-origin
  (loopback) callers -- the public console can never self-approve.

There is no mock path. ``/v1/infer`` performs a real Ollama generation; if Ollama
is unreachable the route returns an honest ``502`` rather than fabricating output.
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .config import RunnerConfig
from .ollama import OllamaClient, OllamaError
from .security import AuthStore, PairingLimitError, host_authority_allowed, validate_scopes

STATIC_DIR = Path(__file__).parent / "static"

_CORS_METHODS = "GET, POST, OPTIONS"
_CORS_HEADERS = "content-type, x-ceops-token, x-ceops-pairing-challenge"
_CONSOLE_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
    "form-action 'none'; frame-ancestors 'none'"
)


def _apply_cors(response: Response, origin: str) -> None:
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = _CORS_METHODS
    response.headers["Access-Control-Allow-Headers"] = _CORS_HEADERS
    response.headers["Access-Control-Max-Age"] = "600"


class GuardMiddleware(BaseHTTPMiddleware):
    """Host allowlist + CORS + no-store, applied before routing."""

    def __init__(self, app, config: RunnerConfig) -> None:
        super().__init__(app)
        self._config = config

    async def dispatch(self, request: Request, call_next):
        cfg = self._config
        host = request.headers.get("host")
        if not host_authority_allowed(host, cfg.host_allowlist):
            return JSONResponse(
                {"error": "host_not_allowed", "detail": "exact Host authority required"},
                status_code=421,
            )

        origin = request.headers.get("origin")
        origin_ok = origin is not None and origin in cfg.allowed_origins

        if request.method == "OPTIONS":
            if origin_ok:
                resp = Response(status_code=204)
                _apply_cors(resp, origin)  # type: ignore[arg-type]
                resp.headers["Cache-Control"] = "no-store"
                return resp
            return JSONResponse({"error": "origin_not_allowed"}, status_code=403)

        response = await call_next(request)
        if origin_ok:
            _apply_cors(response, origin)  # type: ignore[arg-type]
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


# -- authorization dependencies -----------------------------------------------


def _require_public_origin(request: Request) -> str:
    cfg: RunnerConfig = request.app.state.config
    origin = request.headers.get("origin")
    if not origin or origin not in cfg.allowed_origins:
        return _forbidden("origin_not_allowed")
    return origin


def _require_local_origin(request: Request) -> str | None:
    """Deprecated: retained only so nothing imports a missing symbol. The local
    approval surface is now gated by the host-side admin secret, not by Origin."""
    raise RuntimeError("local approval is gated by require_local_admin")


def _forbidden(detail: str):
    from fastapi import HTTPException

    raise HTTPException(status_code=403, detail=detail)


def require_token(scope: str):
    def dependency(request: Request):
        from fastapi import HTTPException

        cfg: RunnerConfig = request.app.state.config
        store: AuthStore = request.app.state.store
        origin = request.headers.get("origin")
        token_value = request.headers.get("x-ceops-token")
        token = store.validate_token(token_value, origin)
        if token is None:
            raise HTTPException(status_code=401, detail="invalid_or_missing_token")
        # Close the no-Origin bypass: a token minted for a public console origin
        # must always present that Origin. A token minted for an origin the runner
        # itself serves (its own Host authority, e.g. the runner-served local UI)
        # may omit Origin, since browsers drop it on same-origin GETs.
        if origin is None:
            authority = token.origin.split("://", 1)[-1]
            if authority not in cfg.host_allowlist and token.origin not in cfg.local_origins:
                raise HTTPException(status_code=401, detail="origin_required")
        if scope not in token.scopes:
            raise HTTPException(status_code=403, detail=f"missing_scope:{scope}")
        return token

    return dependency


def _write_admin_file(path: str, token: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, (token + "\n").encode())
    finally:
        os.close(fd)


def require_local_admin(request: Request) -> bool:
    """Gate the local approval surface on a host-only secret.

    The secret is generated at startup and written to a mode-0600 file readable
    only on the runner host (or provided via CEOPS_LOCAL_ADMIN_TOKEN). LAN
    reachability alone can never approve a pairing (SDD 6.3/6.7).
    """
    from fastapi import HTTPException

    provided = request.headers.get("x-ceops-local-admin", "")
    expected = getattr(request.app.state, "local_admin_token", "")
    if not provided or not expected or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="local_admin_required")
    return True


# -- application factory ------------------------------------------------------


def create_app(
    config: RunnerConfig | None = None,
    *,
    store: AuthStore | None = None,
    ollama: OllamaClient | None = None,
) -> FastAPI:
    cfg = config or RunnerConfig.from_env()
    auth = store or AuthStore(cfg.pairing_ttl_seconds, cfg.token_ttl_seconds)
    backend = ollama or OllamaClient(cfg.ollama_url, timeout=cfg.inference_timeout_seconds)

    app = FastAPI(
        title="CEOps Runner",
        version=cfg.runner_version,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.config = cfg
    app.state.store = auth
    app.state.ollama = backend
    app.state.local_admin_token = cfg.local_admin_token or secrets.token_urlsafe(32)
    if cfg.local_admin_token is None and cfg.local_admin_file:
        _write_admin_file(cfg.local_admin_file, app.state.local_admin_token)
    app.add_middleware(GuardMiddleware, config=cfg)

    _register_routes(app)
    return app


def _register_routes(app: FastAPI) -> None:
    from fastapi import Body, Header, HTTPException, Path as PathParam

    # -- console (runner-served local UI; also hostable verbatim) -------------

    def _console_response() -> HTMLResponse:
        index = STATIC_DIR / "index.html"
        html = index.read_text(encoding="utf-8")
        resp = HTMLResponse(html)
        resp.headers["Content-Security-Policy"] = _CONSOLE_CSP
        return resp

    @app.get("/", include_in_schema=False)
    def console() -> HTMLResponse:
        return _console_response()

    @app.get("/app.js", include_in_schema=False)
    def console_js() -> Response:
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        resp = Response(js, media_type="application/javascript")
        resp.headers["Content-Security-Policy"] = _CONSOLE_CSP
        return resp

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(status_code=204)

    # -- read-only ------------------------------------------------------------

    @app.get("/v1/health")
    def health(request: Request) -> JSONResponse:
        cfg: RunnerConfig = request.app.state.config
        return JSONResponse(
            {
                "status": "ok",
                "runner_version": cfg.runner_version,
                "api_version": cfg.api_version,
                "instance_id": cfg.instance_id,
                "pairing_ready": True,
                "lan_bound": cfg.lan_bound,
            }
        )

    @app.get("/v1/capabilities")
    async def capabilities(request: Request, token=Depends(require_token("runner:read"))) -> JSONResponse:
        cfg: RunnerConfig = request.app.state.config
        backend: OllamaClient = request.app.state.ollama
        try:
            ollama_version = await backend.version()
            models = await backend.tags()
        except OllamaError:
            raise HTTPException(status_code=502, detail="ollama_unreachable")
        return JSONResponse(
            {
                "runner_version": cfg.runner_version,
                "api_version": cfg.api_version,
                "instance_id": cfg.instance_id,
                "backend": {"kind": "ollama", "version": ollama_version},
                "models": [
                    {"name": m.get("name"), "size": m.get("size"), "family": (m.get("details") or {}).get("family")}
                    for m in models
                ],
                "pairing": {"origin": token.origin, "scopes": list(token.scopes), "expires_at": token.expires_at},
            }
        )

    @app.get("/v1/models")
    async def models(request: Request, token=Depends(require_token("runner:read"))) -> JSONResponse:
        backend: OllamaClient = request.app.state.ollama
        try:
            tags = await backend.tags()
        except OllamaError:
            raise HTTPException(status_code=502, detail="ollama_unreachable")
        return JSONResponse(
            {"models": [{"name": m.get("name"), "size": m.get("size")} for m in tags]}
        )

    # -- pairing --------------------------------------------------------------

    @app.post("/v1/pairing/request")
    def pairing_request(
        request: Request,
        origin: str = Depends(_require_public_origin),
        payload: dict[str, Any] = Body(...),
    ) -> JSONResponse:
        store: AuthStore = request.app.state.store
        challenge = str(payload.get("challenge", ""))
        scopes = payload.get("scopes") or []
        client_version = str(payload.get("client_version", "unknown"))
        if not isinstance(scopes, list):
            raise HTTPException(status_code=400, detail="scopes must be a list")
        try:
            validate_scopes([str(s) for s in scopes])
            pairing = store.create_pairing(challenge, origin, [str(s) for s in scopes])
        except PairingLimitError as exc:
            raise HTTPException(status_code=429, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        _announce_pairing(request, pairing)
        return JSONResponse(
            {
                "pairing_id": pairing.pairing_id,
                "confirm_phrase": pairing.confirm_phrase,
                "requested_scopes": list(pairing.scopes),
                "origin": pairing.origin,
                "expires_at": pairing.expires_at,
                "poll_after_seconds": 2,
            },
            status_code=201,
        )

    @app.get("/v1/pairing/{pairing_id}")
    def pairing_poll(
        request: Request,
        pairing_id: str = PathParam(...),
        challenge: str = Header(..., alias="X-CEOps-Pairing-Challenge"),
    ) -> JSONResponse:
        store: AuthStore = request.app.state.store
        try:
            token = store.retrieve_token(pairing_id, challenge)
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown_pairing")
        except PermissionError:
            raise HTTPException(status_code=403, detail="challenge_mismatch")
        except LookupError as exc:
            status = (exc.args[0] if exc.args else "pending") or "pending"
            return JSONResponse({"status": status})
        return JSONResponse(
            {
                "status": "confirmed",
                "token": token.value,
                "scopes": list(token.scopes),
                "expires_at": token.expires_at,
            }
        )

    @app.get("/v1/pairing/pending/list")
    def pairing_pending(request: Request, _admin=Depends(require_local_admin)) -> JSONResponse:
        """Local approval surface: pending pairings, gated by the host-side secret."""
        store: AuthStore = request.app.state.store
        store.purge_expired()
        pending = [
            {
                "pairing_id": p.pairing_id,
                "origin": p.origin,
                "scopes": list(p.scopes),
                "confirm_phrase": p.confirm_phrase,
                "expires_at": p.expires_at,
            }
            for p in store.pending_pairings()
        ]
        return JSONResponse({"pending": pending})

    @app.post("/v1/pairing/{pairing_id}/confirm")
    def pairing_confirm(
        request: Request,
        pairing_id: str = PathParam(...),
        _admin=Depends(require_local_admin),
    ) -> JSONResponse:
        store: AuthStore = request.app.state.store
        try:
            pairing = store.confirm_pairing(pairing_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown_pairing")
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return JSONResponse(
            {"status": pairing.status, "confirm_phrase": pairing.confirm_phrase, "scopes": list(pairing.scopes)}
        )

    @app.post("/v1/pairing/{pairing_id}/deny")
    def pairing_deny(
        request: Request,
        pairing_id: str = PathParam(...),
        _admin=Depends(require_local_admin),
    ) -> JSONResponse:
        store: AuthStore = request.app.state.store
        store.deny_pairing(pairing_id)
        return JSONResponse({"status": "denied"})

    @app.post("/v1/pairings/current/revoke")
    def revoke(request: Request, token=Depends(require_token("runner:read"))) -> JSONResponse:
        store: AuthStore = request.app.state.store
        store.revoke_token(token.value)
        return JSONResponse({"revoked": True})

    # -- inference ------------------------------------------------------------

    @app.post("/v1/infer")
    async def infer(
        request: Request,
        origin: str = Depends(_require_public_origin),
        token=Depends(require_token("experiment:execute")),
        payload: dict[str, Any] = Body(...),
    ) -> JSONResponse:
        backend: OllamaClient = request.app.state.ollama
        model = str(payload.get("model", "")).strip()
        prompt = payload.get("prompt")
        options = payload.get("options")
        if not model:
            raise HTTPException(status_code=400, detail="model is required")
        if not isinstance(prompt, str) or not prompt.strip():
            raise HTTPException(status_code=400, detail="prompt is required")
        if options is not None and not isinstance(options, dict):
            raise HTTPException(status_code=400, detail="options must be an object")

        try:
            available = await backend.model_names()
        except OllamaError:
            raise HTTPException(status_code=502, detail="ollama_unreachable")
        if model not in available:
            raise HTTPException(
                status_code=400,
                detail={"error": "unknown_model", "requested": model, "available": available},
            )

        try:
            result = await backend.generate(model, prompt, options)
        except OllamaError:
            raise HTTPException(status_code=502, detail="inference_failed")

        return JSONResponse(
            {
                "model": result.model,
                "response": result.response,
                "total_duration_ms": result.total_duration_ms,
                "eval_count": result.eval_count,
                "prompt_eval_count": result.prompt_eval_count,
                "tokens_per_second": result.tokens_per_second,
                "created_at": result.created_at,
                "done_reason": result.done_reason,
            }
        )


def _announce_pairing(request: Request, pairing) -> None:
    cfg: RunnerConfig = request.app.state.config
    authority = f"{cfg.bind_host}:{cfg.port}"
    admin_src = cfg.local_admin_file or "$CEOPS_LOCAL_ADMIN_TOKEN"
    lines = [
        "",
        "==================== CEOps pairing request ====================",
        f"  pairing id : {pairing.pairing_id}",
        f"  origin     : {pairing.origin}",
        f"  scopes     : {', '.join(pairing.scopes)}",
        f"  phrase     : {pairing.confirm_phrase}",
        "  approve on this host (needs the host-only local-admin secret):",
        f"    curl -s -X POST http://{authority}/v1/pairing/{pairing.pairing_id}/confirm \\",
        f'      -H "X-CEOps-Local-Admin: $(cat {admin_src})"',
        "===============================================================",
        "",
    ]
    print("\n".join(lines), file=sys.stderr, flush=True)
