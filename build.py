# -*- coding: utf-8 -*-
"""
Cosy Prints static site generator.

    python build.py

Reads data/site.json + data/products.json and writes real HTML files — one per
page, no client-side routing. Real documents are what make cross-document view
transitions and search indexing work.
"""
from urllib.parse import quote
import json, os, re, shutil, html, hashlib
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

SITE = json.load(open(os.path.join(DATA, "site.json"), encoding="utf8"))
CAT = json.load(open(os.path.join(DATA, "products.json"), encoding="utf8"))
_PHOTOS_JSON = os.path.join(DATA, "photos.json")
PHOTOS = json.load(open(_PHOTOS_JSON, encoding="utf8")) if os.path.exists(_PHOTOS_JSON) else {}

BRAND = SITE["brand"]
CATEGORIES = CAT["categories"]

# A product's `status` decides whether it is published at all:
#   live     — listed, has a page, can be ordered
#   concept  — listed in "Not yet for sale", has a page, cannot be ordered
#   draft    — not published: no page, no listing, not in the sitemap
# Anything else stops the build, so a typo can never quietly publish a page.
PUBLISHED = ("live", "concept")
for _p in CAT["products"]:
    if _p.get("status", "live") not in PUBLISHED + ("draft",):
        raise SystemExit(f"product '{_p.get('slug')}' has status '{_p.get('status')}' — use live, concept or draft")
PRODUCTS = [p for p in CAT["products"] if p.get("status", "live") in PUBLISHED]

e = html.escape

SLOT_LABEL = "Photo coming soon"


def asset(path):
    """URL for a file under the site root, versioned by its content.

    The HTML changes on every deploy but the CSS/JS URLs did not, so browsers and
    the CDN kept serving stale styles against new markup. A content hash in the
    query string makes a changed file a new URL. Line endings are normalised so a
    Windows checkout and CI produce the same hash.
    """
    with open(os.path.join(ROOT, path.lstrip("/")), "rb") as f:
        body = f.read().replace(b"\r\n", b"\n")
    return f"{path}?v={hashlib.sha256(body).hexdigest()[:10]}"


# `sizes` hints for the frames that can hold a photo: how wide the frame is drawn.
SIZES_HERO = "(min-width: 62em) min(38vw, 560px), 92vw"
SIZES_SHOT = "(min-width: 62em) min(50vw, 760px), (min-width: 48em) 46vw, 92vw"
SIZES_CARD = "(min-width: 62em) min(25vw, 380px), (min-width: 48em) 31vw, 46vw"
SIZES_FEATURE = "(min-width: 62em) min(48vw, 740px), (min-width: 48em) 56vw, 92vw"
SIZES_CAT_A = "(min-width: 62em) min(54vw, 860px), 92vw"
SIZES_CAT_B = "(min-width: 62em) min(38vw, 600px), 92vw"
SIZES_HALF = "(min-width: 62em) min(25vw, 380px), (min-width: 48em) 23vw, 46vw"


def picture(photo, sizes, eager=False):
    """<picture> for a photo made by tools/photos.py: WebP with a JPEG fallback.

    `photo` is {"name": ..., "alt": ...}. The build fails loudly if the photo is
    not in data/photos.json or a file is missing, rather than ship a broken image.
    """
    name, alt = photo.get("name"), (photo.get("alt") or "").strip()
    if name not in PHOTOS:
        raise SystemExit(f"photo '{name}' is not in data/photos.json — run tools/photos.py first")
    if not alt or is_placeholder(alt):
        raise SystemExit(f"photo '{name}' needs real alt text")
    meta = PHOTOS[name]
    widths = meta["widths"]
    for w in widths:
        for ext in ("webp", "jpg"):
            if not os.path.exists(os.path.join(ROOT, "assets", "img", f"{name}-{w}.{ext}")):
                raise SystemExit(f"missing assets/img/{name}-{w}.{ext}")
    rw, rh = (int(x) for x in meta["ratio"].split(":"))
    big = widths[-1]
    srcset = lambda ext: ", ".join(f"/assets/img/{name}-{w}.{ext} {w}w" for w in widths)
    load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return (f'<picture><source type="image/webp" srcset="{srcset("webp")}" sizes="{sizes}">'
            f'<img src="/assets/img/{name}-{big}.jpg" srcset="{srcset("jpg")}" sizes="{sizes}" '
            f'width="{big}" height="{round(big * rh / rw)}" alt="{e(alt)}" {load}></picture>')


def square(photo):
    """The same photo as drawn in a 1:1 frame. A photo may name a `square`
    crop (made with tools/photos.py --ratio 1:1) so a card is composed for its
    frame rather than centre-cut from the 4:5; it keeps the parent's alt text."""
    if photo and photo.get("square"):
        return {"name": photo["square"], "alt": photo.get("alt")}
    return photo


