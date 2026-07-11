# Environment Record

Status: canonical environment map; static and per-run values are machine locked.

The frozen paper and future thesis runs use different environment artifacts:

- Static hardware: `data/hardware-profile.home-ai.json` and `docs/HARDWARE.md`.
- Runtime policy: `data/runtime-policy.json`.
- Frozen paper row-level OS/kernel/runtime/power facts:
	`data/snapshots/results_snapshot.csv`, bound by `data/analysis-manifest.json`.
- Future run launch locks: `data/run-manifest.json` plus each `run.meta` and
	row-level `env.*` capture.
- Claim-bearing analysis/release interpreter: Python 3.14.5 in
	`.python-version`.
- Complete analysis/release package graph and hashes: `requirements-lock.txt`;
	generated from `requirements-lock.in` with uv and installed using
	`pip --require-hashes`.
- Lock validation performs a constrained semantic fixed-point check against the
	tracked inputs; it proves self-consistency, not availability of newer upstream
	packages.
- Dependency-license policy: `data/tool-license-policy.json`, validated by
	`scripts/audit-tool-licenses.py`; every universal-lock package is covered,
	including exact-version declarations for platform-gated dependencies and
	commit-pinned upstream license evidence. The active package count is evaluated
	from environment markers and therefore varies by platform.

The model-running harness remains stdlib-first and supports Python 3.10+. That
does not relax the exact environment required to regenerate claim-bearing
notebook outputs, figures, Croissant metadata, or release packages.
