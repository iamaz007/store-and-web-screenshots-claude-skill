#!/usr/bin/env python3
"""Composite a site into the screen of a real photograph.

The drawn laptop frame in `collage.py` is clean but synthetic. A photographic
mockup - an actual desk, an actual machine, real light - is a different and
warmer register, and worth having in a set for one or two projects so the
portfolio is not nine variations of the same treatment.

The screen is a quadrilateral in the photo, given as four corner points in
photo pixels, clockwise from the top-left. The capture is perspective-mapped
into that quad, masked to it, and given back the screen's own reflection and
falloff so it sits in the photo rather than on top of it.

    python3 photo_mockup.py --photo desk.jpg --shot home.png \\
        --quad "285,360 1395,330 1432,980 300,1005" \\
        --out board.png --size 1280x769
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFilter

from collage import _persp_coeffs, load_piece


def fit_screen(photo, shot, quad, glare=0.10, tint=0.06):
    """Map `shot` into `quad` on `photo`."""
    w, h = shot.size
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    co = _persp_coeffs(src, quad)
    if co is None:
        raise SystemExit("degenerate quad")
    warped = shot.convert("RGB").transform(photo.size, Image.PERSPECTIVE, co,
                                           Image.BICUBIC)

    mask = Image.new("L", photo.size, 0)
    ImageDraw.Draw(mask).polygon([tuple(p) for p in quad], fill=255)
    # Feather by a hair so the edge meets the bezel instead of cutting it.
    mask = mask.filter(ImageFilter.GaussianBlur(1.2))

    out = photo.convert("RGB").copy()
    out.paste(warped, (0, 0), mask)

    if tint:
        # The photo's own screen colour, pushed back over the paste: a screen
        # in a room is never the flat sRGB of the source file.
        amb = photo.convert("RGB").filter(ImageFilter.GaussianBlur(60))
        out = Image.blend(out, Image.composite(amb, out, mask), tint)
    if glare:
        # A soft diagonal sheen across the panel - the single cue that stops a
        # composite reading as a rectangle pasted onto a photograph.
        g = Image.new("L", photo.size, 0)
        gd = ImageDraw.Draw(g)
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = quad
        gd.polygon([(x0, y0), (x0 + (x1 - x0) * 0.55, y1),
                    (x3 + (x2 - x3) * 0.18, y3), (x3, y3)], fill=255)
        g = g.filter(ImageFilter.GaussianBlur(photo.width * 0.03))
        g = Image.composite(g, Image.new("L", photo.size, 0), mask)
        white = Image.new("RGB", photo.size, (255, 255, 255))
        out = Image.composite(Image.blend(out, white, glare), out,
                              g.point(lambda v: int(v * 0.9)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo", required=True)
    ap.add_argument("--shot", required=True, help="capture, `~a+t` accepted")
    ap.add_argument("--quad", required=True,
                    help='"x,y x,y x,y x,y" clockwise from the top-left')
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", required=True, help="WxH")
    ap.add_argument("--crop", default="",
                    help="l,t,r,b as fractions of the photo, applied last")
    ap.add_argument("--glare", type=float, default=0.10)
    ap.add_argument("--tint", type=float, default=0.06)
    a = ap.parse_args()

    Image.MAX_IMAGE_PIXELS = None
    photo = Image.open(os.path.expanduser(a.photo))
    quad = [tuple(float(v) for v in p.split(",")) for p in a.quad.split()]
    shot = load_piece(a.shot, trim=False)

    # Only the top of a long page fits a screen; take a screen-shaped piece of
    # it rather than squeezing the whole page into the panel.
    qw = max(p[0] for p in quad) - min(p[0] for p in quad)
    qh = max(p[1] for p in quad) - min(p[1] for p in quad)
    want_h = int(shot.width * qh / qw)
    if shot.height > want_h:
        shot = shot.crop((0, 0, shot.width, want_h))

    out = fit_screen(photo, shot, quad, a.glare, a.tint)

    if a.crop:
        l, t, r, b = [float(v) for v in a.crop.split(",")]
        out = out.crop((int(l * out.width), int(t * out.height),
                        int(r * out.width), int(b * out.height)))

    W, H = (int(v) for v in a.size.lower().split("x"))
    k = max(W / out.width, H / out.height)          # cover, then centre-crop
    out = out.resize((max(1, round(out.width * k)), max(1, round(out.height * k))),
                     Image.LANCZOS)
    x = (out.width - W) // 2
    y = (out.height - H) // 2
    out = out.crop((x, y, x + W, y + H))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    out.save(a.out)
    print(f"{a.out}  {W}x{H}  photo mockup")


if __name__ == "__main__":
    main()


def detect_quad(photo, region=None):
    """Find the screen in the photograph, instead of eyeballing its corners.

    A lit screen is a large bright quadrilateral inside a dark bezel. Threshold
    for it, take the largest bright region, and read the extreme corner points
    off that. Measuring by eye is what left the capture sitting on the bezel and
    over the edge of the lid - a few pixels of error there is instantly visible.
    """
    from PIL import ImageFilter
    N = 300
    sm = photo.convert("L").resize((N, max(1, round(N * photo.height / photo.width))))
    sm = sm.filter(ImageFilter.MedianFilter(3))
    W, H = sm.size
    px = sm.load()
    lo = sorted(px[x, y] for x in range(0, W, 3) for y in range(0, H, 3))
    thr = lo[int(len(lo) * 0.72)]                 # brightest ~28% is the panel
    x0, y0, x1, y1 = region or (0, 0, W, H)

    seen = [[False] * W for _ in range(H)]
    best = None
    for sy in range(y0, y1):
        for sx in range(x0, x1):
            if seen[sy][sx] or px[sx, sy] < thr:
                continue
            stack, pts = [(sx, sy)], []
            seen[sy][sx] = True
            while stack:
                x, y = stack.pop()
                pts.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if (x0 <= nx < x1 and y0 <= ny < y1 and not seen[ny][nx]
                            and px[nx, ny] >= thr):
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if best is None or len(pts) > len(best):
                best = pts
    if not best or len(best) < W * H * 0.02:
        return None
    k = photo.width / W
    # corners of a rotated rectangle: the extremes of x+y and x-y
    tl = min(best, key=lambda p: p[0] + p[1])
    br = max(best, key=lambda p: p[0] + p[1])
    tr = max(best, key=lambda p: p[0] - p[1])
    bl = min(best, key=lambda p: p[0] - p[1])
    return [(p[0] * k, p[1] * k) for p in (tl, tr, br, bl)]