def photo_url(photo):
    """Absolute URL of a photo's largest JPEG, for og:image and JSON-LD."""
    return f"https://{BRAND['domain']}/assets/img/{photo['name']}-{PHOTOS[photo['name']]['widths'][-1]}.jpg"


# Every page shares a picture. Pages without a photo of their own use the three
# lamps side by side — a landscape image, the shape link previews crop to.
SHARE_DEFAULT = {"name": "share-lamps",
                 "alt": "The Pleated, Ribbed and Puffed lamps, each lit on an oak side table."}


def og_image(photo):
    photo = photo or SHARE_DEFAULT
    meta = PHOTOS[photo["name"]]
    rw, rh = (int(x) for x in meta["ratio"].split(":"))
    w = meta["widths"][-1]
    return "\n".join([
        f'<meta property="og:image" content="{photo_url(photo)}">',
        f'<meta property="og:image:width" content="{w}">',
        f'<meta property="og:image:height" content="{round(w * rh / rw)}">',
        f'<meta property="og:image:alt" content="{e(photo.get("alt", ""))}">',
    ])


def slot(cls="", label=SLOT_LABEL, style="", photo=None, sizes=SIZES_CARD, eager=False):
    """A frame for product photography.

    With `photo`, it holds the picture. Without, it is a labelled reserved frame —
    the layout is final either way, so photos drop in without moving anything.
    """
    c = (" " + cls) if cls else ""
    s = f' style="{style}"' if style else ""
    if photo:
        return f'<div class="slot slot--photo{c}"{s}>{picture(photo, sizes, eager)}</div>'
    return f'<div class="slot{c}"{s}><span class="slot__label">{e(label)}</span></div>'


def mailto(subject=None):
    """mailto: link to the shop, with the subject URL-encoded. HTML-escaping alone
    is not enough: an "&" (as in "Sage & white") ends the subject parameter and
    the rest of it is lost."""
    href = f"mailto:{BRAND['email']}"
    if subject:
        href += "?subject=" + quote(subject, safe="")
    return e(href)


def money(v):
    if v is None:
        return ""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return f"{BRAND['currencySymbol']}{s}"


def is_placeholder(v):
    return not v or str(v).strip().upper().startswith("PLACEHOLDER")


# Where a piece can also be bought. Plain text buttons — the site names the
# marketplace, it never carries its logo. (field, label, allowed host pattern)
MARKETS = [
    ("leboncoinUrl", "Leboncoin", r"(^|\.)leboncoin\.fr$"),
    ("vintedUrl", "Vinted", r"(^|\.)vinted\.[a-z]{2,3}(\.[a-z]{2})?$"),
]


def market_links(p):
    """[(label, url)] for the listings a product has, checked at build time.

    A listing is a second public price for the same piece, so the build refuses
    one until `priceConfirmed` says the price here was copied from it. Every
    price in products.json started life as a placeholder.
    """
    links = []
    for field, label, host in MARKETS:
        url = (p.get(field) or "").strip()
        if not url:
            continue
        u = urlparse(url)
        if u.scheme != "https" or not re.search(host, (u.hostname or "").lower()):
            raise SystemExit(f"{p['slug']}: {field} must be an https link to {label}, got {url!r}")
        links.append((label, url))
    if links and not (p.get("priceConfirmed") and p.get("price")):
        raise SystemExit(f"{p['slug']}: has a marketplace listing, so its price must match it — "
                         f"set `price` to the listing price and `priceConfirmed: true`")
    return links


# The spec table reads the same on every product: these rows first, in this
# order, then anything product-specific (a "Water" warning, a "Fits" note) as
# written. A row with no value is not rendered — no dashes, no "TBC".
SPEC_ORDER = ["Dimensions", "Weight", "Material", "Layer height", "Light source", "Heat limit", "Made"]


def spec_rows(p):
    specs = {k: str(v).strip() for k, v in (p.get("specs") or {}).items()
             if v is not None and not is_placeholder(v)}
    known = [(k, specs[k]) for k in SPEC_ORDER if k in specs]
    return known + [(k, v) for k, v in specs.items() if k not in SPEC_ORDER]


HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def colours(p):
    """The product's `colours`, checked: [{"name", "hex", "photo"}].

    Nothing renders until the data exists. Swatches need at least two colours
    that each have a hex and a photo — a swatch that changes nothing on screen is
    worse than a sentence.
    """
    out = []
    for c in p.get("colours") or []:
        name = (c.get("name") or "").strip()
        if not name or is_placeholder(name):
            raise SystemExit(f"{p['slug']}: every colour needs a real name")
        if c.get("hex") and not HEX.match(c["hex"]):
            raise SystemExit(f"{p['slug']}: colour {name!r} hex must look like #A1B2C3, got {c['hex']!r}")
        out.append({"name": name, "hex": c.get("hex"), "photo": c.get("photo")})
    return out


