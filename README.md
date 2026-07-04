# cosyprints.com

Static, no-build site for CosyPrints (3D printing, Saint-Martin-d'Uriage), hosted on
GitHub Pages — `main` is live. French is the source language in the HTML; English is
applied at runtime from `assets/i18n.en.js` (see the header of `assets/i18n.js`).

Sales happen on [Vinted](https://www.vinted.fr/member/60879390-cosyprints) and
[Leboncoin](https://www.leboncoin.fr/profil/0408d333-46e3-4487-b2f3-4743fd34c872) —
the site is a showcase whose product cards link out to the live listings.

## Catalogue

### How data flows

```
data/vinted-manual.json     (you maintain — your Vinted listings)
data/leboncoin-manual.json  (you maintain — your Leboncoin listings)
data/manual.json            (you maintain — optional off-platform items)
        │  npm run sync:catalog
        ▼
data/vinted.json, data/leboncoin.json   (normalized per source)
data/catalog.json                       (merged, deduped, canonical)
assets/products.js                      (window.CP_PRODUCTS — loaded by boutique.html)
```

`boutique.html` renders `window.CP_PRODUCTS`. Everything under `data/` plus
`assets/products.js` is generated **except** the three `*manual*.json` source files,
which the scripts never modify.

### What is automated vs. manual

**Manual (you):** keeping the three `data/*manual*.json` files in step with your live
listings — add an entry when you list something, flip `"status": "sold"` or delete the
entry when it sells.

**Automated (scripts):** everything else — validation, price parsing (`"24,90 €"` →
`24.9`), category + badge inference, cross-platform dedupe (same title + price on both
platforms collapses into one card, the second link kept in `also_on`), stable
timestamps, and regeneration of the files the site reads.

### Why nothing is scraped (please keep it that way)

- **Leboncoin** — `leboncoin.fr/robots.txt` states that automated access requires
  their permission and disallows `/profile/` even for Google; their CGU prohibit
  extraction of listings. `node scripts/import-leboncoin.js --check-policy`
  re-inspects robots.txt if you want to see for yourself.
- **Vinted** — their Terms prohibit crawling/screen-scraping, and there is no public
  export or API for member catalogues.

Copying **your own** listing text into a file in **your own** repo is not scraping —
you authored that content. That is the whole design: the manual files are the lawful
source, the scripts do the boring part. If either platform ever offers an official
export or partner API, plug it into the matching `scripts/import-*.js` and nothing
else has to change.

### Refreshing the catalogue

1. Edit `data/vinted-manual.json` and/or `data/leboncoin-manual.json`. Minimal entry:

   ```json
   { "title_fr": "Vase spirale terracotta", "price": "24,90", "source_url": "https://www.vinted.fr/items/1234567890-vase" }
   ```

2. Run `npm run sync:catalog` (Node ≥ 18, no dependencies to install).
3. Check the result locally: `npm run dev` → http://localhost:8080/boutique.html
4. Commit and push — GitHub Pages redeploys `main`.

### Item fields

Required: `title_fr` (or `title`). Everything else is optional:

| Field | Notes |
|---|---|
| `source_url` | Public listing URL — becomes the card's CTA (new tab, `noopener noreferrer`) |
| `price` | Number or French string; normalized to a EUR number |
| `title_en`, `desc_fr`, `desc_en` | Missing English falls back to French automatically |
| `img`, `images[]` | Card photo; no photo shows the placeholder |
| `category` | `homie-vibe` \| `cable-management` \| `lampes` \| `bureau` \| `gadgets` — inferred from keywords when omitted |
| `badge` | `eco-pla` \| `limited` \| `made-to-order` — inferred (e.g. "sur commande", "série limitée", "PLA"); set `"badge": null` to force none |
| `status` | `active` (default) \| `sold` \| `soon` |
| `material`, `location`, `created_at` | Metadata; `created_at` (YYYY-MM-DD) drives the "Nouveautés" sort |

Category slugs must match `CATEGORIES` in `boutique.html` and
`scripts/lib/normalize.js` — update both if you ever add a universe.

### Scripts

| Command | What it does |
|---|---|
| `npm run sync:catalog` | Full refresh: both importers, then merge → `catalog.json` + `products.js` |
| `npm run import:vinted` | Only normalize `vinted-manual.json` → `vinted.json` |
| `npm run import:leboncoin` | Only normalize `leboncoin-manual.json` → `leboncoin.json` |
| `npm run dev` | Zero-dependency static server on http://localhost:8080 |

Re-running the sync with unchanged sources is byte-identical (timestamps are
preserved via content fingerprints), so diffs only appear when listings actually
change.

## Repo map

- `index.html`, `boutique.html`, `engagement.html`, `404.html` — pages
- `assets/theme.css` — design system (paper & ink + terracotta)
- `assets/i18n.js` + `assets/i18n.en.js` — bilingual runtime layer
- `assets/site.js` — shared behaviour (cart drawer, count-up)
- `assets/products.js` — **generated** catalogue data
- `data/` — catalogue sources (manual) and generated JSON
- `scripts/` — Node sync tooling (no dependencies)
- `CNAME`, `robots.txt`, `sitemap.xml` — domain + SEO (don't touch casually)
