# Contributing to cosyprints.com

Short version for humans. The exhaustive rules (design system, bilingual mechanics,
category/status invariants) live in [CLAUDE.md](CLAUDE.md) — read it before a substantial
change.

## Setup (2 minutes)

```bash
git clone https://github.com/cosyprintsshop-dotcom/cosyprintsshop-dotcom.github.io.git
cd cosyprintsshop-dotcom.github.io
nvm use            # Node 20 (see .nvmrc)
npm install        # only @sanity/client
npm run dev        # → http://localhost:8080
```

There is **no build step for the pages** — open `index.html` through the dev server and
edit HTML/CSS/JS directly. `npm run build` only regenerates the catalogue data files.

## The five things that trip people up

1. **No framework, no bundler.** Hand-written static HTML + CSS + vanilla JS. Don't
   introduce React, Tailwind, or a build pipeline for the pages. (The `cosyprints-design-lab`
   sandbox is where React mockups live; port their *look*, not their code.)
2. **French is the source, in the HTML.** English is applied at runtime — add the key to
   `assets/i18n.en.js`, mark the node `data-i18n="key"`. Check both languages after any
   copy change. `<title>`/meta keys are page-specific.
3. **Never hand-edit generated files.** `assets/products.js`, `assets/content.js`, and the
   generated `data/*.json` are outputs of `npm run sync:catalog`. Edit the source (Sanity or
   `data/*manual*.json`) and re-run the sync.
4. **Never write a scraper** for Vinted/Leboncoin. Copying *your own* listings into
   `data/*manual*.json` is the lawful design — see the README.
5. **Verify at ~375px first.** More visitors are on mobile; a mobile-only bug has slipped
   through desktop-only checks before.

## Making a change

- Branch off `main`. **Pushing to `main` is a production deploy** — open a PR for anything
  substantial; CI (`ci.yml`) will build and validate it.
- Keep design tokens in `assets/theme.css` (warm editorial sage) — don't hardcode colours.
- Use `npm run format` (Prettier) and keep the diff minimal.
- If you touch category slugs or product status, update **both** `boutique.html` and
  `scripts/lib/normalize.js` (they duplicate the list on purpose).

## Content edits (no code)

Most catalogue/copy changes need no git at all — edit in the Sanity Studio
([cosyprints.sanity.studio](https://cosyprints.sanity.studio)) and publish. The 15-minute
`rebuild.yml` workflow regenerates the site automatically.