def can_swatch(cols):
    return len(cols) >= 2 and all(c["hex"] and c["photo"] for c in cols)


def lead_photo(p):
    """The picture a product leads with. With working swatches it is the first
    colour's, so the photo matches the colour shown as picked; otherwise the
    first photo, else the first colour's if it has one."""
    photos, cols = p.get("photos") or [], colours(p)
    if can_swatch(cols) or (cols and not photos):
        return cols[0]["photo"]
    return photos[0] if photos else None


def colour_picker(p, cols):
    """A text list of the colours (no JS), and — when every colour has a photo —
    real radio buttons that swap the first frame. site.js unhides the radios and
    hides the list; without it the first colour's photo simply stays."""
    if not cols:
        return ""
    names = ", ".join(c["name"] for c in cols)
    text = (f'<p class="pdp__colours" data-colour-list><span class="label">'
            f'{"Colours" if len(cols) > 1 else "Colour"}</span> {e(names)}</p>')
    if not can_swatch(cols):
        return text
    radios = "".join(
        f'<label class="swatch"><input class="swatch__input" type="radio" name="colour" value="{i}"'
        f' data-name="{e(c["name"])}"{" checked" if i == 0 else ""}>'
        f'<span class="swatch__chip" style="--sw:{c["hex"]}" aria-hidden="true"></span>'
        f'<span class="vh">{e(c["name"])}</span></label>'
        for i, c in enumerate(cols))
    pics = "".join(f'<template data-colour-photo="{i}">{picture(c["photo"], SIZES_SHOT)}</template>'
                   for i, c in enumerate(cols))
    return text + f"""<fieldset class="swatches" data-swatches hidden>
          <legend class="swatches__legend"><span class="label">Colour</span> <span class="swatches__name" data-colour-name>{e(cols[0]['name'])}</span></legend>
          <div class="swatches__row">{radios}</div>{pics}
        </fieldset>"""


def count_words(n, noun):
    """'Six shapes', 'One shape' — headings that count, without going stale."""
    words = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve"]
    return f"{words[n] if n < len(words) else n} {noun}{'' if n == 1 else 's'}"


def related(p, n=4):
    """Up to four pieces for the "More …" row: the rest of the category first,
    closest by shared rooms, then pieces from elsewhere that share a room, so
    the row is always full. Concepts are only used to fill a concept's row."""
    rooms = set(p.get("rooms", []))
    near = lambda q: -len(rooms & set(q.get("rooms", [])))
    pool = [q for q in by_cat(p["category"]) if q["name"] != p["name"]]   # twins are linked up top
    out = sorted(pool, key=near)[:n]
    if len(out) < n and p.get("status") == "concept":
        out += [q for q in by_cat(p["category"], "concept") if q["slug"] != p["slug"]][:n - len(out)]
    if len(out) < n:
        others = [q for q in PRODUCTS if q["category"] != p["category"]
                  and q.get("status", "live") == "live" and rooms & set(q.get("rooms", []))]
        out += sorted(others, key=near)[:n - len(out)]
    return out


def by_cat(slug, status="live"):
    return [p for p in PRODUCTS if p["category"] == slug and p.get("status", "live") == status]


# --------------------------------------------------------------------- shell
def shell(title, desc, body, page="", extra_head="", tone_start="day",
          path="/", og_type="website", share=None):
    """`path` is the page's own URL path (canonical + og:url); `share` the photo
    a shared link previews (defaults to SHARE_DEFAULT)."""
    url = f"https://{BRAND['domain']}{path}"
    nav_items = [
        ("/lamps/", "Lamps", False),
        ("/decorations/", "Decorations", False),
        ("/#how", "How it works", True),
    ]
    links = "".join(
        '<a class="nav__link{sec}" href="{h}"{cur}>{t}</a>'.format(
            sec=" nav__link--sec" if secondary else "",
            h=h, t=t,
            cur=' aria-current="page"' if page and h.startswith("/" + page) else "",
        )
        for h, t, secondary in nav_items
    )
    year = 2026
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="preload" href="/assets/fonts/archivo-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/newsreader-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/vendor/lenis.css">
<link rel="stylesheet" href="{asset('/assets/css/site.css')}">
<meta name="theme-color" content="#EDE7DB">
<link rel="canonical" href="{e(url)}">
<meta property="og:site_name" content="{e(BRAND['name'])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{e(url)}">
<meta name="twitter:card" content="summary_large_image">
{og_image(share)}
{extra_head}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="nav">
  <div class="wrap nav__in">
    <a class="nav__brand" href="/">Cosy&nbsp;Prints</a>
    <nav class="nav__links" aria-label="Main">{links}</nav>
  </div>
