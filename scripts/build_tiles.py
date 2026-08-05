#!/usr/bin/env python3
"""Composite store-screenshot tiles from real app captures.

The app UI is pasted from the source capture at its TRUE aspect ratio - never
redrawn, restyled or stretched. Everything else (background, type, cards,
device bodies) is drawn locally, so type is never distorted.

THERE IS NO HOUSE STYLE. Palette, background and layout come from the config.
Choose them per app - see references/art-direction.md.

    python3 build_tiles.py --platform ios --config tiles.json \\
        --shots ./captures --out ./designed

    python3 build_tiles.py --palette-from icon.png     # suggest an accent

Requires: numpy, pillow.
"""
import argparse
import json
import math
import os

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HEAVY, DEMI, MEDIUM, REGULAR = "heavy", "demi", "medium", "regular"

# Typefaces live in fonts.py: a Google Fonts registry (fetched on demand and
# cached under assets/fonts/) plus macOS system faces as an offline fallback.
# THERE IS NO DEFAULT WORTH REUSING - run `python3 scripts/fonts.py "<what the
# app is>"` and take the pairing it recommends. Shipping the same face for
# every app is how two unrelated products end up looking like siblings.
from fonts import ALL as TYPEFACES, advise, ensure, resolve   # noqa: E402

_ACTIVE = {"display": "outfit", "text": "inter"}

# Exact store slots - see references/platform-specs.md
PRESETS = {
    "android-phone":  dict(size=(1080, 1920), orient="portrait"),
    "android-tablet": dict(size=(1920, 1080), orient="landscape"),
    "ios":            dict(size=(1320, 2868), orient="portrait"),   # 6.9" (required)
    "ios-65":         dict(size=(1242, 2688), orient="portrait"),   # 6.5" (optional)
    "ipad":           dict(size=(2064, 2752), orient="portrait"),
    "macos":          dict(size=(2880, 1800), orient="landscape"),
    # Website / marketing surfaces - see references/platform-specs.md
    "web-hero":       dict(size=(2560, 1440), orient="landscape"),
    "web-og":         dict(size=(1200, 630), orient="landscape"),
    "web-square":     dict(size=(1080, 1080), orient="landscape"),
    "web-tall":       dict(size=(1440, 2160), orient="portrait"),
}

# Platforms whose default frame is a browser window rather than a phone.
WEB_PLATFORMS = {"web-hero", "web-og", "web-square", "web-tall"}

# Fallback only. Real projects MUST supply "theme" in the config.
THEME = dict(bg="#F6F7FB", bg2="#E8ECFA", accent="#2F6BFF", accent2="#7C4DFF",
             ink="#101828", sub="#667085", card="#FFFFFF", background="gradient",
             device_body="#1A1A1E")


def hexc(v):
    v = v.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


_FONT_CACHE = {}


def font(size, face=HEAVY, role="text"):
    """`role` picks the pairing: headlines use "display", everything else "text"."""
    name = _ACTIVE.get(role, _ACTIVE["text"])
    key = (name, face, int(size))
    if key not in _FONT_CACHE:
        path, index, weight = resolve(name, face)
        f = ImageFont.truetype(path, int(size), index=index)
        if weight is not None:
            # Variable Google family: pick the weight off the wght axis. The
            # axis is not always first, so set it by position in get_variation_axes.
            axes = [a["default"] for a in f.get_variation_axes()]
            for i, a in enumerate(f.get_variation_axes()):
                if a["name"] in (b"Weight", "Weight"):
                    axes[i] = weight
            f.set_variation_by_axes(axes)
        _FONT_CACHE[key] = f
    return _FONT_CACHE[key]


# ---------------------------------------------------------------- palette help

