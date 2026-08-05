#!/usr/bin/env python3
"""Typeface registry and category-aware font advice for store tiles.

Two sources, one lookup:

* **Google Fonts** - fetched on demand from the official `google/fonts` repo
  into `assets/fonts/`, cached thereafter. Most are variable fonts, so one file
  covers every weight via `set_variation_by_axes`.
* **macOS system fonts** - always present, used offline and as a fallback.

The point of this module is that a set should NOT default to one house face.
`advise()` maps what an app *is* to a pairing that suits it, with a reason, so
a security tool and a recipe app do not ship the same typography.
"""
import os
import urllib.request

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")
_RAW = "https://raw.githubusercontent.com/google/fonts/main/ofl/{d}/{f}"

ROLES = ("heavy", "demi", "medium", "regular")


def _g(dirname, filename, weights, tags, note, caps=False):
    """Variable Google family: one file, weights set on the wght axis."""
    return dict(kind="google", files={filename: _RAW.format(d=dirname, f=filename)},
                roles={r: (filename, w) for r, w in zip(ROLES, weights)},
                tags=tags, note=note, caps=caps)


# --------------------------------------------------------------- the registry

GOOGLE = {
    # ---- geometric sans: modern consumer products
    "outfit": _g("outfit", "Outfit[wght].ttf", (800, 600, 500, 400),
                 "consumer lifestyle fintech shopping social travel booking modern friendly",
                 "Geometric and even-toned. Reads modern and approachable without "
                 "being childish. Safe when the product is mainstream consumer."),
    "poppins": dict(kind="google", files={
        f"Poppins-{w}.ttf": _RAW.format(d="poppins", f=f"Poppins-{w}.ttf")
        for w in ("ExtraBold", "SemiBold", "Medium", "Regular")},
        roles={"heavy": ("Poppins-ExtraBold.ttf", None), "demi": ("Poppins-SemiBold.ttf", None),
               "medium": ("Poppins-Medium.ttf", None), "regular": ("Poppins-Regular.ttf", None)},
        tags="beauty food travel ecommerce retail fashion wellness lifestyle friendly round",
        note="Monoline geometric with circular bowls. Warm and popular - great "
             "for lifestyle and retail, too soft for anything technical.", caps=False),

    # ---- engineered sans: tools, data, infrastructure
    "manrope": _g("manrope", "Manrope[wght].ttf", (800, 700, 500, 400),
                  "productivity saas developer utility cleaner storage system tool "
                  "dashboard crisp modern neutral",
                  "Semi-geometric with tight, confident forms. Precise without "
                  "feeling cold - the right register for utilities and SaaS."),
    "inter": _g("inter", "Inter[opsz,wght].ttf", (800, 600, 500, 400),
                "dashboard analytics fintech developer data interface neutral ui default",
                "Designed for screens; the most neutral option here. Best as the "
                "TEXT half of a pairing when the display face carries character."),
    "ibm-plex-sans": _g("ibmplexsans", "IBMPlexSans[wdth,wght].ttf", (700, 600, 500, 400),
                        "enterprise security privacy vpn backup infrastructure b2b "
                        "engineering serious institutional",
                        "Engineered and slightly mechanical. Signals rigour - good "
                        "for security, backup, infrastructure and B2B."),
    "space-grotesk": _g("spacegrotesk", "SpaceGrotesk[wght].ttf", (700, 600, 500, 400),
                        "ai crypto web3 developer technical experimental startup "
                        "futuristic quirky",
                        "Grotesque with odd, memorable details. Reads technical and "
                        "current - AI, crypto, dev tools. Distinctive, so use sparingly."),

    # ---- grotesques with weight: utility and news
    "archivo": _g("archivo", "Archivo[wdth,wght].ttf", (800, 600, 500, 400),
                  "news sports utility tool scanner cleaner bold punchy editorial "
                  "impact strong",
                  "Gets genuinely heavy without collapsing, so short headlines hit "
                  "hard at thumbnail size. Strong choice for punchy utility tiles."),
    "bebas-neue": dict(kind="google", files={
        "BebasNeue-Regular.ttf": _RAW.format(d="bebasneue", f="BebasNeue-Regular.ttf")},
        roles={r: ("BebasNeue-Regular.ttf", None) for r in ROLES},
        tags="fitness gym sports events music streaming poster display bold caps",
        note="Condensed all-caps display. Enormous presence in a small space, but "
             "DISPLAY ONLY - pair it with a separate text face.", caps=True),

    # ---- humanist and rounded: people-facing, calm
    "rubik": _g("rubik", "Rubik[wght].ttf", (700, 600, 500, 400),
                "kids family health habit wellness meditation fitness education "
                "warm rounded friendly approachable",
                "Slightly rounded corners take the edge off. Warm and calm - health, "
                "habit, kids and wellness apps."),
    "work-sans": _g("worksans", "WorkSans[wght].ttf", (700, 600, 500, 400),
                    "education government civic documents accessibility reading "
                    "clear plain legible",
                    "Humanist and unusually legible at small sizes. Right when "
                    "clarity matters more than personality."),

    # ---- serifs: premium, editorial, considered
    "playfair-display": _g("playfairdisplay", "PlayfairDisplay[wght].ttf",
                           (800, 600, 500, 400),
                           "luxury fashion jewellery realestate hotel wedding premium "
                           "elegant editorial high-contrast",
                           "High-contrast didone. Expensive and editorial - luxury, "
                           "fashion, property. Needs generous size to breathe."),
    "fraunces": _g("fraunces", "Fraunces[SOFT,WONK,opsz,wght].ttf", (800, 600, 500, 400),
                   "food recipe craft indie coffee editorial magazine playful "
                   "characterful soft",
                   "Soft, wonky old-style serif with real personality. Craft food, "
                   "indie products, anything that should feel made by humans."),
    "lora": _g("lora", "Lora[wght].ttf", (700, 600, 500, 400),
               "reading journaling books writing publishing notes calm literary",
               "Comfortable reading serif with brushed contrast. Journals, readers "
               "and writing tools."),
    "source-serif-4": _g("sourceserif4", "SourceSerif4[opsz,wght].ttf",
                         (700, 600, 500, 400),
                         "finance legal insurance banking investing longform "
                         "trustworthy institutional serious",
                         "Sturdy, unfussy serif. Reads trustworthy and grown-up - "
                         "finance, legal and insurance."),
}