</header>

<main id="main">
{body}
</main>

<footer class="foot" data-tone="night">
  <div class="wrap">
    <div class="grid foot__grid">
      <div class="foot__brand">
        <p class="h3" style="color:var(--chalk);max-width:18ch">{e(BRAND['tagline'])}</p>
      </div>
      <div class="foot__col">
        <p class="label foot__title">Shop</p>
        <ul class="foot__list">
          <li><a href="/lamps/">Lamps</a></li>
          <li><a href="/decorations/">Decorations</a></li>
        </ul>
      </div>
      <div class="foot__col">
        <p class="label foot__title">About</p>
        <ul class="foot__list">
          <li><a href="/#how">How it works</a></li>
          <li><a href="/#faq">Questions</a></li>
        </ul>
      </div>
      <div class="foot__col">
        <p class="label foot__title">Contact</p>
        <ul class="foot__list">
          <li><a href="mailto:{e(BRAND['email'])}">{e(BRAND['email'])}</a></li>
          <li><a href="/legal/">Legal &amp; returns</a></li>
        </ul>
      </div>
    </div>
    <div class="foot__base">
      <span>&copy; {year} {e(BRAND['name'])} — printed in {e(BRAND['country'])}</span>
    </div>
  </div>
</footer>

<script src="{asset('/assets/js/site.js')}" defer></script>
</body>
</html>
"""


# ------------------------------------------------------------------- pieces
def product_card(p, feature=False, morph=True):
    price = money(p.get("price"))
    tag = ""
    if p.get("status") == "concept":
        tag = '<span class="pcard__tag">In development</span>'
    rooms = "|".join(p.get("rooms", []))
    cls = "pcard pcard--feature" if feature else "pcard"
    return f"""<a class="{cls}" href="/shop/{p['slug']}/" data-rooms="{e(rooms)}"{' data-morph' if morph else ''}>
  {slot('pcard__media lay', photo=lead_photo(p) if feature else square(lead_photo(p)), sizes=SIZES_FEATURE if feature else SIZES_CARD)}
  <div class="pcard__top">
    <span class="pcard__name">{e(p['name'])}</span>
    <span class="pcard__price">{price or '—'}</span>
  </div>
  <p class="pcard__meta">{e(p.get('variant',''))}</p>
  {tag}
</a>"""


# --------------------------------------------------------------------- home
def build_home():
    lamps = by_cat("lamps")
    decos = by_cat("decorations")
    lamp_cat = next(c for c in CATEGORIES if c["slug"] == "lamps")
    deco_cat = next(c for c in CATEGORIES if c["slug"] == "decorations")

    bens = "".join(f"""<div class="ben rise">
      <div class="ridge ridge--rule ben__rule"></div>
      <h3 class="h3 ben__title">{e(b['title'])}</h3>
      <p class="ben__body">{e(b['body'])}</p>
    </div>""" for b in SITE["benefits"])

    steps = "".join(f"""<li class="step rise">
      <span class="step__n" aria-hidden="true"></span>
      <div class="step__body">
        <h3 class="h3 step__title">{e(s['step'])}</h3>
        <p class="step__text">{e(s['body'])}</p>
      </div>
    </li>""" for s in SITE["howItWorks"])

    trust = "".join(f"""<div class="trust__cell">
      <p class="label trust__label">{e(t['label'])}</p>
      <p class="trust__value">{e(t['value'])}</p>
    </div>""" for t in SITE["trust"])

    faqs = "".join(f"""<details class="qa">
      <summary class="qa__q">{e(q['q'])}<span class="qa__sign" aria-hidden="true"></span></summary>
      <div class="qa__a"><div>{e(q['a'])}</div></div>
    </details>""" for q in SITE["faq"])

    dark_line = """<p class="label" style="margin-bottom:1.4rem">After dark</p>
    <p class="display h2" style="max-width:24ch" data-split>A lamp is the only thing in a room that changes what time it feels like.</p>"""
    dark_photo = SITE.get("afterDark", {}).get("photo")
    if dark_photo:
        after_dark = f"""<section class="sec" data-tone="night">
  <div class="wrap">
    <div class="grid dark__grid">
      <div class="dark__media">{slot('lay', SLOT_LABEL, 'aspect-ratio:4/5', photo=dark_photo, sizes=SIZES_HERO)}</div>
      <div class="dark__copy">{dark_line}</div>
    </div>
  </div>
</section>"""
    else:
        after_dark = f"""<section class="sec" data-tone="night">
  <div class="wrap">
    {dark_line}
  </div>
</section>"""
    hero_photo = SITE.get("hero", {}).get("photo")

    body = f"""
