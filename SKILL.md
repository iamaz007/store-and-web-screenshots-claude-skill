---
name: store-screenshots
description: Design App Store and Google Play screenshot sets for any app — Android phone, Android tablet, iPhone, iPad and macOS — and designed website screenshots for landing pages, docs, README hero images, OG cards and social posts. Use when the user asks to create, redesign or resize store screenshots, listing images, store tiles, feature graphics, "screenshots for the Play Store / App Store", or a framed/branded screenshot of a website or web app. Covers researching reference listings first, writing benefit-led copy, and compositing at the exact sizes each surface requires.
---

# Store screenshots

Store screenshots are the **highest-leverage conversion surface an app has** — most
installs are decided in the store listing, from the first two tiles, at thumbnail
size, without the description ever being read. Treat them as a designed set, not
six exports.

## The one rule that matters most

**Never use an image generator to reproduce app UI.** Image models *regenerate*
whatever screenshot you give them — they cannot composite exact pixels. Doing so
produces, reliably: invented empty gaps in the UI, a substituted layout from a
different device, a missing status bar, and horizontally stretched UI. No prompt
wording prevents this.

Composite locally instead — `scripts/build_tiles.py` does it with Pillow. Image
generation is acceptable **only** for background art that contains no UI and no
text. See `references/pitfalls.md` for the full list of failures this avoids.

## The second rule: no house style

**Every app gets its own art direction.** The compositor ships no default look —
palette, background and layout all come from config. Derive them from the app's
own brand and category (`references/art-direction.md`).

If two different apps come out of this skill looking like siblings — same
background treatment, same accent, same composition — it was used wrong. Never
copy the theme from a previous project.

## Workflow

Work through these in order. Do not skip to rendering.

If the subject is a **website or web app** rather than a store listing, read
`## Website screenshots` below first — the intake questions differ — then come
back and follow the same steps.

### 1. Understand the product

Never write copy from screenshot contents alone. Establish what the app actually
does and which claims are true:

- Read the codebase — screens, routes, feature flags, the paywall, any README or
  architecture doc. Note what is real vs. placeholder.
- Read the product's own marketing site if one exists. Its headlines are the
  authoritative brand voice, and its numbers (states covered, items indexed,
  users) are the numbers legal/marketing already stand behind.
- Reconcile conflicts. If the code says 20 species and the site says 23, the site
  is marketing-authoritative for the store — but flag the discrepancy to the user.

Produce a short feature inventory: what the feature is, where it lives, and **what
it does for the user**. That last column becomes the copy.

### 2. Research reference listings — before designing

Look at how competitors in this exact category present themselves, on the store
the tiles are destined for. Use the browser, and search the actual storefront:

- **Google Play** — `https://play.google.com/store/search?q=<category>&c=apps`
- **App Store** — `https://apps.apple.com/us/search?term=<category>`

Open the top 3–5 listings and capture what the good ones do: headline length,
whether copy sits above or below the device, use of a continuous background motif
across tiles, how the first tile differs from the rest. Note the conventions of
the *category* — a hunting app and a calendar app have different visual norms.

Report what you found to the user before building. See
`references/research.md` for what to look for and how to judge it.

### 3. Choose the art direction — and ask

Read `references/art-direction.md`, then propose a direction derived from this
app: accent extracted from its icon (`--palette-from`), a background style, and
a composition archetype that suits its nature.

Put the proposal to the user as concrete choices, with your recommendation
first. Ask in one round — these change the design materially and are cheap to
answer, expensive to redo:

- **Background** — soft brand gradient / mesh / dots / flat / motif (which motif?)
- **Composition** — feature list beside the device, or one big device with callouts?
- **Extras** (any combination): floating 3D objects or props · brand logos of
  integrated services · benefit check-row · CTA pill on the last tile ·
  trust badge (privacy, ratings, user count) · accent underline
- **Devices** — single, or overlapping multiples?
- **Mood** — calm and premium, or bright and energetic?

Only ask about things you cannot settle from the app itself. If the icon is
unmistakably one colour, take the accent and say so rather than asking.

**Ask about props explicitly** — they change the character of the whole set:

