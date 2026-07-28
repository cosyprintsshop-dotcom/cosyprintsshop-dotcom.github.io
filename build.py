# -*- coding: utf-8 -*-
"""
Cosy Prints static site generator.

    python build.py

Reads data/site.json + data/products.json and writes real HTML files — one per
page, no client-side routing. Real documents are what make cross-document view
transitions and search indexing work.
"""
import json, os, re, shutil, html

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
PROD_DIR = os.path.join(ROOT, "assets", "products")

SITE = json.load(open(os.path.join(DATA, "site.json"), encoding="utf8"))
CAT = json.load(open(os.path.join(DATA, "products.json"), encoding="utf8"))

BRAND = SITE["brand"]
PRODUCTS = [p for p in CAT["products"]]
CATEGORIES = CAT["categories"]

DIMS = {"square": (1600, 1600), "portrait": (1440, 1800), "wide": (2400, 1600)}
SMALL = {"square": 800, "portrait": 720, "wide": 1200}

try:
    MANIFEST = json.load(open(os.path.join(PROD_DIR, "_manifest.json"), encoding="utf8"))
except Exception:
    MANIFEST = {}

e = html.escape


def has(slug, aspect):
    return os.path.exists(os.path.join(PROD_DIR, f"{slug}-{aspect}.webp"))


def pick(slug, want):
    """Fall back to whatever aspect actually got rendered for this slug."""
    for a in [want, "square", "portrait", "wide"]:
        if has(slug, a):
            return a
    return None


def img(slug, aspect="square", alt="", sizes="100vw", eager=False, cls=""):
    a = pick(slug, aspect)
    if a is None:
        return f'<div class="ph" role="img" aria-label="{e(alt)}"></div>'
    w, h = DIMS[a]
    sw = SMALL[a]
    base = f"/assets/products/{slug}-{a}"
    loading = "" if eager else ' loading="lazy"'
    prio = ' fetchpriority="high"' if eager else ""
    c = f' class="{cls}"' if cls else ""
    return (
        "<picture>"
        f'<source type="image/webp" srcset="{base}-{sw}.webp {sw}w, {base}.webp {w}w" sizes="{sizes}">'
        f'<img{c} src="{base}-{sw}.jpg" srcset="{base}-{sw}.jpg {sw}w, {base}.jpg {w}w" sizes="{sizes}" '
        f'width="{w}" height="{h}" alt="{e(alt)}" decoding="async"{loading}{prio}>'
        "</picture>"
    )


def money(v):
    if v is None:
        return ""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return f"{BRAND['currencySymbol']}{s}"


def prod_alt(p, i=0):
    base = f"{p['name']}, {p['variant']}" if p.get("variant") else p["name"]
    return base if i == 0 else f"{base} — alternative view"


def by_cat(slug, status="live"):
    return [p for p in PRODUCTS if p["category"] == slug and p.get("status", "live") == status]