<section class="sec hero" data-tone="day">
  <div class="wrap">
    <div class="grid hero__grid">
      <div class="hero__copy">
        <p class="label hero__eyebrow rise" style="--rd:350ms">3D-printed lighting &amp; objects — made in {e(BRAND['country'])}</p>
        <h1 class="display h1 hero__title lines" style="--rd:450ms">
          <span class="l"><span>Warm light and</span></span>
          <span class="l"><span>small things</span></span>
          <span class="l"><span>for the rooms</span></span>
          <span class="l"><span>you sit in.</span></span>
        </h1>
        <p class="lead hero__lead rise" style="--rd:700ms">We print lighting and small home pieces to order in our own workshop, one at a time. Pick a shape and we make yours.</p>
        <div class="hero__actions rise" style="--rd:950ms">
          <a class="btn" href="/lamps/">Shop lamps</a>
          <a class="tlink" href="/decorations/">Shop decorations <span class="tlink__arrow">&rarr;</span></a>
        </div>
      </div>
      <div class="hero__media">
        {slot('lay', SLOT_LABEL, 'aspect-ratio:4/5', photo=hero_photo, sizes=SIZES_HERO, eager=True)}
      </div>
    </div>
  </div>
</section>

<section class="sec" data-tone="day" id="shop">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">Two ways in</p>
      <h2 class="display h2 shead__title" data-split>Start with the light, or start with the shelf.</h2>
      <p class="lead shead__note">Everything is printed to order, so the two paths work the same way — you are choosing a shape, not picking from what is left in a warehouse.</p>
    </div>
    <div class="grid cats">
      <a class="cat cat--a" href="/lamps/" data-morph>
        {slot('cat__media lay', photo=lamp_cat.get('photo'), sizes=SIZES_CAT_A)}
        <div class="cat__row">
          <h3 class="display h3">Lamps</h3>
          <span class="cat__count">{len(lamps)} pieces</span>
        </div>
        <p class="cat__lead">{e(lamp_cat['lead'])}</p>
      </a>
      <a class="cat cat--b" href="/decorations/" data-morph>
        {slot('cat__media lay', photo=deco_cat.get('photo'), sizes=SIZES_CAT_B)}
        <div class="cat__row">
          <h3 class="display h3">Decorations</h3>
          <span class="cat__count">{len(decos)} pieces</span>
        </div>
        <p class="cat__lead">{e(deco_cat['lead'])}</p>
      </a>
    </div>
  </div>
</section>

<section class="sec" data-tone="day">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">Why these</p>
      <h2 class="display h2 shead__title" data-split>Made slowly, on purpose.</h2>
    </div>
    <div class="grid bens">{bens}</div>
  </div>
</section>

<section class="sec" data-tone="day" id="how">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">How it works</p>
      <h2 class="display h2 shead__title" data-split>Four steps, about ten days.</h2>
      <p class="lead shead__note">Nothing is stocked. That is slower than a warehouse and it is the reason nothing gets thrown away.</p>
    </div>
    <ol class="grid steps">{steps}</ol>
  </div>
</section>

<section class="sec" data-tone="day" style="padding-block:0">
  <div class="wrap"><div class="trust">{trust}</div></div>
</section>

<div class="dusk" aria-hidden="true"></div>

{after_dark}

<section class="sec" data-tone="night" id="faq">
  <div class="wrap">
    <div class="grid faq__grid">
      <div class="faq__side">
        <p class="label" style="margin-bottom:1rem">Questions</p>
        <h2 class="display h3" data-split>The things people ask before ordering.</h2>
      </div>
      <div class="faq__list">{faqs}</div>
    </div>
  </div>
</section>

<section class="sec" data-tone="night">
  <div class="wrap">
    <div class="grid cta__grid">
      <div class="cta__copy">
        <h2 class="display h2" data-split>Start with one piece. See how it sits in the room.</h2>
      </div>
      <div class="cta__side">
        <div class="hero__actions">
          <a class="btn btn--ghost" href="/lamps/">Shop lamps</a>
          <a class="tlink" href="/decorations/">Shop decorations <span class="tlink__arrow">&rarr;</span></a>
        </div>
      </div>
    </div>
  </div>
