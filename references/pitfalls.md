# Pitfalls

Every item here is a failure that actually occurred on a real store-screenshot
project. They cost multiple rounds of rework each.

## 1. Letting an image generator draw the app UI

**Symptom:** invented empty gaps in the interface, a tablet layout appearing
inside a phone frame, a missing status bar, horizontally stretched UI, restyled
labels, altered row spacing.

**Cause:** image models regenerate a reference image; they never composite it.
There is no prompt wording that makes this reliable.

**Fix:** composite locally (`scripts/build_tiles.py`). Restrict image generation
to background art containing no UI and no text.

**If you must use a generated tile containing UI:** compare the status bar,
row spacing and aspect ratio against the source capture before accepting it.

## 2. Stretched or distorted type

**Symptom:** headline letterforms squashed or spread to fill a width.

**Fix:** render text with a real font at a natural width. Never scale a text
layer non-uniformly. Never fake weight by outlining. Give the headline and the
support card **one shared left margin** so they form a single alignment column.

## 3. Copying app data as marketing copy

**Symptom:** a headline or card reading something like `100% @ 8 pts` — real data
from the app that means nothing to a prospective user.

**Fix:** every string on a tile answers "what does this do for me?". Pull the
phrasing from the product's own marketing site where one exists. Feature labels
lifted from UI are the single most common way a set reads as amateur.

## 4. Publishing internal wording

**Symptom:** anatomical terms, internal hunt/SKU codes, debug values or
placeholder content visible on a public tile.

**Fix:** review every visible string in the capture, not just the copy you wrote.
Crop or choose a different screen when the app legitimately shows wording that is
wrong for a public storefront.

## 5. 3D perspective skew on the device

**Symptom:** "weird angle, can't understand anything" — the device tapers, the UI
warps, and text inside becomes unreadable.

**Fix:** flat in-plane rotation of 3–5° only. No perspective transform, no taper,
no fake depth. Upright is always safe.

## 6. Stacking everything in a column

**Symptom:** headline, then card, then device, all centred down the tile — reads
as a slide, not a designed screenshot.

**Fix:** headline top, device centre/lower cropped by the edge, card floating
**over** the device edge so it reads as a callout pulled out of the app.

## 7. Treating tiles as six independent images

**Symptom:** the set looks inconsistent when scrolled in the store grid.

**Fix:** generate the background motif once at full strip width, then slice per
tile so it genuinely continues. Keep one palette, one type scale, one card style
across the whole set — and across platforms, so iOS and Android read as one brand.

## 8. Hiding a product bug instead of reporting it

**Symptom:** tablet captures arrive letterboxed with black bars because the app
has no tablet layout. Cropping them makes the tiles look fine while the actual
tablet experience stays broken.

**Fix:** crop for the tile *and* tell the user plainly. Store reviewers and users
see what the tiles hide, and platform quality guidelines check for it.

## 9. Wrong pixel dimensions

**Symptom:** upload rejected, or the store rescales and softens the whole set.

**Fix:** build at the exact slot size (`references/platform-specs.md`). Prefer
captures already at native device resolution so app UI composites 1:1 without
resampling. Save RGB with no alpha — Apple rejects alpha channels.

## 10. Reusing the last project's art direction

**Symptom:** a productivity app comes out looking like the hunting app built
before it — same background motif, same accent, same composition. The user's
words were: "it generates same UI like we designed for X, this is wrong, I need
creativity based on app nature".

**Cause:** treating one project's design tokens as the tool's defaults.

**Fix:** derive palette from the app's own icon (`--palette-from`), pick a
background and archetype that suit its category, and **ask the user** about
optional elements (gradient, props, feature list, CTA) before building. See
`references/art-direction.md`. The compositor has no house style — if the output
looks familiar, the config was lazy.

## 11. Unverified attachments and silent substitution

**Symptom:** a tool renders using a stale or wrong source file and the output
looks plausible but shows the wrong screen.

**Fix:** confirm the intended source file is the one actually in use before every
render, and check the output against the source. Never accept "close enough" on
app UI — it is the one part of the tile that must be literally true.

## 12. Shipping every project in the same typeface

**Symptom:** a security tool, a recipe app and a disk cleaner all arrive set in
the same sans. Nothing is technically wrong and the whole set reads generic.

**Cause:** treating the compositor's fallback face as a default.

**Fix:** run `--suggest-fonts "<what the app is>"` before writing the config and
use the pairing it returns. `references/art-direction.md` has the category
table. The fallback face is a fallback, not a house style.

