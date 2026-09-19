#!/usr/bin/env python3
"""
html_tiles.py - "poster" store tiles rendered from HTML/CSS with headless Chrome.

This is the engine behind the bold, high-attention sets (dark brand field, huge
two-line title with one highlighted word, straight device, ONE real UI card
lifted out of the screen, per-screen 3D props, faint subject doodles).
Every pixel of app UI comes from a real capture - nothing is redrawn.

Usage
  python3 html_tiles.py build  config.json            # render every tile
  python3 html_tiles.py measure shot.png X Y          # exact card rect around a point
  python3 html_tiles.py check  config.json            # verify prop URLs resolve (no 404 boxes)

Config (JSON) - see references/html-tiles.md for the full schema and examples:
{
  "platform": "ios-69" | "ios-65" | "android-phone" | "android-tablet" | "ipad" | "mac",
  "out": "docs/store-screenshots/ios-iphone",
  "theme": {                     # optional - defaults are a dark violet field
    "bg": "<css background>", "title": "#fff", "accent": "#ffd84d",
    "doodle": "#c9b8ff", "doodle_opacity": 0.28, "grid": true,
    "font": "Rubik", "hand_font": "Caveat"   # ALWAYS choose per app - see rule 16
  },
  "tiles": [{
    "name": "01_snap_solve",
    "title": "Snap. Solve. <b>Learn.</b>",       # <b> = highlight colour; <br> allowed on phones
    "shot": "captures/answer.png",               # full-res capture of THIS platform
    "card": [48, 1131, 1224, 246],                # px rect in the capture (use `measure`), or null
    "doodles": "math" | ["x²", "..."],           # bank name or explicit list; use a different bank per tile
    "props": [{"emoji": "Pencil", "x": -30, "y": 560, "w": 230, "rot": -20}],
    "split": ["light.png", "dark.png"]            # optional: two overlapping devices instead of shot/card
  }]
}
"""
import json, os, subprocess, sys, urllib.request

CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
FLUENT = "https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/assets/"

# canvas size, device kind, device box (left, top, width) and screen inset
PLATFORMS = {
    "ios-69":         dict(W=1320, H=2868, kind="iphone",  dev=(150, 720, 1020), title=178, top=120),
    "ios-65":         dict(W=1242, H=2688, kind="iphone",  dev=(141, 676, 960),  title=168, top=112),
    "android-phone":  dict(W=1080, H=1920, kind="android", dev=(150, 560, 780),  title=112, top=90),
    "ipad":           dict(W=2752, H=2064, kind="tablet",  dev=(426, 470, 1900), title=196, top=130),
    "android-tablet": dict(W=1920, H=1080, kind="tablet",  dev=(300, 250, 1320), title=110, top=60),
    "mac":            dict(W=2880, H=1800, kind="mac",     dev=(390, 420, 2100), title=170, top=110),
}

DOODLES = {
    "math": ["x² − 5x + 6 = 0", "√144 = 12", "π ≈ 3.14", "∑ n", "y = mx + b", "a² + b² = c²", "∫ f(x) dx", "3/4 + 1/8",
             "sin²θ + cos²θ = 1", "log₁₀100 = 2", "Δ = b² − 4ac", "f(x) = 2x + 1", "∞", "%", "x ≠ 0"],
    "biology": ["DNA", "C₆H₁₂O₆", "ATP", "mitosis", "6CO₂ + 6H₂O", "cell", "RNA", "chlorophyll", "O₂", "genes",
                "Aa × Aa", "enzyme", "photosynthesis", "neuron", "protein"],
    "physics": ["F = ma", "E = mc²", "v = u + at", "P = IV", "λ = v/f", "W = Fd", "g = 9.8 m/s²", "KE = ½mv²",
                "V = IR", "p = mv", "Ω", "Hz", "ρ = m/V", "Δv / t", "c = 3×10⁸"],
    "chemistry": ["H₂O", "NaCl", "CO₂", "pH = 7", "2H₂ + O₂ → 2H₂O", "mol", "Fe", "CH₄", "NH₃", "H⁺", "Na⁺ Cl⁻",
                  "e⁻", "C", "6.02×10²³", "Avogadro"],
    "history": ["1945", "WWII", "1939", "1776", "Rome", "Magna Carta", "1492", "Renaissance", "Pharaoh", "1914",
                "Empire", "timeline", "Industrial Rev.", "Treaty", "Revolution"],
    "languages": ["Hola", "Bonjour", "こんにちは", "Hallo", "안녕", "Olá", "Ciao", "你好", "Привет", "Merhaba",
                  "Hej", "Salut", "Γειά", "Ahoj", "Namaste"],
    "english": ["noun", "verb", "adjective", "“quote”", "Shakespeare", "essay", "grammar", "poem", "metaphor",
                "thesis", "synonym", "past tense", "A B C", "; :", "Aa"],
    "code": ["{ }", "</>", "fn()", "=>", "if (x)", "[]", "null", "0101", "#include", "print()", "git push",
             "λ", "async", "SELECT *", "npm i"],
    "finance": ["$", "€", "%", "+12.4%", "ROI", "₿", "budget", "¥", "£", "APR", "Σ", "save", "invest", "×2", "📈"],
}


