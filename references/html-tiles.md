# Poster tiles with real UI - the `html_tiles.py` workflow

The level of finish that actually gets approved. A bold brand field, a huge title,
a **straight** device holding a **real** capture, one real UI card lifted out of
it, props that match the screen, and faint subject doodles for texture. Every
pixel of app UI is the app's own - nothing is redrawn by a model.

Use this for every store surface: Android phone, Android tablet, iPhone 6.9″ and
6.5″, iPad 13″, macOS. Same design system, native canvas per platform.

## 0. Rules learned the hard way (read before anything)

1. **Fill the app with data before capturing anything.** Empty states,
   "No activity yet", "0 Day Streak" are never a store screenshot. Solve real
   questions, run a chat, finish a quiz, generate flashcards, set a language.
   Capturing an empty screen - even "just to check" - reads as sloppy.
2. **Tablets and iPads are always landscape.** Never portrait.
3. **Devices are straight.** No tilt, no 3D perspective, no diagonal floating.
   (At most tile 1 may carry a slight in-plane angle; the rest are straight.)
4. **Use the right device for the store.** iPhone frames only on the App Store,
   Pixel-style punch-hole frames only on Google Play. An iPhone on a Play listing
   (or vice versa) is a rejection risk and the user will notice immediately.
5. **Never use AI generation for the UI.** Image models redraw the screen and
   invent details (a timestamp changed to "Yesterday", warped text). Real
   captures composited in HTML only.
6. **Plain words.** No slang or "marketing-AI" phrasing ("Ace it", "Level up",
   "Supercharge"). A student who doesn't speak idiomatic English must understand
   every title. "Scan it. Solve it." beats "Snap it. Ace it."
7. **Measure crops, never guess.** A guessed rectangle slices the card's own
   rounded corners and border. Use `html_tiles.py measure`.
8. **One lifted card per tile - never a magnifier circle.** Circles look like
   a template. Lift the real card, a little wider than the device, sitting over
   the exact place it lives in the app.
9. **Don't duplicate.** If the lifted card is the same thing already fully
   visible in the phone, the tile reads as repetition - pick a screen where the
   card adds emphasis, or show a different screen in the device.
10. **Doodles differ per tile.** Each tile gets its own subject bank (math,
    physics, chemistry, biology, history, languages, English...). Never the same
    equations on every tile.
11. **Props match the screen.** Scan → pencil/100; quiz → trophy/leaf; tutor →
    speech bubble/bulb; flashcards → brain/card index; languages → globe/bubble;
    light/dark → sun/moon. Max 2 per tile, placed at the upper corners beside
    the device.
12. **Titles are huge and bold.** Weight 900, highlight word in the accent
    colour. The engine auto-shrinks a title only if it would clip.
13. **Light/dark tile = two devices**, light in front-left, dark overlapping
    front-right. Never a split screen through one device (reads as "pasted").
14. **Check props resolve.** A 404 emoji renders as an empty outlined box.
    Run `html_tiles.py check` - e.g. "Globe showing Europe-Africa" does not
    exist in Fluent; use "Globe with meridians".
15. **Background and theme stay constant across the set**; only props,
    doodles, title and screen change. iOS may use a different field from
    Android, but within one platform it never changes.
16. **Pick fonts per app - never default to the same face.** The title font,
    and the handwritten doodle font, come from the app's brand and category:
    a playful rounded face for a kids/study app, an engineered grotesk for a
    security or dev tool, a didone or editorial serif for luxury or reading,
    a slab for utilities, a condensed display for fitness/sport. Run
    `python3 scripts/build_tiles.py --suggest-fonts "what the app is"`, read
    the app's own UI/website fonts, and set `theme.font` / `theme.hand_font`
    to Google Fonts families (e.g. `"Bricolage Grotesque"`, `"Fraunces"`,
    `"Space Grotesk"`, `"Nunito"`, `"Archivo Black"`; hand fonts like
    `"Caveat"`, `"Kalam"`, `"Patrick Hand"`, `"Gloria Hallelujah"`). If the
    last project used a face, choose a different one. State which fonts you
    chose and why.
17. **Keep every variant.** Save new versions next to old ones
    (`ios-iphone-v2/`, `-v3/`...); never overwrite a set the user reviewed.

## 1. Capture (per platform, with data)

| Platform | Device | Capture command |
|---|---|---|
| Android phone | emulator 1080×2400 | `adb exec-out screencap -p > shot.png` |
| Android tablet | emulator 2560×1600 landscape | same |
| iPhone 6.9″ | iPhone 17 Pro Max sim (1320×2868) | `xcrun simctl io booted screenshot shot.png` |
| iPad 13″ | iPad Pro 13″ sim, rotate to landscape (⌘→ in Simulator) | same, then `Image.rotate(-90, expand=True)` → 2752×2064 |
| macOS | the app window | `screencapture -l <windowid> shot.png` |

Clean status bars first:
- iOS: `xcrun simctl status_bar booted override --time 9:41 --batteryState discharging --batteryLevel 100 --wifiBars 3 --cellularBars 4`
- Android: SystemUI demo mode (`settings put global sysui_demo_allowed 1`, then
  `am broadcast -a com.android.systemui.demo -e command clock -e hhmm 0941`, battery 100, notifications hidden). Exit demo mode when done.

