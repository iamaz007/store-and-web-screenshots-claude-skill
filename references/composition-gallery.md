# Composition gallery — website boards

The look this file describes is the studio-portfolio board: several captures of
one site, at several scales, overlapping, some cut by the canvas edge, sitting
on a brand-coloured field. It is what a case-study card, a portfolio thumbnail,
an OG image or a "we built this" social post wants — and it is *not* what
`page_mockup.py`'s tidy columns produce.

Build it with `scripts/collage.py`. `python3 collage.py --list-layouts` prints
the archetypes and their slot counts.

## The variety rule

**Rotate the archetype, the field and the palette on every project.** These
boards fail in one specific way: the operator finds one combination that worked,
and then every client's board is a cascade on a flat blue field with two stat
cards. A portfolio of those reads as a template, which is the opposite of the
point.

Before you build, write down the previous project's `--layout`, `--field` and
accent — and pick different ones. If the brief genuinely calls for the same
archetype twice, change everything else: containment, tilt direction, whether
copy appears, which extras are on, how many pieces, how much bleeds.

Cheap dials that change a board completely, in rough order of effect:

1. **Archetype** (`--layout`) — the structure itself.
2. **Field** (`--field` + `--bg`) — flat colour, gradient, diagonal split,
   background geometry, vignette.
3. **Containment** (`--frame`) — board loose on the colour, or held inside a
   rounded white card with a colour margin. Two totally different objects.
4. **Tilt** (`--tilt -8 … 8`) — the whole assembly rotated as one.
5. **Scale spread** — one huge sheet against small ones, or all pieces close in
   size. Use `@aspect` on each piece to control how tall each sheet reads.
6. **Extras** — stat cards, accent pills, round icon badges, lifted UI chips.

## The eleven archetypes

| Archetype | Structure | Reaches for |
|---|---|---|
| `cascade` | hero left, secondaries stepping down-right, heavy overlap | narrative case studies; the default when a site has a story |
| `scatter` | six pieces, varied scale, three leaving the frame | the most designed look; needs strong captures |
| `stack-tilt` | four sheets stacked, whole board rotated | energy without chaos; pairs with `--tilt -8` |
| `diptych` | two large sheets, offset, one clipped at top | finance, legal, healthcare — calm and editorial |
| `spotlight` | one near-1:1 sheet, two small fragments | when UI text must stay genuinely readable |
| `mosaic` | six near-equal cards, two anchors | product suites, multi-feature marketing sites |
| `ribbon` | horizontal run of sections, both ends cropped | wide formats only, 3:1 and wider; a site as filmstrip |
| `orbit` | upright hero centre, four smaller around it | the safe one; captures are the story |
| `fan` | sheets fanned at increasing rotation | consumer, creative, events |
| `handset-row` | landscape hero behind a row of portrait screens | apps, mobile-first products |
| `editorial` | copy panel left, pieces stacked right | when the board must carry a headline |

## Start here: the whole-page board

**The most presentable board is also the simplest, and it is not a collage.**
Two to four *complete, uncropped* page captures, laid side by side, tilted
together in perspective on a soft gradient field:

    python3 collage.py --layout pages3 --out board.png --size 1280x769 \
        --pieces "home.png;pricing.png;about.png" \
        --field gradient --bg "#EEF0EA,#C6D0BA" --perspective "22,16" --radius 6

Why it wins: **nothing is cropped, so nothing can be cropped badly.** Every
failure mode of the fragment collages - a headline sliced mid-word, a diagram
cut in half, a paragraph blown up until it reads as a caption - simply cannot
happen, because each piece is a whole page. It is also what a competent junior
produces in Canva in ten minutes, and it looks better than an elaborate
generated collage. Reach for `pages2` / `pages3` / `pages4` first, every time.

**This overrides the "in-plane rotation only, never perspective" rule.** That
rule belongs to store tiles, where the screenshot IS the product demo and UI
legibility is everything. On a portfolio board the page reads as an *object*,
and laying it back in space is the entire effect. `--perspective "tilt,yaw"`
tilts the assembled board as one group - never each sheet separately, which
gives every page its own vanishing point and reads as a pile.

Order of preference for a portfolio board:

1. **Whole pages, tilted** (`pages2/3/4`) - the default. Safe and presentable.
2. **A device mockup** (`device-hero`, `device-crop`, `device-stack`) - the site
   in a drawn laptop or browser frame on a flat brand field, with a lifted stat
   card. Use it to break up a set of whole-page boards.
3. **A fragment collage** (`cascade`, `dense`, `scatter`, …) - only when the
   material genuinely suits it, and expect to check every crop.

**Filter dead captures first.** A demo site that has gone offline returns a
"Site not found" page, and a 404 on a portfolio board is worse than one fewer
page. Run the captures through OCR and drop them; `textmap.swift` prints the
recognized text alongside the boxes for exactly this.

## What the reference work actually does

