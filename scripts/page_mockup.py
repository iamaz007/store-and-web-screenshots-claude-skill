#!/usr/bin/env python3
"""Full-page website mockup: the whole page, sliced into columns, on a backdrop.

The long-sheet look - a full-page capture cut into 2-3 vertical columns, rounded,
shadowed and floated on a gradient. Use it when the answer to "whole page or one
part?" is *whole page*: the page reads as a shape and a rhythm, not as text.

    python3 page_mockup.py --shot page.png --out docs/ --size 1280x769 \\
        --bg "#14150F,#0B0B0A" --glow "#C6F94F" --cols 2

Every column keeps the capture's true aspect ratio - the slice is a crop, and
both axes scale by the same factor. Nothing here can stretch UI.
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys_path_note = None  # fonts.py lives beside this file


def hexc(v):
    v = v.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def trim_blank(im, tol=6, pad=None):
    """Drop uniform rows at the bottom - a viewport taller than the page leaves
    a slab of background that reads as a broken capture.

    `pad` keeps a strip of page background below the last real content, so the
    footer sits on the page rather than flush against the cut edge.
    """
    g = im.convert("L")
    w, h = g.size
    row = h
    base = g.getpixel((w // 2, h - 2))
    while row > 2:
        strip = g.crop((0, row - 2, w, row))
        lo, hi = strip.getextrema()
        if hi - lo > tol or abs(lo - base) > tol:
            break
        row -= 2
    pad = int(w * 0.035) if pad is None else pad
    return im.crop((0, 0, w, min(h, row + pad)))


def gradient(size, c0, c1, angle=155):
    """Linear gradient at an arbitrary angle.

    Computed on a small grid and scaled up: a linear ramp survives bilinear
    interpolation exactly, and the per-pixel loop at full tile size is the
    slowest thing in this script by an order of magnitude.
    """
    w, h = size
    sw, sh = max(2, w // 8), max(2, h // 8)
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    im = Image.new("RGB", (sw, sh))
    px = im.load()
    span = abs(dx) * sw + abs(dy) * sh
    ox = 0 if dx >= 0 else sw
    oy = 0 if dy >= 0 else sh
    for y in range(sh):
        for x in range(sw):
            t = (abs(x - ox) * abs(dx) + abs(y - oy) * abs(dy)) / span
            px[x, y] = tuple(round(a0 + (a1 - a0) * t) for a0, a1 in zip(c0, c1))
    return im.resize((w, h), Image.BILINEAR)


def glow(canvas, cx, cy, r, colour, alpha=120):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 26
    for i in range(steps, 0, -1):
        k = i / steps
        # ImageDraw *overwrites* alpha rather than accumulating it, so the
        # falloff has to be baked into each ring: opaque at the core, nothing
        # at the rim. Drawing equal alphas here yields an invisible glow.
        a = int(alpha * (1 - k) ** 1.8)
        d.ellipse([cx - r * k, cy - r * k * 0.72, cx + r * k, cy + r * k * 0.72],
                  fill=colour + (max(1, a),))
    layer = layer.filter(ImageFilter.GaussianBlur(r * 0.14))
    canvas.alpha_composite(layer)


def grain(canvas, amount=7, seed=5):
    rnd = random.Random(seed)
    w, h = canvas.size
    n = Image.new("L", (w // 2, h // 2))
    n.putdata([rnd.randint(128 - amount * 8, 128 + amount * 8)
               for _ in range((w // 2) * (h // 2))])
    n = n.resize((w, h), Image.BILINEAR)
    noise = Image.merge("RGBA", (n, n, n, Image.new("L", (w, h), amount * 3)))
    canvas.alpha_composite(noise)


def rounded(im, radius):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1],
                                        radius, fill=255)
    out = im.convert("RGBA")
    out.putalpha(m)
    return out


def drop(canvas, layer, x, y, blur, spread, alpha, dy):
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    a = layer.split()[-1].point(lambda v: min(255, v * alpha // 255))
    body = Image.new("RGBA", layer.size, (0, 0, 0, 255))
    body.putalpha(a)
    body = body.resize((layer.width + spread * 2, layer.height + spread * 2),
                       Image.LANCZOS)
    sh.alpha_composite(body, (x - spread, y - spread + dy))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


def backdrop(size, bg, glow_hex, angle, seed, glow_k):
    W, H = size
    canvas = gradient(size, hexc(bg[0]), hexc(bg[1]), angle).convert("RGBA")
    if glow_hex:
        # Bloom goes where the backdrop is actually visible - the margins and
        # corners. A glow behind the sheets is a glow nobody sees.
        # Centres sit off-canvas so only the falloff lands in frame - an
        # in-frame core reads as a coloured blob, not as light.
        glow(canvas, int(W * -0.06), int(H * -0.12), int(W * 0.62),
             hexc(glow_hex), int(150 * glow_k))
        glow(canvas, int(W * 1.04), int(H * 1.06), int(W * 0.52),
             hexc(glow_hex), int(105 * glow_k))
    grain(canvas, seed=seed)
    return canvas


def sheet(im, cw, radius, edge, shadow_alpha):
    ch = round(cw * im.height / im.width)             # derived, never assumed
    im = rounded(im.resize((cw, ch), Image.LANCZOS), radius)
    if edge:
        ImageDraw.Draw(im).rounded_rectangle([0, 0, cw - 1, ch - 1], radius,
                                             outline=hexc(edge) + (90,), width=2)
    return im


_FACES = {}


def _face(name, size, weight_role="heavy"):
    """A face by name and weight role, fetched and cached by fonts.py."""
    from fonts import ensure, resolve
    key = (name, weight_role, int(size))
    if key not in _FACES:
        ensure(name)
        path, index, weight = resolve(name, weight_role)
        f = ImageFont.truetype(path, int(size), index=index)
        if weight is not None:
            # Variable family: set the wght axis by position, it is not always
            # the first axis in the table.
            axes = [a["default"] for a in f.get_variation_axes()]
            for i, a in enumerate(f.get_variation_axes()):
                if a["name"] in (b"Weight", "Weight"):
                    axes[i] = weight
            f.set_variation_by_axes(axes)
        _FACES[key] = f
    return _FACES[key]


def text_panel(canvas, box, th, title, headline, sub, pills):
    """Brand block beside the screens: mark, headline, one line, small pills.

    The marketplace-tile convention - copy on one side, product on the other.
    Keep it short; this panel competes with the screens for the first read.
    """
    x, y0, w, h = box
    ink, accent, muted = hexc(th["ink"]), hexc(th["accent"]), hexc(th["muted"])
    # Draw on an overlay: ImageDraw with a sub-255 alpha *replaces* the canvas
    # alpha instead of blending, so a "70% outline" drawn straight onto the
    # backdrop comes out fully opaque once the tile is flattened to RGB.
    over = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    lines = []                                   # (font, text, fill, gap after)

    if title:
        f = _face(th["display"], int(w * 0.075), "heavy")
        lines.append((f, title.upper(), ink, int(w * 0.10)))
    if headline:
        f = _face(th["display"], int(w * 0.155), "heavy")
        for i, part in enumerate(headline.split("|")):
            lines.append((f, part.strip(), ink if i == 0 else accent,
                          int(w * 0.02)))
        lines[-1] = lines[-1][:3] + (int(w * 0.07),)
    if sub:
        f = _face(th["text"], int(w * 0.068), "regular")
        # Wrap by measured width - never letter-space or squeeze to fit.
        words, line = sub.split(), ""
        for word in words:
            trial = f"{line} {word}".strip()
            if d.textlength(trial, font=f) > w and line:
                lines.append((f, line, muted, int(w * 0.018)))
                line = word
            else:
                line = trial
        lines.append((f, line, muted, int(w * 0.09)))

    total = sum(f.getbbox(t)[3] - f.getbbox(t)[1] + g for f, t, _, g in lines)
    pill_f = _face(th["text"], int(w * 0.056), "medium") if pills else None
    pill_h = int(w * 0.13)
    if pills:
        total += pill_h

    y = y0 + (h - total) // 2
    for f, t, fill, g in lines:
        d.text((x, y), t, font=f, fill=fill)
        y += f.getbbox(t)[3] - f.getbbox(t)[1] + g

    px = x
    for p in pills:
        pw = int(d.textlength(p, font=pill_f) + w * 0.095)
        if px + pw > x + w:                       # wrap rather than overflow
            px, y = x, y + pill_h + int(w * 0.025)
        d.rounded_rectangle([px, y, px + pw, y + pill_h], pill_h // 2,
                            outline=ink + (105,), width=2)
        d.text((px + pw // 2, y + pill_h // 2), p, font=pill_f, fill=ink,
               anchor="mm")
        px += pw + int(w * 0.028)

    canvas.alpha_composite(over)


def build_board(columns, size, out_path, bg, glow_hex, radius, gap, vgap,
                margin, angle, edge, seed, glow_k, card_aspect, shadow_alpha,
                balance=True, tilt=0.0, panel=None, bleed=0.0, ss=2,
                per_col=False):
    """Columns of stacked sheets: the long marketing page beside the product.

    Column one is normally the whole landing page; the rest are app screens
    cropped to a common card aspect so the stack reads as an even rhythm
    instead of a ragged pile.
    """
    # Everything below works in supersampled space; the final resize brings it
    # back to the requested size.
    W, H = size[0] * ss, size[1] * ss
    gap, margin, radius = gap * ss, margin * ss, radius * ss
    stacks = []
    for col in columns:
        items = []
        for path in col:
            im = trim_blank(Image.open(path).convert("RGB"))
            if len(col) > 1 and card_aspect:
                # Take the top of the screen: header plus the content that
                # actually identifies the page. A crop, never a squeeze.
                keep = min(im.height, int(im.width / card_aspect))
                im = im.crop((0, 0, im.width, keep))
            items.append(im)
        stacks.append(items)

    # One scale for the whole board, set by the tallest column.
    def col_ratio(items, g):
        return sum(i.height / i.width for i in items) + g * (len(items) - 1)

    if balance and not per_col:
        # A column holding three screens ends far short of one holding four,
        # and the ragged bottom edge reads as a mistake. Let the short columns
        # show *more* of each screen instead - taller crops, same scale, no
        # gaps to explain. Capped by how much screen there actually is.
        target = max(col_ratio(s, vgap) for s in stacks)
        for col, items in zip(columns, stacks):
            if len(items) < 2:
                continue
            for _ in range(6):
                short = target - col_ratio(items, vgap)
                if short <= 0.01:
                    break
                grew = False
                for i, (path, im) in enumerate(zip(col, items)):
                    full = trim_blank(Image.open(path).convert("RGB"))
                    want = im.height + int(short / len(items) * im.width)
                    keep = min(full.height, want)
                    if keep > im.height:
                        items[i] = full.crop((0, 0, full.width, keep))
                        grew = True
                if not grew:
                    break

    n = len(stacks)
    # A tilted board needs its own bounding box: rotating by t costs
    # sin(t) * width of vertical room and sin(t) * height of horizontal room.
    t = math.radians(abs(tilt))
    # With a copy panel the board takes the right-hand share of the tile and is
    # allowed to run off the edges, the way marketplace tiles do.
    board_x = int(W * panel["col"]) if panel else 0
    avail_w = W - board_x - margin * 2 - gap * (n - 1) + int(W * bleed)
    avail_h = H - margin * 2 + int(H * bleed * 2)
    fit_h = max(80.0, (avail_h - math.sin(t) * avail_w) / math.cos(t))
    fit_w = max(80.0, (avail_w - math.sin(t) * avail_h) / math.cos(t))
    if per_col:
        # Each column fills the height on its own terms. One shared scale lets
        # the tallest column - usually the whole landing page - shrink every
        # app screen beside it to an unreadable size; sizing per column keeps
        # the long page as a shape while the product screens stay legible.
        widths = [fit_h / col_ratio(s, vgap) for s in stacks]
        if sum(widths) > fit_w:             # fit_w is the room for all columns
            k = fit_w / sum(widths)
            widths = [w * k for w in widths]
        col_ws = [int(w) for w in widths]
    else:
        col_ws = [int(min(fit_w / n,
                          min(fit_h / col_ratio(s, vgap) for s in stacks)))] * n
    total_w = sum(col_ws) + gap * (n - 1)
    x0 = board_x + (W - board_x - total_w) // 2

    canvas = backdrop((W, H), bg, glow_hex, angle, seed, glow_k)
    if panel:
        pm = int(W * 0.045)
        text_panel(canvas, (pm, 0, board_x - pm * 2, H), panel,
                   panel.get("title"), panel.get("headline"),
                   panel.get("sub"), panel.get("pills", []))
    # Sheets and their shadows share one layer so the whole board rotates as a
    # single object - shadows tilt with the sheets they belong to.
    pad = int(max(W, H) * 0.35)
    layer = Image.new("RGBA", (W + pad * 2, H + pad * 2), (0, 0, 0, 0))
    x = x0 + pad
    for ci, items in enumerate(stacks):
        col_w = col_ws[ci]
        vg = int(col_w * vgap)
        sheets = [sheet(im, col_w, radius, edge, shadow_alpha) for im in items]
        col_h = sum(s.height for s in sheets) + vg * (len(sheets) - 1)
        y = (H - col_h) // 2 + pad
        for s in sheets:
            drop(layer, s, x, y, blur=int(col_w * 0.16), spread=4,
                 alpha=shadow_alpha, dy=int(col_w * 0.05))
            layer.alpha_composite(s, (x, y))
            y += s.height + vg
        x += col_w + gap

    if tilt:
        layer = layer.rotate(tilt, resample=Image.BICUBIC, center=(
            layer.width / 2, layer.height / 2))
    canvas.alpha_composite(layer.crop((pad, pad, pad + W, pad + H)))

    out = canvas.convert("RGB")
    if ss > 1:
        # Supersample down. Compositing and rotating at final size resamples a
        # 2880px capture twice at low resolution and the UI goes soft; doing the
        # whole board large and reducing once keeps the edges.
        out = out.resize((W // ss, H // ss), Image.LANCZOS)
        out = out.filter(ImageFilter.UnsharpMask(radius=0.7, percent=55,
                                                 threshold=2))
    out.save(out_path)
    print("wrote", out_path, out.size, f"{n} columns, sheet width {col_w // ss}")


def build(shot_path, size, out_path, bg, glow_hex, cols, radius, gap,
          stagger, margin, angle, edge, seed, glow_k=1.0, shadow_alpha=150):
    W, H = size
    shot = trim_blank(Image.open(shot_path).convert("RGB"))
    canvas = backdrop(size, bg, glow_hex, angle, seed, glow_k)

    # Slice: each column is a crop of the capture, so the page continues from
    # the bottom of one column into the top of the next.
    slice_h = shot.height // cols
    pieces = [shot.crop((0, i * slice_h, shot.width,
                         shot.height if i == cols - 1 else (i + 1) * slice_h))
              for i in range(cols)]

    # Fit by height first: the tallest column decides the scale, and the same
    # factor applies to both axes.
    tallest = max(p.height / p.width for p in pieces)
    avail_h = H - margin * 2 - abs(stagger)
    col_w = min(int(avail_h / tallest), int((W - margin * 2 - gap * (cols - 1)) / cols))
    total_w = col_w * cols + gap * (cols - 1)
    x0 = (W - total_w) // 2

    for i, p in enumerate(pieces):
        cw = col_w
        ch = round(cw * p.height / p.width)          # derived, never assumed
        p = p.resize((cw, ch), Image.LANCZOS)
        p = rounded(p, radius)
        if edge:
            d = ImageDraw.Draw(p)
            d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius,
                                outline=hexc(edge) + (70,), width=2)
        x = x0 + i * (cw + gap)
        y = (H - ch) // 2 + (stagger if i % 2 else -stagger)
        drop(canvas, p, x, y, blur=34, spread=8, alpha=150, dy=18)
        canvas.alpha_composite(p, (x, y))

    canvas.convert("RGB").save(out_path)
    print("wrote", out_path, (W, H))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shot", help="full-page capture (2x DPR), sliced into --cols")
    ap.add_argument("--board", help="columns of stacked sheets: paths separated "
                                    "by ',' within a column and '|' between "
                                    "columns, e.g. 'page.png|a.png,b.png'")
    ap.add_argument("--card-aspect", type=float, default=1.6,
                    help="w/h each stacked screen is cropped to (0 = no crop)")
    ap.add_argument("--vgap", type=float, default=0.045,
                    help="vertical gap inside a column, as a fraction of width")
    ap.add_argument("--shadow", type=int, default=150, help="drop shadow alpha")
    ap.add_argument("--title", default="", help="brand mark line in the panel")
    ap.add_argument("--headline", default="",
                    help="panel headline; '|' splits lines, later lines accent")
    ap.add_argument("--sub", default="", help="one supporting line")
    ap.add_argument("--pills", default="", help="comma-separated chips")
    ap.add_argument("--text-col", type=float, default=0.0,
                    help="fraction of the tile given to the copy panel")
    ap.add_argument("--per-column-scale", action="store_true",
                    help="size each column to fill the height on its own, so a "
                         "tall landing page does not shrink the app screens")
    ap.add_argument("--supersample", type=int, default=2,
                    help="render at NxN and reduce once; 1 disables")
    ap.add_argument("--bleed", type=float, default=0.0,
                    help="let the board run off the edges by this fraction")
    ap.add_argument("--ink", default="#14150F")
    ap.add_argument("--accent-ink", default="#6C8B12")
    ap.add_argument("--muted", default="#6A6A62")
    ap.add_argument("--font-display", default="archivo")
    ap.add_argument("--font-text", default="inter")
    ap.add_argument("--tilt", type=float, default=0.0,
                    help="in-plane rotation of the whole board, degrees (3-5 reads best)")
    ap.add_argument("--no-balance", action="store_true",
                    help="leave short columns short instead of growing crops")
    ap.add_argument("--out", required=True, help="output png path")
    ap.add_argument("--size", required=True, help="WxH, e.g. 1280x769")
    ap.add_argument("--bg", default="#14150F,#0B0B0A", help="two hex stops")
    ap.add_argument("--glow", default="", help="accent hex bloomed into the margins")
    ap.add_argument("--glow-strength", type=float, default=1.0)
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--radius", type=int, default=14)
    ap.add_argument("--gap", type=int, default=40)
    ap.add_argument("--stagger", type=int, default=0, help="px offset, alternating")
    ap.add_argument("--margin", type=int, default=52)
    ap.add_argument("--angle", type=int, default=155)
    ap.add_argument("--edge", default="", help="hairline hex on the sheet edge")
    ap.add_argument("--seed", type=int, default=5)
    a = ap.parse_args()

    if not (a.shot or a.board):
        ap.error("pass --shot (slice one page) or --board (columns of screens)")

    w, h = (int(v) for v in a.size.lower().split("x"))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    panel = None
    if a.text_col:
        panel = dict(col=a.text_col, title=a.title, headline=a.headline,
                     sub=a.sub, pills=[p for p in a.pills.split(",") if p],
                     ink=a.ink, accent=a.accent_ink, muted=a.muted,
                     display=a.font_display, text=a.font_text)
    if a.board:
        columns = [[p.strip() for p in col.split(",") if p.strip()]
                   for col in a.board.split("|")]
        build_board(columns, (w, h), a.out, a.bg.split(","), a.glow, a.radius,
                    a.gap, a.vgap, a.margin, a.angle, a.edge, a.seed,
                    a.glow_strength, a.card_aspect, a.shadow,
                    balance=not a.no_balance, tilt=a.tilt,
                    panel=panel, bleed=a.bleed, ss=max(1, a.supersample),
                    per_col=a.per_column_scale)
    else:
        build(a.shot, (w, h), a.out, a.bg.split(","), a.glow, a.cols, a.radius,
              a.gap, a.stagger, a.margin, a.angle, a.edge, a.seed,
              glow_k=a.glow_strength, shadow_alpha=a.shadow)


if __name__ == "__main__":
    main()