- **Props off** (`"props": "none"`) — nothing floats; the device and type carry
  the tile. Calmest, and correct for finance, security and enterprise.
- **Flat props** (`"props": "flat"`) — solid colour tiles, plain shadow, no
  glow. Graphic and restrained.
- **3D props** (`"props": "3d"`, default) — gradient body, specular sheen, glow
  and drop shadow, so objects read as floating in front of the device. This is
  the look people mean by "like the AI-generated ones". `"icon_style"` takes the
  same values for the feature-row icons.

**Never pick the typeface by habit.** Run the advisor before writing any config:

    python3 scripts/build_tiles.py --suggest-fonts "what the app actually is"

It ranks display/text pairings against the app's category and prints why each
fits — a slab for a utility, an engineered sans for security, a didone for
luxury, a soft serif for craft food. Put the winner in the theme as
`"font_display"` and `"font_text"`. Google families are fetched on demand into
`assets/fonts/` and cached; macOS system faces are the offline fallback. A set
that ships in the same face as the last project was not art-directed.

**When the target is iOS, also ask about the 6.5″ slot.** App Store Connect shows
a 6.5″ panel next to 6.9″; it is optional ("Keep using 6.9″ Display") but many
teams fill it. The two slots have **different aspect ratios**, so a 6.5″ set must
be rendered natively (`--platform ios-65`) — never resized from the 6.9″ output.
Ask once, up front, so both sizes come out of the same run.

### 4. Write the copy

- **2–3 words per headline.** Long headlines vanish at thumbnail size.
- **Sell the benefit, never app data.** A badge copied off a screenshot (`100% @ 8 pts`)
  is meaningless to someone who has never used the app. Say what it does for them.
- Colour one **accent word** per headline; underline it only if the chosen art
  direction uses that device.
- Support text per tile: a card, a feature list, or a check row — whichever the
  archetype calls for. Each item is a big line plus a small qualifier.
- Screen for wording that is fine inside an app but wrong on a public store tile
  (anatomical terms, internal codes, debug values).
- Do not claim a trial length, price or rating on a tile unless the user confirms it.

### 5. Build

Use `scripts/build_tiles.py`. It generates the background, typography, callout
cards and device bodies locally, and pastes each capture **at its true aspect
ratio** — the ratio is derived from the source image, never assumed, so UI
physically cannot stretch.

Layout patterns and the config schema are in `references/art-direction.md`.
Whichever archetype is chosen, these hold:

- Headline reads **before** the device does — top, or beside it in a left column.
  Never stacked in a centred column under the device.
- Supporting cards **overlap** the device so they read as callouts pulled out of
  the app, rather than floating in dead space.
- Device is flat with a slight 3–5° in-plane rotation, or perfectly upright —
  **never 3D perspective skew**, which makes UI unreadable and looks broken.
- The background runs edge to edge across the whole set, generated once at full
  strip width then sliced, so it continues between tiles.
- Type is never stretched, condensed or letter-spaced to fit. Text in a column
  shares one left margin.

### 6. Lift the feature out of the device

**A tile that pastes a whole screen into a phone and stops is the single most
common way this skill gets used badly.** Look at any listing in a competitive
category: the collage, the cutout, the before/after is *pulled out* of the
phone, blown up two or three times, matted in white and floated over the device
so it breaks the phone's outline. At browse size that is the difference between
a tile someone can read and a tile they scroll past — inside the frame, the
feature is a 200px-wide postage stamp.

Two shapes, both per-tile config:

```jsonc
"lift":    {"crop": [l,t,r,b], "w": 0.80, "y": 0.62, "rot": -2}
"lift_ba": {"before": {"shot": "a.png", "crop": [...]},
            "after":  {"shot": "b.png", "crop": [...]},
            "w": 0.94, "y": 0.62, "labels": ["Before","After"], "chevron": true}
```

`crop` is fractional on the source capture, `w` is the slab's width as a
fraction of the tile, `y` its centre. `lift_ba` builds the two-panel Before |
After card with pills and an accent chevron. Both draw **after** the device, so
they overlap it on purpose.

