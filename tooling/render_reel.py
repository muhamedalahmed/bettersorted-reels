import sys, math, subprocess, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content'))
import importlib
REELS = importlib.import_module(os.environ.get('CONTENT', 'serie1_loesungen')).REELS

W, H, FPS, DUR = 1080, 1920, 30, 20.0
NAVY = (28, 22, 49)
BLUE = (63, 148, 198)
SKY = (108, 207, 246)
MUTED = (84, 82, 104)
BG = (244, 249, 252)
FD = "/usr/share/fonts/opentype/inter/"
def F(name, size): return ImageFont.truetype(FD + name, size)

ML = 84            # linker Rand
CW = 870           # Inhaltsbreite (rechts frei für IG-Buttons)
OUT = sys.argv[2] if len(sys.argv) > 2 else "out"

# ---------- Logo (weiß -> transparent) ----------
def load_logo(path, height):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    mn = a.min(axis=2)
    alpha = np.clip((255 - mn) / 190.0, 0, 1)
    rgb = np.where(alpha[..., None] > 0.01,
                   (a - 255 * (1 - alpha[..., None])) / np.maximum(alpha[..., None], 0.01), 255)
    rgba = np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")
    im = im.crop(im.getbbox())
    w = int(im.width * height / im.height)
    return im.resize((w, height), Image.LANCZOS)

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = load_logo(os.path.join(HERE, "assets", "logo.jpeg"), 74)

# ---------- Hintergrund ----------
def make_bg():
    m = 300
    big = Image.new("RGB", (W + 2 * m, H + 2 * m), BG)
    lay = Image.new("RGBA", big.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for (cx, cy, r, col, a) in [(1150, 420, 520, SKY, 120), (180, 1500, 560, BLUE, 70),
                                (1050, 1900, 420, SKY, 90), (300, 300, 300, BLUE, 40)]:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (a,))
    lay = lay.filter(ImageFilter.GaussianBlur(160))
    big.paste(lay, (0, 0), lay)
    # dezentes Netz-Motiv aus dem Logo, sehr hell
    net = Image.new("RGBA", big.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(net)
    col = BLUE + (26,)
    ox, oy = 1020, 1380
    for (nx, ny) in [(ox + 330, oy - 260), (ox + 380, oy), (ox + 330, oy + 260)]:
        d.line((ox, oy, nx, ny), fill=col, width=14)
        d.ellipse((nx - 46, ny - 46, nx + 46, ny + 46), outline=col, width=16)
    big.paste(net, (0, 0), net)
    return big, m

BG_BIG, BGM = make_bg()

def bg_frame(t):
    dx = int(BGM + 60 * math.sin(t * 0.25))
    dy = int(BGM + 80 * math.cos(t * 0.18))
    return BG_BIG.crop((dx, dy, dx + W, dy + H)).convert("RGBA")

# ---------- Text-Helfer ----------
def tokens(markup):
    out, hi = [], False
    for w in markup.split(" "):
        s = w
        if s.startswith("["): hi = True; s = s[1:]
        end = s.endswith("]") or s.endswith("]?") or s.endswith("].") or s.endswith("]“")
        s2 = s.replace("]", "")
        out.append((s2, hi))
        if end: hi = False
    return out

def wrap(tok, font, maxw):
    lines, cur, cw = [], [], 0
    sp = font.getlength(" ")
    for w, hi in tok:
        wl = font.getlength(w)
        if cur and cw + sp + wl > maxw:
            lines.append(cur); cur, cw = [], 0
        cw = cw + (sp if cur else 0) + wl
        cur.append((w, hi))
    if cur: lines.append(cur)
    return lines

def text_block(markup, font, maxw, color=NAVY, hcolor=BLUE, lh=1.12):
    lines = wrap(tokens(markup), font, maxw)
    asc, desc = font.getmetrics()
    lhp = int((asc + desc) * lh)
    im = Image.new("RGBA", (maxw + 20, lhp * len(lines) + desc), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    sp = font.getlength(" ")
    for i, ln in enumerate(lines):
        x = 0
        for w, hi in ln:
            d.text((x, i * lhp), w, font=font, fill=hcolor if hi else color)
            x += font.getlength(w) + sp
    return im.crop((0, 0, im.width, im.getbbox()[3] + 6 if im.getbbox() else im.height))

def shadowed(im, radius=30, off=(0, 18), alpha=40):
    pad = radius * 2
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    a = im.split()[3].point(lambda v: alpha if v > 0 else 0)
    sh.paste(NAVY + (255,), (pad + off[0], pad + off[1]), a)
    sh = sh.filter(ImageFilter.GaussianBlur(radius))
    out.alpha_composite(sh)
    out.alpha_composite(im, (pad, pad))
    return out, pad

def glass(w, h, r=44, fill=(255, 255, 255, 190)):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), r, fill=fill, outline=(255, 255, 255, 240), width=3)
    return im