</section>
"""
    return shell(
        f"{BRAND['name']} — 3D-printed lamps and home decorations",
        "Lamps and small home objects, 3D-printed to order in France. Warm light, plant-based PLA, made by hand in our workshop.",
        body,
        path="/",
    )


# ----------------------------------------------------------------- category
def editorial_grid(items):
    """The catalogue as a magazine spread rather than a uniform grid.

    Each `featured` piece gets a wide 4:5 frame, with up to four of the
    following pieces nested beside it in a tight 2-column grid of 1:1 frames.
    Spreads alternate sides. Whatever is left runs on as plain rows. It is
    built from frames, so it reads the same empty, half-photographed or full.
    When a room filter is on, site.js flattens it back to an even grid
    (`data-filtered`), because holes in a spread look like mistakes.
    """
    feats = [p for p in items if p.get("featured")]
    rest = [p for p in items if not p.get("featured")]
    blocks = []
    for i, f in enumerate(feats):
        nest, rest = rest[:4], rest[4:]
        mods = f" ed__spread--n{len(nest)}" + (" ed__spread--flip" if i % 2 else "")
        nested = "".join(product_card(q) for q in nest)
        blocks.append(f"""<div class="ed__spread{mods}">
      <div class="ed__feature">{product_card(f, feature=True)}</div>
      {f'<div class="ed__nest">{nested}</div>' if nest else ''}
    </div>""")
    if rest:
        n = len(rest) if len(rest) < 4 else 4
        blocks.append(f'<div class="ed__rows ed__rows--n{n}">{"".join(product_card(q) for q in rest)}</div>')
    return f'<div class="ed" data-ed data-batch>{"".join(blocks)}</div>'


def build_category(cat):
    live = by_cat(cat["slug"], "live")
    concepts = by_cat(cat["slug"], "concept")
    rooms = sorted({r for p in live for r in p.get("rooms", [])})

    filters = ""
    if len(rooms) > 1:
        btns = '<button class="filter" data-room="" aria-pressed="true">Everything</button>'
        btns += "".join(f'<button class="filter" data-room="{e(r)}" aria-pressed="false">{e(r)}</button>' for r in rooms)
        filters = f'<div class="filters" data-filters role="group" aria-label="Filter by room">{btns}</div>'


    concept_block = ""
    if concepts:
        cc = "".join(product_card(p, morph=False) for p in concepts)
        concept_block = f"""
<section class="sec" data-tone="night">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">Not yet for sale</p>
      <h2 class="display h2 shead__title" data-split>{count_words(len(concepts), "shape")} we are still working on.</h2>
      <p class="lead shead__note">None of these is in production yet. They are here so you can tell us which one to finish first.</p>
    </div>
    <div class="grid pgrid pgrid--3" data-batch>{cc}</div>
  </div>
</section>"""

    body = f"""
<section class="sec pdp" data-tone="day" style="padding-bottom:clamp(2rem,5vw,4rem)">
  <div class="wrap">
    <div class="shead grid" style="margin-bottom:clamp(2rem,4vw,3rem)">
      <p class="label shead__eyebrow" style="grid-column:1/-1">{len(live)} pieces</p>
      <h1 class="display h2 shead__title lines">
        <span class="l"><span>{e(cat['name'])}</span></span>
      </h1>
      <p class="lead shead__note">{e(cat['lead'])}</p>
    </div>
    {filters}
    <p class="vh" data-filter-count aria-live="polite">{len(live)} pieces</p>
    {editorial_grid(live)}
  </div>
