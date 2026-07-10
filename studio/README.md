# CosyPrints Studio (Sanity CMS)

The visual editor where you and your partner manage the site — products, homepage,
donation figures, FAQ — with no code. Content is fetched at build time by
`../scripts/fetch-sanity.js` and rendered by the static site.

## One-time setup (you run these — they create your account/project)

From this `studio/` folder:

```bash
npm install
npx sanity login          # opens the browser — sign in / create a free account
npx sanity init           # create a NEW project named "CosyPrints", dataset "production"
                          # choose "reconfigure with existing config" so your schemas are kept
```

`sanity init` writes your **Project ID** into `.env` (`SANITY_STUDIO_PROJECT_ID`).
Copy that same ID to the site build (see below). Then:

```bash
npm run dev               # http://localhost:3333 — the editor, running locally
npx sanity deploy         # publish the editor to https://<name>.sanity.studio
```

## Wire the build (site repo root)

The build script reads two env vars. Set them locally and in Cloudflare Pages:

```
SANITY_PROJECT_ID=<the id sanity init printed>
SANITY_DATASET=production
```

Then `npm run build` (site root) fetches published content → `data/sanity.json` +
`data/content.json` → renders the static site.

## Invite your partner

sanity.io/manage → your project → **Members** → invite by email. They log in with
email/password — no GitHub, no code.

## Guardrails already built in

- **Singletons** (Homepage, Dons & impact, Réglages) can't be duplicated or deleted.
- **Drafts**: nothing is live until you click **Publier**; the build only reads published docs.
- **Validation**: a product can't be marked *Disponible* without a photo; `%` is capped 0–100.
- **Last-good deploy**: if a build ever fails, Cloudflare keeps the previous site live.

## Category slugs

Category slugs must match the boutique: `homie-vibe`, `cable-management`, `lampes`,
`bureau`, `gadgets` (see `../scripts/lib/normalize.js`).