**Measure the crop, never estimate it.** Eyeballing a region off a screenshot is
wrong by one or two percent every time, which is enough to lift a slab of empty
white along with the feature, or to clip it. App UI is mostly flat colour
fields, so find the real bounds from the pixels:

```python
a = np.asarray(Image.open(shot).convert("RGB")).astype(int)
ys, xs = np.nonzero((a[...,1] > 200) & (a[...,2] < 120))   # e.g. a lime card
rect = (xs.min()/W, ys.min()/H, xs.max()/W, ys.max()/H)
```

**For a before/after, capture both states from the same screen** so the two
crops line up — toggle the app's own compare control, or drag its own
before/after divider to each end. Two panels shot from different screens will
frame the subject differently and the comparison stops being one.

**Do not lift on every tile.** Lift where the *artifact* is the message — a
finished document, a cutout, a before/after. Leave the screen plain where the
*spread* is the message: a catalogue tile saying "200 templates" is advertising
breadth, and a blown-up single card sits on top of the very grid it is selling.
The same goes for a library or history screen. A set where every tile carries a
slab reads as a formula.

A **focus ring** drawn inside the screen is the weaker cousin of this: it points
at a feature the viewer still cannot see. Use it only where the thing genuinely
cannot be lifted — a selection in a list, a control being tapped.

### 7. Verify before delivering

Check every tile against `references/checklist.md`. At minimum: exact pixel size
for the target slot, no alpha channel, app UI matches the source capture
(status bar present, spacing unchanged), and text legible when the tile is
scaled to thumbnail width.

## Website screenshots

Same compositor, same rules — a website screenshot is a designed tile with a
browser window in it instead of a phone. Build with `--platform web-hero`,
`web-og`, `web-square` or `web-tall`; the frame style defaults to `browser`
(traffic lights plus a URL pill — pass the real URL as `"url"` on the tile).

**Ask this intake round before capturing anything.** These five answers change
the capture itself, so getting them after the fact means recapturing:

1. **Scope — whole page, or one part?** A full-page capture is 5–10× taller than
   it is wide and shrinks to an unreadable ribbon inside a tile. Ask which it is:
   - *whole page* — use `web-tall` and expect the page to read as a shape, not as
     text; good for "here is the site", useless for showing a feature.
   - *a specific part* (hero, pricing table, dashboard, one component) — name the
     section, capture the viewport around it, or crop with `"shot_crop": [l,t,r,b]`
     (fractions of the capture). Cropping is allowed; scaling one axis is not.
   Default to asking rather than guessing — "a screenshot of my site" means
   either one, and the tiles look nothing alike.
2. **References — an image or a URL?** Ask for one of each if they have it: a
   reference *image* (a tile they like, a moodboard, a brand board) or a
   reference *URL* (a site whose look they want, or their own brand site). Fetch
   the URL and look at it; open the image and read the palette, type and spacing
   off it. If they have neither, derive the direction from the site itself and
   say what you derived and why.
3. **Background type** — flat, brand gradient, mesh, dots, grid, noise, motif,
   photographic, or a dark stage. Offer these as concrete options with your
   recommendation first; the background carries more of the tile's character
   than anything else on it.
4. **Font style** — do not just pick, *understand*. Ask what the site's own type
   does (geometric sans, grotesk, editorial serif, mono/technical) and whether
   the tile should match it or deliberately contrast with it. Confirm the actual
   families in use — read the site's CSS or `@font-face`/Google Fonts links
   rather than eyeballing — then run the advisor before writing config:

       python3 scripts/build_tiles.py --suggest-fonts "what the site actually is"

5. **Props and extras** — ask explicitly, same three options as store tiles
   (`"props": "none" | "flat" | "3d"`), plus anything web-specific worth adding:
   a cursor or click ring, a floating UI card lifted out of the page, a logo row
   of integrations, a stat pill, a CTA pill, a URL bar as the only chrome.

**Never reuse a look.** Every site gets its own palette, its own typeface pairing
and its own background treatment — not the ones from the last site, and not the
ones from this skill's examples. If two projects come out looking related, it was
used wrong. Extract the accent from the site's own brand (`--palette-from` on a
logo or favicon) and state which colours came from where.