Two findings from going through a full portfolio of these boards. Both contradict
what seems obvious, and both were got wrong first time here.

### The boards carry no added text

Not one reference board has a caption card, a headline written about the site,
a step number, or a label. **The only words on a board are the words already
inside the screenshots.** Everything floating over the sheets is a component
*lifted out of the site itself* - a stat card, a testimonial, a pricing box, a
plan row, a circular icon badge. Never a note about the work.

This is the opposite of the instinct to explain, and it is right: the pages
already say what the product is, in the client's own voice and type. A caption
laid over them competes with that and reads as a slide, not a portfolio piece.

So: `--caption` and `--headline` exist, but the default is to use neither.
Reach for them only when a board must stand completely alone with no surrounding
context - and even then, prefer lifting a real stat card out of the page.

### The field is a saturated brand hue, chosen for lightness contrast

The background is never a pale wash of the site's colour. It is the brand hue at
strength, picked so the **pages contrast with it in lightness**:

| Site's pages | Field | Examples |
|---|---|---|
| light / white | saturated mid or deep brand colour | lime under black-and-white pages; periwinkle, orange, forest, deep teal under cream pages |
| dark | pale, cool tint | light blue-grey under a near-black site; pale cyan under a dark one |

A cream field under cream pages is the failure: the sheets stop reading as
objects, the board goes flat, and anything placed on it screams. Check the two
lightnesses before choosing; if they are within roughly 25%, the field is wrong.

Take the hue from the site, then push its saturation and move its lightness away
from the pages - do not simply sample a colour off the page and use it as-is.

## The board has to explain the product

A board is not a texture. Someone who has never seen the product should be able
to say what it does after two seconds, and these three things are what decide
that:

*(The rules below apply when a board genuinely must caption itself - a rare
case. Default to the no-text convention above.)*

1. **Lead with the hero, whole and readable.** Logo, nav and headline intact, at
   a size where the headline can actually be read. Every reference board in this
   genre does this; a board assembled from mid-page fragments does not say what
   the product is, no matter how well composed it is.
2. **Use whole sections, never percentage bands.** `page.png~2` takes the third
   real section, found at the page's seams. A guessed `#0,0.72,1,0.83` crop cuts
   through the middle of a diagram or slices a headline through its x-height -
   and on a long page it can land in a duplicate of the page entirely. Check
   what you are about to use: `collage.py --list-sections page.png`.
3. **Caption it in plain language.** `--caption "What it is|One sentence"`.
   Write it for someone outside the industry: what the thing does and who for.
   Not the site's own headline, not a feature name, not a step number.

**Never number the boards on the image.** `01 / 02 / 03` step markers are not a
thing the reference work does - the order belongs in the filename. A card on the
board earns its place only if it carries a real number the site itself
publishes ("700+ websites built", "$1B+ in deals signed") or the plain-language
caption above.

## Resolution: deliver a 2x, always

Work out what the site's own text will measure on the finished board before
choosing a delivery size:

    slot_px = board_width x slot_fraction
    scale   = slot_px / capture_css_width
    ui_text = 14 x scale

A 1280-wide board with four framed screens gives each ~560px for a 1280 CSS-px
page: 44% scale, so 14px UI text renders at **6px** - unreadable, and no amount
of sharpening recovers it, because the pixels are not there. Under ~10px the
text is decoration rather than content.

So render every board at the requested size **and at 2x**, and hand over both.
Composite at 3x supersample, reduce once, and apply a single light unsharp pass
(radius 1.1, 62%, threshold 3) *after* the reduction - never to an intermediate.

Note Pillow's decompression-bomb guard trips on full-page captures at DPR 3 and
on framed devices at 3x supersample; set `Image.MAX_IMAGE_PIXELS = None` for
your own files.

## Alignment and spacing

Everything below is what separates a composition from a pile of screenshots on
a colour, and all of it is enforced by the compositor rather than left to taste.

**Slots live on a 12-column grid.** `resolve()` turns grid units (`c` start
column, `r` start row, `cs` column span) into pixels with one margin and one
gutter for the whole board. Hand-picked decimals — `x=0.34, y=0.62` — are what
produce edges that almost line up and gaps that are all slightly different
sizes. If you add an archetype, add it in grid units.

- **Every left edge lands on a column line, every top edge on a row line.**
  Heights come from each capture's own aspect, so a slot fixes the top-left
  corner only; that is enough for the eye to read the board as aligned.
- **One gutter, one margin.** Not a different gap between each pair.
- **Bleed in whole columns.** `c=-1` or `c+cs > 12` puts a piece off the edge
  deliberately; a piece that misses the edge by 2% looks like a mistake.
- **The type block and the caption card sit on the same grid** — same margin, a
  whole number of columns wide — so the copy lines up with the sheets beside it.

