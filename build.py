# -*- coding: utf-8 -*-
"""
Cosy Prints static site generator.

    python build.py

Reads the data in data/ and writes real HTML files — one per page and language,
no client-side routing. Real documents are what make cross-document view
transitions and search indexing work.

Languages: French is the main language and lives at the site root (/, /lamps/,
/shop/<slug>/ …); English is a full copy under /en/. The words come from:
  data/site.json + data/products.json   English, and everything that is not words
  data/site.fr.json + data/products.fr.json   the French for those
  data/ui.json                          fixed interface text, both languages
A published page with any French missing stops the build.
"""
import json, os, re, html, hashlib
from urllib.parse import urlparse, quote

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf8") as f:
        return json.load(f)


SITE_EN = load("site.json")
CAT = load("products.json")
UI = load("ui.json")
SITE_FR = load("site.fr.json")
CAT_FR = load("products.fr.json")
PHOTOS = load("photos.json") if os.path.exists(os.path.join(DATA, "photos.json")) else {}

# ------------------------------------------------------------------ languages
LANGS = ("fr", "en")
DEFAULT_LANG = "fr"                  # served at the root; every other language under /<code>/
LANG_NAME = {"fr": "Français", "en": "English"}   # each written in its own language
LOCALE = {"fr": "fr_FR", "en": "en_GB"}
L = DEFAULT_LANG                     # the language being built right now (see main)


def _typo(v):
    """French typography: a narrow no-break space before : ; ? ! so the mark never
    wraps onto a line of its own."""
    if isinstance(v, str):
        return re.sub(r" ([:;?!])", " \\1", v)
    if isinstance(v, list):
        return [_typo(x) for x in v]
    if isinstance(v, dict):
        return {k: _typo(x) for k, x in v.items()}
    return v


for _k, _v in UI.items():
    if _k.startswith("_"):
        continue
    missing = [lang for lang in LANGS if lang not in _v]
    if missing:
        raise SystemExit(f"ui.json: {_k!r} has no {', '.join(missing)} text")
    _v["fr"] = _typo(_v["fr"])
SITE_FR = _typo(SITE_FR)
CAT_FR = _typo(CAT_FR)


def overlay(base, over, where):
    """The English data with the French words laid over it. The French file may
    only hold keys the English has, and lists must match item for item."""
    if isinstance(over, dict):
        if not isinstance(base, dict):
            raise SystemExit(f"{where}: is a group in French but not in English")
        out = dict(base)
        for k, v in over.items():
            if k.startswith("_"):
                continue
            if k not in base:
                raise SystemExit(f"{where}.{k}: not in the English file — a typo?")
            out[k] = overlay(base[k], v, f"{where}.{k}")
        return out
    if isinstance(over, list):
        if not isinstance(base, list) or len(base) != len(over):
            raise SystemExit(f"{where}: needs {len(base)} items to match the English, has {len(over)}")
        for i, (b, o) in enumerate(zip(base, over)):
            if isinstance(b, dict) and isinstance(o, dict) and set(b) - set(o):
                raise SystemExit(f"{where}[{i}]: missing French for {', '.join(sorted(set(b) - set(o)))}")
        return [overlay(b, o, f"{where}[{i}]") for i, (b, o) in enumerate(zip(base, over))]
    return over


# These parts of site.json are words, so each needs its French in site.fr.json.
FR_REQUIRED = ["brand.tagline", "shipping.workshopTime", "howItWorks", "benefits", "trust", "faq",
               "legal.customExemptionNote"]
if (SITE_EN.get("hero") or {}).get("photo"):
    FR_REQUIRED.append("hero.photo.alt")
for _path in FR_REQUIRED:
    _d = SITE_FR
    for _part in _path.split("."):
        if not isinstance(_d, dict) or _part not in _d:
            raise SystemExit(f"site.fr.json: missing French for {_path}")
        _d = _d[_part]


def _fill(v, tokens, where):
    """Figures that appear all over the copy are set once and written as {tokens}
    (shipping time, returns window), so changing one can never leave a stale copy
    behind. An unknown {token} stops the build."""
    if isinstance(v, str):
        out = re.sub(r"\{(\w+)\}", lambda m: tokens.get(m.group(1), m.group(0)), v)
        left = re.findall(r"\{(\w+)\}", out)
        if left:
            raise SystemExit(f"{where}: unknown {{{left[0]}}} — use one of "
                             + ", ".join("{" + k + "}" for k in tokens))
        return out
    if isinstance(v, list):
        return [_fill(x, tokens, f"{where}[{i}]") for i, x in enumerate(v)]
    if isinstance(v, dict):
        return {k: _fill(x, tokens, f"{where}.{k}") for k, x in v.items()}
    return v


SITES = {}
for _lang in LANGS:
    _raw = SITE_EN if _lang == "en" else overlay(SITE_EN, SITE_FR, f"site.{_lang}.json")
    _tokens = {"workshopTime": _raw["shipping"]["workshopTime"], "returnsDays": str(_raw["legal"]["returnsDays"])}
    SITES[_lang] = _fill(_raw, _tokens, f"site.{_lang}.json" if _lang != "en" else "site.json")


def S():
    """site.json, in the language being built."""
    return SITES[L]


def T(key, **kw):
    """Fixed interface text from ui.json, in the language being built."""
    try:
        s = UI[key][L]
    except KeyError:
        raise SystemExit(f"ui.json: no {L!r} text for {key!r}")
    return s.format(**kw) if kw else s


