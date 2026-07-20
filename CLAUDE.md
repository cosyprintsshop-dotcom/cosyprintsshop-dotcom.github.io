# CLAUDE.md — cosyprints.com

Read this before touching anything in this repo.

## What this is

**cosyprints.com** — the public site for CosyPrints, a French cosy-themed 3D-printing
shop based in Saint-Martin-d'Uriage. It is a **vitrine (showcase), not a checkout**:
actual sales happen on Vinted and Leboncoin, and product cards link out to those
listings.

> Never add or imply on-site payment — no CB, Apple Pay, PayPal, Stripe, no "buy now"
> that takes money. The cart drawer collects intent and links out; that's it.

This repo is the **live site**. `main` is production — pushing to `main` deploys via
GitHub Pages to cosyprints.com.

## Stack — read this before proposing anything

- **Hand-coded static HTML + CSS + vanilla JS.** No React, no Tailwind, no bundler, no
  framework, no build step for the pages themselves.
- Node ≥ 20 (`.nvmrc`) is used **only** for the catalogue/CMS sync scripts in `scripts/`.
- Content comes from **Sanity** (headless CMS) → generated JS files → static pages.
- Hosting: **GitHub Pages** from `main`. Domain via `CNAME`. (An earlier Cloudflare
  Pages move was abandoned — ignore stale references to it.)
- The repo name `cosyprintsshop-dotcom.github.io` **must not change** — GitHub Pages
  user sites require the `<owner>.github.io` name.

**Sid pastes React / shadcn / Lovable mockups.** Those come from the separate private
design sandbox `cosyprints-design-lab`. Do **not** scaffold React or copy `.tsx` into
this repo — there is no React runtime here. Port the look and behaviour to vanilla
HTML/CSS/JS using the tokens in `assets/theme.css`.

## Repo map

```
index.html  boutique.html  engagement.html  404.html   pages (French source text)
assets/theme.css      design system — all tokens live here
assets/site.js        shared behaviour (cart drawer, count-up, nav)
assets/i18n.js        FR⇄EN runtime engine
assets/i18n.en.js     the English dictionary (window.CP_EN)
assets/cms.js         renders CMS content into [data-cms="..."] hooks
assets/products.js    GENERATED — window.CP_PRODUCTS, read by boutique.html
assets/content.js     GENERATED — window.CP_CONTENT (homepage/impact/FAQ/settings)
data/*manual*.json    hand-maintained catalogue sources (scripts never write these)
data/{vinted,leboncoin,catalog,sanity,content}.json   GENERATED
scripts/              zero-dependency ESM Node tooling
studio/               Sanity Studio config + 6 schemas
.github/workflows/rebuild.yml   15-min auto-rebuild from Sanity
CNAME  robots.txt  sitemap.xml  — domain + SEO, don't touch casually
```

**Never hand-edit generated files** (`assets/products.js`, `assets/content.js`,
`data/catalog.json`, `data/sanity.json`, `data/content.json`, `data/vinted.json`,
`data/leboncoin.json`). Edit the source, re-run the sync. They *are* committed —
that's the convention here.

## Commands

| Command | What it does |
|---|---|
| `npm run dev` | Zero-dependency static server → http://localhost:8080 |
| `npm run sync:catalog` | Full refresh: Sanity + both importers → generated files |
| `npm run build` | Alias for `sync:catalog` (what CI runs) |
| `npm run seed:sanity` | Mirror current content into a fresh Sanity project (needs `SANITY_WRITE_TOKEN`) |

Preview via the `site` launch config in `.claude/launch.json` (port 8080) — never run
a dev server through Bash.

## Design system — "warm editorial sage" (live since 2026-07-05)

Tokens in `assets/theme.css`; use them, don't hardcode colours.

`--page #faf9f6` warm off-white · `--ink #2d312a` charcoal olive · `--sage #7b8e7e` ·
`--sage-deep #5b6f5e` · `--stone #f1efe7` bands · `--sand #e9e2d2`.
Instrument Serif (display) + Instrument Sans (UI/body). 2px corners on plates, full
pills for labels/chips/cart, stone section bands, bento category grid, calm 200–700ms
motion. **Light-only by design** — dark mode was deliberately dropped. No announcement
bar, no mono font. Sticky header is 64px at every width.

**Banned — Sid actively disliked these:** WebGL hero shaders, glowing auras, tubelight
pill nav, bouncy transitions, cursor-spotlight glows, marquee bands.