# --------------------------------------------------------------------- shell
def shell(title, desc, body, page="", extra_head="", tone_start="day"):
    nav_items = [
        ("/lamps/", "Lamps", False),
        ("/decorations/", "Decorations", False),
        ("/#how", "How it works", True),
        ("/#give", "Giving back", True),
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
<link rel="stylesheet" href="/assets/css/site.css">
<meta name="theme-color" content="#EDE7DB">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
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
          <li><a href="/#give">Giving back</a></li>
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
      <span>{SITE['donation']['share']}% of revenue goes to our local hospital</span>
    </div>
  </div>
</footer>

<script src="/assets/js/site.js" defer></script>
</body>
</html>
"""


# ------------------------------------------------------------------- pieces
def product_card(p, lead=False, morph=True):
    imgs = p.get("images", [])
    first = imgs[0] if imgs else ""
    second = imgs[1] if len(imgs) > 1 else ""
    sizes = "(min-width:62em) 22vw, (min-width:48em) 30vw, 46vw"
    if lead:
        sizes = "(min-width:62em) 46vw, 92vw"
    alt_img = ""
    if second and pick(second, "square"):
        a2 = pick(second, "square")
        b2 = f"/assets/products/{second}-{a2}"
        alt_img = (
            f'<img class="alt" src="{b2}-{SMALL[a2]}.jpg" width="{DIMS[a2][0]}" height="{DIMS[a2][1]}" '
            f'alt="" aria-hidden="true" loading="lazy" decoding="async">'
        )
    price = money(p.get("price"))
    tag = ""
    if p.get("status") == "concept":
        tag = '<span class="pcard__tag">Design render — in development</span>'
    rooms = "|".join(p.get("rooms", []))
    return f"""<a class="pcard" href="/shop/{p['slug']}/" data-rooms="{e(rooms)}"{' data-morph' if morph else ''}>
  <div class="pcard__media lay">{img(first, 'square', prod_alt(p), sizes, cls='primary')}{alt_img}</div>
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

    d = SITE["donation"]
    hosp = d["recipientName"]

    body = f"""
<section class="sec hero" data-tone="day">
  <div class="wrap">
    <div class="grid hero__grid">
      <div class="hero__copy">
        <p class="label hero__eyebrow" data-hero-eyebrow>3D-printed lighting &amp; objects — made in {e(BRAND['country'])}</p>
        <h1 class="display h1 hero__title lines">
          <span class="l"><span>Warm light and</span></span>
          <span class="l"><span>small things</span></span>
          <span class="l"><span>for the rooms</span></span>
          <span class="l"><span>you sit in.</span></span>
        </h1>
        <p class="lead hero__lead">We print lighting and small home pieces to order in our own workshop, one at a time. Pick a shape, pick a finish, and we make yours.</p>
        <div class="hero__actions" data-hero-cta>
          <a class="btn" href="/lamps/">Shop lamps</a>
          <a class="tlink" href="/decorations/">Shop decorations <span class="tlink__arrow">&rarr;</span></a>
        </div>
      </div>
      <div class="hero__media">
        <div class="figure" style="aspect-ratio:4/5" data-hero-media>
          {img('lamp-black', 'portrait', 'The Ridge Lamp in ink black, unlit', '(min-width:62em) 46vw, 92vw', eager=True)}
        </div>
      </div>
    </div>
  </div>
</section>

<section class="sec" data-tone="day" id="shop">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">Two ways in</p>
      <h2 class="display h2 shead__title" data-split>Start with the light, or start with the shelf.</h2>
      <p class="lead shead__note">Everything is printed to order, so the two paths work the same way — you are choosing a shape and a finish, not picking from what is left in a warehouse.</p>
    </div>
    <div class="grid cats">
      <a class="cat cat--a" href="/lamps/" data-morph>
        <div class="cat__media figure lay" style="aspect-ratio:4/5">
          {img(lamp_cat['cover'], 'portrait', 'The Ridge Lamp on a rose gold base', '(min-width:62em) 56vw, 92vw')}
        </div>
        <div class="cat__row">
          <h3 class="display h3">Lamps</h3>
          <span class="cat__count">{len(lamps)} pieces</span>
        </div>
        <p class="cat__lead">{e(lamp_cat['lead'])}</p>
      </a>
      <a class="cat cat--b" href="/decorations/" data-morph>
        <div class="cat__media figure lay" style="aspect-ratio:4/5">
          {img(deco_cat['cover'], 'portrait', 'A pair of ribbed Japandi cats', '(min-width:62em) 30vw, 92vw')}
        </div>
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
      <h2 class="display h2 shead__title" data-split>Four steps, about a week.</h2>
      <p class="lead shead__note">Nothing is stocked. That is slower than a warehouse and it is the reason nothing gets thrown away.</p>
    </div>
    <ol class="grid steps">{steps}</ol>
  </div>
</section>

<section class="sec" data-tone="day" style="padding-block:0">
  <div class="wrap"><div class="trust">{trust}</div></div>
</section>

<div class="dusk" aria-hidden="true"></div>

<section class="sec" data-tone="night" style="padding-block:0">
  <div class="figure lay" style="aspect-ratio:3/2" data-glow>
    {img('lamp-black-lit', 'wide', 'A Ridge Lamp glowing in a dark room', '100vw')}
  </div>
</section>

<section class="sec" data-tone="night" id="give">
  <div class="wrap">
    <div class="grid give__grid">
      <div class="give__copy">
        <p class="label" style="margin-bottom:1rem">Giving back</p>
        <p class="give__share">{d['share']}%</p>
        <h2 class="display h2" style="margin-bottom:1.4rem" data-split>of revenue goes to our local hospital.</h2>
        <div class="prose">
          <p>Not ten percent of profit — ten percent of revenue. It comes off the top, so it is paid in a bad month as well as a good one.</p>
          <p>It goes to {e(hosp)}{(', ' + e(d['recipientCity'])) if d.get('recipientCity') else ''}. We publish what we sent and when, once a quarter, because a claim like this is worth nothing if you cannot check it.</p>
        </div>
      </div>
      <div class="give__facts">
        <dl class="give__list">
          <div class="give__item"><dt>Share</dt><dd>{d['share']}% of revenue, before costs</dd></div>
          <div class="give__item"><dt>Paid</dt><dd>Quarterly, with the amount published</dd></div>
          <div class="give__item"><dt>Recipient</dt><dd>{e(hosp)}</dd></div>
        </dl>
      </div>
    </div>
  </div>
</section>

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
        "Lamps and small home objects, 3D-printed to order in France. Warm light, plant-based PLA, and 10% of revenue to our local hospital.",
        body,
    )


# ----------------------------------------------------------------- category
def build_category(cat):
    live = by_cat(cat["slug"], "live")
    concepts = by_cat(cat["slug"], "concept")
    rooms = sorted({r for p in live for r in p.get("rooms", [])})

    filters = ""
    if len(rooms) > 1:
        btns = '<button class="filter" data-room="" aria-pressed="true">Everything</button>'
        btns += "".join(f'<button class="filter" data-room="{e(r)}" aria-pressed="false">{e(r)}</button>' for r in rooms)
        filters = f'<div class="filters" data-filters role="group" aria-label="Filter by room">{btns}</div>'

    cards = "".join(product_card(p, lead=(i == 0)) for i, p in enumerate(live))

    concept_block = ""
    if concepts:
        cc = "".join(product_card(p, morph=False) for p in concepts)
        concept_block = f"""
<section class="sec" data-tone="night">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">Not yet for sale</p>
      <h2 class="display h2 shead__title" data-split>Six shapes we are still working on.</h2>
      <p class="lead shead__note">These are design renders, not photographs, and none of them is in production yet. They are here so you can tell us which one to finish first.</p>
    </div>
    <div class="grid pgrid" data-batch>{cc}</div>
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
    <div class="grid pgrid pgrid--lead" data-batch>{cards}</div>
  </div>
</section>
{concept_block}
"""
    return shell(
        f"{cat['name']} — {BRAND['name']}",
        cat["lead"],
        body,
        page=cat["slug"],
    )


# ------------------------------------------------------------------ product
def build_product(p):
    imgs = [s for s in p.get("images", []) if pick(s, "portrait")]
    shots = ""
    for i, s in enumerate(imgs):
        a = pick(s, "portrait" if i == 0 else "square")
        vt = ' style="view-transition-name:hero-media"' if i == 0 else ""
        shots += f'<div class="pdp__shot lay"{vt}>{img(s, a, prod_alt(p, i), "(min-width:62em) 56vw, 92vw", eager=(i == 0))}</div>'

    specs = ""
    if p.get("specs"):
        rows = "".join(f'<div class="pdp__spec"><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in p["specs"].items())
        specs = f'<dl class="pdp__specs">{rows}</dl>'

    concept = p.get("status") == "concept"
    if concept:
        buy = f"""<div class="notice"><strong>Not for sale yet.</strong> The image on this page is a design render, not a photograph of a finished piece. Email us if you want to be told when it is ready.</div>
        <div class="pdp__buy"><a class="btn" href="mailto:{e(BRAND['email'])}?subject={e(p['name'])}%20—%20tell%20me%20when%20it%20is%20ready">Tell me when it is ready</a></div>"""
        price_html = ""
    else:
        checkout = p.get("checkoutUrl")
        if checkout:
            action = f'<a class="btn" href="{e(checkout)}">Add to basket — {money(p["price"])}</a>'
        else:
            subj = f"Order: {p['name']}" + (f" ({p['variant']})" if p.get("variant") else "")
            action = f'<a class="btn" href="mailto:{e(BRAND["email"])}?subject={e(subj)}">Order by email</a>'
        buy = f"""<div class="pdp__buy">{action}</div>
        <p class="pdp__care">Printed after you order. In the workshop 3–5 working days, then posted with tracking.</p>"""
        price_html = f'<p class="pdp__price">{money(p.get("price"))}</p>'

    care = f'<p class="pdp__care">{e(p["care"])}</p>' if p.get("care") else ""
    other = [q for q in by_cat(p["category"]) if q["slug"] != p["slug"]][:4]
    more = "".join(product_card(q) for q in other)

    cat_name = next(c["name"] for c in CATEGORIES if c["slug"] == p["category"])

    body = f"""
<section class="sec pdp" data-tone="day">
  <div class="wrap">
    <p class="label" style="margin-bottom:1.5rem"><a href="/{p['category']}/" style="text-decoration:none">{e(cat_name)}</a></p>
    <div class="grid pdp__grid">
      <div class="pdp__media"><div class="pdp__shots">{shots}</div></div>
      <div class="pdp__info">
        <h1 class="display h2 pdp__name">{e(p['name'])}</h1>
        <p class="pdp__variant">{e(p.get('variant',''))}</p>
        {price_html}
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
      <h2 class="display h3 shead__title" data-split>More {e(cat_name.lower())}</h2>
    </div>
    <div class="grid pgrid" data-batch>{more}</div>
  </div>
</section>
"""
    ld = {
        "@context": "https://schema.org", "@type": "Product",
        "name": f"{p['name']} {p.get('variant','')}".strip(),
        "description": p["blurb"], "brand": {"@type": "Brand", "name": BRAND["name"]},
    }
    if p.get("price") and not concept:
        ld["offers"] = {"@type": "Offer", "price": p["price"], "priceCurrency": BRAND["currency"],
                        "availability": "https://schema.org/MadeToOrder"}
    head = f'<script type="application/ld+json">{json.dumps(ld)}</script>'

    return shell(f"{p['name']} — {BRAND['name']}", p["blurb"], body, page=p["category"], extra_head=head)


# -------------------------------------------------------------------- legal
def build_legal():
    body = f"""
<section class="sec pdp" data-tone="day">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">Legal</p>
      <h1 class="display h2 shead__title lines"><span class="l"><span>Terms, returns and privacy</span></span></h1>
    </div>
    <div class="prose" style="max-width:66ch">
      <div class="notice"><strong>Incomplete.</strong> The sections below are drafted but need your real company details before this site goes live. A French online shop must publish mentions légales (legal form, SIREN, registered address, publication director and host), CGV, and a cookie/privacy notice.</div>

      <h2 class="h3" style="margin-top:2.5rem">Returns and the right to change your mind</h2>
      <p>You have {SITE['legal']['returnsDays']} days from the day you receive an order to withdraw from it, without giving a reason. Tell us by email and send the item back in a condition we can resell. We refund the item once it arrives.</p>
      <p>{e(SITE['legal']['customExemptionNote'])} In plain terms: a piece printed in a colour you chose specially, or with a name on it, cannot be returned.</p>

      <h2 class="h3" style="margin-top:2.5rem">Delivery</h2>
      <p>Every order is printed after it is placed. Allow 3–5 working days in the workshop, then normal postal time. You get a tracking number on the day it ships.</p>

      <h2 class="h3" style="margin-top:2.5rem">The 10% donation</h2>
      <p>Ten percent of revenue — not profit — is paid to {e(SITE['donation']['recipientName'])}. We publish the amount and the date quarterly. If you want the receipts, ask.</p>

      <h2 class="h3" style="margin-top:2.5rem">Privacy</h2>
      <p>This site sets no cookies and runs no analytics or third-party trackers. Fonts and scripts are served from this domain, not from a CDN, so loading a page tells nobody but us that you were here. If you email us, we keep the email to answer it.</p>

      <h2 class="h3" style="margin-top:2.5rem">Mentions légales</h2>
      <p><em>To be completed: legal form, share capital, SIREN/SIRET, registered address, VAT status, publication director, and hosting provider (GitHub Pages, GitHub Inc., 88 Colin P. Kelly Jr. St, San Francisco, CA 94107, USA).</em></p>
    </div>
  </div>
</section>
"""
    return shell(f"Legal — {BRAND['name']}", "Returns, delivery, privacy and legal information.", body)


# --------------------------------------------------------------------- main
def write(rel, content):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf8", newline="\n").write(content)
    return rel


def main():
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


if __name__ == "__main__":
    main()