## 13. Drawing translucent fills straight onto an RGBA layer

**Symptom:** a glossy prop or icon tile renders with a see-through top half, as
if the shape were torn.

**Cause:** `ImageDraw` REPLACES the alpha channel with the fill's alpha rather
than blending. A specular highlight drawn with `fill=(255,255,255,46)` punches
a 46-alpha hole through the tile it was meant to sit on.

**Fix:** draw the highlight on its own layer, multiply its alpha by the body's
alpha, then `alpha_composite` it (`add_sheen` in `build_tiles.py`). The same
trap applies to any "cut a hole" fill of `(0,0,0,0)`.

## 14. Rotating a layer without expand=True

**Symptom:** a rotated prop comes out sheared, with its corners clipped off.

**Fix:** `layer.rotate(angle, resample=Image.BICUBIC, expand=True)`, then centre
the expanded layer on the intended point.

## 15. Faking a 3D hero object by smearing the silhouette

**Symptom:** the user's words were "wtf is this? is like stretched from one side
instead of 3d". An app icon meant to read as a tilted solid comes out as a
lumpy diagonal smudge.

**Cause:** stacking offset, darkened copies of the silhouette behind the face.
It is the obvious shortcut and it never reads as an object.

**Fix:** `solid3d()` in `build_tiles.py`. Project the artwork's rounded outline
at z=0 and at z=-depth, then fill the region between them. Three things each
cost a round of rework if you get them wrong:

1. **Extrude the rounded outline, not the bounding square.** Square side faces
   leave dark corners sticking out past a squircle icon.
2. **Fill the convex hull of both rims, not per-edge quads.** For a convex solid
   the hull *is* the silhouette. Per-quad back-face culling flips winding at the
   corners and sprays stray triangular fins.
3. **Keep the focal length long (8-12).** Under a short focal the back face
   shrinks toward the vanishing point about as fast as the yaw displaces it
   sideways, so the side wall collapses to a hairline and the object reads flat
   again. Let `depth` and `yaw` create the thickness, not the perspective.

This is the one place perspective is allowed. Pitfall #5 still stands for any
tile showing app UI.

## 16. The accent underline drawn through the line below it

**Symptom:** the hand-drawn stroke under the accent word runs straight across
the sub-line, as if someone had crossed the sentence out.

**Cause:** `underline` draws a stroke of **fixed pixel height** regardless of the
type size, but the line advance is a fraction of the type size. At any headline
below ~470px the stroke is taller than the gap, so it lands on whatever comes
next.

**Fix:** `headline()` now clears `UNDERLINE_CLEARANCE` past the stroke before
returning. The general lesson: any drawing helper whose geometry does not scale
with its type size will collide with something eventually — advance past the
**drawn extent**, not past a multiple of the font size.

## 17. The wrong slab body for the store

**Symptom:** an Android tile that reads as "an iPhone with the wrong icons", or
an iPad tile whose corners are so round the body looks like a lozenge.

**Cause:** one phone body reused for every slot. A polished titanium rail and a
three-button left-hand cluster are iPhone tells; a 14.8%-of-width corner radius
is right for a phone and grotesque on a 13" tablet.

**Fix:** `"device_style"` — `phone`, `android` (matte rail, right-side buttons,
tighter radius) or `tablet` (thin uniform rail, no buttons, 3.8% radius).

**And crop the status bar when re-purposing captures across platforms.** An iOS
Dynamic Island inside a Pixel body is the first thing a Play reviewer notices.
`"shot_crop": [0, 0.052, 1, 1]` removes it. For a listing that ships, capture on
the platform you are listing on.

## 18. Chasing a render Pillow cannot produce

**Symptom:** round after round polishing a fake-3D hero object that still reads
as cardboard next to the reference.

**Cause:** the reference was a real 3D render - lighting, bevels, reflections,
material. `solid3d()` gives correct geometry with a flat-shaded side wall. It is
a decent fallback and it will never match a render.

**Fix:** decide early which of these you are doing.
1. **Composite a real render.** Have the user supply the object as a transparent
   PNG from a 3D tool or an image generator. This is within the rules - it is
   object art containing no UI and no text - and it is the only route that
   actually matches a reference like that.
2. **Drop the hero object.** Often the better answer anyway; see
   `references/research.md` on category conventions.
3. **Use `solid3d()` knowingly**, as a fallback, having told the user it will
   not match a render.

Say which one you are doing before spending a round on it.