_S = "/System/Library/Fonts/"
_X = _S + "Supplemental/"


def _m(files, tags, note):
    return dict(kind="local", files={}, roles=files, tags=tags, note=note, caps=False)


# Always available - no network. Use when offline or when a fetch fails.
LOCAL = {
    "avenir-next": _m({"heavy": (_S + "Avenir Next.ttc", 8), "demi": (_S + "Avenir Next.ttc", 2),
                       "medium": (_S + "Avenir Next.ttc", 5), "regular": (_S + "Avenir Next.ttc", 7)},
                      "neutral fallback offline general",
                      "Stock macOS geometric sans. The offline fallback."),
    "helvetica-neue": _m({"heavy": (_S + "HelveticaNeue.ttc", 1), "demi": (_S + "HelveticaNeue.ttc", 10),
                          "medium": (_S + "HelveticaNeue.ttc", 10), "regular": (_S + "HelveticaNeue.ttc", 0)},
                         "neutral swiss offline general",
                         "Stock neutral grotesque."),
    "futura": _m({"heavy": (_X + "Futura.ttc", 2), "demi": (_X + "Futura.ttc", 2),
                  "medium": (_X + "Futura.ttc", 0), "regular": (_X + "Futura.ttc", 0)},
                 "fashion travel lifestyle geometric offline",
                 "Stock geometric with strong character."),
    "didot": _m({"heavy": (_X + "Didot.ttc", 2), "demi": (_X + "Didot.ttc", 2),
                 "medium": (_X + "Didot.ttc", 0), "regular": (_X + "Didot.ttc", 0)},
                "luxury fashion premium editorial offline",
                "Stock high-contrast serif."),
    "georgia": _m({"heavy": (_X + "Georgia Bold.ttf", 0), "demi": (_X + "Georgia Bold.ttf", 0),
                   "medium": (_X + "Georgia.ttf", 0), "regular": (_X + "Georgia.ttf", 0)},
                  "reading publishing offline serif",
                  "Stock screen serif."),
}

ALL = dict(LOCAL)
ALL.update(GOOGLE)


# ------------------------------------------------------------------- fetching

def ensure(name, quiet=False):
    """Download a Google family into the cache if it is not already there."""
    spec = ALL.get(name)
    if not spec or spec["kind"] != "google":
        return
    os.makedirs(FONT_DIR, exist_ok=True)
    for fn, url in spec["files"].items():
        dest = os.path.join(FONT_DIR, fn)
        if os.path.exists(dest) and os.path.getsize(dest) > 4096:
            continue
        if not quiet:
            print(f"  fetching {name}: {fn}")
        urllib.request.urlretrieve(url.replace("[", "%5B").replace("]", "%5D"), dest)


def resolve(name, role):
    """-> (path, ttc_index, variable_weight_or_None) for one weight."""
    spec = ALL.get(name)
    if spec is None:
        raise KeyError(f"unknown typeface {name!r}; choose from: {', '.join(sorted(ALL))}")
    if spec["kind"] == "local":
        path, index = spec["roles"][role]
        return path, index, None
    ensure(name)
    fn, weight = spec["roles"][role]
    return os.path.join(FONT_DIR, fn), 0, weight


