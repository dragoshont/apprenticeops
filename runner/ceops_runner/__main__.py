"""Command-line entry point: ``ceops-runner``.

Resolves configuration, prints an honest startup banner (including the LAN
exposure warning when opt-in LAN bind is used), and serves the FastAPI app with
uvicorn on the configured private/loopback address.
"""

from __future__ import annotations

import argparse
import os
import sys

from .config import RunnerConfig


def _build_env(args: argparse.Namespace) -> dict[str, str]:
    env = dict(os.environ)
    if args.bind:
        env["CEOPS_RUNNER_BIND"] = args.bind
    if args.port:
        env["CEOPS_RUNNER_PORT"] = str(args.port)
    if args.ollama_url:
        env["CEOPS_OLLAMA_URL"] = args.ollama_url
    if args.allow_origin:
        origins = ["https://experiment.ceops.org", *args.allow_origin]
        env["CEOPS_ALLOWED_ORIGINS"] = ",".join(dict.fromkeys(origins))
    return env


def _print_banner(cfg: RunnerConfig) -> None:
    lines = [
        "",
        "  CEOps runner",
        f"    version    : {cfg.runner_version} (api {cfg.api_version})",
        f"    instance   : {cfg.instance_id}",
        f"    bind       : http://{cfg.bind_host}:{cfg.port}",
        f"    ollama     : {cfg.ollama_url}",
        f"    origins    : {', '.join(sorted(cfg.allowed_origins))}",
        f"    local UI   : http://127.0.0.1:{cfg.port}/",
    ]
    if cfg.lan_bound:
        lines += [
            "",
            "  ⚠ LAN bind is ON. Anyone who can reach "
            f"{cfg.bind_host}:{cfg.port} on the network can attempt to connect.",
            "    Only the pairing token and your host firewall stand in front of it.",
            "    Bind one trusted interface and keep it off untrusted networks.",
        ]
    lines.append("")
    print("\n".join(lines), file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ceops-runner",
        description="CEOps user-owned experiment runner (loopback-first).",
    )
    parser.add_argument("--bind", help="bind address (default 127.0.0.1; must be private/loopback)")
    parser.add_argument("--port", type=int, help="listen port (default 8799)")
    parser.add_argument("--ollama-url", dest="ollama_url", help="Ollama base URL (default http://127.0.0.1:11434)")
    parser.add_argument(
        "--allow-origin",
        dest="allow_origin",
        action="append",
        default=[],
        help="additional allowed console origin (repeatable)",
    )
    args = parser.parse_args(argv)

    try:
        cfg = RunnerConfig.from_env(_build_env(args))
    except SystemExit as exc:  # raised by from_env on an unsafe bind
        print(str(exc), file=sys.stderr)
        return 2

    from .app import create_app  # local import so --help works without uvicorn
    import uvicorn

    app = create_app(cfg)
    _print_banner(cfg)
    uvicorn.run(app, host=cfg.bind_host, port=cfg.port, log_level="info", access_log=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
