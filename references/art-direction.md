# Art direction

**A screenshot set must look like it was designed for *this* app.** Never reuse a
previous project's palette, background motif or composition. If two different
apps come out of this skill looking like siblings, the skill was used wrong.

The compositor ships no house style — palette, background and layout are all
config. What follows is how to choose them.

## Step 1 — read the app's nature

| Signal | Where to get it | What it implies |
|---|---|---|
| Brand colour | app icon, splash, primary buttons in captures | the accent; everything keys off it |
| Category | store category + what the app does | register: utility, creative, finance, health, games |
| UI density | the captures themselves | dense dashboards want space around them; sparse UI can be shown large |
| Light or dark UI | captures | tile background is usually the *opposite* end of the scale so the UI pops |
| Emotional job | why someone opens it | anxious→calm (finance, security), boring→energetic (habit, fitness) |

Extract the accent from the app icon rather than inventing one:

    python3 scripts/build_tiles.py --palette-from path/to/icon.png

## Step 2 — pick a composition archetype

| Archetype | Shape | Best for |
|---|---|---|
| `feature-left` | icon + headline + vertical feature list on the left, device right | feature-rich apps that must prove breadth; the most information-dense option |
| `hero-center` | big headline top, device centred below, callout cards over its edges | single-purpose apps with one strong screen |
| `showcase` | headline + benefit check-row on top, wide window/device below, corner cards | desktop apps and dashboards; landscape tiles |
| `stacked-devices` | two or three devices overlapping at different depths | flows worth showing as a sequence |
| `object-hero` | 3D icon or props floating, minimal UI | tile 1 only — an opener before the UI tiles |
| `hero-mac` | text column left, machine/browser window right, atmosphere behind both | macOS tiles and website tiles on landscape ratios |

For **website tiles**, `hero-mac` (text column left, frame right) and `showcase`
are the two that survive a landscape ratio; `hero-center` needs a tall tile.
Set `"device_style": "browser"` and cap the frame with `"device_h"`.

Vary within a set, but keep one skeleton: a set where every tile is the same
archetype reads flat; a set where all six differ reads chaotic. Typical: tile 1
`object-hero` or `feature-left`, tiles 2–6 alternating `hero-center` sides.

## Step 3 — background

| Style | Use when |
|---|---|
| `gradient` | default for consumer apps — soft wash of the brand colour, near-white at one corner |
| `mesh` | two or three brand hues blended; energetic, good for AI/creative apps |
| `contour` | topographic lines; only when the app is about terrain, maps, navigation |
| `dots` | subtle grid; technical and developer tools |
| `solid` | maximum restraint; premium and finance |

Whatever is chosen, generate it across the full strip width and slice per tile so
it continues between tiles.

## Step 4 — typography

**Pick the typeface from what the app is, never from what you used last time.**
Ask the advisor and paste its answer into the theme:

    python3 scripts/build_tiles.py --suggest-fonts "storage cleaner for mac"
    #   "font_display": "archivo", "font_text": "inter"

A *display* face carries headlines; a *text* face carries body copy, cards and
feature rows. One family for both is fine only when it has real weight range.

| Register | Pairing | Fits |
|---|---|---|
| Punchy utility | `archivo` + `inter` | cleaners, scanners, optimisers, news |
| Engineered | `ibm-plex-sans` | security, VPN, backup, B2B, infrastructure |
| Technical-current | `space-grotesk` + `inter` | AI, crypto, dev tools |
| Work tool | `manrope` + `inter` | dashboards, SaaS, productivity |
| Trustworthy | `source-serif-4` + `inter` | finance, legal, insurance |
| Expensive | `playfair-display` + `work-sans` | luxury, fashion, property |
| Handmade | `fraunces` + `work-sans` | food, craft, indie, editorial |
| Poster shout | `bebas-neue` + `archivo` | fitness, sport, events (Bebas is display-only) |
| Calm | `rubik` | health, wellness, habit, kids |
| Readable | `lora` + `inter` | reading, journaling, publishing |
| Mainstream consumer | `poppins` + `outfit` | retail, beauty, travel, social |

Google families download on first use into `assets/fonts/`. macOS faces
(`avenir-next`, `helvetica-neue`, `futura`, `didot`, `georgia`) need no network
and are the fallback when a fetch fails.

Whatever you choose: never stretch or condense type to fit, and keep one type
scale across the whole set and across platforms.