Aim for editorial, considered, Awwwards-tier restraint — not centred-card-with-shadow
SaaS defaults. Push back on bland options rather than defaulting to the safe one.

## Bilingual (FR source, EN runtime)

French lives **directly in the HTML** (SEO + no-JS). English lives **only** in
`assets/i18n.en.js`.

- Mark a node translatable: `data-i18n="some.key"` (sets innerHTML), then add the EN
  string to `assets/i18n.en.js`. Values may contain inline HTML (`<em>`, `<b>`).
- Attributes: `data-i18n-attr="content:key"` (used on `<meta name="description">`).
- `<title>` and meta keys must be **page-specific** (`meta.title.boutique`, …) — the
  dictionary is shared across all pages.
- Resolution order: `?lang=` → localStorage → `<html lang>` → `fr`. EN URL is `?lang=en`.
- Anything that renders dynamically must re-render on the `cp:langchange` event.
- Keep `hreflang` alternates in each `<head>` and in `sitemap.xml` in step.

Product text fields accept either a plain string or `{ fr, en }`; missing EN falls back
to FR.

## Content & catalogue

**Sanity is the editing surface.** Project id `1qw286fu` (public, not a secret),
dataset `production`. Hosted Studio: https://cosyprints.sanity.studio (login-gated).
Sanity holds **French only** — English stays in the i18n layer. Editorial copy
(hero, headings, FAQ prose) intentionally stays in the HTML/i18n layer, not the CMS.

Flow: Sanity + `data/*manual*.json` → `npm run sync:catalog` → `data/catalog.json` +
`assets/products.js` / `assets/content.js` → pages. `.github/workflows/rebuild.yml`
runs this every 15 min (and on demand) and commits the result, so publishing in Sanity
reaches the live site without anyone touching git.

**Never scrape Vinted or Leboncoin.** This was decided deliberately: Leboncoin's
robots.txt forbids automated access and disallows `/profile/`, and Vinted's ToS
prohibit screen-scraping. Copying your *own* listings into `data/*manual*.json` is the
lawful design. Don't revisit this by writing a scraper. `--check-policy` on the
importers re-inspects robots.txt.

Keep these in sync by hand — they're duplicated:
- Category slugs `homie-vibe | cable-management | lampes | bureau | gadgets` →
  `CATEGORIES` in `boutique.html` **and** `scripts/lib/normalize.js`.
- Status vocabulary → `fetch-sanity.js` must emit only `active | soon | sold`, which is
  all `boutique.html` renders. (A past bug emitted `coming_soon`/`sold_out`, which
  silently rendered items as buyable.)
- Badge slugs `eco-pla | limited | made-to-order` → bilingual labels in `boutique.html`.

## Engagement page

`engagement.html` is a charity/tribute page tied to a co-founder's personal loss. Keep
the tone **sober and universal** — no marketing gloss, no exploitation of the story.
Donations split **10% total (5% La Ligue contre le cancer + 5% The SeaCleaners)**.
That figure appears in the CMS impact doc, FR source, EN dictionary, engagement +
index meta/OG, and count-up fallbacks — change all of them together.

## Pending / known gaps

- **Real product photos are missing.** Everything in `assets/img/` is a stone-coloured
  "PHOTO À VENIR" placeholder. Drop real JPGs in with the same names and change the
  `.svg` extension in markup.
- The four homepage "essentiels" cards are **invented names** shown as "Bientôt" with
  no prices or add-to-cart. Replace with real products, then restore prices/buttons.
- Instant-publish webhook (Sanity → `repository_dispatch`) is an optional future add-on;
  the 15-min cron covers it for now.

## Working agreements

- **Verify at mobile width first (~375px).** More visitors are on mobile than desktop,
  and a mobile-only scroll-restoration bug already slipped through desktop-only checks.
- Preview **screenshots reliably hang on this site** (environment issue, confirmed
  repeatedly). Use `preview_eval` / `preview_inspect` — computed styles,
  `getBoundingClientRect`, scroll position, synthetic clicks. Chrome DevTools MCP can't
  launch on Sid's machine (Edge only, no Chrome).
- `preview_eval` pins to the first page it loaded; to test another page, set
  `window.location.href` in one eval and read state in a second. No long `await sleep()`
  loops — the harness times out at 30s.
- Check both languages after any copy or render change.
- **Pushing to `main` is a production deploy.** Ask before pushing; open a PR when the
  change is substantial.