# ------------------------------------------------------------------ the advice

# Pairings that work, keyed by what the app IS. A display face carries the
# headline; a text face carries body, cards and feature rows. Same face for
# both is fine when it has enough weight range - it is listed explicitly when so.
PAIRINGS = [
    (("cleaner", "storage", "utility", "system", "optimiser", "optimizer", "disk",
      "maintenance", "battery", "speed"),
     ("archivo", "inter"),
     "Utility needs headlines that punch at thumbnail size and body copy that "
     "disappears. Archivo goes properly heavy; Inter stays out of the way."),
    (("security", "vpn", "privacy", "password", "backup", "encryption", "enterprise", "b2b"),
     ("ibm-plex-sans", "ibm-plex-sans"),
     "Engineered forms signal rigour. One family across the set reads as a "
     "system rather than a campaign."),
    (("ai", "crypto", "web3", "developer", "devtool", "api", "terminal", "code"),
     ("space-grotesk", "inter"),
     "Space Grotesk reads current and technical without slipping into sci-fi; "
     "Inter keeps dense supporting copy readable."),
    (("dashboard", "analytics", "data", "reporting", "crm", "saas", "productivity",
      "project", "task", "notes"),
     ("manrope", "inter"),
     "Crisp and precise up top, fully neutral underneath - the register users "
     "expect from a work tool."),
    (("finance", "bank", "invest", "trading", "tax", "accounting", "insurance", "legal"),
     ("source-serif-4", "inter"),
     "A sturdy serif buys trust in money and law; a neutral sans keeps figures "
     "and disclosures legible."),
    (("luxury", "fashion", "jewellery", "jewelry", "realestate", "property", "hotel",
      "wedding", "interior", "premium"),
     ("playfair-display", "work-sans"),
     "High-contrast didone is the shorthand for expensive; a quiet humanist "
     "sans keeps it from becoming a wedding invitation."),
    (("food", "recipe", "restaurant", "coffee", "craft", "indie", "magazine", "blog"),
     ("fraunces", "work-sans"),
     "Fraunces has handmade warmth that suits food and craft; Work Sans keeps "
     "instructions plain."),
    (("fitness", "gym", "sport", "run", "workout", "training", "event", "music", "streaming"),
     ("bebas-neue", "archivo"),
     "Condensed caps give a poster-like shout for short headlines; Archivo "
     "carries everything Bebas cannot (it is display-only)."),
    (("health", "wellness", "meditation", "sleep", "habit", "mood", "therapy", "care"),
     ("rubik", "rubik"),
     "Rounded terminals read calm and non-clinical, which is the whole job for "
     "wellbeing apps."),
    (("kids", "child", "family", "education", "learning", "school", "language", "study"),
     ("rubik", "work-sans"),
     "Friendly but not cartoonish up top, maximum legibility for the copy a "
     "parent or learner actually reads."),
    (("reading", "book", "journal", "writing", "diary", "publishing", "news"),
     ("lora", "inter"),
     "A reading serif signals the product is about text; a neutral sans handles "
     "the UI-flavoured supporting lines."),
    (("shopping", "ecommerce", "retail", "beauty", "travel", "booking", "social",
      "dating", "photo", "video"),
     ("poppins", "outfit"),
     "Warm geometric shapes for mainstream consumer, with a slightly tighter "
     "companion so the two do not fight."),
]

FALLBACK = (("outfit", "inter"),
            "No strong category signal - a friendly geometric display with a "
            "neutral text face. Replace this the moment the category is clear.")


def advise(description, top=3):
    """Rank pairings against a free-text description of the app."""
    words = {w.strip(".,/()-").lower() for w in description.split()}
    blob = description.lower()
    scored = []
    for keys, pair, why in PAIRINGS:
        hits = sum(1 for k in keys if k in words) * 2 + sum(1 for k in keys if k in blob)
        if hits:
            scored.append((hits, pair, why))
    scored.sort(key=lambda r: -r[0])
    out = [(p, w) for _, p, w in scored[:top]]
    return out or [FALLBACK]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--fetch-all":
        for n in GOOGLE:
            print(n)
            ensure(n)
    else:
        q = " ".join(sys.argv[1:]) or "storage cleaner utility for mac"
        print(f"App: {q}\n")
        for (disp, text), why in advise(q):
            print(f"  display={disp:18} text={text:18}")
            print(f"    {why}")
            for r in {disp, text}:
                print(f"    - {r}: {ALL[r]['note']}")
            print()
