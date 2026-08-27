#!/usr/bin/env python3
"""Portfolio-style website collages: many pieces, one composed board.

`page_mockup.py` does one thing - a page sliced into tidy columns. That look is
correct for a README strip and wrong for a portfolio card, a case-study hero or
a social post, where the convention is a *composition*: one hero sheet at a
readable scale, secondary sections overlapping it at other scales, small
fragments lifted out of the UI floating as their own cards, some pieces
deliberately cropped by the canvas edge, all sitting on a brand-coloured field.

This script composes that. It ships eleven layout archetypes derived from
studio portfolio work, five background fields and three synthetic card types
(stat, badge, label). Pick a *different* archetype per project - the archetype
is the single biggest reason two boards look unrelated.

    python3 collage.py --layout cascade --out board.png --size 1600x1600 \\
        --pieces "home.png@1.9,about.png@1.2,pricing.png@1.1" \\
        --chips "home.png:0,0.62,1,0.78" \\
        --stats "70%|of athletes face hardship" \\
        --field flat --bg "#6C7BF5" --ink "#FFFFFF" --tilt -3

Every piece keeps its true aspect ratio. Crops are crops; nothing scales on one
axis only. See references/composition-gallery.md for what each archetype looks
like and when to reach for it.
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFilter

from page_mockup import (_face, gradient, grain, hexc, rounded, trim_blank)

# Full-page captures at DPR 3, and framed devices rendered at 3x supersample,
# both run past Pillow's decompression-bomb guard. These are our own files, not
# untrusted input.
Image.MAX_IMAGE_PIXELS = None


# --------------------------------------------------------------------------
# layout archetypes
#
# Each entry is a list of slots, in the order pieces are consumed. Units are
# fractions of the *canvas*: x/y are the top-left corner, w is the piece width.
# x < 0 or x + w > 1 is intentional - a piece cropped by the edge is what makes
# a board read as a composition instead of a contact sheet.
#
#   rot    in-plane rotation, degrees. Never perspective skew.
#   z      paint order; higher lands on top.
#   sh     shadow weight, 0-1, scaled by --shadow.
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# A 12-column grid. Slots are placed in grid units, never in hand-picked
# decimals - that is the whole difference between a composition and a pile.
#
#   c   start column (may be negative: the piece bleeds off the left edge)
#   r   start row, 0-7 (may be negative: bleeds off the top)
#   cs  column span - the piece's width
#   z   paint order; sh shadow weight; rot in-plane rotation only
#
# Heights come from each capture's own aspect, so a slot fixes the top and left
# edge. Every left edge in a board therefore lands on a column line and every
# top edge on a row line, which is what makes the spacing read as deliberate.
# --------------------------------------------------------------------------
COLS, ROWS = 12, 8


def metrics(W, H, margin=0.045, gutter=0.018):
    m, g = W * margin, W * gutter
    return (m, g, (W - 2 * m - (COLS - 1) * g) / COLS,
            (H - 2 * m - (ROWS - 1) * g) / ROWS)


def slot_box(slot, im, W, H):
    """Place one slot, sizing it by *visual weight* rather than a fixed span.

    A fixed span is why a set comes out with some pieces huge and some tiny for
    no reason: the same 4 columns makes a wide, short strip look small and a
    tall full-page sheet look enormous, because width alone says nothing about
    how much of the board a piece covers.

    `wt` is the share of the canvas a piece should occupy. Width follows from
    that and the capture's own aspect - so a long landing page comes out narrow
    and tall, a wide section comes out short and wide, and both carry the same
    weight. The result snaps back to whole columns so the grid still holds.
    """
    if slot.get("page"):               # a whole page, sized against the canvas
        return dict(x=slot["x"], y=slot["y"], w=slot["dw"], page=True,
                    rot=slot.get("rot", 0), z=slot.get("z", 2),
                    sh=slot.get("sh", 1.0))
    if slot.get("dev"):                # device: an explicit size on the canvas
        return dict(x=slot["x"], y=slot["y"], w=slot["dw"], dev=slot["dev"],
                    rot=slot.get("rot", 0), z=slot.get("z", 2),
                    sh=slot.get("sh", 1.0))
    if "rw" in slot:                   # a quilt region: the piece fills it
        return dict(x=slot["rx"], y=slot["ry"], w=slot["rw"],
                    rh=slot["rh"], cover=True, rot=slot.get("rot", 0),
                    z=slot.get("z", 2), sh=slot.get("sh", 1.0))
    if "x" in slot:                    # measured: anchor given, width derived
        aspect = im.height / im.width
        w = math.sqrt(slot["wt"] * W * H / max(aspect, 0.10)) / W
        return dict(x=slot["x"], y=slot["y"], w=min(w, 1.15),
                    rot=slot.get("rot", 0), z=slot.get("z", 2),
                    sh=slot.get("sh", 1.0))
    m, g, cw, rh = metrics(W, H)
    aspect = im.height / im.width
    want = math.sqrt(slot.get("wt", 0.14) * W * H / max(aspect, 0.08))
    span = max(2, min(slot["cs"], int(round((want + g) / (cw + g)))))
    w = span * cw + (span - 1) * g
    return dict(x=(m + slot["c"] * (cw + g)) / W,
                y=(m + slot["r"] * (rh + g)) / H, w=w / W,
                rot=slot.get("rot", 0), z=slot.get("z", 2),
                sh=slot.get("sh", 1.0))


LAYOUTS = {
    # Hero left, secondaries stepping down and right, heavy overlap.
    "cascade": [
        dict(c=-1, r=0, cs=7, wt=0.3, z=2, sh=1.0),
        dict(c=6, r=-1, cs=6, wt=0.2, z=3, sh=0.9),
        dict(c=7, r=3, cs=5, wt=0.1, z=4, sh=0.8),
        dict(c=1, r=5, cs=6, wt=0.14, z=5, sh=0.8),
        dict(c=7, r=6, cs=6, wt=0.08, z=6, sh=0.7),
    ],
    # Varied scale, several pieces leaving the frame.
    "scatter": [
        dict(c=0, r=0, cs=7, wt=0.26, z=2, sh=1.0),
        dict(c=7, r=1, cs=6, wt=0.18, z=4, sh=0.9),
        dict(c=-2, r=4, cs=5, wt=0.12, z=3, sh=0.8),
        dict(c=4, r=5, cs=5, wt=0.12, z=5, sh=0.9),
        dict(c=9, r=5, cs=5, wt=0.09, z=6, sh=0.7),
        dict(c=2, r=7, cs=4, wt=0.06, z=7, sh=0.6),
    ],
    # Sheets stacked with a constant step, whole board rotated.
    "stack-tilt": [
        dict(c=0, r=1, cs=8, wt=0.32, z=2, sh=1.0),
        dict(c=5, r=0, cs=6, wt=0.2, z=3, sh=0.9),
        dict(c=4, r=4, cs=7, wt=0.22, z=4, sh=0.9),
        dict(c=-1, r=5, cs=5, wt=0.1, z=5, sh=0.8),
    ],
    # Two large sheets, offset by one row, one clipped at the top.
    "diptych": [
        dict(c=0, r=1, cs=6, wt=0.3, z=3, sh=1.0),
        dict(c=6, r=-1, cs=6, wt=0.26, z=2, sh=0.9),
        dict(c=3, r=6, cs=6, wt=0.14, z=4, sh=0.8),
    ],
    # One near-1:1 sheet with small fragments at the margins.
    "spotlight": [
        dict(c=1, r=0, cs=10, wt=0.4, z=2, sh=1.0),
        dict(c=0, r=5, cs=5, wt=0.12, z=4, sh=0.9),
        dict(c=7, r=6, cs=5, wt=0.1, z=5, sh=0.8),
    ],
    # Equal-weight cards in a grid with two oversized anchors.
    "mosaic": [
        dict(c=0, r=0, cs=5, wt=0.16, z=2, sh=0.9),
        dict(c=6, r=0, cs=6, wt=0.16, z=2, sh=0.9),
        dict(c=0, r=3, cs=6, wt=0.22, z=3, sh=1.0),
        dict(c=7, r=4, cs=5, wt=0.12, z=3, sh=0.8),
        dict(c=2, r=6, cs=5, wt=0.14, z=4, sh=0.8),
        dict(c=8, r=6, cs=4, wt=0.08, z=4, sh=0.7),
    ],
    # A horizontal run of sections, both ends cropped. Wide formats only.
    "ribbon": [
        dict(c=-1, r=1, cs=3, wt=0.1, z=2, sh=0.8),
        dict(c=2, r=0, cs=3, wt=0.1, z=3, sh=0.8),
        dict(c=5, r=1, cs=3, wt=0.1, z=2, sh=0.8),
        dict(c=8, r=0, cs=3, wt=0.1, z=3, sh=0.8),
        dict(c=11, r=1, cs=3, wt=0.1, z=2, sh=0.8),
    ],
    # Upright hero centre, smaller pieces around it.
    "orbit": [
        dict(c=3, r=1, cs=7, wt=0.3, z=3, sh=1.0),
        dict(c=-1, r=2, cs=4, wt=0.1, z=2, sh=0.8),
        dict(c=9, r=2, cs=4, wt=0.1, z=2, sh=0.8),
        dict(c=1, r=6, cs=4, wt=0.12, z=4, sh=0.8),
        dict(c=7, r=6, cs=4, wt=0.12, z=4, sh=0.8),
    ],
    # Sheets fanned at increasing rotation from a shared origin.
    "fan": [
        dict(c=0, r=1, cs=7, rot=-6, wt=0.24, z=2, sh=0.9),
        dict(c=3, r=0, cs=7, rot=-2, wt=0.24, z=3, sh=0.9),
        dict(c=6, r=0, cs=7, rot=2, wt=0.28, z=4, sh=1.0),
        dict(c=1, r=5, cs=5, rot=-4, wt=0.12, z=5, sh=0.8),
    ],
    # Landscape hero behind a row of portrait screens, evenly spanned.
    "handset-row": [
        dict(c=0, r=0, cs=8, wt=0.28, z=2, sh=0.9),
        dict(c=0, r=4, cs=3, wt=0.07, z=4, sh=1.0),
        dict(c=3, r=4, cs=3, wt=0.07, z=4, sh=1.0),
        dict(c=6, r=4, cs=3, wt=0.07, z=4, sh=1.0),
        dict(c=9, r=4, cs=3, wt=0.07, z=4, sh=1.0),
    ],
    # Copy column left, pieces stacked right - the type block owns columns 0-3.
    "editorial": [
        dict(c=3, r=0, cs=9, wt=0.32, z=2, sh=1.0),
        dict(c=5, r=4, cs=6, wt=0.17, z=3, sh=0.9),
        dict(c=0, r=2, cs=4, wt=0.11, z=4, sh=0.9),
        dict(c=1, r=6, cs=5, wt=0.12, z=5, sh=0.8),
        dict(c=9, r=6, cs=4, wt=0.09, z=6, sh=0.8),
    ],
    # One dominant sheet bleeding off two edges, with small lifted details
    # against open field. The scale gap is the point.
    "hero-detail": [
        dict(c=4, r=-1, cs=10, wt=0.42, z=2, sh=1.0),
        dict(c=0, r=5, cs=4, wt=0.11, z=5, sh=1.0),
        dict(c=4, r=6, cs=4, wt=0.09, z=6, sh=0.9),
        dict(c=8, r=7, cs=4, wt=0.1, z=4, sh=0.8),
    ],
    # Packed: every edge is crossed, no bare field left over.
    "dense": [
        dict(c=-1, r=-1, cs=8, wt=0.3, z=2, sh=1.0),
        dict(c=6, r=2, cs=7, wt=0.24, z=3, sh=0.9),
        dict(c=1, r=4, cs=5, wt=0.16, z=5, sh=1.0),
        dict(c=5, r=5, cs=4, wt=0.1, z=6, sh=0.9),
        dict(c=9, r=6, cs=4, wt=0.11, z=4, sh=0.8),
        dict(c=-1, r=7, cs=3, wt=0.06, z=7, sh=0.8),
    ],
    # Type owns the top rows, one sheet runs off the bottom edge.
    "poster": [
        dict(c=2, r=2, cs=10, wt=0.30, z=2, sh=1.0),
        dict(c=-1, r=4, cs=4, wt=0.11, z=5, sh=1.0),
        dict(c=8, r=0, cs=5, wt=0.13, z=4, sh=0.9),
        dict(c=0, r=0, cs=4, wt=0.10, z=3, sh=0.9),
        dict(c=5, r=6, cs=5, wt=0.12, z=6, sh=0.8),
    ],
    # A tall portrait piece against a wide one - shape contrast.
    "portrait-pair": [
        dict(c=0, r=0, cs=4, wt=0.16, z=4, sh=1.0),
        dict(c=4, r=-1, cs=9, wt=0.34, z=2, sh=0.9),
        dict(c=5, r=5, cs=5, wt=0.13, z=5, sh=0.9),
        dict(c=9, r=6, cs=4, wt=0.09, z=6, sh=0.8),
    ],
}


# --------------------------------------------------------------------------
# Layouts measured off real portfolio boards.
#
# Each entry is the sheet geometry extracted from a published board by
# thresholding field-vs-sheet and recovering the rectangles (see
# references/composition-gallery.md). x, y and w are fractions of the canvas,
# taken directly from the source - not drawn by hand and not derived from a
# weight. Pieces are consumed largest-first, so the biggest capture lands in
# the biggest measured slot.
#
# Common structure across all of them: one dominant sheet at 0.45-0.66 wide,
# two or three mid sheets at 0.25-0.45, one or two accents at 0.12-0.23,
# several sharing an x or y edge, and one or two running off the canvas.
# --------------------------------------------------------------------------
MEASURED = {
    # Silicon Hills - two aligned columns, one raised above them
    "columns": [
        dict(x=0.04, y=0.31, w=0.45, wt=0.122, z=3, sh=1.0),
        dict(x=0.50, y=0.31, w=0.43, wt=0.095, z=2, sh=0.9),
        dict(x=0.52, y=0.02, w=0.41, wt=0.062, z=4, sh=0.9),
        dict(x=0.00, y=0.06, w=0.22, wt=0.05, z=2, sh=0.8),
    ],
    # Fokus - a left column of two, a wide sheet bleeding along the bottom
    "left-stack": [
        dict(x=0.04, y=0.39, w=0.64, wt=0.192, z=3, sh=1.0),
        dict(x=0.03, y=0.78, w=0.94, wt=0.103, z=2, sh=0.9),
        dict(x=0.04, y=0.04, w=0.64, wt=0.077, z=4, sh=0.9),
        dict(x=0.75, y=0.15, w=0.20, wt=0.028, z=5, sh=0.8),
    ],
    # Loomia - a centred stack with a small accent off the left edge
    "centre-stack": [
        dict(x=0.23, y=0.27, w=0.63, wt=0.151, z=3, sh=1.0),
        dict(x=0.19, y=0.54, w=0.62, wt=0.143, z=4, sh=0.9),
        dict(x=0.23, y=0.16, w=0.66, wt=0.073, z=2, sh=0.9),
        dict(x=0.33, y=0.00, w=0.32, wt=0.038, z=5, sh=0.8),
        dict(x=-0.03, y=0.54, w=0.19, wt=0.029, z=2, sh=0.8),
    ],
    # Homebuilder AI - a wide band with pieces above and below it
    "banded": [
        dict(x=0.61, y=0.63, w=0.38, wt=0.137, z=4, sh=1.0),
        dict(x=0.05, y=0.50, w=0.93, wt=0.121, z=2, sh=0.9),
        dict(x=0.11, y=0.66, w=0.45, wt=0.122, z=5, sh=0.9),
        dict(x=0.24, y=0.14, w=0.26, wt=0.057, z=3, sh=0.8),
        dict(x=0.50, y=0.11, w=0.25, wt=0.038, z=3, sh=0.8),
    ],
    # Flo Corp - a tall sheet off the left edge, two accents in the corners
    "tall-left": [
        dict(x=0.51, y=0.51, w=0.49, wt=0.098, z=3, sh=1.0),
        dict(x=-0.02, y=0.48, w=0.25, wt=0.085, z=4, sh=0.9),
        dict(x=0.02, y=0.03, w=0.50, wt=0.07, z=2, sh=0.9),
        dict(x=0.84, y=0.79, w=0.16, wt=0.018, z=5, sh=0.8),
        dict(x=0.15, y=0.88, w=0.15, wt=0.014, z=5, sh=0.8),
    ],
    # Lucky Voice - top-left anchor, pieces stepping down both sides
    "step-down": [
        dict(x=-0.01, y=0.00, w=0.66, wt=0.099, z=2, sh=1.0),
        dict(x=0.00, y=0.59, w=0.32, wt=0.074, z=4, sh=0.9),
        dict(x=0.04, y=0.82, w=0.52, wt=0.057, z=5, sh=0.9),
        dict(x=0.70, y=0.59, w=0.29, wt=0.055, z=3, sh=0.8),
        dict(x=0.76, y=0.00, w=0.23, wt=0.03, z=3, sh=0.8),
    ],
    # Market Fair - weight in the lower right, one accent top
    "lower-right": [
        dict(x=0.59, y=0.79, w=0.41, wt=0.086, z=4, sh=1.0),
        dict(x=-0.02, y=0.71, w=0.54, wt=0.047, z=3, sh=0.9),
        dict(x=0.55, y=0.68, w=0.45, wt=0.041, z=2, sh=0.9),
        dict(x=0.61, y=0.03, w=0.22, wt=0.022, z=5, sh=0.8),
        dict(x=0.04, y=0.10, w=0.48, wt=0.06, z=2, sh=0.9),
    ],
    # Adina - full-bleed horizontal bands, one accent off the right edge
    "bleed-bands": [
        dict(x=-0.02, y=0.38, w=1.04, wt=0.27, z=3, sh=1.0),
        dict(x=-0.02, y=0.66, w=1.04, wt=0.12, z=4, sh=0.9),
        dict(x=0.40, y=0.80, w=0.60, wt=0.09, z=5, sh=0.9),
        dict(x=0.45, y=0.00, w=0.55, wt=0.072, z=2, sh=0.9),
        dict(x=0.86, y=0.13, w=0.14, wt=0.02, z=6, sh=0.8),
    ],
    # iBridge - a tall right anchor over stacked full-width bands
    "right-anchor": [
        dict(x=0.51, y=0.00, w=0.46, wt=0.129, z=4, sh=1.0),
        dict(x=-0.01, y=0.65, w=1.02, wt=0.11, z=3, sh=0.9),
        dict(x=0.03, y=0.45, w=0.92, wt=0.101, z=2, sh=0.9),
        dict(x=0.03, y=0.07, w=0.47, wt=0.094, z=3, sh=0.9),
        dict(x=0.62, y=0.85, w=0.36, wt=0.05, z=5, sh=0.8),
    ],
    # Prova Health - near-total coverage, wide bands, minimal field
    "full-bleed": [
        dict(x=-0.02, y=0.26, w=1.04, wt=0.34, z=3, sh=1.0),
        dict(x=-0.02, y=0.00, w=1.04, wt=0.23, z=2, sh=0.9),
        dict(x=0.21, y=0.60, w=0.79, wt=0.166, z=4, sh=0.9),
        dict(x=-0.02, y=0.81, w=1.04, wt=0.15, z=5, sh=0.9),
        dict(x=-0.02, y=0.60, w=0.22, wt=0.042, z=4, sh=0.8),
    ],
}
# Consume the slots widest-first. Pieces arrive in importance order - the beat's
# own section, then the hero, then lifted components - so without this a small
# lifted card can land in the widest slot and a paragraph gets blown up until it
# reads as a caption laid over the board.
for _name, _slots in MEASURED.items():
    _slots.sort(key=lambda d: -d["wt"])
LAYOUTS.update(MEASURED)


def quilt(n, W, H, seed=0, bleed=0.03, gutter=0.012):
    """Subdivide the canvas into n regions - the structure behind every
    high-coverage reference board.

    Prova Health (98% covered), Rest+Wild (93%), Travis (91%), Teif (90%) and
    Adina (88%) are not scattered compositions. The canvas is divided up and
    each region carries a sheet, with the field showing only as thin lines
    between them and a margin around the outside. Coverage comes out of the
    construction instead of being chased afterwards by scaling pieces up, which
    is what kept collapsing: growing sheets anchored on top of each other just
    piles them deeper without covering more canvas.

    Regions on an outer edge bleed slightly past it, so the board reads as a
    crop out of something larger rather than as a diagram floating in a box.
    """
    rnd = random.Random(seed)
    regions = [(0.0, 0.0, 1.0, 1.0)]
    while len(regions) < n:
        i = max(range(len(regions)), key=lambda k: regions[k][2] * regions[k][3])
        x, y, w, h = regions.pop(i)
        # split the long way, near the middle but never exactly on it
        f = rnd.uniform(0.40, 0.60)
        if w * W >= h * H:
            regions += [(x, y, w * f, h), (x + w * f, y, w * (1 - f), h)]
        else:
            regions += [(x, y, w, h * f), (x, y + h * f, w, h * (1 - f))]
    regions.sort(key=lambda r: -r[2] * r[3])
    slots = []
    for i, (x, y, w, h) in enumerate(regions):
        l = x - (bleed if x <= 0.001 else gutter / 2)
        t = y - (bleed if y <= 0.001 else gutter / 2)
        r = x + w + (bleed if x + w >= 0.999 else gutter / 2)
        b = y + h + (bleed if y + h >= 0.999 else gutter / 2)
        slots.append(dict(rx=l, ry=t, rw=r - l, rh=b - t, z=2 + i,
                          sh=1.0 if i == 0 else 0.85))
    return slots



# --------------------------------------------------------------------------
# Device-mockup boards. A separate family from the collages: the site sits in
# a laptop or a browser window on a flat brand field, cropped by the canvas,
# with a floating stat card or badge. Reach for these to break up a set - a
# portfolio of nothing but collages reads as one template however varied the
# compositions are.
# --------------------------------------------------------------------------
DEVICES = {
    # the whole laptop, centred, its base running off the bottom edge
    "device-hero": [dict(x=0.115, y=0.13, dw=0.77, cs=12, dev="macbook",
                         z=2, sh=1.0)],
    # pushed off the right and bottom, so the screen reads near full size
    "device-crop": [dict(x=0.10, y=0.15, dw=1.30, cs=12, dev="macbook",
                         z=2, sh=1.0)],
    # a laptop with a second screen behind it in a browser frame
    "device-stack": [dict(x=0.04, y=0.30, dw=0.62, cs=12, dev="macbook",
                          z=3, sh=1.0),
                     dict(x=0.44, y=0.06, dw=0.54, cs=12, dev="browser",
                          z=2, sh=0.85)],
    # Several portal screens at once, each in its own browser frame. A
    # signed-in app is mostly viewport-shaped screens, and this is the shape
    # that shows a lot of the actual product without cropping any of it.
    # A strict 2x2. Equal outer margins on both sides, one gutter, both rows
    # on the same two x positions. Every frame the same size.
    "device-grid": [
        dict(x=0.045, y=0.050, dw=0.44, cs=12, dev="browser", z=2, sh=0.95),
        dict(x=0.515, y=0.050, dw=0.44, cs=12, dev="browser", z=2, sh=0.95),
        dict(x=0.045, y=0.520, dw=0.44, cs=12, dev="browser", z=3, sh=0.95),
        dict(x=0.515, y=0.520, dw=0.44, cs=12, dev="browser", z=3, sh=0.95),
    ],
    # A cascade with a CONSTANT step - each frame moves the same distance right
    # and the same distance down as the one before it. That constant is what
    # gives a board direction; three frames at hand-picked offsets read as a
    # pile no matter how good the screens are.
    "device-trio": [
        dict(x=0.030, y=0.060, dw=0.52, cs=12, dev="browser", z=2, sh=0.85),
        dict(x=0.200, y=0.200, dw=0.52, cs=12, dev="browser", z=3, sh=0.95),
        dict(x=0.370, y=0.340, dw=0.52, cs=12, dev="browser", z=4, sh=1.0),
    ],
    # The same constant-step idea with two frames, larger.
    "device-duo": [
        dict(x=0.045, y=0.070, dw=0.60, cs=12, dev="browser", z=2, sh=0.9),
        dict(x=0.310, y=0.310, dw=0.60, cs=12, dev="browser", z=3, sh=1.0),
    ],
}
LAYOUTS.update(DEVICES)


# --------------------------------------------------------------------------
# Whole-page boards. Complete, uncropped page captures laid side by side and
# tilted together in perspective - the simplest and most presentable of all the
# families, because nothing is cropped and so nothing can be cropped badly.
# Pieces are full pages (no `~section`, no `!block`).
# --------------------------------------------------------------------------
PAGES = {
    "pages3": [dict(x=0.02, y=0.03, dw=0.36, page=True, z=4, sh=1.0),
               dict(x=0.37, y=0.06, dw=0.36, page=True, z=3, sh=0.9),
               dict(x=0.72, y=0.09, dw=0.36, page=True, z=2, sh=0.8)],
    "pages2": [dict(x=0.04, y=0.04, dw=0.46, page=True, z=3, sh=1.0),
               dict(x=0.52, y=0.10, dw=0.46, page=True, z=2, sh=0.9)],
    "pages4": [dict(x=-0.02, y=0.02, dw=0.30, page=True, z=5, sh=1.0),
               dict(x=0.27, y=0.05, dw=0.30, page=True, z=4, sh=0.9),
               dict(x=0.55, y=0.08, dw=0.30, page=True, z=3, sh=0.85),
               dict(x=0.82, y=0.11, dw=0.30, page=True, z=2, sh=0.8)],
}
LAYOUTS.update(PAGES)

# Slots for the synthetic cards. Chips are UI fragments, stats are numbers,
# badges are round icon tokens. They sit above every screen piece.
CHIP_SLOTS = [
    dict(x=0.66, y=0.04, w=0.30), dict(x=0.00, y=0.38, w=0.26),
    dict(x=0.70, y=0.52, w=0.28), dict(x=0.22, y=0.88, w=0.26),
]
# Stat cards go in a named corner - `--stat-pos`. A stat dropped in the middle
# of the board lands on top of the UI it is meant to caption.
STAT_POS = {
    "tl": dict(x=0.035, y=0.05, w=0.25), "tr": dict(x=0.715, y=0.05, w=0.25),
    "bl": dict(x=0.035, y=0.68, w=0.25), "br": dict(x=0.715, y=0.68, w=0.25),
    "bc": dict(x=0.375, y=0.72, w=0.25), "tc": dict(x=0.375, y=0.04, w=0.25),
}
STAT_SLOTS = [STAT_POS["br"], STAT_POS["tl"], STAT_POS["bl"]]
BADGE_SLOTS = [
    dict(x=0.022, y=0.035, w=0.075), dict(x=0.903, y=0.035, w=0.075),
    dict(x=0.022, y=0.885, w=0.075), dict(x=0.903, y=0.885, w=0.075),
]


# --------------------------------------------------------------------------
# background fields
# --------------------------------------------------------------------------
def field(kind, size, colours, angle, seed, grain_amt):
    """The ground the board sits on. Carries more character than anything else."""
    W, H = size
    c = [hexc(x) for x in colours]
    if kind == "flat":
        canvas = Image.new("RGBA", size, c[0] + (255,))
    elif kind == "gradient":
        canvas = gradient(size, c[0], c[-1], angle).convert("RGBA")
    elif kind == "split":
        # Two blocks on a diagonal - a colour-field poster, not a gradient.
        canvas = Image.new("RGBA", size, c[0] + (255,))
        d = ImageDraw.Draw(canvas)
        a = math.radians(angle)
        far = (W + H) * 2
        cx, cy = W * 0.5, H * 0.55
        dx, dy = math.cos(a) * far, math.sin(a) * far
        nx, ny = -dy, dx
        d.polygon([(cx + dx + nx, cy + dy + ny), (cx - dx + nx, cy - dy + ny),
                   (cx - dx, cy - dy), (cx + dx, cy + dy)],
                  fill=c[-1] + (255,))
    elif kind == "shapes":
        # Oversized rotated parallelograms in a near-tone. Reads as brand
        # geometry; stays quiet enough to sit behind UI.
        canvas = Image.new("RGBA", size, c[0] + (255,))
        over = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        rnd = random.Random(seed)
        tone = c[-1] + (70,)
        for i in range(3):
            bx = W * (-0.2 + 0.55 * i) + rnd.uniform(-W * 0.05, W * 0.05)
            sk = W * 0.22
            d.polygon([(bx, -H * 0.1), (bx + W * 0.28, -H * 0.1),
                       (bx + W * 0.28 - sk, H * 1.1), (bx - sk, H * 1.1)],
                      fill=tone)
        canvas.alpha_composite(over)
    elif kind == "vignette":
        canvas = gradient(size, c[0], c[-1], angle).convert("RGBA")
        over = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        for i in range(28):
            k = i / 28
            d.ellipse([-W * 0.3 + W * 0.65 * k, -H * 0.3 + H * 0.65 * k,
                       W * 1.3 - W * 0.65 * k, H * 1.3 - H * 0.65 * k],
                      outline=(0, 0, 0, 8), width=int(W * 0.02) + 1)
        canvas.alpha_composite(over.filter(ImageFilter.GaussianBlur(W * 0.02)))
    else:
        raise SystemExit(f"unknown --field {kind}")
    if grain_amt:
        grain(canvas, amount=grain_amt, seed=seed)
    return canvas


# --------------------------------------------------------------------------
# pieces
# --------------------------------------------------------------------------
_TEXT_CACHE = {}
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".textcache")


def text_boxes(im):
    """Where the words are, as normalized boxes, via Apple's Vision OCR.

    Everything else in this file reasons about pixels; this is the only thing
    that knows a headline is a headline. Without it the compositor crops blind,
    and a cut line through the middle of a word is the clearest possible sign
    that a board was generated rather than composed.

    Results are cached on disk by image content, because the same section is
    reused across several boards and OCR costs about two seconds a call.
    """
    import hashlib, subprocess, tempfile
    sm = im.convert("RGB")
    if sm.width > 900:
        sm = sm.resize((900, max(1, round(900 * sm.height / sm.width))),
                       Image.BILINEAR)
    key = hashlib.sha1(sm.tobytes()).hexdigest()[:16]
    if key in _TEXT_CACHE:
        return _TEXT_CACHE[key]
    os.makedirs(_CACHE_DIR, exist_ok=True)
    cache = os.path.join(_CACHE_DIR, key + ".txt")
    if not os.path.exists(cache):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "textmap.swift")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            sm.save(tf.name)
            try:
                out = subprocess.run(["swift", script, tf.name],
                                     capture_output=True, text=True,
                                     timeout=90).stdout
            except Exception:
                out = ""                     # no OCR available: fail open
            finally:
                os.unlink(tf.name)
        open(cache, "w").write(out)
    boxes = []
    for ln in open(cache):
        f = ln.split()
        if len(f) >= 4:
            boxes.append(tuple(float(v) for v in f[:4]))
    _TEXT_CACHE[key] = boxes
    return boxes


def safe_cuts(im, axis, margin=0.004):
    """Fractions along `axis` ('x' or 'y') where a cut misses every word.

    A crop has to land somewhere; this says where it can land without slicing
    through type. Returns the free intervals, so the caller can snap an
    unavoidable crop to the nearest one instead of cutting wherever it likes.
    """
    boxes = text_boxes(im)
    if not boxes:
        return [(0.0, 1.0)]
    spans = sorted((b[1] - margin, b[3] + margin) if axis == "y"
                   else (b[0] - margin, b[2] + margin) for b in boxes)
    free, cur = [], 0.0
    for a, b in spans:
        if a > cur:
            free.append((cur, a))
        cur = max(cur, b)
    if cur < 1.0:
        free.append((cur, 1.0))
    return free


def snap_cut(im, axis, frac):
    """Move a cut to the nearest position that misses the text."""
    for a, b in safe_cuts(im, axis):
        if a <= frac <= b:
            return frac
    best, bd = frac, 9.0
    for a, b in safe_cuts(im, axis):
        for cand in (a, b):
            if abs(cand - frac) < bd:
                best, bd = cand, abs(cand - frac)
    return min(max(best, 0.0), 1.0)


def quiet_rows(im, tol=4):
    """Rows where the page is a flat band of one colour - the seams between
    sections. Cropping anywhere else cuts through content, which is what makes
    a board unreadable: half a diagram, a headline sliced through the x-height.
    """
    g = im.convert("L").resize((160, im.height // 8), Image.BILINEAR)
    rows = []
    px = g.load()
    for y in range(g.height):
        lo = hi = px[0, y]
        for x in range(1, 160):
            v = px[x, y]
            lo, hi = min(lo, v), max(hi, v)
        if hi - lo <= tol:
            rows.append(y * 8)
    return rows


def sections(im, min_frac=0.035):
    """Split a full-page capture into its real sections at the seams.

    Band crops at guessed percentages cut through content - half a diagram, a
    headline sliced through the x-height - and a board made of those explains
    nothing. Whole sections are self-contained: a heading, its copy and its
    picture, the way a visitor actually sees them.
    """
    rows = quiet_rows(im)
    if not rows:
        return [(0, im.height)]
    # Collapse runs of adjacent quiet rows to a single seam at their centre.
    seams, run = [], [rows[0]]
    for r in rows[1:]:
        if r - run[-1] <= 16:
            run.append(r)
        else:
            seams.append(sum(run) // len(run))
            run = [r]
    seams.append(sum(run) // len(run))
    # A section has to be tall enough to be worth showing - roughly half a
    # viewport - or it comes back as a sliver holding two words of a headline.
    floor = max(im.height * min_frac, im.width * 0.45)
    cuts, last = [0], 0
    for y in seams:
        if y - last >= floor:
            cuts.append(y)
            last = y
    cuts.append(im.height)
    segs = [(a, b) for a, b in zip(cuts, cuts[1:])]
    if len(segs) > 1 and segs[-1][1] - segs[-1][0] < floor * 0.6:
        segs[-2] = (segs[-2][0], segs[-1][1])       # fold a runt tail back in
        segs.pop()
    # Drop anything that is essentially blank - a capture's empty stretches are
    # not sections, and a blank sheet on a board looks like a broken export.
    keep = []
    for a, b in segs:
        g = im.crop((0, a, im.width, b)).convert("L").resize((80, 40))
        lo, hi = g.getextrema()
        if hi - lo > 24:
            keep.append((a, b))
    return keep or segs


def find_blocks(im, want=6):
    """Bounding boxes of the distinct UI blocks inside a capture.

    The move that makes a portfolio board look designed rather than exported is
    lifting a *single component* out of the page - one pricing card, one stat,
    one form, one row of the table - and floating it at its own scale with its
    own shadow. Doing that by hand means guessing crop rectangles; this finds
    them.

    Method: knock the page background out to a mask, close small gaps so a card
    and its own contents read as one region, then take connected components and
    keep the ones shaped like a card.
    """
    W = 240
    sm = im.convert("RGB").resize((W, max(1, int(W * im.height / im.width))))
    px = sm.load()
    bg = px[2, 2]
    w, h = sm.size

    def near(c, d, tol=14):
        return all(abs(a - b) <= tol for a, b in zip(c, d))

    mask = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            mask[y][x] = 0 if near(px[x, y], bg) else 1
    # Close horizontal gaps: a card's inner whitespace is the page colour too,
    # so without this every card shatters into its own text lines.
    for y in range(h):
        run = 0
        for x in range(w):
            if mask[y][x]:
                if run and run < 26:
                    for k in range(x - run, x):
                        mask[y][k] = 1
                run = 0
            else:
                run += 1

    seen = [[False] * w for _ in range(h)]
    boxes = []
    for y0 in range(h):
        for x0 in range(w):
            if not mask[y0][x0] or seen[y0][x0]:
                continue
            stack, x1, x2, y1, y2, n = [(x0, y0)], x0, x0, y0, y0, 0
            seen[y0][x0] = True
            while stack:
                x, y = stack.pop()
                n += 1
                x1, x2 = min(x1, x), max(x2, x)
                y1, y2 = min(y1, y), max(y2, y)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                               (2, 0), (0, 2), (-2, 0), (0, -2)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] \
                            and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            bw, bh = x2 - x1 + 1, y2 - y1 + 1
            if bw < w * 0.10 or bh < 10 or n < bw * bh * 0.35:
                continue
            if bw / bh > 4.5 or bh / bw > 6:         # strips and rules
                continue
            boxes.append((n, x1, y1, x2, y2))

    boxes.sort(reverse=True)
    k = im.width / w
    out = []
    for _, x1, y1, x2, y2 in boxes[:want * 4]:
        # Reject near-empty regions. A whitespace-heavy page will happily hand
        # back a big blank rectangle, and a blank card on a board reads as a
        # failed export rather than a lifted detail.
        probe = im.crop((int(x1 * k), int(y1 * k),
                         int((x2 + 1) * k), int((y2 + 1) * k)))
        pg = probe.convert("L").resize((60, 40))
        lo, hi = pg.getextrema()
        ink = sum(1 for v in pg.getdata() if abs(v - hi) > 18) / 2400
        if hi - lo < 30 or ink < 0.06:
            continue
        pad = 3
        b = (max(0, int((x1 - pad) * k)), max(0, int((y1 - pad) * k)),
             min(im.width, int((x2 + 1 + pad) * k)),
             min(im.height, int((y2 + 1 + pad) * k)))
        if b[2] - b[0] > im.width * 0.06 and b[3] - b[1] > im.width * 0.03:
            out.append(b)
    return out[:want]


def snap(im, y, rows, window):
    """Move a crop edge to the nearest seam within `window` pixels."""
    if not rows:
        return y
    near = min(rows, key=lambda r: abs(r - y))
    return near if abs(near - y) <= window else y


def split_specs(s):
    """Piece lists separate on `;`. Commas are accepted too, but only when no
    spec uses a `#l,t,r,b` crop - those commas belong to the crop box."""
    if not s:
        return []
    sep = ";" if (";" in s or "#" in s) else ","
    return [p.strip() for p in s.split(sep) if p.strip()]


def load_piece(spec, trim=True, snap_sections=False):
    """`path`, `path@aspect` (crop from top to w:h = 1:aspect), or
    `path#l,t,r,b` (crop by fractions of the capture)."""
    crop = None
    aspect = None
    sect = None
    path = spec
    blockn = None
    if "!" in path:
        path, blockn = path.split("!", 1)
        blockn = int(blockn)
    rng = None
    if "~" in path:
        path, sect = path.split("~", 1)
        if "+" in sect:
            # `page.png~3+1.9`: start at section 3 and keep adding whole
            # sections until the piece is at least 1.9x as tall as it is wide.
            # A page column has to run off the bottom edge - the references all
            # do - and a fixed section range cannot guarantee that, which is
            # what left a dead band of bare field across the bottom.
            a, target = sect.split("+", 1)
            rng = ("auto", int(a), float(target))
            sect = None
        elif "-" in sect:
            # `page.png~0-2`: sections 0 through 2 as ONE tall piece, cut only
            # at the seams between them. This is how a site with a single
            # content-rich page still yields several page-like pieces - without
            # putting a near-empty sign-in screen on the board to pad it out.
            a, b = sect.split("-", 1)
            rng = (int(a), int(b))
            sect = None
        else:
            sect = int(sect)
    if "#" in path:
        path, box = path.split("#", 1)
        crop = [float(v) for v in box.split(",")]
    if "@" in path:
        path, a = path.split("@", 1)
        aspect = float(a)
    im = Image.open(os.path.expanduser(path)).convert("RGB")
    if trim:
        im = trim_blank(im)
    if rng is not None and rng[0] == "auto":
        segs = sections(im)
        i0 = min(rng[1], len(segs) - 1)
        top = segs[i0][0]
        bot = segs[i0][1]
        j = i0
        while (bot - top) / im.width < rng[2] and j + 1 < len(segs):
            j += 1
            bot = segs[j][1]
        # Ran out of page below: extend upward instead. The last column
        # otherwise stops short of the bottom edge, which is exactly the dead
        # band this whole mechanism exists to remove.
        k = i0
        while (bot - top) / im.width < rng[2] and k - 1 >= 0:
            k -= 1
            top = segs[k][0]
        im = im.crop((0, top, im.width, bot))
    elif rng is not None:
        segs = sections(im)
        a = segs[min(rng[0], len(segs) - 1)][0]
        b = segs[min(rng[1], len(segs) - 1)][1]
        im = im.crop((0, a, im.width, b))
    elif sect is not None:
        segs = sections(im)
        a, b = segs[min(sect, len(segs) - 1)]
        im = im.crop((0, a, im.width, b))
    if blockn is not None:
        bs = find_blocks(im, want=blockn + 1)
        if bs:
            im = im.crop(bs[min(blockn, len(bs) - 1)])
    if crop:
        l, t, r, b = crop
        top, bot = int(t * im.height), int(b * im.height)
        if snap_sections:
            rows = quiet_rows(im)
            window = int(im.height * 0.035)
            top, bot = snap(im, top, rows, window), snap(im, bot, rows, window)
        im = im.crop((int(l * im.width), top, int(r * im.width), max(bot, top + 8)))
    if aspect:
        h = min(im.height, int(im.width * aspect))
        im = im.crop((0, 0, im.width, h))
    return im


def stat_card(text, w, th, ss):
    """`1B+|in NIL deals signed since 2021` - a number and its qualifier."""
    big, _, small = text.partition("|")
    pad = int(w * 0.09)
    fb = _face(th["display"], int(w * 0.30), "heavy")
    fs = _face(th["text"], int(w * 0.075), "regular")
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines, line = [], ""
    for word in small.split():
        trial = f"{line} {word}".strip()
        if tmp.textlength(trial, font=fs) > w - pad * 2 and line:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    bh = fb.getbbox(big)[3] - fb.getbbox(big)[1]
    lh = int(w * 0.105)
    h = pad * 2 + bh + (int(w * 0.06) + lh * len(lines) if lines else 0)
    card = Image.new("RGBA", (w, h), hexc(th["card"]) + (255,))
    d = ImageDraw.Draw(card)
    d.text((pad, pad - fb.getbbox(big)[1]), big, font=fb, fill=hexc(th["card_ink"]))
    y = pad + bh + int(w * 0.06)
    for ln in lines:
        d.text((pad, y), ln, font=fs, fill=hexc(th["card_muted"]))
        y += lh
    return rounded(card, int(w * 0.045))


def caption_card(text, w, th):
    """`What it is|One sentence a non-technical reader understands.`

    Not a stat and not a headline lifted off the site - a plain description of
    what the product does, in words someone outside the industry would use.
    """
    title, _, body = text.partition("|")
    pad = int(w * 0.075)
    ft = _face(th["display"], int(w * 0.088), "heavy")
    fb = _face(th["text"], int(w * 0.053), "regular")
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    def wrap(f, t):
        out, line = [], ""
        for word in t.split():
            trial = f"{line} {word}".strip()
            if tmp.textlength(trial, font=f) > w - pad * 2 and line:
                out.append(line)
                line = word
            else:
                line = trial
        if line:
            out.append(line)
        return out

    tl, bl = wrap(ft, title), wrap(fb, body)
    th_, bh_ = int(w * 0.112), int(w * 0.076)
    h = pad * 2 + th_ * len(tl) + (int(w * 0.045) + bh_ * len(bl) if bl else 0)
    card = Image.new("RGBA", (w, h), hexc(th["card"]) + (255,))
    d = ImageDraw.Draw(card)
    y = pad
    for ln in tl:
        d.text((pad, y), ln, font=ft, fill=hexc(th["card_ink"]))
        y += th_
    y += int(w * 0.045)
    for ln in bl:
        d.text((pad, y), ln, font=fb, fill=hexc(th["card_muted"]))
        y += bh_
    return rounded(card, int(w * 0.04))


def label_card(text, w, th):
    """A single line in a pill - a nav item, a tag, a CTA lifted off the page."""
    f = _face(th["text"], int(w * 0.13), "medium")
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    tw = int(tmp.textlength(text, font=f))
    pad = int(w * 0.12)
    cw, ch = tw + pad * 2, int(w * 0.34)
    card = Image.new("RGBA", (cw, ch), hexc(th["accent"]) + (255,))
    ImageDraw.Draw(card).text((cw // 2, ch // 2), text, font=f,
                              fill=hexc(th["accent_ink"]), anchor="mm")
    return rounded(card, ch // 2)


def badge_card(w, th, seed=0):
    """A round accent token with a simple glyph. Punctuation, not information."""
    card = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.ellipse([0, 0, w - 1, w - 1], fill=hexc(th["accent"]) + (255,))
    ink = hexc(th["accent_ink"]) + (255,)
    m, r = int(w * 0.30), int(w * 0.05)
    rnd = random.Random(seed)
    kind = rnd.choice(("doc", "grid", "spark", "arrow"))
    if kind == "doc":
        d.rounded_rectangle([m, m - r, w - m, w - m], r, outline=ink,
                            width=max(2, w // 22))
        for i in range(3):
            yy = m + int(w * (0.10 + 0.09 * i))
            d.line([m + r * 2, yy, w - m - r * 2, yy], fill=ink,
                   width=max(2, w // 26))
    elif kind == "grid":
        s = (w - m * 2 - r) // 2
        for gx in (m, m + s + r):
            for gy in (m, m + s + r):
                d.rounded_rectangle([gx, gy, gx + s, gy + s], r // 2,
                                    outline=ink, width=max(2, w // 24))
    elif kind == "spark":
        cx = w // 2
        d.line([cx, m, cx, w - m], fill=ink, width=max(2, w // 20))
        d.line([m, w // 2, w - m, w // 2], fill=ink, width=max(2, w // 20))
        d.line([m + r, m + r, w - m - r, w - m - r], fill=ink, width=max(2, w // 26))
        d.line([w - m - r, m + r, m + r, w - m - r], fill=ink, width=max(2, w // 26))
    else:
        d.line([m, w // 2, w - m, w // 2], fill=ink, width=max(2, w // 18))
        d.line([w - m - int(w * 0.12), w // 2 - int(w * 0.12), w - m, w // 2],
               fill=ink, width=max(2, w // 18))
        d.line([w - m - int(w * 0.12), w // 2 + int(w * 0.12), w - m, w // 2],
               fill=ink, width=max(2, w // 18))
    return card


# --------------------------------------------------------------------------
# compositing
# --------------------------------------------------------------------------
def shadow(canvas, layer, x, y, alpha, blur, dy):
    if alpha <= 0:
        return
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    a = layer.split()[-1].point(lambda v: min(255, v * alpha // 255))
    body = Image.new("RGBA", layer.size, (0, 0, 0, 255))
    body.putalpha(a)
    sh.alpha_composite(body, (int(x), int(y + dy)))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


PLACED = []


def _persp_coeffs(src, dst):
    """Solve for the 8 perspective coefficients mapping dst -> src."""
    A, B = [], []
    for (sx, sy), (dx, dy) in zip(src, dst):
        A.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy]); B.append(sx)
        A.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy]); B.append(sy)
    # Gaussian elimination - avoids pulling numpy in for an 8x8 solve
    n = 8
    M = [row[:] + [b] for row, b in zip(A, B)]
    for i in range(n):
        piv = max(range(i, n), key=lambda r: abs(M[r][i]))
        M[i], M[piv] = M[piv], M[i]
        if abs(M[i][i]) < 1e-12:
            return None
        for r in range(n):
            if r == i:
                continue
            f = M[r][i] / M[i][i]
            for c in range(i, n + 1):
                M[r][c] -= f * M[i][c]
    return [M[i][n] / M[i][i] for i in range(n)]


def perspective(im, tilt=14.0, yaw=10.0, squeeze=0.10):
    """Lay the sheet back in space, the way a designer rotates a mockup group.

    Every one of these boards - and the ones people knock together in Canva in
    ten minutes - is built from *whole, uncropped* page screenshots tilted in
    3D on a plain field. It is the entire effect, and it is why those read as
    presentable while a fragment collage does not: nothing is cut, so nothing
    can be cut badly.

    Note this deliberately contradicts the store-tile rule of "in-plane rotation
    only, never perspective". That rule protects UI legibility on a phone tile,
    where the screenshot IS the product demo. On a portfolio board the page
    reads as an object, and the perspective is the point.
    """
    w, h = im.size
    dx = w * (yaw / 90.0) * 0.42
    dy = h * (tilt / 90.0) * 0.16
    sq = w * squeeze
    # far edge (left) shorter than the near edge (right): a simple one-point view
    dst = [(0, dy), (w, 0), (w - sq * 0.15, h), (sq * 0.15, h - dy * 0.55)]
    dst = [(x + dx * 0.0, y) for x, y in dst]
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    co = _persp_coeffs(src, dst)
    if co is None:
        return im
    xs = [p[0] for p in dst]; ys = [p[1] for p in dst]
    out_w, out_h = int(max(xs) - min(xs)), int(max(ys) - min(ys))
    return im.transform((max(1, out_w), max(1, out_h)), Image.PERSPECTIVE, co,
                        Image.BICUBIC)


def macbook(screen, w):
    """A laptop body with the capture in its screen.

    A whole board family in the reference work is simply the site inside a
    device on a flat brand field - no collage at all. Drawn rather than
    composited from a photo so it scales cleanly and carries no stock-mockup
    lighting that would fight the brand colour.
    """
    r = max(6, int(w * 0.022))                 # outer corner radius
    bez = max(4, int(w * 0.013))               # bezel
    sw = w - bez * 2
    sh_ = round(sw * screen.height / screen.width)
    h = sh_ + bez * 2
    body = Image.new("RGBA", (w, h + int(w * 0.018)), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle([0, 0, w - 1, h - 1], r, fill=(28, 28, 30, 255))
    # a hairline of lighter metal along the top edge reads as an aluminium lid
    d.rounded_rectangle([0, 0, w - 1, h - 1], r, outline=(92, 94, 98, 255),
                        width=max(1, int(w * 0.0016)))
    body.paste(screen.resize((sw, sh_), Image.LANCZOS), (bez, bez))
    # camera notch, centred on the bezel
    nw, nh = int(w * 0.085), max(2, int(bez * 0.62))
    d.rounded_rectangle([w // 2 - nw // 2, 1, w // 2 + nw // 2, 1 + nh],
                        nh // 2, fill=(20, 20, 22, 255))
    d.ellipse([w // 2 - 1, 1 + nh // 3, w // 2 + 1, 3 + nh // 3],
              fill=(48, 60, 80, 255))
    # hinge lip below the lid
    lip = int(w * 0.018)
    d.rounded_rectangle([-int(w * 0.012), h - lip, w + int(w * 0.012), h + lip],
                        lip // 2, fill=(38, 38, 41, 255))
    return body


def browser(screen, w, url=""):
    """A browser window - traffic lights and a URL pill, nothing else."""
    bar = max(10, int(w * 0.038))
    sw = w
    sh_ = round(sw * screen.height / screen.width)
    im = Image.new("RGBA", (w, sh_ + bar), (246, 246, 248, 255))
    d = ImageDraw.Draw(im)
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        cx = int(bar * (0.55 + i * 0.42))
        rr = max(2, int(bar * 0.15))
        d.ellipse([cx - rr, bar // 2 - rr, cx + rr, bar // 2 + rr], fill=c)
    if url:
        pw = int(w * 0.34)
        d.rounded_rectangle([w // 2 - pw // 2, int(bar * 0.22),
                             w // 2 + pw // 2, int(bar * 0.78)],
                            int(bar * 0.28), fill=(230, 230, 234, 255))
    im.paste(screen.resize((sw, sh_), Image.LANCZOS), (0, bar))
    return rounded(im, max(4, int(w * 0.012)))


def place(canvas, im, slot, W, H, radius, shadow_alpha, blur, stroke=None):
    w = max(8, int(slot["w"] * W))
    h = max(8, round(w * im.height / im.width))     # derived, never assumed
    if slot.get("dev"):
        # Frame first, then place: the frame is part of the object, so it takes
        # the shadow and the rotation with it.
        framed = (macbook(im, w) if slot["dev"] == "macbook"
                  else browser(im, w))
        piece = framed
        w, h = piece.size
        rot = slot.get("rot", 0)
        if rot:
            piece = piece.rotate(rot, expand=True, resample=Image.BICUBIC)
        x, y = int(slot["x"] * W), int(slot["y"] * H)
        shadow(canvas, piece, x, y, int(shadow_alpha * slot.get("sh", 1.0)),
               blur, int(blur * 0.55))
        canvas.alpha_composite(piece, (x, y))
        PLACED.append((x, y, x + piece.width, y + piece.height))
        return
    if slot.get("cover"):
        # Fill the region: scale so the capture covers it on both axes, then
        # crop. Both axes scale by the same factor, so nothing stretches - the
        # region simply shows a window onto the capture, which is exactly what
        # an overlapping sheet cropped by its neighbour looks like.
        rw, rh = max(8, int(slot["w"] * W)), max(8, int(slot["rh"] * H))
        k = max(rw / im.width, rh / im.height)
        sc = im.resize((max(1, round(im.width * k)),
                        max(1, round(im.height * k))), Image.LANCZOS)
        piece = rounded(sc.crop((0, 0, rw, min(rh, sc.height))), radius)
        w, h = piece.size
    else:
        piece = rounded(im.resize((w, h), Image.LANCZOS), radius)
    if stroke:
        ImageDraw.Draw(piece).rounded_rectangle(
            [0, 0, w - 1, h - 1], radius, outline=hexc(stroke) + (120,), width=2)
    rot = slot.get("rot", 0)
    if rot:
        piece = piece.rotate(rot, expand=True, resample=Image.BICUBIC)
    x, y = int(slot["x"] * W), int(slot["y"] * H)
    shadow(canvas, piece, x, y, int(shadow_alpha * slot.get("sh", 1.0)),
           blur, int(blur * 0.55))
    canvas.alpha_composite(piece, (x, y))
    PLACED.append((x, y, x + piece.width, y + piece.height))


def clear_box(W, H, pad_cols=0):
    """The largest run of grid cells no piece covers.

    Type must never sit on top of UI - a caption card laid over a screenshot
    reads as a mistake, because in the reference work the only things floating
    over a sheet are lifted pieces of that sheet, never words about it. Rather
    than nominate a corner per archetype and hope, measure what the pieces
    actually left free and set the copy there.
    """
    m, g, cw, rh = metrics(W, H)
    free = [[True] * COLS for _ in range(ROWS)]
    for c in range(COLS):
        for r in range(ROWS):
            x0, y0 = m + c * (cw + g), m + r * (rh + g)
            x1, y1 = x0 + cw, y0 + rh
            for px0, py0, px1, py1 in PLACED:
                if px0 < x1 and px1 > x0 and py0 < y1 and py1 > y0:
                    free[r][c] = False
                    break
    best = None
    for r0 in range(ROWS):
        for c0 in range(COLS):
            if not free[r0][c0]:
                continue
            for r1 in range(r0, ROWS):
                for c1 in range(c0, COLS):
                    if not all(free[r][c] for r in range(r0, r1 + 1)
                               for c in range(c0, c1 + 1)):
                        continue
                    cols, rows = c1 - c0 + 1, r1 - r0 + 1
                    if cols < 3 or rows < 2:
                        continue
                    # Favour a column of copy over a wide shallow strip: a
                    # headline needs height more than it needs width.
                    score = cols * rows + rows * 1.5
                    if best is None or score > best[0]:
                        best = (score, c0, r0, cols, rows)
    if best is None:
        return None
    _, c0, r0, cols, rows = best
    return (int(m + c0 * (cw + g)), int(m + r0 * (rh + g)),
            int(cols * cw + (cols - 1) * g), int(rows * rh + (rows - 1) * g))


def copy_block(canvas, box, th, title, headline, sub):
    """Left-hand copy for the `editorial` archetype. Optional everywhere else."""
    from page_mockup import text_panel
    text_panel(canvas, box, th, title, headline, sub, [])


def build(args):
    ss = max(1, args.supersample)
    W, H = (int(v) * ss for v in args.size.lower().split("x"))
    th = dict(display=args.font_display, text=args.font_text, ink=args.ink,
              accent=args.accent, accent_ink=args.accent_ink,
              muted=args.muted, card=args.card, card_ink=args.card_ink,
              card_muted=args.card_muted)

    canvas = field(args.field, (W, H), args.bg.split(","), args.angle,
                   args.seed, args.grain)

    # Everything that can bleed is drawn on its own layer so a containment
    # card can clip it. Without the separate layer a bleeding piece would
    # overrun the frame and the frame would stop meaning anything.
    board = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    if args.layout.startswith("quilt"):
        want = int(args.layout[5:] or 5)
        LAYOUTS[args.layout] = quilt(want, W, H, seed=args.seed)
    if args.layout not in LAYOUTS:
        raise SystemExit(f"unknown --layout {args.layout}; "
                         f"choose from {', '.join(sorted(LAYOUTS))}")
    slots = LAYOUTS[args.layout]
    specs = split_specs(args.pieces)
    if len(specs) > len(slots):
        print(f"note: {args.layout} has {len(slots)} slots, "
              f"{len(specs) - len(slots)} piece(s) dropped", file=sys.stderr)
    if len(specs) < len(slots):
        print(f"note: {len(slots) - len(specs)} slot(s) of {args.layout} unused",
              file=sys.stderr)

    radius = int(args.radius * ss)
    blur = int(W * 0.018 * args.shadow_blur)
    items = []                                   # (z, kind, image, slot)
    for spec, slot in zip(specs, slots):
        im = load_piece(spec, not args.no_trim, args.snap)
        items.append((slot.get("z", 2), im, slot_box(slot, im, W, H)))

    chips = split_specs(args.chips)
    for i, spec in enumerate(chips[:len(CHIP_SLOTS)]):
        s = dict(CHIP_SLOTS[i], z=20 + i, sh=0.9)
        items.append((s["z"], load_piece(spec, False, args.snap), s))

    is_device = any(sl.get("dev") or sl.get("page") for _, _, sl in items)

    # Coverage constraint. The reference boards are almost entirely covered by
    # sheets - the field reads as a margin and as the gaps between overlapping
    # pieces, never as a rectangular hole in the middle of the composition.
    # Weights alone cannot guarantee that, so scale the whole set up until the
    # sheets cover the canvas, then let the edges do the cropping.
    def coverage(scaled):
        grid = [[False] * 24 for _ in range(16)]
        for _, im_, sl in scaled:
            w = sl["w"] * W
            h = w * im_.height / im_.width
            x0, y0 = sl["x"] * W, sl["y"] * H
            for gy in range(16):
                for gx in range(24):
                    cx, cy = (gx + 0.5) * W / 24, (gy + 0.5) * H / 16
                    if x0 <= cx <= x0 + w and y0 <= cy <= y0 + h:
                        grid[gy][gx] = True
        return sum(r.count(True) for r in grid) / 384.0

    # Coverage is bought with tight packing and enough pieces, NOT by inflating
    # each sheet: past ~1.2x the pieces outgrow the canvas and the crop starts
    # slicing through nav bars and mid-sentence. Cap the scaling, then report
    # honestly if the archetype simply has too few pieces to fill the frame -
    # the fix there is more pieces, not bigger ones.
    # The measured per-slot areas are underestimates: the extractor splits each
    # sheet at its internal content boundaries, so one 30%-of-canvas panel is
    # recorded as three 10% fragments. The trustworthy measurements are the
    # anchors and the 83% coverage figure, so let coverage drive the size - but
    # cap each piece so growth never turns into slicing content apart.
    k = 1.0
    while not is_device and coverage(items) < args.coverage and k < 1.10:
        k *= 1.05
        for _, _, sl in items:
            sl["w"] = min(sl["w"] * 1.05, 1.02)
    cov = coverage(items)
    if cov < args.coverage:
        print(f"note: coverage {cov:.0%} (target {args.coverage:.0%}) with "
              f"{len(items)} pieces - add pieces rather than enlarging them",
              file=sys.stderr)

    # Connectivity constraint, measured off 21 real boards: the sheets form ONE
    # connected mass covering ~77% of the canvas, so the field reads only as a
    # margin and as the narrow gaps between overlaps. Islands of screenshot
    # separated by bare colour is the single clearest tell of a generated board.
    def rects(scaled):
        out = []
        for _, im_, sl in scaled:
            w = sl["w"] * W
            out.append((sl["x"] * W, sl["y"] * H, w, w * im_.height / im_.width))
        return out

    def overlaps(a, b, pad=0.0):
        return (a[0] < b[0] + b[2] + pad and a[0] + a[2] + pad > b[0] and
                a[1] < b[1] + b[3] + pad and a[1] + a[3] + pad > b[1])

    for _ in range(0 if is_device else 24):
        rs = rects(items)
        if len(rs) < 2:
            break
        # grow the connected set out from the largest piece
        root = max(range(len(rs)), key=lambda i: rs[i][2] * rs[i][3])
        group, changed = {root}, True
        while changed:
            changed = False
            for i, r in enumerate(rs):
                if i in group:
                    continue
                if any(overlaps(r, rs[j]) for j in group):
                    group.add(i)
                    changed = True
        stray = [i for i in range(len(rs)) if i not in group]
        if not stray:
            break
        # pull each stray toward the nearest member of the mass
        for i in stray:
            r = rs[i]
            cx, cy = r[0] + r[2] / 2, r[1] + r[3] / 2
            j = min(group, key=lambda k: (rs[k][0] + rs[k][2] / 2 - cx) ** 2 +
                                         (rs[k][1] + rs[k][3] / 2 - cy) ** 2)
            t = rs[j]
            tx, ty = t[0] + t[2] / 2, t[1] + t[3] / 2
            items[i][2]["x"] += (tx - cx) * 0.22 / W
            items[i][2]["y"] += (ty - cy) * 0.22 / H

    # How pieces meet the canvas edge. Three rules, in this order:
    #
    # 1. Vision OCR snaps horizontal cuts into the gaps between lines of text -
    #    a cut across the middle of a line's glyphs is always avoidable, because
    #    there is always leading above and below it.
    # 2. Vertical cuts cannot be snapped the same way: on a text-dense page every
    #    x position hits some line. So the rule is commit or don't - clip a piece
    #    by at least a third of its width, so it plainly continues past the frame,
    #    or pull it fully inside. A sheet missing 5% of its words is a mistake; a
    #    sheet half off-canvas is a composition.
    # 3. Cap how many pieces are clipped at all. Measured across the reference
    #    boards: a median of ONE piece crosses an edge, not three or four.
    if not args.no_ocr and not is_device:
        for _, im_, sl in items:
            w = sl["w"]
            h = w * im_.height / im_.width * (W / H)
            if sl["y"] < 0:
                sl["y"] = -snap_cut(im_, "y", -sl["y"] / h) * h
            elif sl["y"] + h > 1:
                sl["y"] = 1 - snap_cut(im_, "y", (1 - sl["y"]) / h) * h

    MIN_CLIP, MAX_CLIPPED = 0.34, 2
    clipped = [] if is_device else []
    for idx, (_, im_, sl) in enumerate(() if is_device else items):
        w = sl["w"]
        left, right = -sl["x"], (sl["x"] + w) - 1.0
        if left > 0 or right > 0:
            clipped.append((max(left, right) / w, idx, "l" if left > 0 else "r"))
    clipped.sort(reverse=True)                    # keep the boldest clips
    for rank, (amt, idx, side) in enumerate(clipped):
        sl = items[idx][2]
        w = sl["w"]
        if rank >= MAX_CLIPPED or amt < MIN_CLIP * 0.5:
            sl["x"] = max(0.012, min(sl["x"], 1 - w - 0.012))   # pull inside
        elif amt < MIN_CLIP:
            sl["x"] = -MIN_CLIP * w if side == "l" else 1 - (1 - MIN_CLIP) * w

    items.sort(key=lambda t: t[0])
    for _, im, slot in items:
        place(board, im, slot, W, H, radius, args.shadow, blur, args.edge or None)

    # Synthetic cards ride above every capture.
    stats = [s for s in args.stats.split(";") if s.strip()] if args.stats else []
    order = [STAT_POS[p] for p in args.stat_pos.split(",") if p in STAT_POS] \
        or STAT_SLOTS
    for i, text in enumerate(stats[:len(order)]):
        s = order[i % len(order)]
        card = stat_card(text.strip(), int(s["w"] * W), th, ss)
        x, y = int(s["x"] * W), int(s["y"] * H)
        # Bottom-anchored slots are positioned by their *bottom* edge: the card
        # grows downward with its qualifier, and a long one would otherwise run
        # off the canvas and lose its last line.
        if s["y"] > 0.5:
            y = int(H * 0.94) - card.height
        shadow(board, card, x, y, args.shadow, blur, int(blur * 0.55))
        board.alpha_composite(card, (x, y))

    if args.caption:
        cw = int(W * args.caption_w)
        card = caption_card(args.caption, cw, th)
        cs = STAT_POS[args.caption_pos]
        m = int(W * 0.03)
        cx = m if cs["x"] < 0.5 else W - cw - m
        cy = m if cs["y"] < 0.5 else H - card.height - m
        shadow(board, card, cx, cy, args.shadow, blur, int(blur * 0.55))
        board.alpha_composite(card, (cx, cy))

    labels = [s for s in args.labels.split(",") if s.strip()] if args.labels else []
    for i, text in enumerate(labels[:len(STAT_SLOTS)]):
        s = STAT_SLOTS[(i + 2) % len(STAT_SLOTS)]
        card = label_card(text.strip(), int(s["w"] * W), th)
        shadow(board, card, s["x"] * W, s["y"] * H, args.shadow, blur // 2,
               int(blur * 0.4))
        board.alpha_composite(card, (int(s["x"] * W), int(s["y"] * H)))

    for i in range(min(args.badges, len(BADGE_SLOTS))):
        s = BADGE_SLOTS[i]
        card = badge_card(int(s["w"] * W), th, args.seed + i)
        shadow(board, card, s["x"] * W, s["y"] * H, args.shadow, blur // 2,
               int(blur * 0.4))
        board.alpha_composite(card, (int(s["x"] * W), int(s["y"] * H)))

    if args.perspective:
        # Tilt the assembled board as ONE group, exactly as a designer rotates
        # a group of mockups - not each sheet separately, which would give every
        # page its own vanishing point and read as a pile.
        t, y_ = [float(v) for v in args.perspective.split(",")]
        tilted = perspective(board, tilt=t, yaw=y_)
        # Fit proportionally and centre. Resizing straight back to the canvas
        # squashes the transform out again, which is why the tilt kept coming
        # back invisible.
        k = min(W / tilted.width, H / tilted.height)
        tilted = tilted.resize((max(1, int(tilted.width * k)),
                                max(1, int(tilted.height * k))), Image.LANCZOS)
        board = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        board.alpha_composite(tilted, ((W - tilted.width) // 2,
                                       (H - tilted.height) // 2))

    if args.tilt:
        # Rotate the assembled board as one object, shadows included, so the
        # pieces keep their relationships. In-plane only - perspective skew
        # makes UI unreadable and reads as a template.
        board = board.rotate(args.tilt, resample=Image.BICUBIC, expand=False,
                             center=(W // 2, H // 2))

    if args.frame:
        # Containment: the whole board lives inside a rounded card inset from
        # the edge, and bleeding pieces are cut by the card, not the canvas.
        m = int(args.frame_margin * W)
        card = Image.new("RGBA", (W - m * 2, H - m * 2),
                         hexc(args.frame_colour) + (255,))
        card = rounded(card, int(args.frame_radius * ss))
        shadow(canvas, card, m, m, 90, blur, int(blur * 0.5))
        canvas.alpha_composite(card, (m, m))
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [m, m, W - m, H - m], int(args.frame_radius * ss), fill=255)
        board.putalpha(Image.composite(board.split()[-1],
                                       Image.new("L", (W, H), 0), mask))

    canvas.alpha_composite(board)

    if args.headline or args.title or args.sub:
        # On the field, never in a box over a sheet, and in whatever space the
        # pieces actually left free.
        if args.text_box:
            bx, by, bw, bh = [float(v) for v in args.text_box.split(",")]
            box = (int(bx * W), int(by * H), int(bw * W), int(bh * H))
        else:
            box = clear_box(W, H)
        if box:
            copy_block(canvas, box, th, args.title, args.headline, args.sub)
        else:
            print("note: no clear space for the copy - it was dropped",
                  file=sys.stderr)

    out = canvas.convert("RGB")
    if ss > 1:
        out = out.resize((W // ss, H // ss), Image.LANCZOS)
        from PIL import ImageFilter
        out = out.filter(ImageFilter.UnsharpMask(radius=1.1, percent=62,
                                                 threshold=3))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    out.save(args.out)
    print(f"{args.out}  {out.width}x{out.height}  layout={args.layout} "
          f"field={args.field}")


def main():
    ap = argparse.ArgumentParser(
        description="Portfolio-style website collage boards.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--layout", default="cascade",
                    help="archetype: " + ", ".join(sorted(LAYOUTS)))
    ap.add_argument("--list-blocks", default="",
                    help="print the distinct UI blocks found in a capture")
    ap.add_argument("--list-sections", default="",
                    help="print a capture's detected sections and exit")
    ap.add_argument("--list-layouts", action="store_true",
                    help="print the archetypes with their slot counts and exit")
    ap.add_argument("--pieces", default="",
                    help="captures, hero first, separated by `;`. "
                         "`path@1.6` crops from the top to that aspect; "
                         "`path#l,t,r,b` crops by fractions of the capture")
    ap.add_argument("--chips", default="",
                    help="UI fragments floated as their own cards, `;` separated; "
                         "(use `#` crops to lift a card out of a page)")
    ap.add_argument("--stats", default="",
                    help="semicolon-separated `BIG|qualifier` cards")
    ap.add_argument("--text-box", default="",
                    help="x,y,w,h fractions for the --headline block")
    ap.add_argument("--caption", default="",
                    help="`What it is|One plain sentence` - the card that makes "
                         "the board legible to someone who has never seen the "
                         "product. Write it for a non-technical reader.")
    ap.add_argument("--caption-pos", default="bl",
                    help="corner for the caption card: tl, tr, bl, br")
    ap.add_argument("--caption-w", type=float, default=0.28)
    ap.add_argument("--no-ocr", action="store_true",
                    help="skip the Vision text pass (crops will cut blind)")
    ap.add_argument("--coverage", type=float, default=0.86,
                    help="minimum share of the canvas the sheets must cover. "
                         "Below this a board reads as screenshots floating in "
                         "a colour rather than as a composition.")
    ap.add_argument("--snap", action="store_true",
                    help="snap band crops to the page's section seams, so a "
                         "piece never cuts through the middle of content")
    ap.add_argument("--stat-pos", default="br",
                    help="corner(s) for the stat cards: tl, tr, bl, br, tc, bc")
    ap.add_argument("--labels", default="", help="comma-separated accent pills")
    ap.add_argument("--badges", type=int, default=0,
                    help="round accent icon tokens, 0-4")
    ap.add_argument("--out", help="output png path")
    ap.add_argument("--size", help="WxH, e.g. 1600x1600")
    ap.add_argument("--field", default="flat",
                    help="flat | gradient | split | shapes | vignette")
    ap.add_argument("--bg", default="#6C7BF5,#4A56D6", help="one or two hex stops")
    ap.add_argument("--angle", type=int, default=150)
    ap.add_argument("--grain", type=int, default=5, help="0 disables")
    ap.add_argument("--perspective", default="",
                    help="`tilt,yaw` in degrees - lays the whole board back in "
                         "space. This is the whole-page board's entire effect.")
    ap.add_argument("--tilt", type=float, default=0.0,
                    help="in-plane rotation of the whole board, degrees")
    ap.add_argument("--frame", action="store_true",
                    help="contain the board in a rounded card inset from the edge")
    ap.add_argument("--frame-margin", type=float, default=0.035)
    ap.add_argument("--frame-radius", type=int, default=28)
    ap.add_argument("--frame-colour", default="#FFFFFF")
    ap.add_argument("--radius", type=int, default=10, help="sheet corner radius")
    ap.add_argument("--edge", default="", help="hairline hex on sheet edges")
    ap.add_argument("--shadow", type=int, default=70, help="shadow alpha 0-255")
    ap.add_argument("--shadow-blur", type=float, default=1.0)
    ap.add_argument("--no-trim", action="store_true",
                    help="keep trailing blank rows on captures")
    ap.add_argument("--supersample", type=int, default=2)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--title", default="")
    ap.add_argument("--headline", default="", help="`|` splits lines; later "
                                                   "lines take the accent")
    ap.add_argument("--sub", default="")
    ap.add_argument("--ink", default="#14150F")
    ap.add_argument("--accent", default="#6C7BF5")
    ap.add_argument("--accent-ink", default="#FFFFFF")
    ap.add_argument("--muted", default="#6A6A62")
    ap.add_argument("--card", default="#FFFFFF")
    ap.add_argument("--card-ink", default="#14150F")
    ap.add_argument("--card-muted", default="#6A6A62")
    ap.add_argument("--font-display", default="archivo")
    ap.add_argument("--font-text", default="inter")
    args = ap.parse_args()

    if args.list_blocks:
        im = Image.open(os.path.expanduser(args.list_blocks)).convert("RGB")
        for i, b in enumerate(find_blocks(im, want=10)):
            print(f"{i:>3}  {b}  {(b[2]-b[0])/im.width:5.1%} wide")
        return
    if args.list_sections:
        im = Image.open(os.path.expanduser(args.list_sections)).convert("RGB")
        for i, (a, b) in enumerate(sections(im)):
            print(f"{i:>3}  y {a:>6}-{b:<6}  {(b - a) / im.height:6.1%} of page")
        return
    if args.list_layouts:
        for name, slots in sorted(LAYOUTS.items()):
            bleeds = sum(1 for s in slots
                         if s["c"] < 0 or s["c"] + s["cs"] > COLS or s["r"] < 0)
            print(f"{name:<13} {len(slots)} slots, {bleeds} bleeding off-canvas")
        return
    if not (args.pieces and args.out and args.size):
        raise SystemExit("--pieces, --out and --size are required "
                         "(or use --list-layouts)")
    build(args)


if __name__ == "__main__":
    main()