def pill(text, font, fg, bg, padx=30, pady=16, outline=None):
    tw = font.getlength(text); asc, desc = font.getmetrics()
    w, h = int(tw + 2 * padx), asc + desc + 2 * pady - 8
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=bg, outline=outline, width=3 if outline else 0)
    d.text((padx, pady - 4), text, font=font, fill=fg)
    return im

def check_icon(size, num=None):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, s - 1, s - 1), fill=BLUE + (255,))
    if num is None:
        d.line([(s * .28, s * .52), (s * .44, s * .68), (s * .73, s * .35)], fill="white", width=int(s * .1), joint="curve")
    else:
        f = F("Inter-Bold.otf", int(s * .55))
        tw = f.getlength(str(num)); asc, desc = f.getmetrics()
        d.text(((s - tw) / 2, (s - asc - desc) / 2), str(num), font=f, fill="white")
    return im.resize((size, size), Image.LANCZOS)

# ---------- Animation ----------
def ease(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3

class El:
    def __init__(s, im, x, y, t_in, t_out, dy=46, dur=0.55, scale=False):
        s.im, s.x, s.y, s.t_in, s.t_out, s.dy, s.dur, s.scale = im, x, y, t_in, t_out, dy, dur, scale
        s.a = im.split()[3]
    def draw(s, frame, t):
        if t < s.t_in or t > s.t_out: return
        p = ease((t - s.t_in) / s.dur)
        q = min(1.0, (s.t_out - t) / 0.32)
        op = p * q
        if op <= 0.003: return
        y = int(s.y + (1 - p) * s.dy - (1 - q) * 20)
        im = s.im
        if op < 0.999:
            im = s.im.copy()
            im.putalpha(s.a.point(lambda v, o=op: int(v * o)))
        frame.alpha_composite(im, (int(s.x), y))

def fmt_num(n, thousands):
    s = f"{int(round(n)):,}".replace(",", ".") if thousands else str(int(round(n)))
    return s

# ---------- Szenen bauen ----------
T1, T2, T3, T4 = 0.0, 4.6, 10.2, 15.0

def build(r, idx):
    els = []
    # Szene 1: Hook
    tag = pill(r["tag"], F("Inter-Bold.otf", 34), BLUE, (255, 255, 255, 215), outline=SKY + (255,))
    els.append(El(tag, ML, 670, -1, T2))
    hs = 112
    while hs > 70 and max(F("InterDisplay-Bold.otf", hs).getlength(w) for w, _ in tokens(r["hook"])) > CW - 30:
        hs -= 6
    hook = text_block(r["hook"], F("InterDisplay-Bold.otf", hs), CW)
    els.append(El(hook, ML, 780, -1, T2, dy=60))
    sub = text_block(r["sub"], F("Inter-Medium.otf", 46), CW - 40, color=MUTED, lh=1.25)
    els.append(El(sub, ML, 800 + hook.height + 50, T1 + 0.6, T2))

    # Szene 2: Lösung (Glas-Karte)
    tt = text_block(r["title"], F("InterDisplay-Bold.otf", 70), CW)
    eyebrow = F("Inter-SemiBold.otf", 32)
    ey = pill(r.get("eyebrow") or {"FÖRDERUNG": "DAS PROGRAMM", "FÖRDERUNG MV": "DAS PROGRAMM", "KI-TOOL": "DAS TOOL",
              "TOOL-CHECK": "ÜBERBLICK", "3 FEHLER": "DIE FEHLER", "SO GEHT'S": "DER WEG", "MYTHOS": "DIE WAHRHEIT"}.get(r["tag"], "DIE LÖSUNG"),
              eyebrow, (255, 255, 255), BLUE + (255,), padx=24, pady=12)
    y0 = 540
    els.append(El(ey, ML, y0, T2 + 0.1, T3))
    els.append(El(tt, ML, y0 + 90, T2 + 0.2, T3))
    bfont = F("Inter-Medium.otf", 46)
    rows = []
    for i, b in enumerate(r.get("bullets", [])):
        txt = text_block(b, bfont, CW - 200, lh=1.22)
        rows.append(txt)
    cy = y0 + 90 + tt.height + 50
    if r.get("versus"):
        rows = []
        for j, (lab_, txt_, col_) in enumerate([("VORHER", r["versus"][0], MUTED), ("MIT KI", r["versus"][1], BLUE)]):
            txt = text_block(txt_, F("Inter-SemiBold.otf", 48), CW - 90, color=NAVY if j else MUTED, lh=1.22)
            lp = pill(lab_, F("Inter-Bold.otf", 28), (255, 255, 255), col_ + (255,), padx=20, pady=10)
            h = txt.height + lp.height + 90
            fill = (255, 255, 255, 140) if j == 0 else (255, 255, 255, 225)
            card = glass(CW, h, r=36, fill=fill)
            if j == 1:
                ImageDraw.Draw(card).rounded_rectangle((0, 0, CW - 1, h - 1), 36, outline=BLUE + (255,), width=4)
            card.alpha_composite(lp, (40, 34))
            card.alpha_composite(txt, (40, 34 + lp.height + 22))
            if j == 0:
                dd = ImageDraw.Draw(card)
                dd.line((40, 34 + lp.height + 22 + txt.height // 2, 40 + min(txt.width, CW - 90), 34 + lp.height + 22 + txt.height // 2), fill=MUTED + (0,), width=0)
            sc, pad = shadowed(card, radius=26, off=(0, 14), alpha=22 if j == 0 else 34)
            els.append(El(sc, ML - pad, cy - pad, T2 + 0.6 + j * 1.6, T3))
            cy += h + 30
            if j == 0:
                ar = Image.new("RGBA", (70, 70), (0, 0, 0, 0))
                ad = ImageDraw.Draw(ar)
                ad.polygon([(10, 18), (60, 18), (35, 58)], fill=BLUE + (255,))
                els.append(El(ar, ML + CW // 2 - 35, cy - 20, T2 + 1.6, T3, dy=20))
                cy += 50
    for i, txt in enumerate(rows):
        h = max(txt.height, 64) + 64
        card = glass(CW, h, r=36)
        ic = check_icon(64, num=i + 1 if r.get("numbered") else None)
        card.alpha_composite(ic, (34, 32))
        card.alpha_composite(txt, (128, 32 + max(0, (64 - txt.height) // 2) if txt.height < 64 else 30))
        sc, pad = shadowed(card, radius=26, off=(0, 14), alpha=26)
        els.append(El(sc, ML - pad, cy - pad, T2 + 0.6 + i * 0.55, T3))
        cy += h + 26

    # Szene 3: Zahl / Kernaussage
    st = r["stat"]
    lab = text_block(r["stat_label"], F("Inter-Medium.otf", 50), CW - 40, color=MUTED, lh=1.25)
    stat_el = dict(stat=st, t_in=T3 + 0.2)
    els.append(El(lab, ML, 1070, T3 + 0.8, T4))
    line = Image.new("RGBA", (120, 10), BLUE + (255,))
    els.append(El(line, ML, 1020, T3 + 0.5, T4, dy=0))

    # Szene 4: CTA
    cta_p = pill(r["cta"], F("Inter-Bold.otf", 40), (255, 255, 255), BLUE + (255,), padx=34, pady=18)
    els.append(El(cta_p, ML, 620, T4 + 0.1, DUR + 1))
    h4 = text_block(r.get("cta_head", "Kostenloses [Erstgespräch.]"), F("InterDisplay-Bold.otf", 108), CW)
    els.append(El(h4, ML, 740, T4 + 0.3, DUR + 1, dy=60))
    sub4 = text_block(r.get("cta_sub", "30 Minuten. Wir sehen uns Ihre Abläufe an und sagen offen, ob sich KI lohnt."),
                      F("Inter-Medium.otf", 44), CW - 40, color=MUTED, lh=1.25)
    ys = 760 + h4.height + 40
    els.append(El(sub4, ML, ys, T4 + 0.8, DUR + 1))
    btn = pill(r.get("cta_button", "bettersorted.de  →"), F("Inter-Bold.otf", 50), (255, 255, 255), NAVY + (255,), padx=46, pady=28)
    bsh, bpad = shadowed(btn, radius=24, off=(0, 14), alpha=50)
    yb = ys + sub4.height + 60
    els.append(El(bsh, ML - bpad, yb - bpad, T4 + 1.3, DUR + 1, scale=True))
    if r.get("share"):
        sh_ = text_block(r.get("share_text", "[↗] Schicken Sie das jemandem, der es braucht."), F("Inter-SemiBold.otf", 36), CW, color=NAVY)
        els.append(El(sh_, ML, yb + btn.height + 50, T4 + 1.7, DUR + 1))
        yb += 60
    badges = text_block(r.get("badges", "BAFA-zugelassen · Autorisierter INQA-Coach · Schwerin"),
                        F("Inter-SemiBold.otf", 32), CW, color=MUTED)
    els.append(El(badges, ML, yb + btn.height + 50, T4 + 1.8, DUR + 1))
    if r.get("foot"):
        ft = text_block(r["foot"], F("Inter-Regular.otf", 26), CW - 60, color=(130, 128, 145), lh=1.3)
        els.append(El(ft, ML, yb + btn.height + 110, T4 + 2.0, DUR + 1))
    return els, stat_el

SFONT = F("InterDisplay-Bold.otf", 200)

def draw_stat(frame, t, se):
    st = se["stat"]
    if t < se["t_in"] or t > T4: return
    p = ease((t - se["t_in"]) / 0.6)
    q = min(1.0, (T4 - t) / 0.32)
    if "num" in st:
        c = ease((t - se["t_in"]) / 1.6)
        s = st.get("prefix", "") + fmt_num(st["num"] * c, st.get("thousands")) + st.get("suffix", "")
    else:
        s = st["text"]
    size = 200
    f = SFONT
    while f.getlength(s) > CW and size > 90:
        size -= 8; f = F("InterDisplay-Bold.otf", size)
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (int(f.getlength(s)) + 20, asc + desc), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, 0), s, font=f, fill=BLUE)
    op = p * q
    if op < 0.999:
        im.putalpha(im.split()[3].point(lambda v: int(v * op)))
    y = 980 - (asc + desc) - 20 + int((1 - p) * 50)
    frame.alpha_composite(im, (ML - 6, y))

def chrome(frame, t, idx):
    frame.alpha_composite(LOGO, (ML, 150))
    f = F("Inter-SemiBold.otf", 30)
    s = f"{idx:02d}/{len(REELS)}"
    d = ImageDraw.Draw(frame)
    d.text((W - ML - f.getlength(s), 172), s, font=f, fill=MUTED)
    # Fortschrittsleiste
    x0, x1, y = ML, W - ML, 258
    d.rounded_rectangle((x0, y, x1, y + 6), 3, fill=(214, 228, 238, 255))
    d.rounded_rectangle((x0, y, x0 + int((x1 - x0) * min(1, t / DUR)), y + 6), 3, fill=BLUE + (255,))

def render(i):
    r = REELS[i]
    idx = i + 1
    els, se = build(r, idx)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"bettersorted-reel-{r['slug']}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", os.path.join(HERE, "assets", "sound.wav"),
           "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for k in range(n):
        t = k / FPS
        fr = bg_frame(t)
        chrome(fr, t, idx)
        for e in els: e.draw(fr, t)
        draw_stat(fr, t, se)
        pr.stdin.write(fr.convert("RGB").tobytes())
        if os.environ.get("STILLS") and k in (75, 225, 390, 560):
            fr.convert("RGB").save(os.path.join(OUT, f"still-{idx:02d}-{k}.png"))
    pr.stdin.close(); pr.wait()
    return path

if __name__ == "__main__":
    which = sys.argv[1]
    ids = range(len(REELS)) if which == "all" else [int(x) - 1 for x in which.split(",")]
    for i in ids:
        print(render(i), flush=True)