</section>
{concept_block}
"""
    return shell(
        f"{cat['name']} — {BRAND['name']}",
        cat["lead"],
        body,
        page=cat["slug"],
        path=f"/{cat['slug']}/",
    )


# ------------------------------------------------------------------ product
def build_product(p):
    photos = p.get("photos") or []
    # live products sharing this name (Bag Clips black/white): the title needs the
    # variant to tell them apart, and each page links to the others
    twins = [q for q in by_cat(p["category"]) if q["name"] == p["name"] and q["slug"] != p["slug"]]
    twin_html = ""
    if twins:
        links = ", ".join(f'<a href="/shop/{q["slug"]}/">{e(q.get("variant") or q["name"])}</a>' for q in twins)
        twin_html = f'<p class="pdp__colours"><span class="label">Also in</span> {links}</p>\n        '

    cols = colours(p)
    first = lead_photo(p)
    n_shots = int(p.get("shots", 1))
    if n_shots not in (1, 2, 3):
        raise SystemExit(f"{p['slug']}: `shots` must be 1, 2 or 3, got {n_shots}")
    n_shots = max(1, min(n_shots, len(photos)))
    shots = slot("pdp__shot lay", "Shape in development" if p.get("status") == "concept" else SLOT_LABEL,
                 "view-transition-name:hero-media",
                 photo=first, sizes=SIZES_SHOT, eager=True)
    for i, label in list(enumerate(["Second view coming soon", "Third view coming soon"], 1))[:n_shots - 1]:
        shots += slot("pdp__shot lay", label, photo=photos[i] if len(photos) > i else None,
                      sizes=SIZES_HALF if n_shots == 3 else SIZES_SHOT)

    specs = ""
    rows = "".join(f'<div class="pdp__spec"><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in spec_rows(p))
    if rows:
        specs = f'<dl class="pdp__specs">{rows}</dl>'

    concept = p.get("status") == "concept"
    if concept:
        buy = f"""<div class="notice"><strong>Not for sale yet.</strong> This shape is still being worked on, so there is no photo of it yet and nothing to buy. Email us and we will tell you when it is ready.</div>
        <div class="pdp__buy"><a class="btn" href="{mailto(p['name'] + ' — tell me when it is ready')}">Tell me when it is ready</a></div>"""
        price_html = ""
    else:
        markets = market_links(p)
        # with a listing to point at, the site's own route steps back to a fallback
        btn = "btn btn--ghost" if markets else "btn"
        checkout = p.get("checkoutUrl")
        if checkout:
            action = f'<a class="{btn}" href="{e(checkout)}">Add to basket — {money(p["price"])}</a>'
        else:
            # with colours, the subject names the one picked (site.js fills it in);
            # without JS it names none, rather than guess the first
            base = f"Order: {p['name']}"
            subj = base if cols else base + (f" ({p['variant']})" if p.get("variant") else "")
            order = f' data-order="{e(base)}"' if can_swatch(cols) else ""
            action = f'<a class="{btn}" href="{mailto(subj)}"{order}>Order by email</a>'
        market_html = ""
        if markets:
            mbtns = "".join(
                f'<a class="btn" href="{e(url)}" target="_blank" rel="noopener noreferrer">'
                f'Buy on {label}<span class="vh"> (opens in a new tab)</span></a>'
                for label, url in markets)
            where = " or ".join(f"{label}'s" for label, _ in markets)
            market_html = f"""<div class="pdp__buy pdp__buy--market">{mbtns}</div>
        <p class="pdp__note">Payment and delivery go through {where} own checkout, not this site.</p>"""
        buy = f"""{market_html}<div class="pdp__buy">{action}</div>
        <p class="pdp__care">Printed after you order. In the workshop 3–5 working days, then posted with tracking.</p>"""
        price_html = f'<p class="pdp__price">{money(p.get("price"))}</p>'

    care = f'<p class="pdp__care">{e(p["care"])}</p>' if p.get("care") else ""
    other = related(p)
    more = "".join(product_card(q) for q in other)
    more_title = (f"More {next(c['name'] for c in CATEGORIES if c['slug'] == p['category']).lower()}"
                  if all(q["category"] == p["category"] and q.get("status", "live") == "live" for q in other)
                  else "You might also like")

    cat_name = next(c["name"] for c in CATEGORIES if c["slug"] == p["category"])

    body = f"""
<section class="sec pdp" data-tone="day">
  <div class="wrap">
    <p class="label" style="margin-bottom:1.5rem"><a href="/{p['category']}/" style="text-decoration:none">{e(cat_name)}</a></p>
    <div class="grid pdp__grid">
      <div class="pdp__media"><div class="pdp__shots pdp__shots--{n_shots}">{shots}</div></div>
      <div class="pdp__info">
        <h1 class="display h2 pdp__name">{e(p['name'])}</h1>
        <p class="pdp__variant">{e(p.get('variant',''))}</p>
        {twin_html}{price_html}
        {colour_picker(p, cols)}
        <div class="prose pdp__desc"><p>{e(p['description'])}</p></div>
        {buy}
        {specs}
        {care}
      </div>
    </div>
  </div>
</section>

<section class="sec" data-tone="day">
  <div class="wrap">
    <div class="shead grid">
      <h2 class="display h3 shead__title" data-split>{e(more_title)}</h2>
    </div>
    <div class="grid pgrid pgrid--more" data-batch>{more}</div>
  </div>
</section>
"""
    path = f"/shop/{p['slug']}/"
    head = ""
    # Structured data only for things that are for sale. A concept is not a
    # Product yet, and a price only becomes an Offer once it is confirmed —
    # every price in products.json started life as a placeholder.
    if not concept:
        ld = {
            "@context": "https://schema.org", "@type": "Product",
            "name": p["name"], "sku": p["slug"], "url": f"https://{BRAND['domain']}{path}",
            "description": p["blurb"], "brand": {"@type": "Brand", "name": BRAND["name"]},
        }
        pics = [q for q in [first] + photos[1:n_shots] if q]
        if pics:
            ld["image"] = [photo_url(q) for q in pics]
        if p.get("price") and p.get("priceConfirmed"):
            ld["offers"] = {"@type": "Offer", "price": p["price"], "priceCurrency": BRAND["currency"],
                            "availability": "https://schema.org/MadeToOrder",
                            "url": f"https://{BRAND['domain']}{path}"}
        # "</" inside the JSON would end the script element early
        head = ('<script type="application/ld+json">'
                + json.dumps(ld).replace("</", "<\\/") + "</script>")

    if concept:
        title = f"{p['name']} lamp (in development) — {BRAND['name']}"
        desc = f"Not for sale yet. {p['blurb']}"
    else:
        variant = f" — {p['variant']}" if twins and p.get("variant") else ""
        title = f"{p['name']}{variant} — {BRAND['name']}"
        desc = f"{p['blurb']} 3D-printed to order in {BRAND['country']}."
    return shell(title, desc, body, page=p["category"], extra_head=head,
                 path=path, og_type="website" if concept else "product", share=first)


# -------------------------------------------------------------------- legal
def build_legal():
    body = f"""