def U(path, lang=None):
    """A site path in a language: /lamps/ stays /lamps/ in the main language and
    becomes /en/lamps/ in English."""
    lang = lang or L
    return path if lang == DEFAULT_LANG else f"/{lang}{path}"


BRAND = SITE_EN["brand"]
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

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate():
    """Check the catalogue before anything is written, and report every problem
    at once. Before this, a misspelt category crashed with a bare StopIteration
    and a duplicated slug silently overwrote the other product's page."""
    errs = []
    cat_slugs = [c.get("slug") for c in CATEGORIES]
    for c in CATEGORIES:
        for k in ("slug", "name", "lead"):
            if not c.get(k):
                errs.append(f"category {c.get('slug') or '?'}: missing `{k}`")
    for s in sorted({s for s in cat_slugs if cat_slugs.count(s) > 1}):
        errs.append(f"category {s!r}: slug used twice")
    for need in ("lamps", "decorations"):
        if need not in cat_slugs:
            errs.append(f"the homepage needs a {need!r} category")
    seen = set()
    for p in CAT["products"]:
        s = p.get("slug") or "?"
        if not SLUG.match(s):
            errs.append(f"product {s!r}: slug must be lowercase-with-dashes")
        if s in seen:
            errs.append(f"product {s!r}: slug used twice — one page would overwrite the other")
        seen.add(s)
        if p.get("status", "live") == "draft":
            continue
        for k in ("name", "category", "blurb", "description"):
            if not p.get(k):
                errs.append(f"product {s!r}: missing `{k}`")
        if p.get("category") and p["category"] not in cat_slugs:
            errs.append(f"product {s!r}: category {p['category']!r} does not exist")
        if p.get("shots", 1) not in (1, 2):
            errs.append(f"product {s!r}: `shots` must be 1 or 2")
        price = p.get("price")
        if price is not None and (isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0):
            errs.append(f"product {s!r}: `price` must be a number or null")
        if p.get("checkoutUrl") and not price:
            errs.append(f"product {s!r}: a `checkoutUrl` needs a `price` for the button")
    if errs:
        raise SystemExit("products.json has problems:\n  - " + "\n  - ".join(errs))


def validate_french():
    """Every published page must exist in French in full: a language switch that
    lands on half-English pages is worse than no switch."""
    errs = []
    for c in CATEGORIES:
        fc = CAT_FR.get("categories", {}).get(c["slug"], {})
        for k in ("name", "lead"):
            if not fc.get(k):
                errs.append(f"category {c['slug']!r}: no French `{k}`")
    rooms = CAT_FR.get("rooms", {})
    for room in sorted({r for p in PRODUCTS for r in p.get("rooms", [])}):
        if not rooms.get(room):
            errs.append(f"room {room!r}: no French name in `rooms`")
    values = CAT_FR.get("specValues", {})
    for p in PRODUCTS:
        s, fp = p["slug"], CAT_FR.get("products", {}).get(p["slug"], {})
        for k in ("name", "blurb", "description") + tuple(k for k in ("variant", "care") if p.get(k)):
            if not fp.get(k):
                errs.append(f"product {s!r}: no French `{k}`")
        for k, v in (p.get("specs") or {}).items():
            if v is None or is_placeholder(v):
                continue
            if f"spec.{k}" not in UI:
                errs.append(f"spec {k!r}: no label in ui.json (add \"spec.{k}\")")
            if not ((fp.get("specs") or {}).get(k) or values.get(str(v).strip())):
                errs.append(f"product {s!r}: no French for spec {k}: {v!r}")
        if p.get("photos") and len(fp.get("photoAlts") or []) != len(p["photos"]):
            errs.append(f"product {s!r}: needs one French alt text per photo in `photoAlts`")
        if p.get("colours") and len(fp.get("colours") or []) != len(p["colours"]):
            errs.append(f"product {s!r}: needs French `colours` (name and alt) for each colour")
    if errs:
        raise SystemExit("products.fr.json is missing French:\n  - " + "\n  - ".join(errs))


e = html.escape


def is_placeholder(v):
    return not v or str(v).strip().upper().startswith("PLACEHOLDER")


validate()
validate_french()


# ------------------------------------------------- words for a product / category
def _fr_product(p):
    return CAT_FR.get("products", {}).get(p["slug"], {})


def PT(p, field):
    """A product's text field in the language being built."""
    return (p.get(field) if L == "en" else _fr_product(p).get(field)) or ""


def CT(c, field):
    """A category's name or lead in the language being built."""
    return c[field] if L == "en" else CAT_FR["categories"][c["slug"]][field]


def room_name(r):
    return r if L == "en" else CAT_FR["rooms"][r]


def photos_of(p):
    """The product's photos, with alt text in the language being built."""
    ph = p.get("photos") or []
    if L == "en" or not ph:
        return ph
    return [dict(x, alt=a) for x, a in zip(ph, _fr_product(p)["photoAlts"])]


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


# The motion libraries site.js fetches, versioned like everything else. They
# reach site.js as `data-vendor` on its script tag, so an updated library can
# never be served stale from a cache.
VENDOR = {n: asset(f"/assets/vendor/{n}")
          for n in ("lenis.min.js", "gsap.min.js", "ScrollTrigger.min.js", "SplitText.min.js", "lenis.css")}