def emoji_url(name):
    return FLUENT + name.replace(" ", "%20") + "/3D/" + name.lower().replace(" ", "_") + "_3d.png"


def slots(W, H):
    """15 doodle positions hugging the edges (never behind the title centre or the device centre)."""
    xs = [0.03, 0.80, 0.02, 0.86, 0.40, 0.02, 0.86, 0.01, 0.76, 0.02, 0.83, 0.80, 0.38, 0.03, 0.85]
    ys = [0.03, 0.02, 0.17, 0.15, 0.20, 0.41, 0.38, 0.60, 0.56, 0.79, 0.73, 0.88, 0.95, 0.93, 0.65]
    rs = [-6, 5, -8, 6, 0, 0, 0, -10, 8, -5, 10, -6, 0, 4, 0]
    return [(int(W * x), int(H * y), r) for x, y, r in zip(xs, ys, rs)]


def device_html(kind, l, t, w, img, W):
    """Frame + screen. The screen is the capture at its true aspect - never stretched."""
    from PIL import Image
    iw, ih = Image.open(img).size
    if kind == "iphone":
        pad, bez = 12, 26
        sh = (w - 2 * (pad + bez)) * ih / iw
        h = sh + 2 * (pad + bez)
        r = w * 0.167
        return (f'<div class="dev iphone" style="left:{l}px;top:{t}px;width:{w}px;height:{h:.0f}px;border-radius:{r:.0f}px;padding:{pad}px">'
                f'<div class=bz style="border-radius:{r-pad:.0f}px;padding:{bez}px"><div class=scr style="border-radius:{r-pad-bez:.0f}px"><img src="{img}"></div></div></div>')
    if kind == "android":
        pad = int(w * 0.03)
        sh = (w - 2 * pad) * ih / iw
        return (f'<div class="dev android" style="left:{l}px;top:{t}px;width:{w}px;height:{sh+2*pad:.0f}px;border-radius:{w*0.11:.0f}px;padding:{pad}px">'
                f'<div class=scr style="border-radius:{w*0.09:.0f}px"><img src="{img}"></div></div>')
    if kind == "tablet":
        pad = int(w * 0.016)
        sh = (w - 2 * pad) * ih / iw
        return (f'<div class="dev tablet" style="left:{l}px;top:{t}px;width:{w}px;height:{sh+2*pad:.0f}px;border-radius:{w*0.037:.0f}px;padding:{pad}px">'
                f'<div class=scr style="border-radius:{w*0.021:.0f}px"><img src="{img}"></div></div>')
    # mac window
    bar = int(w * 0.03)
    sh = w * ih / iw
    return (f'<div class="dev mac" style="left:{l}px;top:{t}px;width:{w}px;height:{sh+bar:.0f}px">'
            f'<div class=bar style="height:{bar}px"><i></i><i></i><i></i></div><img src="{img}"></div>')


def screen_geom(P, img):
    """Where the capture lands on the canvas: (x0, y0, scale)."""
    from PIL import Image
    iw, ih = Image.open(img).size
    l, t, w = P["dev"]
    inset = {"iphone": 38, "android": int(w * 0.03), "tablet": int(w * 0.016), "mac": 0}[P["kind"]]
    top = t + (int(w * 0.03) if P["kind"] == "mac" else inset)
    return l + inset, top, (w - 2 * inset) / iw


FIT = "<script>document.fonts.ready.then(function(){var h=document.querySelector('h1'),f=parseFloat(getComputedStyle(h).fontSize);while(h.scrollWidth>h.clientWidth&&f>40){f-=4;h.style.fontSize=f+'px'}})</script>"


