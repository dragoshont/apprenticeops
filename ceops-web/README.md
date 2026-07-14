# CEOps web preview (design-only)

This is the **design-validation workbench** for the public CEOps benchmark site
(`ceops.org`). It exists to get visual and content sign-off on the approved
visual system **before** any production site code is written.

It is **not** the production site and it is **not** connected to real evidence:

- The production public site is planned as Quarto + GitHub Pages (Phase 2).
- Data shown here is **illustrative preview data**, clearly labelled in every
  view, and must never be cited as published CEOps evidence.
- Design decisions are governed by
  [`docs/research/ceops-benchmark-site-research-2026-07-14.md`](../docs/research/ceops-benchmark-site-research-2026-07-14.md).

## What this validates (Phase 1)

The two lead public pages from the approved delivery order (§12):

1. **Overview** — the first-viewport decision contract.
2. **Selection** — the controlled Pareto evidence explorer.

Both render in the two first-class themes (light neutral, charcoal dark) and are
driven by DTCG-style tokens (`src/styles/tokens.css`) that will later compile
into Quarto and the experiment client rather than becoming a second visual
system.

## Run it

```sh
cd ceops-web
npm install
npm run storybook   # http://127.0.0.1:6007
```

Switch **Theme** in the Storybook toolbar to review light and charcoal.

## Verify the design build

```sh
npm run build-storybook   # deterministic gate for Phase 1
```