# `sizes` hints for the frames that can hold a photo: how wide the frame is drawn.
SIZES_HERO = "(min-width: 62em) min(38vw, 560px), 92vw"
SIZES_SHOT = "(min-width: 62em) min(50vw, 760px), 92vw"
SIZES_CARD = "(min-width: 62em) min(25vw, 380px), (min-width: 40em) 46vw, 92vw"
SIZES_FEATURE = "(min-width: 62em) min(48vw, 740px), (min-width: 48em) 56vw, 92vw"


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


def photo_url(photo):
    """Absolute URL of a photo's largest JPEG, for search engines and link previews."""
    name = photo["name"]
    return f"https://{BRAND['domain']}/assets/img/{name}-{PHOTOS[name]['widths'][-1]}.jpg"


def mailto(subject):
    """A mailto link to the shop with the subject URL-encoded. HTML escaping alone
    left a name containing & or # able to cut the subject short."""
    return e(f"mailto:{BRAND['email']}?subject={quote(subject)}")


def slot(cls="", label=None, style="", photo=None, sizes=SIZES_CARD, eager=False):
    """A frame for product photography.

    With `photo`, it holds the picture. Without, it is a labelled reserved frame —
    the layout is final either way, so photos drop in without moving anything.
    """
    c = (" " + cls) if cls else ""
    s = f' style="{style}"' if style else ""
    if photo:
        return f'<div class="slot slot--photo{c}"{s}>{picture(photo, sizes, eager)}</div>'
    return f'<div class="slot{c}"{s}><span class="slot__label">{e(label or T("slot.photo"))}</span></div>'


def money(v):
    """€59 in English, 59 € in French."""
    if v is None:
        return ""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    if L == "fr":
        return s.replace(".", ",") + " " + BRAND["currencySymbol"]
    return f"{BRAND['currencySymbol']}{s}"


_WORDS = {
    "en": "zero one two three four five six seven eight nine ten eleven twelve".split(),
    "fr": "zéro un deux trois quatre cinq six sept huit neuf dix onze douze".split(),
}


def count(n, noun, cap=False):
    """'Six shapes', 'Une forme' — counts written out in copy, worked out from the
    data instead of typed in, so they cannot go stale. `noun` is a ui.json key
    holding [singular, plural] (+ "f" for a French feminine noun)."""
    forms = T(noun)
    words = _WORDS[L]
    w = words[n] if n < len(words) else str(n)
    if L == "fr" and n == 1 and len(forms) > 2 and forms[2] == "f":
        w = "une"
    return f"{w[:1].upper() + w[1:] if cap else w} {forms[0] if n == 1 else forms[1]}"


def pieces(n):
    return T("pieces.one" if n == 1 else "pieces.many").replace("{n}", str(n))


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
    """[(label, value)] in the language being built. The keys in products.json are
    the English labels; ui.json holds their translations, products.fr.json the
    values (per product, else from the shared `specValues`)."""
    specs = {k: str(v).strip() for k, v in (p.get("specs") or {}).items()
             if v is not None and not is_placeholder(v)}
    rows = [(k, specs[k]) for k in SPEC_ORDER if k in specs] + \
           [(k, v) for k, v in specs.items() if k not in SPEC_ORDER]
    if L == "en":
        return rows
    own = _fr_product(p).get("specs") or {}
    return [(T(f"spec.{k}"), own.get(k) or CAT_FR["specValues"][v]) for k, v in rows]


HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def colours(p):
    """The product's `colours`, checked: [{"name", "hex", "photo"}], with names and
    photo alt text in the language being built.

    Nothing renders until the data exists. Swatches need at least two colours
    that each have a hex and a photo — a swatch that changes nothing on screen is
    worse than a sentence.
    """
    out = []
    fr = _fr_product(p).get("colours") or [] if L != "en" else []
    for i, c in enumerate(p.get("colours") or []):
        name = (c.get("name") or "").strip()
        if not name or is_placeholder(name):
            raise SystemExit(f"{p['slug']}: every colour needs a real name")
        if c.get("hex") and not HEX.match(c["hex"]):
            raise SystemExit(f"{p['slug']}: colour {name!r} hex must look like #A1B2C3, got {c['hex']!r}")
        photo = c.get("photo")
        if fr:
            name = fr[i].get("name") or name
            if photo and fr[i].get("alt"):
                photo = dict(photo, alt=fr[i]["alt"])
        out.append({"name": name, "hex": c.get("hex"), "photo": photo})
    return out


def can_swatch(cols):
    return len(cols) >= 2 and all(c["hex"] and c["photo"] for c in cols)


def lead_photo(p):
    """The picture a product leads with. With working swatches it is the first
    colour's, so the photo matches the colour shown as picked; otherwise the
    first photo, else the first colour's if it has one."""
    photos, cols = photos_of(p), colours(p)
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
            f'{e(T("pdp.colours") if len(cols) > 1 else T("pdp.colour"))}</span> {e(names)}</p>')
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
          <legend class="swatches__legend"><span class="label">{e(T("pdp.colour"))}</span> <span class="swatches__name" data-colour-name>{e(cols[0]['name'])}</span></legend>
          <div class="swatches__row">{radios}</div>{pics}
        </fieldset>"""


def by_cat(slug, status="live"):
    return [p for p in PRODUCTS if p["category"] == slug and p.get("status", "live") == status]


# --------------------------------------------------------------------- shell
def lang_switch(path):
    """The language toggle beside the brand. With two languages it is one link
    that names the other language in that language ("English" on a French page,
    "Français" on an English one) and keeps the visitor on the same page. Narrow
    screens show the two-letter code; the full name stays the link's text."""
    links = []
    for x in LANGS:
        if x == L:
            continue
        links.append(f'<a class="lang" href="{U(path or "/", x)}" hreflang="{x}" lang="{x}">'
                     f'<span class="lang__long">{LANG_NAME[x]}</span>'
                     f'<span class="lang__short" aria-hidden="true">{x.upper()}</span></a>')
    return "".join(links)