## Step 5 — optional elements

Ask the user (see SKILL.md step 3). Each is off by default:

- **3D hero object** — on an opener tile with no app UI, `solid3d()` renders the
  app icon as a tilted solid with a real side wall, contact shadow and light
  swirls. Tune with `yaw`, `pitch`, `depth` and `focal` per tile, and the wall
  colour with the theme's `extrude`. Sensible start: yaw −22, pitch 14,
  depth 0.42, focal 9. This is what makes an opener read as rendered rather
  than as a flat sticker.
- **Floating props** — `"props"` in the theme: `"none"` (nothing floats),
  `"flat"` (solid tiles, plain shadow) or `"3d"` (gradient, specular sheen,
  glow, drop shadow). 3D is what reads as premium and "generated"; `"none"` is
  what reads as serious. `"icon_style"` takes the same three values for the
  feature-row icons — keep the two consistent or the tile fights itself.
  Per-tile placement lives in `"props": [{x, y, glyph, colour, r, s}]`, with
  glyphs `sparkle shield folder clock gauge copies broom disk`.
  Keep props clear of the device's edges and off the laptop base.
- **Feature list** — 3–5 rows, each a coloured icon tile + title + one line.
  Strongest single device for feature-rich apps.
- **Check row** — 3 short benefit phrases with ticks, under the headline.
- **CTA pill** — a wide accent button on the last tile, e.g. "Try it free today".
- **Trust badge** — small card: privacy, user count, rating. Only if true.
- **Brand logos** — of services the app genuinely connects to. High impact, high
  risk: never use a logo the app does not integrate with, and never imply
  endorsement.
- **Accent underline** — hand-drawn stroke under the accent word.

## Step 6 — dial the shadows back

On a **light** background every effect that looked right on dark turns into
grey haze: halo blobs band into visible rings, glows read as smudges, drop
shadows read as dirt. The user's words were "lot of unwanted shadow making it
worse". Every one of these is a theme key — turn them down rather than removing
the element:

| Key | Dark bg | Light bg |
|---|---|---|
| `halo` (concentric rings behind a hero) | 30 | **0** — they band |
| `hero_glow` | 70 | 26 |
| `hero_shadow` | 95 | 20 |
| `ground` (contact shadow) | 70 | 26 |
| `swirl_alpha` | 150 | **0** — reads as a smudge, not light |
| `prop_shadow` / `prop_glow` | 105 / 84 | 42 / 40 |
| `device_shadow` | 105 | 38 |

Rule of thumb: on light, roughly a third of the dark-background value, and drop
the two atmospheric layers (halo, swirls) entirely. The object's own form and
its side wall carry the depth — the shadow only needs to seat it.

## Step 7 — lift the feature out of the device

The archetypes above all put a device on a tile. What separates the listings
that convert from the ones that do not is what happens *next*: the feature is
lifted out of the phone, enlarged and floated over it.

| Config | Shape | Use for |
|---|---|---|
| `lift` | one region, matted and enlarged | the artifact the app makes — a collage, a finished page, a card being chosen |
| `lift_ba` | two panels, pills, accent chevron | anything with a before and an after — cutouts, object removal, enhancement |

Rules that hold for both:

- **Measure the crop off the pixels.** A flat colour field locates itself; an
  estimate is out by a percent or two and lifts empty chrome with the feature.
- **Both halves of a before/after come from the same screen**, via the app's own
  compare toggle or divider, or the two panels frame the subject differently.
- **Let it break the device outline.** A slab that fits neatly inside the phone
  has gained nothing over the screenshot it came from.
- **One lift per tile.** Two slabs fight, and the eye lands on neither.
- **Not every tile.** Lift where the artifact is the message; leave the screen
  plain where the spread is — a "200 templates" tile or a library screen is
  selling breadth, and a blown-up single item covers the thing being sold.

## Judgement

- **Contrast against the store.** Both stores are white; a set that is entirely
  white-on-white disappears in the grid.
- **One accent, one neutral, one ink.** More than two accents reads cheap unless
  the app itself is multi-coloured by nature.
- **Match the app's own UI colours** so the tile and the screenshot inside it feel
  like one product. A tile whose accent fights the UI's accent looks like a
  template someone dropped a screenshot into.
- **Density follows the platform.** Desktop tiles are viewed larger — they carry
  more text and detail than a phone tile ever should.
