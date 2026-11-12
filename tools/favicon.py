# -*- coding: utf-8 -*-
"""
Draw the site icon: favicon.svg for modern browsers and favicon.ico for the
browsers and crawlers that only ask for /favicon.ico.

    python tools/favicon.py

The mark is the ridge — the site's one repeated graphic device — as four light
lines on an ink tile. It is a stand-in until there is a real logo: change the
numbers below (or replace both files) and rerun. Standard library only.
"""
import os, struct, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SIZE, RADIUS = 32, 6
INK, BONE = (0x1F, 0x1B, 0x16), (0xED, 0xE7, 0xDB)
BARS = [9, 13, 17, 21]          # left edge of each 2px line
TOP, BOTTOM = 8, 24             # lines run from y=8 to y=24


def svg():
    bars = "".join(f'<rect x="{x}" y="{TOP}" width="2" height="{BOTTOM - TOP}"/>' for x in BARS)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}">'
            f'<rect width="{SIZE}" height="{SIZE}" rx="{RADIUS}" fill="#1F1B16"/>'
            f'<g fill="#EDE7DB">{bars}</g></svg>\n')


def pixel(x, y):
    """RGBA at the centre of pixel (x, y): transparent outside the rounded tile."""
    cx, cy = x + .5, y + .5
    for kx, ky in ((RADIUS, RADIUS), (SIZE - RADIUS, RADIUS), (RADIUS, SIZE - RADIUS), (SIZE - RADIUS, SIZE - RADIUS)):
        inside_corner_box = (cx < RADIUS if kx == RADIUS else cx > SIZE - RADIUS) and \
                            (cy < RADIUS if ky == RADIUS else cy > SIZE - RADIUS)
        if inside_corner_box and (cx - kx) ** 2 + (cy - ky) ** 2 > RADIUS ** 2:
            return (0, 0, 0, 0)
    on_bar = TOP <= y < BOTTOM and any(bx <= x < bx + 2 for bx in BARS)
    return (*(BONE if on_bar else INK), 255)


def png():
    rows = b"".join(b"\x00" + b"".join(bytes(pixel(x, y)) for x in range(SIZE)) for y in range(SIZE))
    chunk = lambda kind, data: (struct.pack(">I", len(data)) + kind + data
                                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9))
            + chunk(b"IEND", b""))


def ico(image):
    # one 32x32 entry holding a PNG, which every current browser reads
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", SIZE, SIZE, 0, 0, 1, 32, len(image), 6 + 16)
    return header + entry + image


def main():
    with open(os.path.join(ROOT, "favicon.svg"), "w", encoding="utf8", newline="\n") as f:
        f.write(svg())
    with open(os.path.join(ROOT, "favicon.ico"), "wb") as f:
        f.write(ico(png()))
    print("wrote favicon.svg and favicon.ico")


if __name__ == "__main__":
    main()