def shell(title, desc, body, page="", extra_head="", tone_start="day", current="page", path=None, image=None):
    """`page` is the category the page belongs to. On the category page itself the
    nav link is the current page; on a product page (`current="true"`) it only
    marks the section the visitor is in.

    `path` is the page's address without the language prefix (/lamps/). It gives
    the canonical URL, the other-language alternates and the language switch's
    target. `image` (a photo, else the hero photo) is what a shared link shows in
    WhatsApp, Messenger and the like."""
    img = image or S().get("hero", {}).get("photo")
    domain = f"https://{BRAND['domain']}"
    meta = [f'<meta property="og:locale" content="{LOCALE[L]}">']
    meta += [f'<meta property="og:locale:alternate" content="{LOCALE[x]}">' for x in LANGS if x != L]
    if path:
        url = domain + U(path)
        meta += [f'<link rel="canonical" href="{e(url)}">', f'<meta property="og:url" content="{e(url)}">']
        meta += [f'<link rel="alternate" hreflang="{x}" href="{e(domain + U(path, x))}">' for x in LANGS]
        meta.append(f'<link rel="alternate" hreflang="x-default" href="{e(domain + U(path, DEFAULT_LANG))}">')
    if img:
        meta += [f'<meta property="og:image" content="{e(photo_url(img))}">',
                 f'<meta property="og:image:alt" content="{e(img["alt"])}">',
                 '<meta name="twitter:card" content="summary_large_image">']
    meta_html = "\n".join(meta)
    nav_items = [(f"/{c['slug']}/", CT(c, "name"), False) for c in CATEGORIES] + [("/#how", T("nav.how"), True)]
    links = "".join(
        '<a class="nav__link{sec}" href="{h}"{cur}>{t}</a>'.format(
            sec=" nav__link--sec" if secondary else "",
            h=U(h), t=e(t),
            cur=f' aria-current="{current}"' if page and h.startswith("/" + page) else "",
        )
        for h, t, secondary in nav_items
    )
    shop_links = "".join(f'<li><a href="{U("/" + c["slug"] + "/")}">{e(CT(c, "name"))}</a></li>' for c in CATEGORIES)
    # the year of first publication — a copyright line does not need bumping each January
    year = BRAND["copyrightYear"]
    return f"""<!doctype html>
<html lang="{L}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="preload" href="/assets/fonts/archivo-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/newsreader-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{asset('/assets/css/fonts.css')}">
<link rel="stylesheet" href="{asset('/assets/css/site.css')}">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta name="theme-color" content="#EDE7DB">
<meta property="og:site_name" content="{e(BRAND['name'])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
{meta_html}
{extra_head}
</head>
<body>
<a class="skip" href="#main">{e(T("nav.skip"))}</a>

<header class="nav">
  <div class="wrap nav__in">
    <div class="nav__start">
      <a class="nav__brand" href="{U('/')}">Cosy&nbsp;Prints</a>
      <span class="nav__sep" aria-hidden="true"></span>
      {lang_switch(path)}
    </div>
    <nav class="nav__links" aria-label="{e(T('nav.aria'))}">{links}</nav>
  </div>
</header>

<main id="main">
{body}
</main>

<footer class="foot" data-tone="night">
  <div class="wrap">
    <div class="grid foot__grid">
      <div class="foot__brand">
        <p class="h3" style="color:var(--chalk);max-width:18ch">{e(S()['brand']['tagline'])}</p>
      </div>
      <div class="foot__col">
        <p class="label foot__title">{e(T("foot.shop"))}</p>
        <ul class="foot__list">{shop_links}</ul>
      </div>
      <div class="foot__col">
        <p class="label foot__title">{e(T("foot.about"))}</p>
        <ul class="foot__list">
          <li><a href="{U('/#how')}">{e(T("foot.how"))}</a></li>
          <li><a href="{U('/#faq')}">{e(T("foot.questions"))}</a></li>
        </ul>
      </div>
      <div class="foot__col">
        <p class="label foot__title">{e(T("foot.contact"))}</p>
        <ul class="foot__list">
          <li><a href="mailto:{e(BRAND['email'])}">{e(BRAND['email'])}</a></li>
          <li><a href="{U('/legal/')}">{e(T("foot.legal"))}</a></li>
        </ul>
      </div>
    </div>
    <div class="foot__base">
      <span>&copy; {year} {e(BRAND['name'])} — {e(T("foot.printed", country=BRAND['country']))}</span>
    </div>
  </div>
</footer>

<script src="{asset('/assets/js/site.js')}" defer data-vendor="{e(json.dumps(VENDOR))}"></script>
</body>
</html>
"""


