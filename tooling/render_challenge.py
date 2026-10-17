"""bettersorted – #30Tage30Tools: Bild (1080x1350), Video (1080x1920) und Wochen-Rückblick.

Aufruf:
    python3 render_challenge.py images  <ausgabeordner> [tag ...]
    python3 render_challenge.py videos  <ausgabeordner> [tag ...]
    python3 render_challenge.py recap   <ausgabeordner> <titel> <von> <bis> [all]

Design „Tool im Fokus“: dunkler Grund, Glow in der Markenfarbe des Tools, Tool-Logo groß
in der Mitte, bettersorted nur klein oben links. Logos: simple-icons (content/challenge/icons.json).
"""
import sys, os, json, io, colorsys, subprocess
import cairosvg
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_slides import F, load_logo, SKY, HERE

C = os.path.join(HERE, "content", "challenge")
TOOLS = json.load(open(os.path.join(C, "tools.json"), encoding="utf-8"))
ICONS = json.load(open(os.path.join(C, "icons.json"), encoding="utf-8"))
BG = (15, 12, 31); WHITE = (255, 255, 255); SUB = (188, 192, 210); MUTED = (128, 132, 156)
TAG = "#30Tage30Tools"

def hx(h): return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def lum(c): return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255

def accent(t):
    c = hx(ICONS[t["icon"]]["hex"]); h, l, s = colorsys.rgb_to_hls(*[v / 255 for v in c])
    if s < 0.25 or l < 0.12: return SKY
    if l < 0.42: l = 0.58
    if l > 0.72: l = 0.66
    return tuple(int(v * 255) for v in colorsys.hls_to_rgb(h, l, max(s, 0.55)))

def logo_img(t, size):
    c = ICONS[t["icon"]]["hex"]; rgb = hx(c); _, l_, s_ = colorsys.rgb_to_hls(*[v / 255 for v in rgb])
    if s_ < 0.15 and 0.45 < l_ < 0.8: c = "55565E"  # blasse Grautöne auf Weiß kräftiger
    svg = ICONS[t["icon"]]["svg"].replace("<svg ", f'<svg fill="#{c}" ', 1)
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert("RGBA")

