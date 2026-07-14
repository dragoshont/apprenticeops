# ADR 0001: Host CEOps on Cloudflare Pages

- Status: Proposed (staged on branch `ceops-cloudflare`; not yet merged)
- Date: 2026-07-14

## Context

The CEOps public site (`docs/analysis`, brand CEOps, first release ApprenticeOps)
is a **static Quarto site**. It is currently deployed to GitHub Pages at
`https://dragoshont.github.io/apprenticeops`. The canonical domain `ceops.org` is
already on **Cloudflare** (`jillian`/`rex.ns.cloudflare.com`); no records are
configured yet.

Two facts make Cloudflare Pages the natural host:

1. The domain is already on Cloudflare, so a custom domain on a Pages project is a
   one-click CNAME + automatic certificate — no apex `A` records or GitHub domain
   verification.
2. The repository already builds the site in GitHub Actions, including a
   platform-locked `verify-analysis-v1` reproduction and a provenance stamp, so
   only the final deploy hop needs to change.

This mirrors the established pattern in `hai-la-liceu` and `aletheia-strategy`,
which deploy static output to Cloudflare Pages via `cloudflare/wrangler-action`.

## Decision

1. Keep `verify-analysis-v1` (macOS locked reproduction) and the Quarto render +
   provenance stamp unchanged. The locked evidence gate is CEOps-specific and
   stays.
2. Replace only the deploy hop: `actions/deploy-pages` → `cloudflare/wrangler-action`
   running `wrangler pages deploy` for the `ceops` Pages project. The build output
   directory is `docs/analysis/_site`, declared in `wrangler.toml`.
3. Serve content-hashed `site_libs/*` assets with
   `Cache-Control: public, max-age=31536000, immutable` and keep HTML,
   `build.json`, and `search.json` revalidating, via `deploy/cloudflare/_headers`
   copied into `_site` at deploy time (Quarto ignores files starting with `_`).
4. Reduce workflow permissions to `contents: read`; the Pages token is a GitHub
   Actions secret, not a `GITHUB_TOKEN` permission.
5. Bind `ceops.org` and `www.ceops.org` as custom domains on the `ceops` Pages
   project in the Cloudflare dashboard. The deploy token needs **no** Zone/DNS
   rights for this.

## Secrets And Entitlements

- `CLOUDFLARE_API_TOKEN` — a custom token scoped to **Account · Cloudflare Pages ·
  Edit**, restricted to this account. No Zone, Workers, or KV permissions.
- `CLOUDFLARE_ACCOUNT_ID` — the account identifier.
- Both are GitHub Actions repository secrets. Neither is committed, logged, or
  materialized in the repository.

## Consequences

- `ceops.org` gains Cloudflare edge caching and an automatically managed
  certificate, with no GitHub Pages apex-IP dependency.
- The cutover is coordination-sensitive: merging this workflow to `main` deploys
  to Cloudflare, so it must land **after** `CLOUDFLARE_API_TOKEN` exists or the
  run fails. GitHub Pages keeps serving until then.
- `site-url` in `_quarto.yml` stays `dragoshont.github.io/apprenticeops` until
  `ceops.org` is actually bound and serving; it is updated in the same change that
  confirms the custom domain, not before.

## Rollback

- Revert this workflow change; the next merge redeploys to GitHub Pages via
  `actions/deploy-pages`.
- Remove the `ceops.org` custom domain from the Pages project; the site falls back
  to `*.pages.dev` and the GitHub Pages URL.
- No paper evidence, notebook, figure, or dataset is affected by either rollback.
