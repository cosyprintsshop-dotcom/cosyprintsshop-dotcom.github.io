# Cosy Prints — cosyprints.com

Hand-written static site. No framework, no build pipeline at runtime, no CDN.
GitHub Pages serves it; Cloudflare proxies it.

## Before this goes live

Everything below is a placeholder or an assumption I could not verify. Search
`PLACEHOLDER` in `data/site.json`.

1. **Prices.** Every `price` in `data/products.json` is invented. They are
   plausible for small French 3D-printed homeware but they are not yours.
2. **Checkout.** Nothing is connected. Product pages fall back to an
   "Order by email" mailto. To turn any product into a real buy button, create a
   Stripe Payment Link and put the URL in that product's `checkoutUrl`. Only
   then put a payment claim back into `trust` in `site.json`.
3. **Mentions légales.** `/legal/` is drafted but needs your legal form, SIREN,
   registered address, VAT status and publication director.
4. **Delivery times.** "3–5 working days" is an assumption.

## Editing

```bash
python build.py
```

Reads `data/site.json` and `data/products.json`, writes `index.html`,
`lamps/`, `decorations/`, `shop/<slug>/`, `legal/`, `sitemap.xml`, `robots.txt`.
Never edit the generated HTML — it gets overwritten.

## Photography

Frames hold a photo when one exists and a labelled "Photo coming soon" box when
it doesn't (`.slot` in `site.css`, `slot()` in `build.py`). The layout is the
same either way.

To add a photo:

1. `pip install pillow` (once), then
   `python tools/photos.py path/to/photo.jpg NAME --ratio 4:5`
   — 4:5 for the hero and a product's first shot, 1:1 for cards. `--focus 0.3`
   moves the crop up, `0.7` down. It writes `assets/img/NAME-<width>.webp/.jpg`
   (metadata stripped) and records NAME in `data/photos.json`.
2. Point something at it:
   - hero: `"hero": {"photo": {"name": "NAME", "alt": "..."}}` in `site.json`
   - product: `"photos": [{"name": "NAME", "alt": "..."}, ...]` in
     `products.json` — the first fills the card and first shot, the second
     fills the second frame if `shots` is 2.
3. `python build.py`, commit everything.

The build stops if a photo is missing or has no alt text. Use camera originals:
WhatsApp shrinks photos to ~900px, which looks soft on phones and retina screens.
Note the CSS reset needs `img { height: auto }` — without it the `height`
attribute wins and images stretch vertically.

## Motion

Three tiers, each degrading cleanly to the one below:

- **no JS** — everything visible, all links work.
- **`assets/js/site.js`** — nav states, FAQ accordion, room filters, and
  IntersectionObserver reveals driven by CSS transitions.
- **GSAP 3.15.0 + Lenis 1.3.25** (self-hosted in `assets/vendor/`) — smooth
  scroll, line-masked headings via SplitText, batched grid reveals.

Tier 3 is only fetched when the visitor has *not* asked for reduced motion, so
those users never download the ~55 KB. Nothing is hidden by CSS unless JS has
already confirmed it can un-hide it (`html.js-motion`), and the reveal code
carries two `setTimeout` safety nets — rAF and IntersectionObserver callbacks
both need a rendering opportunity, which a background tab never gets, so without
them a page opened in a background tab could stay blank.

The hero is deliberately **not** animated by GSAP. It is above the fold, so a
timeline created after the libraries arrive would re-hide content that had
already painted. Its stagger is CSS `--rd` delays instead (350/450/700/950 ms).

Page-to-page transitions are the native View Transitions API — pure CSS opt-in,
no JS, no polyfill. Firefox does not support cross-document transitions yet and
simply navigates normally.

**If page transitions stop working**, check Cloudflare for a redirect rule
(www→apex, or `*.github.io`→custom domain) sitting between internal links. A
cross-origin redirect in the navigation path silently disables them.

## Motion tokens

Durations and easings in `assets/css/site.css` are taken from what Muuto, Gubi,
Flos and &Tradition actually ship. The rule is ease-**out** only for anything
the visitor watches arrive; ease-in is for exits. Hover is 150–250 ms, editorial
reveals 1100–1600 ms, nothing in between except structural moves. Product image
hover scale is 1.025 — above about 1.06 it reads as a template.

## Fonts

Archivo and Newsreader, self-hosted in `assets/fonts/` (~145 KB for the latin
subsets). Self-hosted rather than Google's CDN: serving Google Fonts from a
French site has been treated as a GDPR problem, and this way the site sets no
third-party requests at all.
