# Pre-delivery checklist

Run every item before handing a set over.

## Technical

- [ ] Exact pixel dimensions for the target slot (`platform-specs.md`)
- [ ] RGB, **no alpha channel** (Apple rejects alpha)
- [ ] PNG or JPEG, under the store's per-file size limit
- [ ] Count within the store's min/max for that slot
- [ ] iOS: 6.5″ set rendered natively if requested — not resized from 6.9″
- [ ] Portrait/landscape consistent across the set

## App UI fidelity

- [ ] Screen content matches the source capture pixel for pixel
- [ ] Status bar present and unaltered (or deliberately normalised)
- [ ] Row spacing, margins and type inside the app unchanged
- [ ] Aspect ratio of the capture preserved — no stretching in either axis
- [ ] The screen shown is the feature the headline claims

## Copy

- [ ] Headlines 2–3 words
- [ ] Every string is a user benefit, not app data or a UI label
- [ ] Spelling and capitalisation correct — no invented words
- [ ] No internal codes, debug values or wording unsuitable for a public store
- [ ] No unverified claims (trial length, price, ratings, user counts)
- [ ] Numbers match the product's authoritative source

## Design

- [ ] Art direction derived from THIS app - not carried over from a past project
- [ ] Typeface chosen via `--suggest-fonts`, not inherited from the last project
- [ ] Prop style (`none`/`flat`/`3d`) matches the app's register, and
      `icon_style` agrees with it
- [ ] Props sit clear of the device edges and the laptop base
- [ ] On a light background: halo and swirls off, every shadow/glow value
      dialled to roughly a third of its dark-background setting
- [ ] No grey haze anywhere - each shadow seats an object, none float free
- [ ] Accent traceable to the app's own brand/icon
- [ ] Background style suits the category (motifs only when meaningful)
- [ ] Type undistorted; text in a column shares one left margin
- [ ] Accent word coloured and marked consistently across the set
- [ ] Device flat, 3–5° rotation maximum, no perspective skew
- [ ] Card overlaps the device edge, alternating sides across the set
- [ ] Background motif continues across tiles as one strip
- [ ] One palette and one type scale across every tile and every platform

## Thumbnail test

- [ ] Scale a tile to ~200 px wide. Headline still readable?
- [ ] Card's big line still readable?
- [ ] Set still distinguishable from competitors at that size?

## Honesty

- [ ] Nothing shown that the app does not actually do
- [ ] Any product defect discovered while capturing (letterboxing, broken layout,
      placeholder content) reported to the user rather than only concealed