**Whole-page mockups** — when the answer to question 1 is *whole page*, the long
sheet on a backdrop reads better than a browser frame. Use `scripts/page_mockup.py`:
it trims the trailing blank rows off the capture, slices the page into 2–3
columns, rounds and shadows them, and floats them on a gradient with an accent
bloom in the margins. Arbitrary output size, so it also covers off-spec asks
(a 1280 × 769 README image, a 1000 × 750 deck slide).

    python3 scripts/page_mockup.py --shot page.png --out docs/site.png \
        --size 1280x769 --bg "#222617,#080907" --glow "#C6F94F" --cols 2 \
        --gap 52 --stagger 16 --angle 135

**Portfolio boards and case-study cards** — the sliced-column look is one
composition, and using it for everything is why sets start looking related. When
the deliverable is a portfolio card, a case-study hero, an OG image or a "we
built this" post, use `scripts/collage.py`: eleven layout archetypes, five
background fields, optional containment card, whole-board tilt, lifted UI chips,
stat cards, accent pills and icon badges.

    python3 scripts/collage.py --list-layouts
    python3 scripts/collage.py --layout cascade --out board.png --size 1280x769 \
        --pieces "home.png@2.0;pricing.png@1.1;about.png@1.2" \
        --chips "home.png#0.05,0.62,0.55,0.80" \
        --stats "700+|websites built" --badges 2 \
        --field shapes --bg "#5B6BF0,#4553CC" --tilt -3

**For a portfolio board, start with whole pages.** Two to four complete,
uncropped page captures side by side, tilted together in perspective on a soft
field (`--layout pages3 --perspective "22,16"`). Nothing is cropped, so nothing
can be cropped badly - and it beats an elaborate generated collage. Device
mockups (`device-hero`) come second; fragment collages last.

Three rules decide whether a fragment collage reads at all: **lead with the whole hero**,
**compose from whole sections** (`page.png~2`, listed with `--list-sections`)
rather than guessed percentage bands, and **caption it in plain language** for
someone outside the industry. Never number the boards on the image itself.

**Read `references/composition-gallery.md` before building one** — it lists the
archetypes with what each is for, the piece/crop syntax, and the rules that hold
across all of them (bleed on purpose, vary the scale, in-plane rotation only).

**Rotate the archetype every project.** Note the previous project's `--layout`,
`--field` and accent, and pick different ones. Two boards from this skill that
share structure, field and palette mean it was used wrong — the variety is the
deliverable, not a bonus.

**Marketing page beside the product** — for a site with a signed-in app, one
landing page is a thin story. Use `--board` instead: column one is the whole
landing page, the remaining columns stack the app screens, cropped to a common
card aspect and auto-balanced so short columns show more of each screen rather
than ending ragged.

    python3 scripts/page_mockup.py --board "page.png|dash.png,plans.png|inbox.png" \
        --out docs/board.png --size 1280x769 --bg "#FDFDF6,#CBD9A2" --glow "#AFDC3C" \
        --tilt -3 --text-col 0.30 --title "Brand" --headline "Two words|accented." \
        --sub "One supporting line." --pills "Landing page,7 app screens"

Two things separate a board that looks designed from one that looks exported:

- **Never leave it dead straight.** `--tilt -3` rotates the whole board, shadows
  included, as one object. Three to five degrees in-plane; never perspective
  skew, which makes UI unreadable.
- **Composite big, reduce once.** `--supersample 3` builds the whole board at
  3x and reduces at the end. Assembling at final size resamples an already
  downscaled capture a second time — and the tilt rotation resamples it again —
  which is what makes a board look soft when the sources were sharp. Capture at
  DPR 3 for the same reason, and at a *narrower* CSS viewport (1280, not 1440)
  so the UI is physically larger on the finished sheet.
- **One scale per column, not per board.** A full landing page is 2.5x taller
  than it is wide; with a single shared scale it caps every column, and the app
  screens beside it land at ~20% of true size where 14px UI text is under 3px
  tall and no sharpening can rescue it. `--per-column-scale` lets each column
  fill the height on its own terms. Before rendering, do the arithmetic:
  `sheet_width / capture_css_width` is the scale, and under ~25% app UI stops
  being readable — either cut screens or ship a 2x export alongside.
