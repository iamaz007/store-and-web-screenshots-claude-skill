# Examples

Real output from this skill, not mockups of it. Every store slot is represented
— phone, tablet and desktop, on both stores — plus the two website treatments,
and each image ships with the config that produced it. The remaining web presets
(`web-og`, `web-square`, `web-tall`) are the same shape as `web-hero` at a
different size.

## Store tiles

| File | Platform | What it shows |
|---|---|---|
| `03-showcase-checkrow.png` | `macos` 2880 × 1800 | `showcase` — benefit check row on top, corner cards over the window |
| `04-direction-mesh.png` | `macos` | Same app, `"background": "mesh"` |
| `05-direction-dots.png` | `macos` | Same app, same captures, `"background": "dots"` |
| `09-ios-calendar-week.png` | `ios` 1320 × 2868 | `hero-center`, `"device_style": "phone"`, card overlapping the device |
| `10-ios-calendar-ask.png` | `ios` | Tile 2 of the same set, card on the opposite side |
| `11-android-subscriptions.png` | `android-phone` 1080 × 1920 | `"device_style": "android"` — matte rail, tighter radius, buttons right only |
| `12-android-spend.png` | `android-phone` | Tile 2 of the same set |
| `13-ipad-dashboard.png` | `ipad` 2064 × 2752 | `showcase`, `"device_style": "tablet"`, dark app UI on a light tile |
| `14-android-tablet-storage.png` | `android-tablet` 1920 × 1080 | `"device_style": "tablet"`, purple mesh, flat icons |

## Website tiles

| File | Platform | What it shows |
|---|---|---|
| `06-web-hero-reverze.png` | `web-hero` 2560 × 1440 | Browser frame with URL pill, dark violet, 3D props |
| `08-board-compound.png` | `page_mockup.py --board` | Whole landing page in column one, seven app screens beside it, `--tilt -3` |
| `15-fullpage-simplelogics.png` | `page_mockup.py --shot` | Whole page — 16,400 px of capture sliced into three columns and angled with `--tilt -4` |

## Configs

| Config | Renders |
|---|---|
| `macos-tiles.json` | a complete five-tile macOS set |
| `ios-tiles.json` | 09, 10 |
| `android-phone-tiles.json` | 11, 12 |
| `ipad-tiles.json` | 13 |
| `android-tablet-tiles.json` | 14 |
| `web-hero-reverze.json` | 06 |

## Two things these are meant to prove

**No house style.** Five different products, one compositor. The homework app is
violet mesh with a punchy grotesque; the calendar is pale blue with flat icons;
the subscription tracker is lime with a *serif* display face because
`--suggest-fonts` puts finance in the trustworthy register; the storage cleaner
is purple on a mesh wash. Nothing is shared between them but the code.

**One brand across every slot.** Tiles 11–12 (Android phone) and tile 13 (iPad)
are the same product — same lime accent, same serif display face, same type
scale, three slots apart. That is the checklist item *"one palette and one type
scale across every tile and every platform"*, and it is why a set built for one
store does not have to be redesigned for the next.

## Caveats worth reading before copying

- **The Android tiles were built from iPhone captures.** `"shot_crop"` trims the
  Dynamic Island off the top, which is the only reason they hold up. For a real
  Play listing, capture on Android — a visible iOS status bar inside a Pixel
  body is what a reviewer notices first.
- **Tile 13's capture is landscape in a portrait slot.** That leaves margin at
  the bottom. Apple accepts an iPad set in either orientation; if your captures
  are landscape, a landscape set is usually the better-looking answer.
- **PNGs here are downscaled for the README** (720–1440 px wide). Real output is
  at the full slot size listed above.
- **Tiles 06 and 15 are the two website answers.** 06 crops a section into a
  browser frame; 15 slices the whole page into columns. Which one you want is
  the first intake question in `SKILL.md` — get it wrong and the capture has to
  be redone, because a whole-page capture and a section capture are not the
  same file.

## Running them

Each config expects the source captures it was written against, which are the
apps' and sites' own UI and are not distributed here. Point `shot` at your own
captures and it runs:

```bash
# store tiles
python3 ../scripts/build_tiles.py --platform ios \
    --config ios-tiles.json --shots ./your-captures --out ./designed

# the 6.5" iPhone slot needs no new config — just a different preset
python3 ../scripts/build_tiles.py --platform ios-65 \
    --config ios-tiles.json --shots ./your-captures --out ./designed-65

# website tiles — capture first, at DPR 2
chrome --headless --force-device-scale-factor=2 --window-size=1440,3600 \
    --screenshot=captures/site.png --virtual-time-budget=12000 https://example.com

python3 ../scripts/build_tiles.py --platform web-hero \
    --config web-hero-reverze.json --shots ./captures --out ./designed

# whole page instead of a framed section — no config file, all flags
python3 ../scripts/page_mockup.py --shot captures/site.png --out designed/page.png \
    --size 1440x900 --bg "#F7FAFF,#C3DCF5" --glow "#0697E6" --cols 3 \
    --gap 42 --stagger 24 --angle 145 --shadow 95 --margin 26 --tilt -4
```

Treat these as shapes to copy, not themes to reuse. Every product gets its own
art direction — see `references/art-direction.md`.