<section class="sec pdp" data-tone="day">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">Legal</p>
      <h1 class="display h2 shead__title lines"><span class="l"><span>Returns, delivery and privacy</span></span></h1>
    </div>
    <div class="prose" style="max-width:66ch">
      <h2 class="h3">Returns and the right to change your mind</h2>
      <p>You have {SITE['legal']['returnsDays']} days from the day you receive an order to withdraw from it, without giving a reason. Tell us by email and send the item back in a condition we can resell. We refund the item once it arrives.</p>
      <p>{e(SITE['legal']['customExemptionNote'])} In plain terms: a piece printed in a colour you chose specially, or with a name on it, cannot be returned.</p>

      <h2 class="h3" style="margin-top:2.5rem">Delivery</h2>
      <p>Every order is printed after it is placed. Allow 3–5 working days in the workshop, then normal postal time. You get a tracking number on the day it ships.</p>

      <h2 class="h3" style="margin-top:2.5rem">Privacy</h2>
      <p>We set no cookies of our own and run no analytics, advertising or tracking scripts. Our fonts and scripts are served from this site, not loaded from Google or other third parties.</p>
      <p>Like any website, pages reach you through service providers who handle technical data, such as your IP address, in order to deliver them. This site is hosted by GitHub Pages and delivered through Cloudflare, which also protects it from abuse. Cloudflare may set a strictly necessary security cookie to tell visitors from bots.</p>
      <p>If you email us, we keep your message to answer it.</p>

      <h2 class="h3" style="margin-top:2.5rem">Mentions légales</h2>
      <p><strong>Publisher:</strong> {e(BRAND['name'])}, {e(BRAND['country'])}. Contact: <a href="mailto:{e(BRAND['email'])}">{e(BRAND['email'])}</a>. Company registration details will be added to this page.</p>
      <p><strong>Host:</strong> GitHub Pages, GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, USA.</p>
      <p><strong>Content delivery and security:</strong> Cloudflare, Inc., 101 Townsend Street, San Francisco, CA 94107, USA.</p>
    </div>
  </div>
</section>
"""
    return shell(f"Legal — {BRAND['name']}", "Returns, delivery, privacy and legal information.", body,
                 path="/legal/")


# --------------------------------------------------------------------- main
def write(rel, content):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf8", newline="\n").write(content)
    return rel


def prune_product_pages():
    """Delete shop/<slug>/ pages whose product was removed, renamed or set to draft.

    The build only ever wrote pages, so a product taken out of products.json kept
    its old page online for good — gone from the listings and the sitemap, still
    served at its URL with its old price. Only the generated index.html is
    deleted (and the folder, if that leaves it empty); anything else survives.
    """
    shop = os.path.join(ROOT, "shop")
    if not os.path.isdir(shop):
        return []
    keep = {p["slug"] for p in PRODUCTS}
    removed = []
    for slug in sorted(os.listdir(shop)):
        folder = os.path.join(shop, slug)
        page = os.path.join(folder, "index.html")
        if slug in keep or not os.path.isfile(page):
            continue
        os.remove(page)
        if not os.listdir(folder):
            os.rmdir(folder)
        removed.append(f"shop/{slug}/index.html")
    return removed


def main():
    removed = prune_product_pages()
    written = []
    written.append(write("index.html", build_home()))
    for c in CATEGORIES:
        written.append(write(f"{c['slug']}/index.html", build_category(c)))
    for p in PRODUCTS:
        written.append(write(f"shop/{p['slug']}/index.html", build_product(p)))
    written.append(write("legal/index.html", build_legal()))

    # sitemap
    urls = ["/", "/lamps/", "/decorations/", "/legal/"] + [f"/shop/{p['slug']}/" for p in PRODUCTS]
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>https://{BRAND['domain']}{u}</loc></url>\n" for u in urls)
          + "</urlset>\n")
    written.append(write("sitemap.xml", sm))
    written.append(write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: https://{BRAND['domain']}/sitemap.xml\n"))

    print(f"wrote {len(written)} files")
    for w in written:
        print("  ", w)
    if removed:
        print(f"removed {len(removed)} page(s) for products no longer published")
        for r in removed:
            print("  ", r)


if __name__ == "__main__":
    main()
