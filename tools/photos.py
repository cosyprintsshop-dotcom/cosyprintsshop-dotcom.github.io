# -*- coding: utf-8 -*-
"""
Turn one source photo into the web-ready files the site serves.

    python tools/photos.py SOURCE NAME [--ratio 4:5] [--focus 0.5]

Crops SOURCE to the frame ratio (4:5 for the hero and a product's first shot,
1:1 for cards), resizes to a few widths, and writes
assets/img/NAME-<width>.webp and .jpg. Metadata (GPS included) is stripped.
It then records NAME in data/photos.json, which is all build.py reads — so
build.py stays standard-library only and CI needs nothing installed.

--focus is where the crop is centred, 0 = top/left, 1 = bottom/right.

Needs Pillow: pip install pillow
"""
import argparse, json, os, sys
from PIL import Image, ImageChops, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "img")
MANIFEST = os.path.join(ROOT, "data", "photos.json")
WIDTHS = [480, 800, 1200, 1600]
WEBP_Q, JPEG_Q = 86, 84
GRAIN = 0.6   # levels of grain added before encoding; see dither()


def dither(im):
    """Break up 8-bit steps before compression. A lit shade is a long, smooth
    gradient: at WebP quality 80 it compressed to visible bands (a 1600px lamp
    photo came out at 27 KB). Sub-level grain gives the encoder detail to keep
    instead of flat steps, and is invisible at any viewing size."""
    noise = Image.merge("RGB", [Image.effect_noise(im.size, GRAIN) for _ in range(3)])
    return ImageChops.add(im, noise, scale=1.0, offset=-128)


def crop_to(im, rw, rh, focus):
    w, h = im.size
    if w * rh > h * rw:                      # too wide: trim the sides
        nw = h * rw // rh
        x = round((w - nw) * focus)
        return im.crop((x, 0, x + nw, h))
    nh = w * rh // rw                        # too tall: trim top/bottom
    y = round((h - nh) * focus)
    return im.crop((0, y, w, y + nh))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("name", help="lowercase-with-dashes, e.g. hero-lamp")
    ap.add_argument("--ratio", default="4:5")
    ap.add_argument("--focus", type=float, default=0.5)
    a = ap.parse_args()

    rw, rh = (int(x) for x in a.ratio.split(":"))
    im = ImageOps.exif_transpose(Image.open(a.source)).convert("RGB")
    im = crop_to(im, rw, rh, a.focus)

    # never upscale: the largest file is the source's own width
    widths = sorted({w for w in WIDTHS if w < im.width} | {min(im.width, WIDTHS[-1])})
    os.makedirs(OUT, exist_ok=True)
    for w in widths:
        r = dither(im.resize((w, round(w * rh / rw)), Image.LANCZOS))
        r.save(os.path.join(OUT, f"{a.name}-{w}.webp"), "WEBP", quality=WEBP_Q, method=6)
        r.save(os.path.join(OUT, f"{a.name}-{w}.jpg"), "JPEG", quality=JPEG_Q, optimize=True, progressive=True)

    data = json.load(open(MANIFEST, encoding="utf8")) if os.path.exists(MANIFEST) else {}
    data[a.name] = {"ratio": a.ratio, "widths": widths}
    with open(MANIFEST, "w", encoding="utf8", newline="\n") as f:
        json.dump(dict(sorted(data.items())), f, indent=2)
        f.write("\n")

    print(f"{a.name}: {a.ratio}, widths {widths}")
    if widths[-1] < 1200:
        print(f"  note: source is only {im.width}px wide after cropping — it will look soft on "
              "high-DPI screens. Use the camera original if you have it.", file=sys.stderr)


if __name__ == "__main__":
    main()