Automation notes:
- Typing into iOS sims via `simctl`/MCP drops characters; use
  `osascript -e 'tell application "System Events" to keystroke "…"'` with
  Simulator frontmost, and ⌘A + delete to clear a field.
- In landscape iPad, simulator tap coordinates stay in *portrait* device points:
  for a point (X, Y) in the landscape view (points), tap `(Y, 1376 − X)`.
- Grant permissions up front (`simctl privacy booted grant photos <bundle>`),
  and put sample homework files in the sim's `File Provider Storage`.
- Unlock paid features with the app's own test switch (dummy plans / sandbox),
  never a real purchase.
- Capture both light and dark Home, and one non-English Home for a language tile.

Save raw captures under `docs/screenshots/<platform>/`.

## 2. Research before designing

Pull 50-100+ listings (same category and adjacent ones) - iTunes Search API for
App Store (`itunes.apple.com/search?term=…&entity=software`), Play store pages
for Google Play. Save contact sheets to `docs/store-research/`, and save the
10-16 strongest full-size sets in `docs/store-research/references/<app>/`
with an `index.html` overview. **Show the references to the user**, and when
they point at one ("check how Headspace highlights"), copy only the aspect they
named - not the colours unless asked.

## 3. Config and build

```json
{
  "platform": "ios-69",
  "out": "../store-screenshots/ios-iphone",
  "theme": {"accent": "#ffd84d", "font": "Bricolage Grotesque", "hand_font": "Kalam"},
  "tiles": [
    {"name": "01_snap_solve", "title": "Snap. Solve.<br><b>Learn.</b>",
     "shot": "ios/03_answer.png", "card": [48, 1131, 1224, 246], "doodles": "math",
     "props": [{"emoji": "Pencil", "x": -30, "y": 560, "w": 230, "rot": -20},
               {"emoji": "Hundred points", "x": 1080, "y": 600, "w": 230}]},
    {"name": "07_light_dark", "title": "Light or <b>Dark</b>",
     "split": ["ios/01_home.png", "ios/01_home_dark.png"], "doodles": "english",
     "props": [{"emoji": "Sun", "x": -20, "y": 590, "w": 240},
               {"emoji": "Crescent moon", "x": 1090, "y": 580, "w": 220}]}
  ]
}
```

```bash
python3 scripts/html_tiles.py measure ios/03_answer.png 400 1200   # → [48,1131,1224,246]
python3 scripts/html_tiles.py check  ios.json
python3 scripts/html_tiles.py build  ios.json
```

- Phones: split the title with `<br>` (two lines, much larger). Tablets/mac:
  one line.
- `card_zoom` (default 1.28 phones, 1.3 tablets) controls how much bigger the
  lifted card is than it appears in the device.
- Props: any Fluent 3D emoji name (`Trophy`, `Brain`, `Light bulb`, `Rocket`,
  `Sparkles`, `Graduation cap`, `Check mark button`, `Herb`, `Speech balloon`,
  `Card index dividers`, `Party popper`, `Chart increasing`, `Sun`,
  `Crescent moon`, `Globe with meridians`...) or `{"src": "local.png"}`.
- Doodle banks: `math physics chemistry biology history languages english code
  finance`, or pass your own list.
- **Always set `theme.font` and `theme.hand_font`** (see rule 16) - the
  engine warns when they're left at the Rubik/Caveat fallback.
- Theme defaults to a dark violet field; override `bg`, `accent`, `title`,
  `doodle`, `font` from the app's own brand. **Derive from the brand - don't
  reuse another app's look.**
- One design, every size: build the same tiles with `ios-69`, `ios-65`,
  `ipad`, `android-phone`, `android-tablet`, `mac` configs pointing at that
  platform's own captures. 6.5″ is rendered natively, never resized from 6.9″.
- The HTML for every tile is written next to its PNG - edit copy there and
  re-run for a seconds-long revision loop.

## 4. Intro / welcome tile (no device)

When asked for a pure call-to-action opener: brand mark + name, one-line hook
("Stuck on homework?"), a 2-line plain-word title, a **visual before→after of
the problem being solved** (e.g. a notebook page with a red ✗ and "??" → an
arrow → the solved page with a ✓ and grade stamp), subject chips, and a pill
"button" ("📸 Scan your homework"). Same background as the set. No mockup.

## 5. Feature graphic (Play, 1024×500)

Same workflow, one canvas: problem on the left (scanned page with brackets and
a scan line), dashed arrow, straight device with the real answer screen and the
lifted answer card on the right, headline + chips on the left. Keep the Play
video-button safe zone (centre) free of text.

## 6. Verify

- Exact pixel size, RGB (no alpha) - the engine asserts both.
- Zoom every lifted card: corners intact, no stray page background.
- No broken prop boxes, no clipped title, no duplicated card.
- Every screen full of real data; no debug/placeholder strings.
- Report untranslated strings or bugs you saw in the captures to the user.
