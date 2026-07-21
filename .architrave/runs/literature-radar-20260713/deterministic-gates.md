# Deterministic Gates

## checks

- `scripts/test-validate-literature-radar.py`: PASS, 16 focused attacks.
- `scripts/validate-literature-radar.py complete --scan-id radar-20260713-initial`:
	PASS, 29 queries / 42 source versions / 42 claim versions / 1 scan / 0 promotions.
- `gates/checks.sh`: PASS, including all existing experiment, persistence,
	promotion, report, privacy, and link tests plus radar validation.

## backend-checks

Not applicable (`kind: knowledge`).

## reconcile

Not applicable (`kind: knowledge`).

## other

- Documentation links: PASS, 133 files / 183 local links.
- Privacy scan: PASS, 21,179 files / zero secret hits.
- Radar run validation: PASS.
- Canonical radar paths: clean and hash-matched to scan manifest.
- VS Code diagnostics: zero errors in radar config, skill, validator, tests, and
	schema.
- `git diff --check`: PASS.
- Paper-impact source trace: PASS, 33 immutable versions referenced and every
	decision-bearing monitor/reject source present by exact version ID.
- Paper-impact boundary: PASS, no bibliography, literature-catalog, manuscript,
	completed-run, or active-experiment path changed.
- Reviewed commit trees: radar `27ab2c7` / tree
	`e47cfeefdfcc899e86e33192e15c1ed5a37c9100`; paper impact `18ba9c9` /
	tree `8b4928d63cc72dd7553aeb78d8d4b5942488726b`.