# ------------------------------------------------------------------- pieces
def product_card(p, feature=False, morph=True):
    price = money(p.get("price"))
    tag = ""
    if p.get("status") == "concept":
        tag = f'<span class="pcard__tag">{e(T("card.inDev"))}</span>'
    rooms = "|".join(p.get("rooms", []))
    cls = "pcard pcard--feature" if feature else "pcard"
    return f"""<a class="{cls}" href="{U('/shop/' + p['slug'] + '/')}" data-rooms="{e(rooms)}"{' data-morph' if morph else ''}>
  {slot('pcard__media lay', photo=lead_photo(p), sizes=SIZES_FEATURE if feature else SIZES_CARD)}
  <div class="pcard__top">
    <span class="pcard__name">{e(PT(p, 'name'))}</span>
    <span class="pcard__price">{price or '—'}</span>
  </div>
  <p class="pcard__meta">{e(PT(p, 'variant'))}</p>
  {tag}
</a>"""


# --------------------------------------------------------------------- home
def build_home():
    lamps = by_cat("lamps")
    decos = by_cat("decorations")
    lamp_cat = next(c for c in CATEGORIES if c["slug"] == "lamps")
    deco_cat = next(c for c in CATEGORIES if c["slug"] == "decorations")
    site = S()

    bens = "".join(f"""<div class="ben rise">
      <div class="ridge ridge--rule ben__rule"></div>
      <h3 class="h3 ben__title">{e(b['title'])}</h3>
      <p class="ben__body">{e(b['body'])}</p>
    </div>""" for b in site["benefits"])

    steps = "".join(f"""<li class="step rise">
      <span class="step__n" aria-hidden="true"></span>
      <div class="step__body">
        <h3 class="h3 step__title">{e(s['step'])}</h3>
        <p class="step__text">{e(s['body'])}</p>
      </div>
    </li>""" for s in site["howItWorks"])

    trust = "".join(f"""<div class="trust__cell">
      <p class="label trust__label">{e(t['label'])}</p>
      <p class="trust__value">{e(t['value'])}</p>
    </div>""" for t in site["trust"])

    faqs = "".join(f"""<details class="qa">
      <summary class="qa__q">{e(q['q'])}<span class="qa__sign" aria-hidden="true"></span></summary>
      <div class="qa__a"><div>{e(q['a'])}</div></div>
    </details>""" for q in site["faq"])

    hero_lines = "\n".join(f'          <span class="l"><span>{e(line)}</span></span>' for line in T("home.heroLines"))
    shop_lamps = e(T("home.shopLamps"))
    shop_decos = e(T("home.shopDecos"))

    body = f"""
<section class="sec hero" data-tone="day">
  <div class="wrap">
    <div class="grid hero__grid">
      <div class="hero__copy">
        <p class="label hero__eyebrow rise" style="--rd:350ms">{e(T("home.eyebrow", country=BRAND['country']))}</p>
        <h1 class="display h1 hero__title lines" style="--rd:450ms">
{hero_lines}
        </h1>
        <p class="lead hero__lead rise" style="--rd:700ms">{e(T("home.lead"))}</p>
        <div class="hero__actions rise" style="--rd:950ms">
          <a class="btn" href="{U('/lamps/')}">{shop_lamps}</a>
          <a class="tlink" href="{U('/decorations/')}">{shop_decos} <span class="tlink__arrow">&rarr;</span></a>
        </div>
      </div>
      <div class="hero__media">
        {slot('lay', None, 'aspect-ratio:4/5', photo=site.get('hero', {}).get('photo'), sizes=SIZES_HERO, eager=True)}
      </div>
    </div>
  </div>
</section>

<section class="sec" data-tone="day" id="shop">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">{e(T("home.waysEyebrow"))}</p>
      <h2 class="display h2 shead__title" data-split>{e(T("home.waysTitle"))}</h2>
      <p class="lead shead__note">{e(T("home.waysNote"))}</p>
    </div>
    <div class="grid cats">
      <a class="cat cat--a" href="{U('/lamps/')}" data-morph>
        {slot('cat__media lay')}
        <div class="cat__row">
          <h3 class="display h3">{e(CT(lamp_cat, 'name'))}</h3>
          <span class="cat__count">{pieces(len(lamps))}</span>
        </div>
        <p class="cat__lead">{e(CT(lamp_cat, 'lead'))}</p>
      </a>
      <a class="cat cat--b" href="{U('/decorations/')}" data-morph>
        {slot('cat__media lay')}
        <div class="cat__row">
          <h3 class="display h3">{e(CT(deco_cat, 'name'))}</h3>
          <span class="cat__count">{pieces(len(decos))}</span>
        </div>
        <p class="cat__lead">{e(CT(deco_cat, 'lead'))}</p>
      </a>
    </div>
  </div>
</section>

<section class="sec" data-tone="day">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">{e(T("home.whyEyebrow"))}</p>
      <h2 class="display h2 shead__title" data-split>{e(T("home.whyTitle"))}</h2>
    </div>
    <div class="grid bens">{bens}</div>
  </div>
</section>

<section class="sec" data-tone="day" id="how">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">{e(T("home.howEyebrow"))}</p>
      <h2 class="display h2 shead__title" data-split>{e(T("home.howTitle", count=count(len(site['howItWorks']), 'noun.step', cap=True)))}</h2>
      <p class="lead shead__note">{e(T("home.howNote"))}</p>
    </div>
    <ol class="grid steps">{steps}</ol>
  </div>
</section>

<section class="sec" data-tone="day" style="padding-block:0">
  <div class="wrap"><div class="trust">{trust}</div></div>
</section>

<div class="dusk" aria-hidden="true"></div>

<section class="sec" data-tone="night">
  <div class="wrap">
    <p class="label" style="margin-bottom:1.4rem">{e(T("home.darkEyebrow"))}</p>
    <p class="display h2" style="max-width:24ch" data-split>{e(T("home.darkLine"))}</p>
  </div>
</section>

<section class="sec" data-tone="night" id="faq">
  <div class="wrap">
    <div class="grid faq__grid">
      <div class="faq__side">
        <p class="label" style="margin-bottom:1rem">{e(T("home.faqEyebrow"))}</p>
        <h2 class="display h3" data-split>{e(T("home.faqTitle"))}</h2>
      </div>
      <div class="faq__list">{faqs}</div>
    </div>
  </div>
</section>

<section class="sec" data-tone="night">
  <div class="wrap">
    <div class="grid cta__grid">
      <div class="cta__copy">
        <h2 class="display h2" data-split>{e(T("home.ctaTitle"))}</h2>
      </div>
      <div class="cta__side">
        <div class="hero__actions">
          <a class="btn btn--ghost" href="{U('/lamps/')}">{shop_lamps}</a>
          <a class="tlink" href="{U('/decorations/')}">{shop_decos} <span class="tlink__arrow">&rarr;</span></a>
        </div>
      </div>
    </div>
  </div>
</section>
"""
    return shell(T("home.title", brand=BRAND['name']), T("home.desc"), body, path="/")


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
        blocks.append(f'<div class="ed__rows">{"".join(product_card(q) for q in rest)}</div>')
    return f'<div class="ed" data-ed data-batch>{"".join(blocks)}</div>'


