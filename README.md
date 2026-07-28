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

## Product photography

`assets/products/` is generated from the raw photos in `../products/` by a
pipeline that cuts each object out, drops it on a consistent warm backdrop with
a contact shadow, grades it warm and exports square/portrait/wide at two widths
in WebP + JPEG. Lit lamps get a dark backdrop and a glow keyed to the colour
the lamp is actually emitting.

Anything named `concept-*` is an AI-generated render, not a photograph, and is
labelled as such on every page it appears on. Do not present those as product
photos.

## Motion

Three tiers, each degrading cleanly to the one below:

- **no JS** — everything visible, all links work.
- **`assets/js/site.js`** — nav states, FAQ accordion, room filters, and
  IntersectionObserver reveals driven by CSS transitions.
- **GSAP 3.15.0 + Lenis 1.3.25** (self-hosted in `assets/vendor/`) — smooth
  scroll, line-masked headings via SplitText, batched grid reveals, the hero
  timeline, one parallax layer.

Tier 3 is only fetched when the visitor has *not* asked for reduced motion, so
those users never download the ~55 KB. Nothing is hidden by CSS unless JS has
already confirmed it can un-hide it (`html.js-motion`).

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