def suggest_palette(path, k=5):
    """Dominant colours of an app icon - use these to derive the accent."""
    im = Image.open(path).convert("RGB").resize((90, 90))
    px = np.asarray(im).reshape(-1, 3).astype(np.float32)
    keep = px[(px.std(axis=1) > 16) & (px.mean(axis=1) < 246)]     # drop greys/white
    if len(keep) < 10:
        keep = px
    idx = np.random.default_rng(0).choice(len(keep), min(len(keep), 4000), replace=False)
    pts = keep[idx]
    centres = pts[np.random.default_rng(1).choice(len(pts), k, replace=False)]
    for _ in range(12):
        d = ((pts[:, None, :] - centres[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            if (lab == j).any():
                centres[j] = pts[lab == j].mean(0)
    order = np.argsort(-np.bincount(lab, minlength=k))
    return ["#%02X%02X%02X" % tuple(int(c) for c in centres[j]) for j in order]


# ------------------------------------------------------------------ background

def _noise(w, h, seed, octaves=(3, 6, 12), weights=(1.0, 0.5, 0.25)):
    rng = np.random.default_rng(seed)
    field = np.zeros((h, w), dtype=np.float32)
    for cells, weight in zip(octaves, weights):
        gh, gw = cells, max(2, int(cells * w / h))
        grid = (rng.random((gh + 1, gw + 1)) * 255).astype(np.uint8)
        img = Image.fromarray(grid).resize((w, h), Image.BICUBIC)
        img = img.filter(ImageFilter.GaussianBlur(max(14, w // (cells * 10))))
        field += np.asarray(img, dtype=np.float32) / 255.0 * weight
    return field / sum(weights)


def make_strip(size, n, th, seed=11):
    """Background across the whole set, sliced per tile so it continues."""
    w, h = size
    W = w * n
    style = th.get("background", "gradient")
    c1, c2 = hexc(th["bg"]), hexc(th.get("bg2", th["bg"]))

    if style == "solid":
        return Image.new("RGBA", (W, h), c1 + (255,))

    if style in ("gradient", "mesh"):
        xs = np.linspace(0, 1, W, dtype=np.float32)[None, :]
        ys = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        t = np.clip(0.45 * xs + 0.55 * ys, 0, 1)
        if style == "mesh":
            t = np.clip(t + 0.35 * _noise(W, h, seed) - 0.17, 0, 1)
        arr = np.zeros((h, W, 3), dtype=np.float32)
        for i in range(3):
            arr[..., i] = c1[i] * (1 - t) + c2[i] * t
        img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
        return img

    img = Image.new("RGBA", (W, h), c1 + (255,))
    if style == "dots":
        d = ImageDraw.Draw(img)
        step, r = max(26, w // 34), max(2, w // 460)
        col = hexc(th.get("bg2", th["bg"])) + (150,)
        for y in range(step, h, step):
            for x in range(step, W, step):
                d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        return img

    if style == "contour":                       # terrain/maps apps only
        field = _noise(W, h, seed)
        g = field * 26
        gy, gx = np.gradient(g)
        dist = np.abs(g - np.round(g)) / (np.hypot(gx, gy) + 1e-6)
        a = np.clip(1.0 - dist / 1.15, 0, 1) ** 0.8
        lines = Image.new("RGBA", (W, h), hexc(th.get("bg2", th["bg"])) + (0,))
        lines.putalpha(Image.fromarray((a * 210).astype(np.uint8)))
        img.alpha_composite(lines)
    return img


def glow(canvas, cx, cy, r, colour, alpha=150, falloff=2.1):
    """Soft radial light. Drawn with a real falloff curve, not stacked ellipses."""
    d = int(r * 2)
    ys, xs = np.ogrid[:d, :d]
    dist = np.hypot(xs - r, ys - r) / r
    a = np.clip(1.0 - dist, 0, 1) ** falloff * alpha
    layer = Image.new("RGBA", (d, d), hexc(colour) + (0,))
    layer.putalpha(Image.fromarray(a.astype(np.uint8)))
    x, y = int(cx - r), int(cy - r)
    # clip to canvas so a glow may hang off the tile edge
    cw, ch = canvas.size
    box = (max(0, -x), max(0, -y), d - max(0, x + d - cw), d - max(0, y + d - ch))
    if box[2] <= box[0] or box[3] <= box[1]:
        return
    canvas.alpha_composite(layer.crop(box), (max(0, x), max(0, y)))


def ribbon_arcs(canvas, specs, seed=3, blur=3):
    """Wide, blurred light arcs sweeping behind the subject."""
    W, H = canvas.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for s in specs:
        cx, cy = int(W * s["x"]), int(H * s["y"])
        rx, ry = int(W * s["rx"]), int(H * s["ry"])
        d.arc([cx - rx, cy - ry, cx + rx, cy + ry], s["a0"], s["a1"],
              fill=hexc(s.get("colour", "#FFFFFF")) + (s.get("alpha", 90),),
              width=s.get("w", 6))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def sparkle_field(canvas, n=42, seed=7, colour="#FFFFFF", region=(0.5, 0.0, 1.0, 1.0),
                  amax=210):
    """Four-point stars and dust motes - the cheap trick that sells depth."""
    W, H = canvas.size
    rng = np.random.default_rng(seed)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = region
    for _ in range(n):
        px = rng.uniform(x0, x1) * W
        py = rng.uniform(y0, y1) * H
        r = rng.uniform(3, 15)
        a = int(rng.uniform(amax * 0.28, amax))
        c = hexc(colour) + (a,)
        if rng.random() < 0.45:
            d.ellipse([px - r * .28, py - r * .28, px + r * .28, py + r * .28], fill=c)
        else:
            d.polygon([(px, py - r), (px + r * .22, py - r * .22),
                       (px + r, py), (px + r * .22, py + r * .22),
                       (px, py + r), (px - r * .22, py + r * .22),
                       (px - r, py), (px - r * .22, py - r * .22)], fill=c)
    canvas.alpha_composite(layer)


def prop(canvas, cx, cy, size, glyph, colour, rotate=0, sheen=True, style="3d",
         shape="square", drop=105, halo=84):
    """A floating tile. style="3d" gives gradient + sheen + glow; "flat" gives a
    solid tile with a plain shadow; "none" is handled by the caller."""
    s = int(size)
    pad = int(s * 0.42)
    layer = Image.new("RGBA", (s + pad * 2, s + pad * 2), (0, 0, 0, 0))

    base = hexc(colour)
    if style == "glass":
        body = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        bd = ImageDraw.Draw(body)
        box = [0, 0, s - 1, s - 1]
        fill = tuple(int(c + (255 - c) * 0.62) for c in base)
        if shape == "circle":
            bd.ellipse(box, fill=fill + (215,),
                       outline=base + (255,), width=max(2, int(s * .05)))
        else:
            bd.rounded_rectangle(box, int(s * .29), fill=fill + (215,),
                                 outline=base + (255,), width=max(2, int(s * .05)))
        add_sheen(body, 90)
        draw_glyph(ImageDraw.Draw(body), glyph,
                   (s * .29, s * .29, s * .71, s * .71), colour)
        layer.alpha_composite(body, (pad, pad))
        if rotate:
            layer = layer.rotate(rotate, resample=Image.BICUBIC, expand=True)
        glow(canvas, cx, cy, s * 1.15, colour, int(halo * .83))
        x, y = int(cx - layer.width / 2), int(cy - layer.height / 2)
        shadow(canvas, layer, x, y, blur=int(s * .32), spread=int(s * .16),
               alpha=int(drop * .67))
        canvas.alpha_composite(layer, (x, y))
        return
    if style == "flat":
        body = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        bdr = ImageDraw.Draw(body)
        if shape == "circle":
            bdr.ellipse([0, 0, s - 1, s - 1], fill=base + (255,))
        else:
            bdr.rounded_rectangle([0, 0, s - 1, s - 1], int(s * .29), fill=base + (255,))
    else:
        grad = Image.new("RGB", (1, s))
        px = grad.load()
        for y in range(s):
            t = y / max(1, s - 1)
            px[0, y] = tuple(int(min(255, c * (1.34 - 0.52 * t))) for c in base)
        body = grad.resize((s, s), Image.BILINEAR).convert("RGBA")
        m = Image.new("L", (s, s), 0)
        if shape == "circle":
            ImageDraw.Draw(m).ellipse([0, 0, s - 1, s - 1], fill=255)
        else:
            ImageDraw.Draw(m).rounded_rectangle([0, 0, s - 1, s - 1], int(s * .29), fill=255)
        body.putalpha(m)
        if sheen:
            add_sheen(body, 46)
    draw_glyph(ImageDraw.Draw(body), glyph,
               (s * .27, s * .27, s * .73, s * .73), "#FFFFFF")
    layer.alpha_composite(body, (pad, pad))
    if rotate:
        # expand=True, or the rotation crops the tile's own corners and the
        # prop renders as a sheared, torn shape.
        layer = layer.rotate(rotate, resample=Image.BICUBIC, expand=True)

    if style != "flat":
        glow(canvas, cx, cy, s * 1.05, colour, halo)
    x, y = int(cx - layer.width / 2), int(cy - layer.height / 2)
    shadow(canvas, layer, x, y, blur=int(s * .30),
           spread=int(s * .17), alpha=drop if style != "flat" else int(drop * .57))
    canvas.alpha_composite(layer, (x, y))


def _perspective_coeffs(dst, src):
    """Coefficients for Image.transform(PERSPECTIVE): maps output -> input."""
    m = []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    A = np.asarray(m, dtype=np.float64)
    B = np.asarray(src, dtype=np.float64).reshape(8)
    return np.linalg.solve(A, B)


def _rounded_outline(radius=0.45, per_corner=14):
    """Squircle outline in unit space (-1..1), counter-clockwise from top-left.

    The extrusion must follow THIS, not the bounding square - side faces built
    from the square leave dark corners sticking out past the rounded artwork.
    """
    r = radius
    pts = []
    for cx, cy, a0 in ((-1 + r, -1 + r, 180), (1 - r, -1 + r, 270),
                       (1 - r, 1 - r, 0), (-1 + r, 1 - r, 90)):
        for i in range(per_corner + 1):
            a = math.radians(a0 + 90 * i / per_corner)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _project(pts, yaw, pitch, z, focal):
    """Project 2D unit-space points sitting on the plane at depth `z`."""
    ry, rx = math.radians(yaw), math.radians(pitch)
    out = []
    for sx, sy in pts:
        x, y, zz = sx, sy, z
        x, zz = x * math.cos(ry) + zz * math.sin(ry), -x * math.sin(ry) + zz * math.cos(ry)
        y, zz = y * math.cos(rx) - zz * math.sin(rx), y * math.sin(rx) + zz * math.cos(rx)
        k = focal / (focal - zz)
        out.append((x * k, y * k))
    return out


def _project_square(yaw, pitch, z, focal):
    return _project([(-1, -1), (1, -1), (1, 1), (-1, 1)], yaw, pitch, z, focal)


def _convex_hull(points):
    """Andrew's monotone chain. Returns the hull counter-clockwise."""
    pts = sorted(set((round(x, 3), round(y, 3)) for x, y in points))
    if len(pts) < 3:
        return pts

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2:
                (ax, ay), (bx, by) = out[-2], out[-1]
                if (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax) > 0:
                    break
                out.pop()
            out.append(p)
        return out

    return half(pts)[:-1] + half(reversed(pts))[:-1]


def _shade(colour, k):
    return tuple(max(0, min(255, int(c * k))) for c in colour)


def solid3d(img, yaw=-20.0, pitch=13.0, depth=0.45, focal=9.0, pad=0.30,
            side="#3A2299"):
    """Render flat square artwork as a tilted SOLID with real side faces.

    The front face is a perspective warp of the artwork; the sides are actual
    projected quads between the front and back rims, back-face culled and
    flat-shaded. Stacking offset copies of the silhouette instead - the obvious
    shortcut - produces a smear, not an object.

    `focal` matters more than it looks. Under a short focal length the back face
    shrinks toward the vanishing point about as fast as the yaw displaces it
    sideways, so the side wall collapses to a hairline and the object reads flat
    again. Keep it long (8-12) and let `depth` and `yaw` do the work.

    NOTE the contrast with the device rule in references/pitfalls.md: a
    *screenshot* must never be perspective-skewed because it warps readable UI.
    An app icon is artwork, so tilting it is what makes it read as a solid.
    """
    w, h = img.size
    outline = _rounded_outline(radius=0.45)
    rim_f = _project(outline, yaw, pitch, 0.0, focal)
    rim_b = _project(outline, yaw, pitch, -depth * 2, focal)
    front = _project_square(yaw, pitch, 0.0, focal)
    back = _project_square(yaw, pitch, -depth * 2, focal)

    pts = rim_f + rim_b
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    out = int(max(w, h) * (1 + pad))
    scale = out / (span * (1 + pad))
    ox = out / 2 - (min(xs) + max(xs)) / 2 * scale
    oy = out / 2 - (min(ys) + max(ys)) / 2 * scale
    def place_pts(seq):
        return [(ox + x * scale, oy + y * scale) for x, y in seq]

    F, B = place_pts(front), place_pts(back)
    RF, RB = place_pts(rim_f), place_pts(rim_b)

    canvas = Image.new("RGBA", (out, out), (0, 0, 0, 0))

    # The body is the convex hull of the front and back rims. For a convex
    # solid that hull IS the silhouette, so it cannot produce the stray fins
    # that per-quad back-face culling gives you when a quad's winding flips.
    hull = _convex_hull(RF + RB)
    body = Image.new("RGBA", (out, out), (0, 0, 0, 0))
    ImageDraw.Draw(body).polygon(hull, fill=(255, 255, 255, 255))

    base = hexc(side)
    grad = Image.new("RGB", (1, out))
    px = grad.load()
    for y in range(out):
        px[0, y] = _shade(base, 0.86 - 0.34 * (y / max(1, out - 1)))
    wall = grad.resize((out, out), Image.BILINEAR).convert("RGBA")
    wall.putalpha(body.split()[3])
    canvas.alpha_composite(wall)

    # a transparent margin makes the warp sample nothing outside the artwork
    m = 2
    padded = Image.new("RGBA", (w + m * 2, h + m * 2), (0, 0, 0, 0))
    padded.alpha_composite(img, (m, m))
    src = [(0, 0), (w + m * 2, 0), (w + m * 2, h + m * 2), (0, h + m * 2)]
    face = padded.transform((out, out), Image.PERSPECTIVE,
                            _perspective_coeffs(F, src), resample=Image.BICUBIC)
    canvas.alpha_composite(face)
    return canvas


def blob(canvas, cx, cy, rx, ry, colour, alpha=255):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                                  fill=hexc(colour) + (alpha,))
    canvas.alpha_composite(layer)


# ---------------------------------------------------------------------- device

def _rail(w, h, radius):
    grad = Image.new("RGB", (1, h))
    px = grad.load()
    for y in range(h):
        t = y / max(1, h - 1)
        v = 118 + 96 * math.exp(-((t - .10) ** 2) / .004) \
                + 78 * math.exp(-((t - .52) ** 2) / .010) \
                + 66 * math.exp(-((t - .93) ** 2) / .005)
        v = int(max(58, min(238, v)))
        px[0, y] = (v, v, min(255, int(v * .985) + 2))
    grad = grad.resize((w, h), Image.BILINEAR).convert("RGBA")
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
    grad.putalpha(m)
    return grad


def _rail_matte(w, h, radius):
    """Android flagship frame: anodised aluminium, not polished titanium.

    Same shape as `_rail`, but the specular bands are flattened into a single
    soft vertical falloff. Polished highlights are an iPhone tell - carrying
    them onto an Android body is what makes a Pixel look like a mis-rendered
    iPhone.
    """
    grad = Image.new("RGB", (1, h))
    px = grad.load()
    for y in range(h):
        t = y / max(1, h - 1)
        v = int(max(52, min(150, 96 + 34 * math.exp(-((t - .30) ** 2) / .09)
                            - 26 * t)))
        px[0, y] = (v, v, v + 2)
    grad = grad.resize((w, h), Image.BILINEAR).convert("RGBA")
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
    grad.putalpha(m)
    return grad


def _window(shot, target_w, bar=52, radius=22, dark=False):
    sw = target_w
    sh = round(sw * shot.height / shot.width)
    shot = shot.resize((sw, sh), Image.LANCZOS)
    w, h = sw, sh + bar
    win = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(win)
    chrome = (28, 28, 32, 255) if dark else (238, 238, 240, 255)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=chrome)
    for i, c in enumerate([(255, 95, 87), (255, 189, 46), (40, 201, 64)]):
        cx = 26 + i * 30
        d.ellipse([cx - 9, bar // 2 - 9, cx + 9, bar // 2 + 9], fill=c + (255,))
    m = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, sw - 1, sh - 1], 4, fill=255)
    win.paste(shot, (0, bar), m)
    return win


def _browser(shot, target_w, bar=None, radius=22, dark=False, url=None):
    """A browser window: traffic lights, a URL pill, then the page.

    Web captures are pages, not app screens - a phone body around them reads as
    a lie. The pill takes the real URL so the tile says which site this is.
    """
    sw = target_w
    sh = round(sw * shot.height / shot.width)
    shot = shot.resize((sw, sh), Image.LANCZOS)
    bar = bar or max(44, int(target_w * 0.042))
    w, h = sw, sh + bar
    win = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(win)
    chrome = (30, 30, 35, 255) if dark else (240, 240, 243, 255)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=chrome)

    dot = max(6, bar // 6)
    for i, c in enumerate([(255, 95, 87), (255, 189, 46), (40, 201, 64)]):
        cx = bar * 0.55 + i * dot * 3
        cy = bar // 2
        d.ellipse([cx - dot, cy - dot, cx + dot, cy + dot], fill=c + (255,))

    # URL pill, centred, sized off the chrome height so it scales with the tile.
    pw, ph = int(w * 0.42), int(bar * 0.56)
    px, py = (w - pw) // 2, (bar - ph) // 2
    d.rounded_rectangle([px, py, px + pw, py + ph], ph // 2,
                        fill=(52, 52, 58, 255) if dark else (255, 255, 255, 255))
    if url:
        f = font(int(ph * 0.62), MEDIUM)
        ink = (196, 198, 204, 255) if dark else (110, 115, 125, 255)
        d.text((w // 2, py + ph // 2), url, font=f, fill=ink, anchor="mm")

    m = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, sw - 1, sh - 1], 4, fill=255)
    win.paste(shot, (0, bar), m)
    return win


def _macbook(shot, target_w):
    """A head-on MacBook: screen slab, hinge, tapered base, rubber feet.

    A flat window frame reads as a wireframe on a store tile; a real machine
    reads as a product. The capture still goes in at its true aspect ratio.
    """
    bezel = max(10, target_w // 84)
    sw = target_w - bezel * 2
    sh = round(sw * shot.height / shot.width)
    shot = shot.resize((sw, sh), Image.LANCZOS)

    lid_w, lid_h = target_w, sh + bezel * 2
    base_h = max(18, int(lid_h * 0.055))
    flare = int(target_w * 0.055)
    foot = max(6, base_h // 3)
    W = target_w + flare * 2
    H = lid_h + base_h + foot

    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox = flare

    # Lid: brushed aluminium edge, then the black bezel inside it.
    d.rounded_rectangle([ox, 0, ox + lid_w - 1, lid_h - 1],
                        int(target_w * .022), fill=(176, 179, 186, 255))
    d.rounded_rectangle([ox + 2, 2, ox + lid_w - 3, lid_h - 3],
                        int(target_w * .020), fill=(17, 17, 21, 255))
    m = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, sw - 1, sh - 1],
                                        max(2, bezel // 2), fill=255)
    im.paste(shot, (ox + bezel, bezel), m)
    # camera
    d.ellipse([ox + lid_w // 2 - 3, bezel // 2 - 3,
               ox + lid_w // 2 + 3, bezel // 2 + 3], fill=(58, 58, 64, 255))

    # Base: tapers outward, lighter at the top edge where the hinge catches light.
    y0, y1 = lid_h, lid_h + base_h
    d.polygon([(ox, y0), (ox + lid_w, y0), (W, y1), (0, y1)],
              fill=(196, 199, 206, 255))
    d.rectangle([ox, y0, ox + lid_w, y0 + max(2, base_h // 7)],
                fill=(120, 123, 131, 255))
    d.rounded_rectangle([0, y1 - base_h // 3, W - 1, y1 + foot],
                        foot, fill=(150, 153, 161, 255))
    # thumb notch
    nw = int(W * 0.11)
    d.chord([W // 2 - nw, y1 - foot, W // 2 + nw, y1 + foot * 2], 0, 180,
            fill=(118, 121, 129, 255))
    return im


def _crop(shot, box):
    """Crop to a fractional [l, t, r, b] box of the capture.

    A full-page capture is 5-10x taller than it is wide; placed whole it shrinks
    to an unreadable ribbon. Cropping to the section that carries the message
    keeps every remaining pixel at its true aspect ratio - unlike scaling one
    axis, which is what this whole script exists to prevent.
    """
    if not box:
        return shot
    l, t, r, b = box
    w, h = shot.size
    return shot.crop((int(l * w), int(t * h), int(r * w), int(b * h)))


def device(path, target_w, style="phone", rail=11, bezel=13, radius_pct=.148,
           buttons=True, dark=False, crop=None, url=None):
    if style == "macbook":
        return _macbook(_crop(Image.open(path).convert("RGB"), crop), target_w)
    shot = _crop(Image.open(path).convert("RGB"), crop)
    if style == "browser":
        return _browser(shot, target_w, dark=dark, url=url)
    if style == "window":
        return _window(shot, target_w, dark=dark)

    # Android bodies differ from iPhone in three ways that are all visible at
    # tile size: a thinner uniform rail, a tighter corner radius, and power +
    # volume on the RIGHT only (no left-hand cluster, no action button).
    android = style == "android"
    if android:
        rail, bezel, radius_pct = 8, 11, .112
    if style == "tablet":
        # iPad / Android tablet: uniform thin rail, and a corner radius that is
        # a much smaller FRACTION of the width than a phone's, because the body
        # is far wider. Reusing the phone's .148 on a 13" slab rounds the
        # corners into a lozenge. No side buttons - at tile size they read as
        # dirt on a body this wide.
        rail, bezel, radius_pct, buttons = 9, 12, .038, False

    sw = target_w - (rail + bezel) * 2
    sh = round(sw * shot.height / shot.width)          # derived, never assumed
    shot = shot.resize((sw, sh), Image.LANCZOS)
    bw, bh = target_w, sh + (rail + bezel) * 2
    radius = int(bw * radius_pct)
    btn = max(7, bw // 105)

    body = Image.new("RGBA", (bw + btn * 2, bh), (0, 0, 0, 0))
    ox = btn
    if buttons:
        d = ImageDraw.Draw(body)
        sides = [(.20, .27, "r"), (.30, .42, "r")] if android else \
                [(.20, .27, "l"), (.31, .40, "l"), (.42, .51, "l"), (.33, .45, "r")]
        fill = (108, 108, 110, 255) if android else (150, 148, 146, 255)
        for y0, y1, side in sides:
            x0 = 0 if side == "l" else ox + bw - 2
            d.rounded_rectangle([x0, int(bh * y0), x0 + btn + 2, int(bh * y1)],
                                btn // 2, fill=fill)
    body.alpha_composite((_rail_matte if android else _rail)(bw, bh, radius), (ox, 0))
    inner = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(inner).rounded_rectangle(
        [rail, rail, bw - rail - 1, bh - rail - 1], radius - rail, fill=(9, 9, 11, 255))
    body.alpha_composite(inner, (ox, 0))
    m = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, sw - 1, sh - 1],
                                        max(2, radius - rail - bezel), fill=255)
    body.paste(shot, (ox + rail + bezel, rail + bezel), m)
    return body


# --------------------------------------------------------------------- drawing

def shadow(canvas, layer, x, y, blur=34, spread=22, alpha=105):
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    a = layer.split()[3].point(lambda v: min(255, v * alpha // 100))
    tint = Image.new("RGBA", layer.size, (12, 20, 32, 255))
    tint.putalpha(a)
    sh.alpha_composite(tint, (x, y + spread))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


def place(canvas, layer, x, y, rotate=0.0, with_shadow=True, alpha=105):
    if rotate:
        layer = layer.rotate(rotate, resample=Image.BICUBIC, expand=True)
    if with_shadow:
        shadow(canvas, layer, x, y, alpha=alpha)
    canvas.alpha_composite(layer, (x, y))


# Vertical space the hand-drawn accent stroke actually occupies below the
# baseline box, measured off `underline` below (centre 30 + rise 7 + radius 8),
# plus breathing room. Anything drawn after an underlined line must clear this.
UNDERLINE_CLEARANCE = 52


def underline(canvas, x, y, width, colour):
    layer = Image.new("RGBA", (width + 40, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(260):
        t = i / 259
        px = 18 + t * width
        py = 30 + math.sin(t * math.pi) * -7 + math.sin(t * 5.5) * 1.4
        r = 1.8 + 6.2 * (math.sin(min(1, t * 1.06) * math.pi) ** .45)
        d.ellipse([px - r, py - r * .62, px + r, py + r * .62], fill=hexc(colour) + (255,))
    canvas.alpha_composite(layer, (x - 18, y))


def add_sheen(body, alpha=46):
    """Specular highlight across the top of a glossy tile.

    Must be composited, not drawn straight onto the RGBA image: ImageDraw
    REPLACES the alpha channel with the fill's alpha, so drawing inline would
    punch a translucent hole through the top of the tile.
    """
    s = body.width
    lay = Image.new("RGBA", body.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).chord([-s * .30, -s * .62, s * 1.06, s * .46], 0, 180,
                              fill=(255, 255, 255, alpha))
    lay.putalpha(ImageChops.multiply(lay.split()[3], body.split()[3]))
    body.alpha_composite(lay)
    return body


def draw_glyph(d, name, box, colour):
    """Minimal vector glyphs so feature rows read without icon assets."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx, cy = x0 + w / 2, y0 + h / 2
    c = hexc(colour) + (255,)
    lw = max(3, int(w * .11))

    if name == "sparkle":
        for (sx, sy, s) in ((cx, cy, .52), (x0 + w * .17, y0 + h * .19, .24),
                            (x1 - w * .15, y1 - h * .21, .20)):
            r = w * s / 2
            d.polygon([(sx, sy - r), (sx + r * .30, sy - r * .30),
                       (sx + r, sy), (sx + r * .30, sy + r * .30),
                       (sx, sy + r), (sx - r * .30, sy + r * .30),
                       (sx - r, sy), (sx - r * .30, sy - r * .30)], fill=c)
    elif name == "shield":
        d.polygon([(cx, y0), (x1 - w * .06, y0 + h * .20),
                   (x1 - w * .06, y0 + h * .55), (cx, y1),
                   (x0 + w * .06, y0 + h * .55), (x0 + w * .06, y0 + h * .20)],
                  fill=c)
    elif name == "folder":
        d.rounded_rectangle([x0, y0 + h * .16, x0 + w * .46, y0 + h * .34],
                            int(w * .06), fill=c)
        d.rounded_rectangle([x0, y0 + h * .26, x1, y1 - h * .10],
                            int(w * .09), fill=c)
    elif name == "clock":
        d.ellipse([x0, y0, x1, y1], outline=c, width=lw)
        d.line([cx, cy, cx, y0 + h * .24], fill=c, width=lw)
        d.line([cx, cy, x1 - w * .26, cy], fill=c, width=lw)
    elif name == "gauge":                        # bar chart - reads at prop size
        bw = w * .22
        for i, k in enumerate((.42, .74, 1.0)):
            bx = x0 + i * (w - bw) / 2
            d.rounded_rectangle([bx, y1 - h * k, bx + bw, y1],
                                int(bw * .32), fill=c)
    elif name == "broom":
        d.line([x0 + w * .18, y1 - h * .12, x1 - w * .26, y0 + h * .10],
               fill=c, width=lw)
        d.polygon([(x0 + w * .04, y1), (x0 + w * .40, y1 - h * .30),
                   (x0 + w * .58, y1 - h * .12), (x0 + w * .24, y1 + h * .04)],
                  fill=c)
    elif name == "disk":
        d.ellipse([x0, y0 + h * .06, x1, y0 + h * .40], outline=c, width=lw)
        d.arc([x0, y1 - h * .40, x1, y1 - h * .06], 0, 180, fill=c, width=lw)
        d.line([x0, y0 + h * .23, x0, y1 - h * .23], fill=c, width=lw)
        d.line([x1, y0 + h * .23, x1, y1 - h * .23], fill=c, width=lw)
    elif name == "copies":
        d.rounded_rectangle([x0, y0, x0 + w * .66, y0 + h * .66],
                            int(w * .12), outline=c, width=lw)
        d.rounded_rectangle([x1 - w * .66, y1 - h * .66, x1, y1],
                            int(w * .12), fill=c)


def icon_tile(size, colour, radius_pct=.28, glyph=None, tint=46, glossy=False):
    t = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(t)
    if glossy:
        # Same treatment as the floating props, so the left column and the
        # objects around the device read as one material.
        base = hexc(colour)
        grad = Image.new("RGB", (1, size))
        px = grad.load()
        for y in range(size):
            k = y / max(1, size - 1)
            px[0, y] = tuple(int(min(255, c * (1.32 - 0.50 * k))) for c in base)
        body = grad.resize((size, size), Image.BILINEAR).convert("RGBA")
        m = Image.new("L", (size, size), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1],
                                            int(size * radius_pct), fill=255)
        body.putalpha(m)
        add_sheen(body, 44)
        p = size * .27
        draw_glyph(ImageDraw.Draw(body), glyph or "sparkle",
                   (p, p, size - p, size - p), "#FFFFFF")
        return body
    d.rounded_rectangle([0, 0, size - 1, size - 1], int(size * radius_pct),
                        fill=hexc(colour) + (tint,))
    if glyph and not os.path.exists(glyph):
        p = size * .28
        draw_glyph(d, glyph, (p, p, size - p, size - p), colour)
        return t
    if glyph and os.path.exists(glyph):
        g = Image.open(glyph).convert("RGBA").resize((int(size * .56), int(size * .56)),
                                                     Image.LANCZOS)
        t.alpha_composite(g, (int(size * .22), int(size * .22)))
    else:
        r = size * .17
        d.ellipse([size / 2 - r, size / 2 - r, size / 2 + r, size / 2 + r],
                  fill=hexc(colour) + (255,))
    return t


def headline(canvas, lines, top, margin, size, th, mark=True):
    d = ImageDraw.Draw(canvas)
    f = font(size, HEAVY, role="display")
    y = top
    for text, accent in lines:
        colour = th["accent"] if accent else th["ink"]
        d.text((margin, y), text, font=f, fill=hexc(colour) + (255,))
        box = d.textbbox((margin, y), text, font=f)
        y = box[3] + int(size * .16)
        if accent and mark:
            top = box[3] + int(size * .05)
            underline(canvas, margin, top, box[2] - box[0], th["accent"])
            # `underline` draws a fixed-height hand-drawn stroke, so its extent
            # does NOT shrink with the type size. Line advance alone therefore
            # runs the stroke through whatever comes next - a sub-line at 60px
            # gets a pen stroke straight across it. Clear the stroke explicitly.
            y = max(y, top + UNDERLINE_CLEARANCE)
    return y


def paragraph(canvas, text, x, y, width, size, th, face=MEDIUM, leading=1.42):
    d = ImageDraw.Draw(canvas)
    f = font(size, face)
    words, line, out = text.split(), "", []
    for wd in words:
        probe = (line + " " + wd).strip()
        if d.textlength(probe, font=f) > width and line:
            out.append(line)
            line = wd
        else:
            line = probe
    out.append(line)
    for ln in out:
        d.text((x, y), ln, font=f, fill=hexc(th["sub"]) + (255,))
        y += int(size * leading)
    return y


def feature_rows(canvas, items, x, y, width, th, scale=1.0):
    """[{title, desc, colour?, icon?}] - icon tile + title + one line."""
    sz = int(96 * scale)
    for n, it in enumerate(items):
        tile = icon_tile(sz, it.get("colour", th["accent"]), glyph=it.get("icon"),
                         tint=th.get("icon_tint", 46),
                         glossy=th.get("icon_style", "flat") == "3d")
        canvas.alpha_composite(tile, (x, y))
        tx = x + sz + int(30 * scale)
        d = ImageDraw.Draw(canvas)
        d.text((tx, y + int(4 * scale)), it["title"], font=font(int(40 * scale), DEMI),
               fill=hexc(th["ink"]) + (255,))
        if it.get("desc"):
            paragraph(canvas, it["desc"], tx, y + int(52 * scale),
                      width - sz - int(30 * scale), int(32 * scale), th)
        y += sz + int(46 * scale)
        if th.get("row_rule") and n < len(items) - 1:
            ry = y - int(23 * scale)
            d.line([tx, ry, x + int(width * 0.78), ry], width=max(1, int(2 * scale)),
                   fill=hexc(th["row_rule"]) + (th.get("row_rule_alpha", 90),))
    return y


def check_row(canvas, items, y, W, th, scale=1.0):
    f = font(int(44 * scale), DEMI)
    d = ImageDraw.Draw(canvas)
    gap = int(56 * scale)
    widths = [d.textlength(t, font=f) + int(62 * scale) for t in items]
    total = sum(widths) + gap * (len(items) - 1)
    x = (W - total) // 2
    palette = [th["accent"], th.get("accent2", th["accent"]), th.get("accent3", th["accent"])]
    for i, t in enumerate(items):
        r = int(20 * scale)
        cy = y + int(22 * scale)
        d.ellipse([x, cy - r, x + 2 * r, cy + r], fill=hexc(palette[i % len(palette)]) + (255,))
        d.line([x + int(r * .55), cy, x + r, cy + int(r * .45),
                x + int(r * 1.5), cy - int(r * .5)], fill=(255, 255, 255, 255),
               width=max(2, int(4 * scale)), joint="curve")
        d.text((x + int(62 * scale), y), t, font=f, fill=hexc(th["ink"]) + (255,))
        x += widths[i] + gap
    return y + int(70 * scale)


def card(canvas, x, y, title, sub, th, tsize=62, ssize=34, pad=44, radius=34,
         anchor="left", fill=None, on_dark=False, width=None):
    ft, fs = font(tsize, DEMI), font(ssize, MEDIUM)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    w = width or int(max(probe.textlength(title, font=ft),
                         probe.textlength(sub, font=fs)) + pad * 2)
    h = tsize + ssize + pad * 2 + 18
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle([0, 0, w - 1, h - 1], radius,
                                            fill=hexc(fill or th["card"]) + (255,))
    d = ImageDraw.Draw(layer)
    # On a dark tile th["ink"] is white, which would be invisible on a white
    # card - cards carry their own ink/sub so both can coexist in one theme.
    ink = "#FFFFFF" if on_dark else th.get("card_ink", th["ink"])
    sb = "#E6E8F0" if on_dark else th.get("card_sub", th["sub"])
    d.text((pad, pad - 6), title, font=ft, fill=hexc(ink) + (255,))
    d.text((pad, pad + tsize + 8), sub, font=fs, fill=hexc(sb) + (255,))
    if anchor == "right":
        x -= w
    shadow(canvas, layer, x, y, blur=30, spread=16, alpha=80)
    canvas.alpha_composite(layer, (x, y))
    return w, h


def cta_bar(canvas, text, x, y, width, th, scale=1.0):
    h = int(150 * scale)
    layer = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle([0, 0, width - 1, h - 1], h // 2,
                                            fill=hexc(th["accent"]) + (255,))
    d = ImageDraw.Draw(layer)
    f = font(int(56 * scale), HEAVY)
    d.text(((width - d.textlength(text, font=f)) // 2, (h - int(56 * scale)) // 2 - 6),
           text, font=f, fill=(255, 255, 255, 255))
    shadow(canvas, layer, x, y, blur=26, spread=14, alpha=70)
    canvas.alpha_composite(layer, (x, y))


# ---------------------------------------------------------------------- layouts

def render(canvas, spec, th, W, H, landscape, style, i):
    # The base scale assumes a 1080-wide portrait phone tile. A 2880x1800 macOS
    # tile is landscape and viewed much larger, so key off its height instead -
    # otherwise every element renders roughly 1.7x too big.
    scale = W / (1800 if landscape else 1080)
    margin = int(90 * scale)
    layout = spec.get("layout", "hero-center")
    hsize = int(spec.get("head_size", 112) * scale)

    dev = None
    if spec.get("shot"):
        dw = int(W * spec.get("device_w", 0.44 if layout == "feature-left" else 0.68))
        dstyle = spec.get("device_style", "macbook" if layout == "hero-mac" else style)
        dev = device(spec["shot"], dw, style=dstyle,
                     buttons=(dstyle in ("phone", "android")),
                     dark=spec.get("dark_window", False),
                     crop=spec.get("shot_crop"), url=spec.get("url"))
        # Layouts size the frame by width, which is right for a portrait phone
        # but overflows for a wide browser window on a landscape tile. Cap the
        # height and scale both axes together - never one of them.
        hmax = spec.get("device_h", 0.78 if dstyle == "browser" else 0)
        if hmax and dev.height > H * hmax:
            k = H * hmax / dev.height
            dev = dev.resize((max(1, round(dev.width * k)),
                              max(1, round(dev.height * k))), Image.LANCZOS)

    if layout == "hero-mac":
        # Text column left, machine right, atmosphere behind both. Order matters:
        # glow and ribbons go down first so the device sits in the light, props
        # and sparkles go on top so they read as floating in front of it.
        col = int(W * 0.47)
        mx = int(W * 0.715)
        my = int(H * 0.50)

        glow(canvas, mx, my, int(W * 0.36), th.get("accent2", th["accent"]), 108)
        glow(canvas, int(W * 0.88), int(H * 0.16), int(W * 0.20), th["accent"], 70)
        ribbon_arcs(canvas, [
            dict(x=.72, y=.52, rx=.30, ry=.46, a0=195, a1=350, w=int(7 * scale),
                 colour=th.get("spark", "#FFFFFF"), alpha=th.get("ribbon_alpha", 70)),
            dict(x=.72, y=.52, rx=.36, ry=.55, a0=20, a1=150, w=int(5 * scale),
                 colour=th["accent"], alpha=95),
            dict(x=.68, y=.48, rx=.24, ry=.36, a0=250, a1=400, w=int(4 * scale),
                 colour=th.get("accent2", th["accent"]), alpha=80),
        ])
        sparkle_field(canvas, n=52, seed=spec.get("seed", 7),
                      region=(0.46, 0.02, 1.0, 0.98),
                      colour=th.get("spark", "#FFFFFF"),
                      amax=th.get("spark_alpha", 210))

        if dev:
            place(canvas, dev, mx - dev.width // 2, my - dev.height // 2,
                  rotate=spec.get("rotate", 0),
                  alpha=th.get("device_shadow", 105))

        pstyle = th.get("props", "3d")
        if pstyle != "none":
            for p in spec.get("props", []):
                prop(canvas, int(W * p["x"]), int(H * p["y"]),
                     W * p.get("s", 0.052), p["glyph"], p["colour"],
                     rotate=p.get("r", 0), style=pstyle,
                     drop=th.get("prop_shadow", 105), halo=th.get("prop_glow", 84))

        y = int(H * 0.10)
        if spec.get("pill"):
            f = font(int(34 * scale), DEMI)
            dd = ImageDraw.Draw(canvas)
            tw = dd.textlength(spec["pill"], font=f)
            ph, pw = int(86 * scale), int(tw + 68 * scale)
            lay = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
            ImageDraw.Draw(lay).rounded_rectangle(
                [0, 0, pw - 1, ph - 1], ph // 2, fill=hexc(th["accent"]) + (48,),
                outline=hexc(th["accent"]) + (150,), width=max(2, int(2 * scale)))
            ImageDraw.Draw(lay).text(
                (int(34 * scale), (ph - int(34 * scale)) // 2 - int(5 * scale)),
                spec["pill"], font=f, fill=hexc(th["accent"]) + (255,))
            canvas.alpha_composite(lay, (margin, y))
            y += int(128 * scale)

        y = headline(canvas, spec["head"], y, margin, hsize, th,
                     mark=spec.get("underline", True))
        if spec.get("sub"):
            y = paragraph(canvas, spec["sub"], margin, y + int(24 * scale),
                          col - margin, int(38 * scale), th) + int(38 * scale)
        if spec.get("features"):
            feature_rows(canvas, spec["features"], margin, y, col - margin, th, scale)
        return

    if layout == "object-hero":
        # Branded opener: no app UI, so every string here must be a claim the
        # app actually delivers - it is the tile reviewers read first.
        col = int(W * 0.50)
        y = margin
        if spec.get("pill"):
            f = font(int(38 * scale), DEMI)
            d = ImageDraw.Draw(canvas)
            tw = d.textlength(spec["pill"], font=f)
            ph, pw = int(96 * scale), int(tw + 76 * scale)
            layer = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
            ImageDraw.Draw(layer).rounded_rectangle(
                [0, 0, pw - 1, ph - 1], ph // 2,
                fill=hexc(th["accent"]) + (48,),
                outline=hexc(th["accent"]) + (140,), width=max(2, int(2 * scale)))
            ImageDraw.Draw(layer).text(
                (int(38 * scale), (ph - int(38 * scale)) // 2 - int(6 * scale)),
                spec["pill"], font=f, fill=hexc(th["accent"]) + (255,))
            canvas.alpha_composite(layer, (margin, y))
            y += int(150 * scale)
        y = headline(canvas, spec["head"], y, margin, hsize, th,
                     mark=spec.get("underline", True))
        if spec.get("sub"):
            y = paragraph(canvas, spec["sub"], margin, y + int(26 * scale),
                          col - margin, int(40 * scale), th) + int(46 * scale)
        if spec.get("features"):
            feature_rows(canvas, spec["features"], margin, y, col - margin, th, scale)

        # Hero object: the app icon as a tilted solid, not a flat sticker.
        if spec.get("app_icon") and os.path.exists(spec["app_icon"]):
            hero = int(W * spec.get("hero", 0.27))
            ccx, ccy = int(W * spec.get("hero_x", 0.70)), int(H * spec.get("hero_y", 0.50))

            for rr, al in ((int(hero * 1.15), th.get("halo", 30)),
                           (int(hero * .86), int(th.get("halo", 30) * 1.5))):
                blob(canvas, ccx, ccy, rr, rr, th.get("accent2", th["accent"]), al)
            glow(canvas, ccx, ccy, hero * 1.25, th.get("accent2", th["accent"]),
                 th.get("hero_glow", 70))

            ic = Image.open(spec["app_icon"]).convert("RGBA").resize(
                (hero, hero), Image.LANCZOS)
            mask = Image.new("L", (hero, hero), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                [0, 0, hero - 1, hero - 1], int(hero * 0.225), fill=255)
            ic.putalpha(mask)
            face = solid3d(ic, yaw=spec.get("yaw", -20), pitch=spec.get("pitch", 13),
                           depth=spec.get("depth", 0.45),
                           focal=spec.get("focal", 9.0),
                           side=th.get("extrude", "#3A2299"))

            fx, fy = ccx - face.width // 2, ccy - face.height // 2
            # contact shadow on the ground plane, then the solid, then the face
            gs = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            ImageDraw.Draw(gs).ellipse(
                [ccx - hero * .58, ccy + hero * .50, ccx + hero * .52, ccy + hero * .76],
                fill=hexc(th.get("shadow_tint", "#2A1A6B")) + (th.get("ground", 70),))
            canvas.alpha_composite(gs.filter(ImageFilter.GaussianBlur(hero // 16)))
            shadow(canvas, face, fx, fy, blur=int(hero * .26),
                   spread=int(hero * .09), alpha=th.get("hero_shadow", 95))
            canvas.alpha_composite(face, (fx, fy))

            # light swirling around the object, drawn over it so it wraps
            ribbon_arcs(canvas, [
                dict(x=ccx / W, y=(ccy + hero * .10) / H, rx=hero * 0.70 / W,
                     ry=hero * 0.30 / H, a0=352, a1=548, w=max(4, hero // 44),
                     colour=th.get("swirl", "#FFFFFF"),
                     alpha=th.get("swirl_alpha", 150)),
                dict(x=ccx / W, y=(ccy - hero * .06) / H, rx=hero * 0.62 / W,
                     ry=hero * 0.26 / H, a0=168, a1=372, w=max(3, hero // 60),
                     colour=th.get("swirl", "#FFFFFF"),
                     alpha=int(th.get("swirl_alpha", 150) * .6)),
            ], blur=max(6, hero // 34))

            orb = int(hero * 0.24)
            glyphs = spec.get("orbs", ["folder", "shield", "clock", "copies"])
            cols = th.get("orb_colours", [th.get("accent2", th["accent"]), th["accent"],
                                          th.get("accent3", th["accent"]),
                                          th.get("accent2", th["accent"])])
            styles = spec.get("orb_styles", ["glass", "3d", "3d", "glass"])
            for name, cl, st, (ax, ay) in zip(
                    glyphs, cols, styles,
                    [(-.70, -.56), (.70, -.60), (-.72, .56), (.72, .52)]):
                prop(canvas, ccx + int(hero * ax), ccy + int(hero * ay), orb,
                     name, cl, style=st, shape="circle",
                     drop=th.get("prop_shadow", 105), halo=th.get("prop_glow", 84))
        return

    if layout == "feature-left":
        col = int(W * 0.46)
        y = margin
        if spec.get("app_icon"):
            ic = icon_tile(int(150 * scale), th["accent"], glyph=spec["app_icon"])
            canvas.alpha_composite(ic, (margin, y))
            y += int(190 * scale)
        y = headline(canvas, spec["head"], y, margin, hsize, th,
                     mark=spec.get("underline", True))
        if spec.get("sub"):
            y = paragraph(canvas, spec["sub"], margin, y + int(20 * scale),
                          col - margin, int(38 * scale), th) + int(40 * scale)
        if spec.get("features"):
            y = feature_rows(canvas, spec["features"], margin, y, col - margin, th, scale)
        if spec.get("badge"):
            card(canvas, margin, H - margin - int(190 * scale), spec["badge"]["title"],
                 spec["badge"]["sub"], th, int(40 * scale), int(32 * scale),
                 int(34 * scale), int(26 * scale))
        if dev:
            dx = W - dev.width - int(W * 0.04)
            dy = (H - dev.height) // 2 if landscape else int(H * 0.22)
            place(canvas, dev, dx, dy, rotate=spec.get("rotate", 0))
        return

    if layout == "showcase":
        y = int(H * 0.05)
        y = headline(canvas, spec["head"], y, margin, hsize, th,
                     mark=spec.get("underline", True))
        if spec.get("checks"):
            y = check_row(canvas, spec["checks"], y + int(24 * scale), W, th, scale)
        if dev:
            dx = (W - dev.width) // 2
            place(canvas, dev, dx, y + int(20 * scale), rotate=spec.get("rotate", 0))
            # Cards clip the window's outer edges as callouts. Kept small on
            # purpose - a card wide enough to reach the middle hides the very UI
            # the tile exists to prove.
            cy = y + int(H * spec.get("card_y", 0.42))
            cs = (int(34 * scale), int(24 * scale), int(26 * scale), int(22 * scale))
            if spec.get("left_card"):
                card(canvas, margin, cy, spec["left_card"]["title"],
                     spec["left_card"]["sub"], th, *cs,
                     fill=spec["left_card"].get("fill"),
                     on_dark=spec["left_card"].get("on_dark", False))
            if spec.get("right_card"):
                card(canvas, W - margin, cy, spec["right_card"]["title"],
                     spec["right_card"]["sub"], th, *cs, anchor="right",
                     fill=spec["right_card"].get("fill"),
                     on_dark=spec["right_card"].get("on_dark", False))
        return

    # hero-center (default)
    y = headline(canvas, spec["head"], int(H * 0.06), margin, hsize, th,
                 mark=spec.get("underline", True))
    if spec.get("sub"):
        y = paragraph(canvas, spec["sub"], margin, y + int(16 * scale),
                      int(W * 0.72), int(38 * scale), th)
    if dev:
        dx = (W - dev.width) // 2 + (int(30 * scale) if i % 2 == 0 else -int(30 * scale))
        dy = y + int(H * 0.04)
        place(canvas, dev, dx, dy, rotate=spec.get("rotate", -3.2 if i % 2 == 0 else 3.2))
        if spec.get("card"):
            cy = dy + int(dev.height * 0.42)
            side = spec.get("side", "left")
            if side == "left":
                card(canvas, margin - int(26 * scale), cy, spec["card"]["title"],
                     spec["card"]["sub"], th, int(62 * scale), int(34 * scale),
                     int(44 * scale))
            else:
                card(canvas, W - margin + int(26 * scale), cy, spec["card"]["title"],
                     spec["card"]["sub"], th, int(62 * scale), int(34 * scale),
                     int(44 * scale), anchor="right")
    if spec.get("cta"):
        cta_bar(canvas, spec["cta"], margin, H - int(220 * scale), W - margin * 2, th, scale)


# ------------------------------------------------------------------------ build

def build(platform, tiles, shots_dir, out_dir, theme, seed=11):
    p = PRESETS[platform]
    (W, H) = p["size"]
    landscape = p["orient"] == "landscape"
    if platform in WEB_PLATFORMS:
        style = "browser"
    elif platform == "macos":
        style = "window"
    else:
        style = "phone"
    th = dict(THEME)
    th.update(theme or {})
    _FONT_CACHE.clear()
    _ACTIVE["text"] = th.get("font_text", th.get("font", "inter"))
    _ACTIVE["display"] = th.get("font_display", th.get("font", _ACTIVE["text"]))
    for role, name in _ACTIVE.items():
        if name not in TYPEFACES:
            raise SystemExit(f"unknown {role} typeface {name!r}; "
                             f"choose from: {', '.join(sorted(TYPEFACES))}")
        ensure(name)
    os.makedirs(out_dir, exist_ok=True)
    strip = make_strip(p["size"], len(tiles), th, seed=seed)

    for i, spec in enumerate(tiles):
        canvas = strip.crop((W * i, 0, W * (i + 1), H)).copy()
        for b in spec.get("blobs", []):
            blob(canvas, int(W * b["x"]), int(H * b["y"]), int(W * b["rx"]),
                 int(H * b["ry"]), b.get("colour", th["accent"]), b.get("alpha", 255))
        if spec.get("shot"):
            spec = dict(spec, shot=os.path.join(shots_dir, spec["shot"]))
        render(canvas, spec, th, W, H, landscape, style, i)

        slug = spec.get("slug") or spec["head"][-1][0].lower().replace(" ", "-").replace(",", "")
        out = os.path.join(out_dir, f"{i + 1:02d}-{slug}.png")
        canvas.convert("RGB").save(out)          # RGB: Apple rejects alpha
        print("wrote", out, canvas.size)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--palette-from", help="suggest accent colours from an app icon")
    ap.add_argument("--suggest-fonts", metavar="DESCRIPTION",
                    help="recommend a display/text pairing for what the app is")
    ap.add_argument("--platform", choices=sorted(PRESETS))
    ap.add_argument("--config", help="JSON: {theme:{...}, tiles:[...]}")
    ap.add_argument("--shots", default=".")
    ap.add_argument("--out", default="./designed")
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()

    if a.suggest_fonts:
        for (disp, text), why in advise(a.suggest_fonts):
            print(f'  "font_display": "{disp}", "font_text": "{text}"')
            print(f"    {why}")
            for r in dict.fromkeys((disp, text)):
                print(f"    - {r}: {TYPEFACES[r]['note']}")
            print()
        return
    if a.palette_from:
        for c in suggest_palette(a.palette_from):
            print(c)
        return
    if not (a.platform and a.config):
        ap.error("--platform and --config are required")

    with open(a.config) as fh:
        cfg = json.load(fh)
    tiles = cfg["tiles"] if isinstance(cfg, dict) else cfg
    theme = cfg.get("theme", {}) if isinstance(cfg, dict) else {}
    for t in tiles:
        t["head"] = [(txt, bool(acc)) for txt, acc in t["head"]]
    build(a.platform, tiles, a.shots, a.out, theme, seed=a.seed)


if __name__ == "__main__":
    main()

# CONFIG EXAMPLE
# {
#   "theme": {"bg": "#F3F8F6", "bg2": "#DCEDE6", "accent": "#12796A",
#             "accent2": "#F5A524", "ink": "#0C1F1B", "sub": "#5B6B66",
#             "background": "gradient"},
#   "tiles": [
#     {"layout": "feature-left", "shot": "home.png", "app_icon": "icon.png",
#      "head": [["One App.", false], ["Every AI Tool.", true]],
#      "sub": "Convert, transcribe, scan and read - all in one suite.",
#      "features": [{"title": "Text to Speech", "desc": "Natural voices.",
#                    "colour": "#12796A"}],
#      "badge": {"title": "Private. Secure.", "sub": "Encrypted, never shared."}},
#     {"layout": "hero-center", "shot": "tts.png",
#      "head": [["Convert Text", false], ["Instantly", true]],
#      "card": {"title": "100+ languages", "sub": "Speak in any of them"},
#      "side": "right", "cta": "Try it free today"}
#   ]
# }
#
# WEB CONFIG EXAMPLE  (--platform web-hero | web-og | web-square | web-tall)
# Frame defaults to "browser"; "url" fills the address pill, "shot_crop" takes
# the fractional [l, t, r, b] slice of a full-page capture, "device_h" caps the
# window height as a fraction of the tile.
# {
#   "theme": {"bg": "#0E1116", "bg2": "#182030", "accent": "#4ADE80",
#             "ink": "#F5F7FA", "sub": "#9AA4B2", "background": "gradient"},
#   "tiles": [
#     {"layout": "hero-mac", "shot": "page.png", "url": "example.com",
#      "shot_crop": [0, 0, 1, 0.42], "device_w": 0.52, "device_h": 0.78,
#      "head": [["Train", false], ["Smarter", true]],
#      "sub": "Programs, check-ins and progress in one place."}
#   ]
# }