def build_category(cat):
    live = by_cat(cat["slug"], "live")
    concepts = by_cat(cat["slug"], "concept")
    rooms = sorted({r for p in live for r in p.get("rooms", [])}, key=room_name)

    filters = ""
    if len(rooms) > 1:
        # data-room keeps the English name: it is the id the cards carry, not text
        btns = f'<button class="filter" data-room="" aria-pressed="true">{e(T("cat.everything"))}</button>'
        btns += "".join(f'<button class="filter" data-room="{e(r)}" aria-pressed="false">{e(room_name(r))}</button>'
                        for r in rooms)
        filters = f'<div class="filters" data-filters role="group" aria-label="{e(T("cat.filterAria"))}">{btns}</div>'

    concept_block = ""
    if concepts:
        cc = "".join(product_card(p, morph=False) for p in concepts)
        concept_block = f"""
<section class="sec" data-tone="night">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">{e(T("cat.notYet"))}</p>
      <h2 class="display h2 shead__title" data-split>{e(T("cat.conceptTitle", count=count(len(concepts), 'noun.shape', cap=True)))}</h2>
      <p class="lead shead__note">{e(T("cat.conceptNote"))}</p>
    </div>
    <div class="grid pgrid" data-batch>{cc}</div>
  </div>
</section>"""

    # site.js rewrites the count after filtering, from these two patterns
    count_attrs = f'data-one="{e(T("pieces.one"))}" data-many="{e(T("pieces.many"))}"'
    body = f"""
<section class="sec pdp" data-tone="day" style="padding-bottom:clamp(2rem,5vw,4rem)">
  <div class="wrap">
    <div class="shead grid" style="margin-bottom:clamp(2rem,4vw,3rem)">
      <p class="label shead__eyebrow" style="grid-column:1/-1">{pieces(len(live))}</p>
      <h1 class="display h2 shead__title lines">
        <span class="l"><span>{e(CT(cat, 'name'))}</span></span>
      </h1>
      <p class="lead shead__note">{e(CT(cat, 'lead'))}</p>
    </div>
    {filters}
    <p class="vh" data-filter-count {count_attrs} aria-live="polite">{pieces(len(live))}</p>
    {editorial_grid(live)}
  </div>
</section>
{concept_block}
"""
    return shell(
        T("cat.title", cat=CT(cat, "name"), brand=BRAND["name"]),
        CT(cat, "lead"),
        body,
        page=cat["slug"],
        path=f"/{cat['slug']}/",
    )