CSS = """*{margin:0;box-sizing:border-box}
body{width:%(W)dpx;height:%(H)dpx;overflow:hidden;font-family:'%(font)s',sans-serif;position:relative;background:%(bg)s}
.grid{position:absolute;inset:0;background-image:linear-gradient(#ffffff0d 2px,transparent 2px),linear-gradient(90deg,#ffffff0d 2px,transparent 2px);background-size:%(gs)dpx %(gs)dpx;-webkit-mask:radial-gradient(circle at 50%% 40%%,#000,transparent 75%%)}
.dd{position:absolute;font-family:'%(hand)s',cursive;font-weight:700;color:%(doodle)s;opacity:%(dop)s;white-space:nowrap}
h1{position:absolute;left:40px;right:40px;top:%(top)dpx;text-align:center;font-size:%(ts)dpx;line-height:1;font-weight:900;color:%(title)s;letter-spacing:-.03em;text-shadow:0 12px 40px #0006;white-space:nowrap}
h1 b{color:%(accent)s}
.dev{position:absolute;box-shadow:0 50px 110px #000a}
.dev .scr{width:100%%;height:100%%;overflow:hidden;background:#000}
.dev img{width:100%%;display:block}
.iphone,.tablet{background:linear-gradient(135deg,#e9e7ee,#8a8792 30%%,#d6d4db 50%%,#6f6c77 75%%,#c9c7ce)}
.iphone .bz{width:100%%;height:100%%;background:#050507}
.iphone:before,.iphone:after{content:'';position:absolute;background:#9a97a2;border-radius:6px}
.iphone:before{left:-10px;top:14%%;width:12px;height:4.6%%;box-shadow:0 7vh 0 #9a97a2}
.iphone:after{right:-10px;top:21%%;width:12px;height:9%%}
.tablet .scr{outline:14px solid #050507}
.android{background:#111116;box-shadow:0 50px 110px #000a,inset 0 0 0 3px #3a3946}
.mac{background:#fff;border-radius:22px;overflow:hidden}
.mac .bar{background:#ececef;display:flex;gap:14px;align-items:center;padding-left:24px}
.mac .bar i{width:22px;height:22px;border-radius:50%%;background:#ff5f57}.mac .bar i+i{background:#febc2e}.mac .bar i+i+i{background:#28c840}
.card{position:absolute;overflow:hidden;border-radius:%(cr)dpx;box-shadow:0 50px 100px #000b;background:#fff}
.card img{position:absolute;display:block}
.prop{position:absolute;filter:drop-shadow(0 30px 34px #0008)}"""