**Size by visual weight, not by column span.** Each slot declares `wt` — the
share of the canvas the piece should occupy — and `slot_box()` derives the width
from that plus the capture's own aspect, then snaps it back to whole columns.
A fixed span cannot work: the same 4 columns makes a wide, short strip look tiny
and a tall full-page sheet look enormous, because width alone says nothing about
how much of the board a piece covers. Weight-based sizing is what stops a set
coming out with "some too big, some too small for no reason".

**Include the whole landing page as one long sheet.** Pass the capture with no
`~section` and no crop. Weight-based sizing turns a 1:3 page into a tall, narrow
column — the shape almost every reference board leans on, and the one thing that
says "this is a website" rather than "these are some screenshots". Put it in a
different beat for each project so the sets do not rhyme.

**A different archetype set per project.** Not just a different order of the
same three. With fifteen archetypes there is no excuse for two projects sharing
a shape; write down the last project's triple before choosing.

**Scale hierarchy is not optional.** One dominant piece at 8–10 columns, the
rest at 3–5. Three sheets at the same size in a row is the failure mode, and no
amount of colour or shadow rescues it. `hero-detail`, `dense`, `poster` and
`portrait-pair` are built around that gap; the older archetypes are flatter.

**Small slots take a lifted component, not another whole sheet.** `page.png~2!0`
crops the largest distinct UI block out of a section — one pricing card, one
form, one stat row — found by `find_blocks()`. A whole page shrunk into a small
slot is unreadable and adds nothing; one component at that size is the move the
reference work makes on every board.

**Never repeat a source in one board.** The same hero twice reads as a bug.

**Type is set, not boxed.** Headlines auto-fit to their column and stack on real
font metrics (ascent + descent + leading), never on glyph bounding boxes — bbox
stacking makes a line without descenders sit tighter than the next one and runs
headline into body copy. Pass `--muted` explicitly: the default is a dark grey
that disappears on a dark field.

## Piece syntax

`--pieces` and `--chips` take `;`-separated specs:

- `home.png` — the whole capture (trailing blank rows trimmed).
- `home.png@1.4` — cropped from the top to a 1 : 1.4 sheet. **This is the main
  height control.** A full page at its natural 1 : 3 shoots far off the bottom
  of the canvas; 0.8–1.6 is card territory, 1.8–2.6 reads as "a page".
- `home.png~2` — **the third whole section of the page**, cut at its real seams.
  Prefer this over any guessed band: it cannot cut through content. List them
  first with `--list-sections`.
- `home.png#0.05,0.62,0.55,0.80` — cropped by fractions of the capture
  (left, top, right, bottom). Use this only to lift one card, one stat row or
  one pricing table out as a chip - not to choose a section. Add `--snap` and
  the edges move to the nearest seam.

Crops are crops. Both axes always scale together — nothing in this script can
stretch UI.

## Extras

- `--stats "70%|of athletes face financial hardship;\$1B+|in deals signed"` —
  white cards, big number over a qualifier. Two is plenty; three is a dashboard.
- `--labels "Book a demo,Get started"` — accent pills, lifted CTAs.
- `--badges 2` — round accent tokens with a simple glyph. Punctuation, not
  information. Three or more and they start to look like a feature list.
- `--title/--headline/--sub` — the left copy panel. `editorial` expects it;
  everywhere else it competes with the screens, so leave it off unless the board
  has to work with no caption beneath it.

## Fields

| `--field` | Look | Notes |
|---|---|---|
| `flat` | one solid brand colour | the strongest, and the hardest to get wrong |
| `gradient` | two stops at `--angle` | keep the stops close; a rainbow reads as stock |
| `split` | two colour blocks on a diagonal | poster energy, good behind a tilted board |
| `shapes` | flat plus oversized parallelograms in a near-tone | brand geometry; stays quiet behind UI |
| `vignette` | gradient darkened at the rim | pushes attention to the centre sheet |

Take the colours off the site itself, not off this file. `build_tiles.py
--palette-from logo.png` extracts them.

## Rules that hold across every archetype

- **Bleed on purpose.** At least one piece should be cut by the canvas or by the
  containment card. A board where every sheet floats fully inside the margins
  reads as a contact sheet.
- **Vary the scale.** If every piece is within 20% of the same width, the board
  has no hierarchy and no focal point.
- **In-plane rotation only.** `--tilt` and per-slot `rot` rotate; nothing skews
  in perspective. Perspective makes UI unreadable and is the single clearest
  tell of a template.
- **Capture at DPR 2–3 and at a narrow CSS viewport** (1280, not 1440) so UI is
  physically larger on the finished board. Then check: `piece_width_px /
  capture_css_width` under ~25% means the UI text is no longer readable, and the
  fix is fewer pieces, not sharpening.
- **Composite big, reduce once.** `--supersample 2` (or 3) is on for a reason —
  the tilt rotation resamples, and assembling at final size resamples an already
  downscaled capture a second time.
- **Shadows stay off the field.** `--shadow 60–90` on light grounds, up to 120
  on dark. Heavier than that and it reads as a drop-shadow preset.