# ------------------------------------------------------------------ product
def build_product(p):
    photos = photos_of(p)
    cols = colours(p)
    first = lead_photo(p)
    name, variant = PT(p, "name"), PT(p, "variant")
    shots = slot("pdp__shot lay", None, "view-transition-name:hero-media",
                 photo=first, sizes=SIZES_SHOT, eager=True)
    if int(p.get("shots", 1)) > 1:
        second = photos[1] if len(photos) > 1 else None
        shots += slot("pdp__shot lay", T("slot.second"), photo=second, sizes=SIZES_SHOT)

    specs = ""
    rows = "".join(f'<div class="pdp__spec"><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in spec_rows(p))
    if rows:
        specs = f'<dl class="pdp__specs">{rows}</dl>'

    concept = p.get("status") == "concept"
    if concept:
        buy = f"""<div class="notice">{T("pdp.conceptNoticeHtml")}</div>
        <div class="pdp__buy"><a class="btn" href="{mailto(T('pdp.conceptSubject', name=name))}">{e(T("pdp.conceptButton"))}</a></div>"""
        price_html = ""
    else:
        markets = market_links(p)
        # with a listing to point at, the site's own route steps back to a fallback
        btn = "btn btn--ghost" if markets else "btn"
        checkout = p.get("checkoutUrl")
        if checkout:
            action = f'<a class="{btn}" href="{e(checkout)}">{e(T("pdp.addToBasket", price=money(p["price"])))}</a>'
        else:
            # with colours, the subject names the one picked (site.js fills it in);
            # without JS it names none, rather than guess the first
            base = T("pdp.orderSubject", name=name)
            subj = base if cols else base + (f" ({variant})" if variant else "")
            order = f' data-order="{e(base)}"' if can_swatch(cols) else ""
            action = f'<a class="{btn}" href="{mailto(subj)}"{order}>{e(T("pdp.orderByEmail"))}</a>'
        market_html = ""
        if markets:
            mbtns = "".join(
                f'<a class="btn" href="{e(url)}" target="_blank" rel="noopener noreferrer">'
                f'{e(T("pdp.buyOn", market=label))}<span class="vh">{e(T("pdp.newTab"))}</span></a>'
                for label, url in markets)
            where = T("pdp.marketOr").join(T("pdp.marketWho", market=label) for label, _ in markets)
            market_html = f"""<div class="pdp__buy pdp__buy--market">{mbtns}</div>
        <p class="pdp__note">{e(T("pdp.marketNote", where=where))}</p>"""
        buy = f"""{market_html}<div class="pdp__buy">{action}</div>
        <p class="pdp__care">{e(T("pdp.shipping", time=S()["shipping"]["workshopTime"]))}</p>"""
        price_html = f'<p class="pdp__price">{money(p.get("price"))}</p>'

    care = f'<p class="pdp__care">{e(PT(p, "care"))}</p>' if p.get("care") else ""
    other = [q for q in by_cat(p["category"]) if q["slug"] != p["slug"]][:4]
    more = "".join(product_card(q) for q in other)

    cat = next(c for c in CATEGORIES if c["slug"] == p["category"])
    cat_name = CT(cat, "name")

    body = f"""
<section class="sec pdp" data-tone="day">
  <div class="wrap">
    <p class="label" style="margin-bottom:1.5rem"><a href="{U('/' + p['category'] + '/')}" style="text-decoration:none">{e(cat_name)}</a></p>
    <div class="grid pdp__grid">
      <div class="pdp__media"><div class="pdp__shots">{shots}</div></div>
      <div class="pdp__info">
        <h1 class="display h2 pdp__name">{e(name)}</h1>
        <p class="pdp__variant">{e(variant)}</p>
        {price_html}
        {colour_picker(p, cols)}
        <div class="prose pdp__desc"><p>{e(PT(p, 'description'))}</p></div>
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
      <h2 class="display h3 shead__title" data-split>{e(T("pdp.more", cat=cat_name.lower()))}</h2>
    </div>
    <div class="grid pgrid" data-batch>{more}</div>
  </div>
</section>
"""
    path = f"/shop/{p['slug']}/"
    url = f"https://{BRAND['domain']}{U(path)}"
    ld = {
        "@context": "https://schema.org", "@type": "Product",
        "name": f"{name} {variant}".strip(),
        "description": PT(p, "blurb"), "brand": {"@type": "Brand", "name": BRAND["name"]},
        "url": url,
    }
    if first:
        ld["image"] = photo_url(first)
    # An Offer tells search engines "this is a price you can buy at", so it waits
    # until the price is real: every price here started life as a placeholder.
    if p.get("price") and p.get("priceConfirmed") and not concept:
        ld["offers"] = {"@type": "Offer", "price": p["price"], "priceCurrency": BRAND["currency"],
                        "availability": "https://schema.org/MadeToOrder", "url": url}
    # `<` escaped so no text in the data can close the script element early
    head = '<script type="application/ld+json">' + json.dumps(ld).replace("<", "\\u003c") + "</script>"

    return shell(T("pdp.title", name=name, brand=BRAND["name"]), PT(p, "blurb"), body, page=p["category"],
                 extra_head=head, current="true", path=path, image=first)


# -------------------------------------------------------------------- legal
def build_legal():
    site = S()
    days = site["legal"]["returnsDays"]
    paras = lambda items: "\n      ".join(f"<p>{x}</p>" for x in items)
    email = f'<a href="mailto:{e(BRAND["email"])}">{e(BRAND["email"])}</a>'
    returns = paras(T("legal.returnsHtml"))
    returns = returns.replace("{days}", str(days))
    body = f"""
<section class="sec pdp" data-tone="day">
  <div class="wrap">
    <div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">{e(T("legal.eyebrow"))}</p>
      <h1 class="display h2 shead__title lines"><span class="l"><span>{e(T("legal.heading"))}</span></span></h1>
    </div>
    <div class="prose" style="max-width:66ch">
      <h2 class="h3">{e(T("legal.returnsH"))}</h2>
      {returns}
      <p>{e(site['legal']['customExemptionNote'])} {e(T("legal.exemptionPlain"))}</p>

      <h2 class="h3" style="margin-top:2.5rem">{e(T("legal.deliveryH"))}</h2>
      <p>{e(T("legal.delivery", time=site["shipping"]["workshopTime"]))}</p>

      <h2 class="h3" style="margin-top:2.5rem">{e(T("legal.privacyH"))}</h2>
      {paras(e(x) for x in T("legal.privacy"))}

      <h2 class="h3" style="margin-top:2.5rem">{e(T("legal.mentionsH"))}</h2>
      <p>{T("legal.publisherHtml", brand=e(BRAND['name']), country=e(BRAND['country']), email=email)}</p>
      <p>{T("legal.hostHtml")}</p>
      <p>{T("legal.cdnHtml")}</p>
    </div>
  </div>
</section>
"""
    return shell(T("legal.title", brand=BRAND["name"]), T("legal.desc"), body, path="/legal/")


# ---------------------------------------------------------------------- 404
def build_404():
    """GitHub Pages serves one /404.html for any missing URL in either language —
    an old product link, a typo — instead of its own grey "Page not found · GitHub
    Pages". So it speaks the main language and repeats the essentials in the
    other one. Every URL in the shell is root-absolute, so it renders the same
    at any depth. Built in the main language (see main)."""
    global L

    def actions():
        first, rest = CATEGORIES[0], CATEGORIES[1:]
        others = "".join(f'<a class="tlink" href="{U("/" + c["slug"] + "/")}">{e(CT(c, "name"))} <span class="tlink__arrow">&rarr;</span></a>'
                         for c in rest)
        return f"""<div class="hero__actions">
      <a class="btn" href="{U('/' + first['slug'] + '/')}">{e(CT(first, 'name'))}</a>
      {others}
      <a class="tlink" href="{U('/')}">{e(T("404.home"))} <span class="tlink__arrow">&rarr;</span></a>
    </div>"""

    main_lang = L
    blocks = []
    for x in [main_lang] + [x for x in LANGS if x != main_lang]:
        L = x
        if x == main_lang:
            blocks.append(f"""<div class="shead grid">
      <p class="label shead__eyebrow" style="grid-column:1/-1">{e(T("404.eyebrow"))}</p>
      <h1 class="display h2 shead__title lines"><span class="l"><span>{e(T("404.heading"))}</span></span></h1>
      <p class="lead shead__note">{e(T("404.note"))}</p>
    </div>
    {actions()}""")
        else:
            blocks.append(f"""<div lang="{x}" style="margin-top:clamp(3rem,7vw,5rem)">
      <p class="label" style="margin-bottom:1rem">{e(T("404.eyebrow"))}</p>
      <p class="lead" style="margin-bottom:1.6rem">{e(T("404.note"))}</p>
      {actions()}
    </div>""")
    L = main_lang
    body = f"""
<section class="sec pdp" data-tone="day">
  <div class="wrap">
    {"".join(blocks)}
  </div>
</section>
"""
    return shell(T("404.title", brand=BRAND["name"]), T("404.desc"), body,
                 extra_head='<meta name="robots" content="noindex">')


# --------------------------------------------------------------------- main
def write(rel, content):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf8", newline="\n") as f:
        f.write(content)
    return rel


def out_dir(lang):
    """Where a language's pages are written: the root for the main language."""
    return "" if lang == DEFAULT_LANG else f"{lang}/"


def prune_product_pages():
    """Delete shop/<slug>/ pages (in every language) whose product was removed,
    renamed or set to draft.

    The build only ever wrote pages, so a product taken out of products.json kept
    its old page online for good — gone from the listings and the sitemap, still
    served at its URL with its old price. Only the generated index.html is
    deleted (and the folder, if that leaves it empty); anything else survives.
    """
    keep = {p["slug"] for p in PRODUCTS}
    removed = []
    for lang in LANGS:
        shop = os.path.join(ROOT, out_dir(lang), "shop")
        if not os.path.isdir(shop):
            continue
        for slug in sorted(os.listdir(shop)):
            folder = os.path.join(shop, slug)
            page = os.path.join(folder, "index.html")
            if slug in keep or not os.path.isfile(page):
                continue
            os.remove(page)
            if not os.listdir(folder):
                os.rmdir(folder)
            removed.append(f"{out_dir(lang)}shop/{slug}/index.html")
    return removed


def main():
    global L
    removed = prune_product_pages()
    written = []
    paths = ["/"] + [f"/{c['slug']}/" for c in CATEGORIES] + ["/legal/"] + [f"/shop/{p['slug']}/" for p in PRODUCTS]
    for lang in LANGS:
        L = lang
        d = out_dir(lang)
        written.append(write(f"{d}index.html", build_home()))
        for c in CATEGORIES:
            written.append(write(f"{d}{c['slug']}/index.html", build_category(c)))
        for p in PRODUCTS:
            written.append(write(f"{d}shop/{p['slug']}/index.html", build_product(p)))
        written.append(write(f"{d}legal/index.html", build_legal()))
    L = DEFAULT_LANG
    written.append(write("404.html", build_404()))

    # sitemap: every page in every language, each listing its translations
    domain = f"https://{BRAND['domain']}"
    entries = []
    for lang in LANGS:
        for path in paths:
            alts = "".join(f'<xhtml:link rel="alternate" hreflang="{x}" href="{domain}{U(path, x)}"/>' for x in LANGS)
            entries.append(f"  <url><loc>{domain}{U(path, lang)}</loc>{alts}</url>\n")
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
          + "".join(entries) + "</urlset>\n")
    written.append(write("sitemap.xml", sm))
    written.append(write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: https://{BRAND['domain']}/sitemap.xml\n"))

    print(f"wrote {len(written)} files ({', '.join(LANGS)})")
    for w in written:
        print("  ", w)
    if removed:
        print(f"removed {len(removed)} page(s) for products no longer published")
        for r in removed:
            print("  ", r)


if __name__ == "__main__":
    main()