def build(cfg_path):
    cfg = json.load(open(cfg_path))
    base = os.path.dirname(os.path.abspath(cfg_path))
    P = dict(PLATFORMS[cfg["platform"]])
    W, H = P["W"], P["H"]
    th = {"bg": "radial-gradient(circle at 80% 18%,#8b5cff 0,transparent 38%),radial-gradient(circle at 10% 70%,#c13cff55 0,transparent 35%),linear-gradient(165deg,#2a1570,#150a3d 55%,#0c0626)",
          "title": "#fff", "accent": "#ffd84d", "doodle": "#c9b8ff", "doodle_opacity": 0.28, "grid": True,
          "font": "Rubik", "hand_font": "Caveat"}
    th.update(cfg.get("theme", {}))
    if "font" not in cfg.get("theme", {}) or "hand_font" not in cfg.get("theme", {}):
        print("WARNING: theme.font / theme.hand_font not set - falling back to Rubik/Caveat. "
              "Pick faces that fit this app (build_tiles.py --suggest-fonts); never reuse one by habit.")
    out = os.path.join(base, cfg.get("out", "out")); os.makedirs(out, exist_ok=True)
    unit = W / 1320
    css = CSS % dict(W=W, H=H, font=th["font"], bg=th["bg"], gs=int(66 * unit) or 40, hand=th["hand_font"],
                     doodle=th["doodle"], dop=th["doodle_opacity"], top=P["top"], ts=P["title"],
                     title=th["title"], accent=th["accent"], cr=int(40 * unit))
    fonts = f"https://fonts.googleapis.com/css2?family={th['font'].replace(' ','+')}:wght@600;800;900&family={th['hand_font'].replace(' ','+')}:wght@700&display=swap"
    S = slots(W, H)
    for t in cfg["tiles"]:
        d = t.get("doodles", [])
        d = DOODLES.get(d, []) if isinstance(d, str) else d
        dsz = int(80 * unit)
        dd = "".join(f'<div class=dd style="left:{x}px;top:{y}px;font-size:{dsz}px;transform:rotate({r}deg)">{s}</div>' for (x, y, r), s in zip(S, d))
        pr = "".join(f'<img class=prop src="{emoji_url(p["emoji"]) if "emoji" in p else p["src"]}" style="left:{p["x"]}px;top:{p["y"]}px;width:{p["w"]}px;transform:rotate({p.get("rot",0)}deg)">' for p in t.get("props", []))
        l, tp, w = P["dev"]
        card = ""
        if t.get("split"):
            a, b = [os.path.join(base, s) for s in t["split"]]
            if P["kind"] in ("tablet", "mac"):
                sw = int(w * 0.84)
                body = device_html(P["kind"], int(W * 0.04), tp + int(H * 0.05), sw, a, W) + device_html(P["kind"], W - sw - int(W * 0.04), tp + int(H * 0.2), sw, b, W)
            else:
                sw = int(w * 0.74)
                body = device_html(P["kind"], int(W * 0.05), tp + int(H * 0.03), sw, a, W) + device_html(P["kind"], W - sw - int(W * 0.05), tp + int(H * 0.13), sw, b, W)
        else:
            shot = os.path.join(base, t["shot"])
            body = device_html(P["kind"], l, tp, w, shot, W)
            if t.get("card"):
                x, y, cw0, ch0 = t["card"]
                x0, y0, sc = screen_geom(P, shot)
                k = sc * t.get("card_zoom", 1.3 if P["kind"] in ("tablet", "mac") else 1.28)
                cw, ch = cw0 * k, ch0 * k
                cx = x0 + (x + cw0 / 2) * sc; cy = y0 + (y + ch0 / 2) * sc
                left = min(max(cx - cw / 2, 40 * unit), W - 40 * unit - cw)
                from PIL import Image
                iw = Image.open(shot).size[0]
                card = (f'<div class=card style="left:{left:.0f}px;top:{cy-ch/2:.0f}px;width:{cw:.0f}px;height:{ch:.0f}px">'
                        f'<img src="{shot}" style="width:{iw*k:.0f}px;left:{-x*k:.0f}px;top:{-y*k:.0f}px"></div>')
        grid = "<div class=grid></div>" if th["grid"] else ""
        html = f'<html><head><link href="{fonts}" rel="stylesheet"><style>{css}</style></head><body>{grid}{dd}<h1>{t["title"]}</h1>{body}{card}{pr}{FIT}</body></html>'
        hp = os.path.join(out, t["name"] + ".html"); open(hp, "w").write(html)
        png = os.path.join(out, t["name"] + ".png")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={W},{H}",
                        "--virtual-time-budget=9000", f"--screenshot={png}", "file://" + hp], stderr=subprocess.DEVNULL)
        from PIL import Image
        im = Image.open(png).convert("RGB")          # stores reject alpha
        assert im.size == (W, H), f"{png} is {im.size}, expected {(W, H)}"
        im.save(png)
        print("ok", png)


def measure(path, X, Y, tol=10):
    """Exact rect of the UI element containing (X,Y), measured against the page background.
    Guessed crops slice the card's own rounded corners - always measure."""
    from PIL import Image
    import numpy as np
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    h, w = a.shape[:2]
    bg = a[Y, 2] if X > w // 4 else a[Y, w - 3]
    row = np.abs(a[Y] - bg).sum(1) > tol
    l = X
    while l > 0 and row[l - 1]: l -= 1
    r = X
    while r < w - 1 and row[r + 1]: r += 1
    col = np.abs(a[:, X] - bg).sum(1) > tol
    t = Y
    while t > 0 and col[t - 1]: t -= 1
    b = Y
    while b < h - 1 and col[b + 1]: b += 1
    print(json.dumps([int(l), int(t), int(r - l + 1), int(b - t + 1)]))


def check(cfg_path):
    cfg = json.load(open(cfg_path)); bad = 0
    for t in cfg["tiles"]:
        for p in t.get("props", []):
            u = emoji_url(p["emoji"]) if "emoji" in p else p["src"]
            if not u.startswith("http"): continue
            try: urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=15)
            except Exception: print("BROKEN", t["name"], u); bad += 1
    print("all props resolve" if not bad else f"{bad} broken prop(s) - they render as empty boxes")


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "build": build(sys.argv[2])
    elif c == "measure": measure(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    elif c == "check": check(sys.argv[2])
    else: print(__doc__)