- **Keep the shadows off the backdrop.** On a light background `--shadow 80` is
  plenty; anything heavier muddies the gradient and reads as a drop-shadow
  preset. Blur scales with sheet width automatically.

`--text-col` gives the left share of the tile to a copy panel — brand mark,
two-line headline (`|` splits, later lines take the accent), one supporting
line, and small outline pills. **Pills say what the user gets, not what it was
built with** — "Progress tracking", not "Next.js + Supabase". A stack name means
nothing to the person deciding whether to click. It renders in the pairing you name with
`--font-display` / `--font-text`, so set it to the *site's own* faces. Check the
panel at 100% before shipping: sub-copy and pills are the first things to fall
below readable, and they need more size than they look like they need.

Signed-in routes need a session, and **you must never type the password**. Launch
a real browser the user can sign into — Playwright's `launch_persistent_context`
with `channel="chrome"`, `headless=False`, `device_scale_factor=2` — poll until
the URL leaves `/login`, then capture each route with `full_page=True`. The
profile directory persists, so a second run needs no second login. Do not try to
lift the session cookie out of another browser; it is a live credential.

Capture the page with headless Chrome at DPR 2 —
`--headless --force-device-scale-factor=2 --window-size=1440,4200 --screenshot=…
--virtual-time-budget=9000` — which gives a real file at full resolution. The
browser tool's screenshot is downscaled for viewing and is not a usable source.

Sizes: see the web rows in the table below. Two more rules specific to web:

- The browser frame is the only chrome — do not put a web page inside a phone.
- Keep the capture at device-pixel-ratio 2 or better, or the page text turns to
  mush at tile scale. Capture at the tile's width or wider, never upscale.

## Platform sizes

Full table with current requirements, counts and formats:
`references/platform-specs.md`. Summary of what you must produce:

| Platform | Size to build | Notes |
|---|---|---|
| Android phone | 1080 × 1920 | 2–8 images, 9:16 |
| Android tablet | 1920 × 1080 or 2560 × 1600 | required if the app targets tablets |
| iPhone | 1320 × 2868 | 6.9″ slot — required; all smaller iPhones auto-scale from it |
| iPhone (optional) | 1242 × 2688 | 6.5″ slot — ask the user; render natively, never resized |
| iPad | 2064 × 2752 | 13″ slot; required for iPad-supporting apps |
| macOS | 2880 × 1800 | 16:10; include the window, not a phone frame |
| Website hero (`web-hero`) | 2560 × 1440 | 16:9 landing/README/docs hero |
| Website OG card (`web-og`) | 1200 × 630 | Open Graph, Twitter/X, LinkedIn preview |
| Website square (`web-square`) | 1080 × 1080 | Instagram, carousel, changelog post |
| Website full page (`web-tall`) | 1440 × 2160 | whole-page capture; page reads as shape |

## Device frames

Styles available per tile via `"device_style"`: `phone`, `window`, `macbook`,
`browser`. Web tiles default to `browser`; `"device_h"` caps the frame's height
as a fraction of the tile (0.78 by default for browser frames) so a wide window
cannot overflow a landscape tile.

Draw real device bodies, not outlines — a flat rounded rectangle reads as a
wireframe and cheapens the set. `build_tiles.py` includes an iPhone body with a
titanium rail (gradient with specular bands), black bezel, correct corner radius
and correctly-placed side buttons. For macOS, frame the app in a window with a
title bar, not in a phone.

Where the capture already contains device chrome (Dynamic Island, status bar),
let it come through from the capture rather than drawing over it.

## Files

- `references/art-direction.md` — archetypes, palettes, backgrounds, optional elements
- `references/platform-specs.md` — exact sizes, counts, formats per store
- `references/research.md` — how to research competitor listings first
- `references/pitfalls.md` — failures this skill exists to prevent
- `references/checklist.md` — pre-delivery verification
- `references/composition-gallery.md` — board archetypes, fields, the variety rule
- `scripts/build_tiles.py` — the compositor
- `scripts/page_mockup.py` — whole-page website mockup (sliced columns on a backdrop)
- `scripts/collage.py` — portfolio-style boards (11 archetypes, fields, chips, stats)
