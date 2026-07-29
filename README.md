# Cosy Prints — cosyprints.com

Hand-written static site. No framework, no build pipeline at runtime, no CDN.
GitHub Pages serves it; Cloudflare proxies it.

## Before this goes live

Everything below is a placeholder or an assumption I could not verify. Search
`PLACEHOLDER` in `data/site.json`.

1. **Prices.** Every `price` in `data/products.json` is invented. They are
   plausible for small French 3D-printed homeware but they are not yours.
2. **The hospital.** `data/site.json → donation.recipientName` says
   `PLACEHOLDER`. The site advertises "10% of revenue to our local hospital"
   in three places. Do not publish a charity claim you cannot evidence.
3. **Checkout.** Nothing is connected. Product pages fall back to an
   "Order by email" mailto. To turn any product into a real buy button, create a
   Stripe Payment Link and put the URL in that product's `checkoutUrl`. Only
   then put a payment claim back into `trust` in `site.json`.
4. **Mentions légales.** `/legal/` is drafted but needs your legal form, SIREN,
   registered address, VAT status and publication director.
5. **Email.** `hello@cosyprints.com` is assumed, not verified.
6. **Delivery times.** "3–5 working days" is an assumption.

## Editing

```bash
python build.py
```

Reads `data/site.json` and `data/products.json`, writes `index.html`,
`lamps/`, `decorations/`, `shop/<slug>/`, `legal/`, `sitemap.xml`, `robots.txt`.
Never edit the generated HTML — it gets overwritten.

## Photography

**There are no photos on this site.** Every shot is a reserved frame — a
hairline box on a raised ground with the ridge motif and a "Photo coming soon"
label (`.slot` in `site.css`, `slot()` in `build.py`). The layout is final, so
real photography drops in without moving anything.

`shots` on each product in `products.json` is how many frames its page reserves
(1 or 2). Product cards, category cards and the hero each reserve one.

To put photography back: render your images, then change `slot()` in `build.py`
to emit a `<picture>` with `width`/`height` set. Keep the frame's aspect ratios
(1:1 for cards, 4:5 for the hero and the first product shot) or the grid shifts.
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
