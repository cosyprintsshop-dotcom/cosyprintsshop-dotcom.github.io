# cosyprints.com

Static, **no-build** site for CosyPrints (3D printing, Saint-Martin-d'Uriage), hosted on
GitHub Pages — `main` is live. French is the source language in the HTML; English is
applied at runtime from `assets/i18n.en.js` (see the header of `assets/i18n.js`).

Sales happen on [Vinted](https://www.vinted.fr/member/60879390-cosyprints) and
[Leboncoin](https://www.leboncoin.fr/profil/0408d333-46e3-4487-b2f3-4743fd34c872) —
the site is a showcase whose product cards link out to the live listings. There is no
on-site checkout by design.

New here? Read [CONTRIBUTING.md](CONTRIBUTING.md) first, and [CLAUDE.md](CLAUDE.md) for
the full working agreements.

## Content & catalogue

There are **two** content sources, merged by one sync step:

1. **Sanity** (headless CMS) — the primary editing surface. Products, homepage copy,
   FAQ, impact figures. Editors work in the hosted Studio
   ([cosyprints.sanity.studio](https://cosyprints.sanity.studio)); no git required.
2. **`data/*manual*.json`** — hand-maintained mirrors of your own Vinted / Leboncoin
   listings (see "Why nothing is scraped" below).

### How data flows

```
Sanity (published docs)          data/vinted-manual.json     (you maintain)
        │  fetch-sanity.js        data/leboncoin-manual.json  (you maintain)
        ▼                         data/manual.json            (you maintain, optional)
data/sanity.json, data/content.json          │
        │                                     │  import-vinted.js / import-leboncoin.js
        │                                     ▼
        │                         data/vinted.json, data/leboncoin.json  (normalized)
        └──────────────┬──────────────────────┘
                       │  sync-catalog.js (merge, dedupe, timestamp)
                       ▼
        data/catalog.json      (merged, canonical)
        assets/products.js     (window.CP_PRODUCTS — read by boutique.html)
        assets/content.js      (window.CP_CONTENT  — homepage/impact/FAQ, read by cms.js)
```

`npm run sync:catalog` runs all four scripts in order. Everything under `data/` plus
`assets/products.js` and `assets/content.js` is **generated** — the only hand-edited
sources are the three `*manual*.json` files (the scripts never modify them) and whatever
lives in Sanity.

### Automated publishing

[`.github/workflows/rebuild.yml`](.github/workflows/rebuild.yml) runs the sync every
15 minutes (and on demand via **Actions → Run workflow**), commits the regenerated files
when content changed, and GitHub Pages republishes. So **publishing in Sanity reaches the
live site without anyone touching git.** The Sanity project id (`1qw286fu`) is public and
lives in the workflow — no secrets. `fetch-sanity.js` exits cleanly if it is unset, so the
site still builds from the manual sources alone.

### Why nothing is scraped (please keep it that way)

- **Leboncoin** — `leboncoin.fr/robots.txt` requires permission for automated access and
  disallows `/profile/` even for Google; their CGU prohibit extraction of listings.
  `node scripts/import-leboncoin.js --check-policy` re-inspects robots.txt.
- **Vinted** — their Terms prohibit crawling/screen-scraping, and there is no public
  export or API for member catalogues.

Copying **your own** listing text into a file in **your own** repo is not scraping — you
authored that content. The manual files are the lawful source; the scripts do the boring
part (validation, price parsing, dedupe). If either platform ever offers an official
export or partner API, plug it into the matching `scripts/import-*.js` and nothing else
changes.

### Refreshing the catalogue by hand

1. Edit content in Sanity, **or** edit `data/*manual*.json`. Minimal manual entry:

   ```json
   { "title_fr": "Vase spirale terracotta", "price": "24,90", "source_url": "https://www.vinted.fr/items/1234567890-vase" }
   ```

2. Run `npm run sync:catalog` (Node ≥ 20, no dependencies beyond `@sanity/client`).
3. Check locally: `npm run dev` → http://localhost:8080/boutique.html
4. Commit and push to `main` — Pages redeploys. (Or just let the 15-min workflow do it.)

### Item fields (manual sources)

Required: `title_fr` (or `title`). Everything else is optional:

| Field | Notes |
|---|---|
| `source_url` | Public listing URL — becomes the card's CTA (new tab, `noopener noreferrer`) |
| `price` | Number or French string; normalized to a EUR number |
| `title_en`, `desc_fr`, `desc_en` | Missing English falls back to French automatically |
| `img`, `images[]` | Card photo; no photo shows the placeholder |
| `category` | `homie-vibe` \| `cable-management` \| `lampes` \| `bureau` \| `gadgets` — inferred from keywords when omitted |
| `badge` | `eco-pla` \| `limited` \| `made-to-order` — inferred; set `"badge": null` to force none |
| `status` | `active` (default) \| `sold` \| `soon` |
| `material`, `location`, `created_at` | Metadata; `created_at` (YYYY-MM-DD) drives the "Nouveautés" sort |

Category slugs must match `CATEGORIES` in `boutique.html` and `scripts/lib/normalize.js`
— update both if you add a universe. Status must stay `active | soon | sold` (what
`boutique.html` renders).

### Scripts

| Command | What it does |
|---|---|
| `npm run build` | Alias for `sync:catalog` — what CI runs |
| `npm run sync:catalog` | Full refresh: Sanity + both importers → `catalog.json` + `products.js` + `content.js` |
| `npm run import:vinted` | Only normalize `vinted-manual.json` → `vinted.json` |
| `npm run import:leboncoin` | Only normalize `leboncoin-manual.json` → `leboncoin.json` |
| `npm run dev` | Zero-dependency static server on http://localhost:8080 |
| `npm run seed:sanity` | Mirror current content into a fresh Sanity project (needs `SANITY_WRITE_TOKEN`) |

Re-running the sync with unchanged sources is byte-identical (timestamps preserved via
content fingerprints), so diffs only appear when listings actually change.

## Deployment & CI

- **Host:** GitHub Pages from `main` (classic deploy-from-branch). Custom domain via
  `CNAME`. There is no separate build server — Pages serves the committed files directly.
- **`ci.yml`** — on every PR: `npm run build`, validate `data/*.json`, assert artefacts.
- **`rebuild.yml`** — the 15-min Sanity sync described above.

## Design system — "warm editorial sage"

Tokens live in `assets/theme.css`; use them, never hardcode colours.

`--page #faf9f6` warm off-white · `--ink #2d312a` charcoal-olive · `--sage #7b8e7e` ·
`--sage-deep #5b6f5e` · `--stone #f1efe7` bands · `--sand #e9e2d2`. Instrument Serif
(display) + Instrument Sans (UI/body). Light-only by design. See CLAUDE.md for the full
rationale and the list of deliberately-rejected effects.

## Repo map

- `index.html`, `boutique.html`, `engagement.html`, `404.html` — pages (French source)
- `assets/theme.css` — design system (warm editorial sage)
- `assets/i18n.js` + `assets/i18n.en.js` — bilingual runtime layer
- `assets/site.js` — shared behaviour (cart drawer, count-up, reveal-on-scroll, mobile menu, newsletter)
- `assets/cms.js` — renders CMS content into `[data-cms]` hooks
- `assets/products.js`, `assets/content.js` — **generated** catalogue + CMS data
- `data/` — catalogue sources (manual) and generated JSON
- `scripts/` — Node sync tooling (`@sanity/client` only)
- `studio/` — Sanity Studio config + schemas
- `.github/workflows/` — `ci.yml`, `rebuild.yml`
- `CNAME`, `robots.txt`, `sitemap.xml` — domain + SEO (don't touch casually)