def tile(t, s):
    """Weiße Kachel mit Tool-Logo; bei sehr hellem Logo dunkle Kachel."""
    light = lum(hx(ICONS[t["icon"]]["hex"])) > 0.72
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.22), fill=(28, 24, 50) if light else WHITE)
    lg = logo_img(t, int(s * 0.56)); im.alpha_composite(lg, ((s - lg.width) // 2, (s - lg.height) // 2))
    return im

def glow(W, H, cx, cy, r, col, a=0.55):
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (int(255 * a),))
    return g.filter(ImageFilter.GaussianBlur(r * 0.55))

def wrap(text, font, maxw):
    d = ImageDraw.Draw(Image.new("RGB", (1, 1))); lines, cur = [], ""
    for w in text.split():
        x = (cur + " " + w).strip()
        if d.textlength(x, font=font) <= maxw: cur = x
        else: lines.append(cur); cur = w
    lines.append(cur); return lines

def centered_text(text, font, maxw, col, lh):
    lines = wrap(text, font, maxw); im = Image.new("RGBA", (maxw, lh * len(lines) + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, l in enumerate(lines): d.text((maxw / 2, i * lh), l, font=font, fill=col, anchor="ma")
    return im

def chip(text, col, filled):
    f = F("Inter-SemiBold.otf", 28); d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    w = int(d0.textlength(text, font=f)) + 48; im = Image.new("RGBA", (w, 54), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if filled: d.rounded_rectangle((0, 0, w - 1, 53), radius=27, fill=col + (56,), outline=col + (150,), width=2)
    else: d.rounded_rectangle((0, 0, w - 1, 53), radius=27, outline=(255, 255, 255, 90), width=2)
    d.text((w / 2, 27), text, font=f, fill=WHITE if not filled else tuple(min(255, int(v * 0.35 + 255 * 0.65)) for v in col), anchor="mm")
    return im

def chips_row(t, ac):
    a, b = chip(t["cat"], ac, True), chip(t["badge"], ac, False)
    im = Image.new("RGBA", (a.width + b.width + 16, 54), (0, 0, 0, 0)); im.alpha_composite(a, (0, 0)); im.alpha_composite(b, (a.width + 16, 0))
    return im

def day_pill(n):
    f1, f2 = F("InterDisplay-Bold.otf", 30), F("Inter-Medium.otf", 30)
    im = Image.new("RGBA", (230, 58), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 229, 57), radius=29, outline=(255, 255, 255, 80), width=2)
    d.text((32, 29), "TAG", font=f2, fill=MUTED, anchor="lm")
    d.text((104, 29), f"{n:02d}", font=f1, fill=WHITE, anchor="lm")
    d.text((152, 29), "/ 30", font=f2, fill=MUTED, anchor="lm")
    return im

def flow_rows(t, ac, w):
    rows = []
    f = F("Inter-Medium.otf", 34); fn = F("InterDisplay-Bold.otf", 30)
    for i, s in enumerate(t["flow"]):
        im = Image.new("RGBA", (w, 96), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, 95), radius=22, fill=(255, 255, 255, 14), outline=(255, 255, 255, 34), width=2)
        d.ellipse((24, 22, 76, 74), fill=ac); d.text((50, 48), str(i + 1), font=fn, fill=BG, anchor="mm")
        d.text((104, 48), s, font=f, fill=WHITE, anchor="lm")
        rows.append(im)
    return rows

def eyebrow(text, ac):
    f = F("Inter-SemiBold.otf", 26); d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    w = int(d0.textlength(text, font=f)) + 4; im = Image.new("RGBA", (w + 120, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.line((0, 20, 40, 20), fill=ac + (200,), width=3); d.text((60, 20), text, font=f, fill=ac, anchor="lm")
    d.line((80 + w, 20, 120 + w, 20), fill=ac + (200,), width=3)
    return im

def layers(t, n, W, H, big):
    ac = accent(t); k = 1.0 if not big else 1.12
    L = {}
    L["bg"] = Image.new("RGBA", (W, H), BG + (255,))
    L["glow"] = glow(W, H, W // 2, int(H * (0.26 if not big else 0.3)), int(340 * k), ac, 0.42)
    L["logo"] = load_logo(36 if not big else 44, on_dark=True)
    L["pill"] = day_pill(n)
    L["tile"] = tile(t, int(250 * k))
    L["name"] = centered_text(t["name"], F("InterDisplay-Bold.otf", int(84 * k)), W - 120, WHITE, int(92 * k))
    L["chips"] = chips_row(t, ac)
    L["what"] = centered_text(t["what"], F("Inter-Regular.otf", 34 if not big else 38), 880, SUB, 48 if not big else 54)
    L["eyebrow"] = eyebrow("SO FUNKTIONIERT’S", ac)
    L["rows"] = flow_rows(t, ac, 820)
    f = F("Inter-SemiBold.otf", 28 if not big else 32)
    ft = Image.new("RGBA", (W - 160, 50), (0, 0, 0, 0)); d = ImageDraw.Draw(ft)
    d.text((0, 25), TAG, font=f, fill=ac, anchor="lm"); d.text((W - 160, 25), t["url"], font=F("Inter-Medium.otf", 28 if not big else 32), fill=MUTED, anchor="rm")
    L["foot"] = ft; L["ac"] = ac
    return L

def positions(L, W, H, big):
    P = {}
    P["logo"] = (80, 74 if not big else 120); P["pill"] = (W - 80 - 230, 62 if not big else 108)
    ty = 170 if not big else 300
    P["tile"] = ((W - L["tile"].width) // 2, ty)
    y = ty + L["tile"].height + (40 if not big else 56)
    P["name"] = (60, y); y += L["name"].height + (6 if not big else 14)
    P["chips"] = ((W - L["chips"].width) // 2, y); y += 54 + (34 if not big else 44)
    P["what"] = ((W - 880) // 2, y); y += L["what"].height + (36 if not big else 60)
    P["eyebrow"] = ((W - L["eyebrow"].width) // 2, y); y += 40 + 22
    P["rows"] = [((W - 820) // 2, y + i * 110) for i in range(3)]
    P["foot"] = (80, H - (100 if not big else 170))
    return P

def compose(L, P, W, H, t=None, timing=None):
    """t=None → statisches Bild; sonst Animationsframe zur Zeit t."""
    def a_of(key, i=None):
        if t is None: return 1.0, 0
        st = timing[key] if i is None else timing[key][i]
        x = max(0.0, min(1.0, (t - st) / 0.45)); e = 1 - (1 - x) ** 3
        return e, (1 - e) * 36
    fr = L["bg"].copy()
    ga = 1.0 if t is None else min(1.0, t / 0.8) * (0.9 + 0.1 * __import__("math").sin(t * 2.2))
    g = L["glow"] if ga >= 0.999 else Image.eval(L["glow"], lambda v: v)
    if ga < 0.999:
        g = L["glow"].copy(); g.putalpha(g.getchannel("A").point(lambda v: int(v * ga)))
    fr.alpha_composite(g)
    def put(im, xy, key, i=None):
        a, dy = a_of(key, i)
        if a <= 0.01: return
        if a < 1: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
        fr.alpha_composite(im, (int(xy[0]), int(xy[1] + dy)))
    put(L["logo"], P["logo"], "top"); put(L["pill"], P["pill"], "top")
    # Kachel mit Pop-Effekt
    a, _ = a_of("tile")
    if a > 0.01:
        tl = L["tile"]
        if a < 1:
            s = 0.82 + 0.18 * a; nw = max(2, int(tl.width * s)); tl = tl.resize((nw, nw), Image.LANCZOS)
            tl.putalpha(tl.getchannel("A").point(lambda v: int(v * a)))
        cx = P["tile"][0] + L["tile"].width // 2; cy = P["tile"][1] + L["tile"].height // 2
        fr.alpha_composite(tl, (cx - tl.width // 2, cy - tl.height // 2))
    put(L["name"], P["name"], "name"); put(L["chips"], P["chips"], "chips"); put(L["what"], P["what"], "what")
    put(L["eyebrow"], P["eyebrow"], "eyebrow")
    for i, r in enumerate(L["rows"]): put(r, P["rows"][i], "rows", i)
    put(L["foot"], P["foot"], "foot")
    return fr

def render_image(n, out):
    t = TOOLS[n - 1]; W, H = 1080, 1350
    L = layers(t, n, W, H, False); P = positions(L, W, H, False)
    compose(L, P, W, H).convert("RGB").save(out, quality=95)

def render_video(n, out, dur=9.0, fps=30):
    t = TOOLS[n - 1]; W, H = 1080, 1920
    L = layers(t, n, W, H, True); P = positions(L, W, H, True)
    nxt = "Morgen: Tag %02d →" % (n + 1) if n < 30 else "Welches Tool war dein Favorit?"
    f = F("Inter-SemiBold.otf", 34); cta = Image.new("RGBA", (W - 160, 70), (0, 0, 0, 0)); d = ImageDraw.Draw(cta)
    d.rounded_rectangle((0, 0, W - 161, 69), radius=35, fill=L["ac"] + (40,), outline=L["ac"] + (140,), width=2)
    d.text(((W - 160) / 2, 35), nxt, font=f, fill=WHITE, anchor="mm")
    cta_y = P["rows"][2][1] + 96 + 50; P["foot"] = (80, cta_y + 110)
    timing = {"top": 0.0, "tile": 0.15, "name": 0.55, "chips": 0.85, "what": 1.15, "eyebrow": 1.9, "rows": [2.2, 3.0, 3.8], "foot": 4.8}
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-i", os.path.join(HERE, "assets", "sound.wav"), "-filter_complex", f"[1:a]volume=0.4,afade=t=out:st={dur - 0.8}:d=0.8[a]",
           "-map", "0:v", "-map", "[a]", "-t", str(dur), "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(dur * fps)):
        tt = i / fps; fr = compose(L, P, W, H, tt, timing)
        x = max(0.0, min(1.0, (tt - 5.4) / 0.45)); e = 1 - (1 - x) ** 3
        if e > 0.01:
            c = cta.copy(); c.putalpha(c.getchannel("A").point(lambda v: int(v * e)))
            fr.alpha_composite(c, (80, int(cta_y + (1 - e) * 30)))
        p.stdin.write(fr.convert("RGB").tobytes())
    p.stdin.close(); p.wait()

def render_recap_cover(out, title, a, b, all_grid=False):
    W, H = 1080, 1350; fr = Image.new("RGBA", (W, H), BG + (255,))
    fr.alpha_composite(glow(W, H, W // 2, 360, 380, SKY, 0.30))
    fr.alpha_composite(load_logo(36, on_dark=True), (80, 74))
    d = ImageDraw.Draw(fr)
    d.text((W / 2, 200), TAG, font=F("Inter-SemiBold.otf", 32), fill=SKY, anchor="mm")
    nm = centered_text(title, F("InterDisplay-Bold.otf", 84), W - 160, WHITE, 92); fr.alpha_composite(nm, (80, 250))
    sub = "Alle 30 Tools auf einen Blick" if all_grid else f"Tag {a}–{b}: die Tools dieser Woche"
    d.text((W / 2, 280 + nm.height + 10), sub, font=F("Inter-Regular.otf", 38), fill=SUB, anchor="mm")
    sel = TOOLS if all_grid else TOOLS[a - 1:b]
    cols = 6 if all_grid else min(4, len(sel)); s = 112 if all_grid else 190; gap = 30 if all_grid else 40
    rows = (len(sel) + cols - 1) // cols
    block = rows * s + (rows - 1) * (30 if all_grid else 90) + (0 if all_grid else 50)
    top = 330 + nm.height + (20 if all_grid else 40); y0 = top + max(0, (H - 170 - top - block) // 2)
    for i, t in enumerate(sel):
        r, c = divmod(i, cols); n_in = min(cols, len(sel) - r * cols)
        x0 = (W - (n_in * s + (n_in - 1) * gap)) // 2
        x = x0 + c * (s + gap); y = y0 + r * (s + (30 if all_grid else 90))
        fr.alpha_composite(tile(t, s), (x, y))
        if not all_grid:
            d.text((x + s / 2, y + s + 34), t["name"], font=F("Inter-SemiBold.otf", 28), fill=WHITE, anchor="mm")
    d.text((W / 2, H - 110), "Swipe für alle Tools →" if not all_grid else "Welches war dein Favorit?", font=F("Inter-Medium.otf", 32), fill=MUTED, anchor="mm")
    fr.convert("RGB").save(out, quality=95)

if __name__ == "__main__":
    mode, outd = sys.argv[1], sys.argv[2]; os.makedirs(outd, exist_ok=True)
    if mode == "recap":
        render_recap_cover(os.path.join(outd, sys.argv[3]), sys.argv[4], int(sys.argv[5]), int(sys.argv[6]), len(sys.argv) > 7)
    else:
        days = [int(x) for x in sys.argv[3:]] or list(range(1, 31))
        for n in days:
            if mode == "images": render_image(n, os.path.join(outd, f"tag-{n:02d}.jpg"))
            else: render_video(n, os.path.join(outd, f"tag-{n:02d}.mp4"))
            print(n, flush=True)
