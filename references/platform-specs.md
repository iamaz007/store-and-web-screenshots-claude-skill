# Platform specifications

Verify against the store's own documentation when a listing is about to be
submitted — Apple and Google both change requirements. Sizes below are current
as of the 2025 simplifications.

## Google Play

Uploaded in Play Console under *Store listing → Graphics*.

| Asset | Size | Rules |
|---|---|---|
| Phone screenshots | **1080 × 1920** (9:16) | 2–8 images. Each side 320–3840 px. 16:9 or 9:16. |
| 7″ tablet | **1920 × 1080** or 1080 × 1920 | Up to 8. Required if the app is distributed to tablets. |
| 10″ tablet | **2560 × 1600** or 1920 × 1080 | Up to 8. |
| Feature graphic | **1024 × 500** | Required. No transparency. Appears in Play's promotional surfaces. |
| App icon | **512 × 512** | 32-bit PNG, alpha allowed. |

- Format: PNG or JPEG, max 8 MB per screenshot.
- The first 2–3 screenshots appear without scrolling — put the strongest claims there.
- Play shows tablet screenshots to tablet users; missing them lowers the tablet
  quality score and can suppress tablet recommendations.
- **Landscape tiles are shown wider in the grid** — for tablets, landscape usually
  outperforms portrait.

## Apple App Store

Uploaded in App Store Connect per localization. Max **10** per size.

| Device slot | Portrait | Landscape |
|---|---|---|
| iPhone **6.9″** (16 Pro Max / 15 Pro Max) | **1320 × 2868** or 1290 × 2796 | 2868 × 1320 / 2796 × 1290 |
| iPhone **6.5″** (optional) | 1242 × 2688 or 1284 × 2778 | 2688 × 1242 / 2778 × 1284 |
| iPad **13″** | **2064 × 2752** or 2048 × 2732 | 2752 × 2064 / 2732 × 2048 |
| iPad 12.9″ (legacy) | 2048 × 2732 | 2732 × 2048 |

- App Store Connect still shows a **6.5″ slot** alongside 6.9″. It is optional -
  the panel offers "Keep using 6.9″ Display" - but filling it gives you art sized
  for that slot rather than Apple's automatic downscale. **Ask the user whether
  they want it** whenever building for iOS.
- 6.9″ and 6.5″ have **different aspect ratios** (0.4603 vs 0.4620). Never resize
  one set into the other - render each natively with `--platform ios` and
  `--platform ios-65`, or the app UI is distorted.
- **Only 6.9″ iPhone and 13″ iPad are required.** Apple auto-scales them down to
  every smaller device, so building those two sizes covers the whole catalogue.
- Format: PNG or JPEG, **RGB, no alpha channel** — an alpha channel is a rejection
  cause. Always `convert("RGB")` before saving.
- Apple rejects screenshots that misrepresent the app, show a device frame that
  imitates Apple marketing chrome, or display a competing platform's branding.
- First 3 screenshots appear in search results; the rest need a tap.
- Do not show a status bar with obviously fake carrier/battery states that
  contradict the device being framed.

## macOS

| Asset | Size |
|---|---|
| Screenshots | **2880 × 1800**, 2560 × 1600, 1440 × 900 or 1280 × 800 |

- 16:10 only. Max 10 images.
- Show the app **in a macOS window** — title bar, traffic-light controls, real
  macOS chrome. Never in a phone frame.
- Desktop screenshots are viewed larger than mobile ones, so dense UI is an asset
  rather than a liability; you can let more of the interface show.
- RGB, no alpha, PNG or JPEG.

## Website / web app

No store validates these, so the constraint is the surface they get posted to
rather than a review guideline.

| Preset | Size | Used for |
|---|---|---|
| `web-hero` | **2560 × 1440** | landing page hero, README header, docs banner |
| `web-og` | **1200 × 630** | Open Graph / Twitter / LinkedIn link preview |
| `web-square` | **1080 × 1080** | Instagram, carousels, changelog and release posts |
| `web-tall` | **1440 × 2160** | whole-page capture, feature walkthrough column |

- The frame is a **browser window** (`"device_style": "browser"`, the default for
  these presets) — traffic lights and a URL pill. Pass the real address as
  `"url"`; a wrong or placeholder URL on a public tile is a credibility leak.
- OG cards are rendered small in every feed. One headline, ≤ 4 words, and either
  a cropped section of the page or no capture at all — a whole page at 1200 × 630
  is illegible.
- Capture at DPR 2 or higher, at or above the tile's width. Never upscale a 1×
  capture; page text is the first thing to fall apart.
- Full-page captures: crop with `"shot_crop": [l, t, r, b]` to the section that
  carries the message. Cropping preserves the aspect ratio; scaling one axis
  never happens.
- Alpha is fine here (unlike the stores) but PNG-24 without alpha travels better
  through link-preview scrapers.
- Check the captured page for anything that should not be public: real customer
  names, internal email addresses, staging banners, debug toolbars, dev-only
  feature flags. Ask before shipping a tile that contains real user data.

## Capturing sources

- **iOS / iPadOS** — Simulator at the exact target device (iPhone 16 Pro Max,
  iPad Pro 13″) gives native pixel dimensions, so tiles composite 1:1 with no
  resampling of app UI.
- **Android** — emulator or device at 1080 × 1920 (phone) and 2560 × 1600 (tablet).
- **Web** — the browser preview tools (`preview_start` + `computer` screenshot),
  or a headless capture at DPR 2. Use `resize_window` to set the viewport to the
  section's natural width before capturing; dismiss cookie banners, chat widgets
  and dev overlays first.
- If a tablet capture is letterboxed with black bars, the app is not laid out for
  that width. Crop the bars for the tile, and tell the user — it is a product bug
  that store reviewers and users will also see.
- Normalise status bars if the user wants polish (Apple convention is 9:41, full
  signal, full battery). Not required, but it is what premium listings do.
