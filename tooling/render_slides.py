"""bettersorted – Karussell-/Bild-Generator (PNG + PDF für LinkedIn-Dokument-Posts).

Aufruf:
    python3 render_slides.py <spec.json> <ausgabeordner>

Format der spec.json (Beispiel: content/karussell_beispiel.json):
{
  "slug": "foerderung-ueberblick",
  "format": "portrait",            # portrait 1080x1350 (Standard, IG+LinkedIn+FB) | square 1080x1080 | story 1080x1920
  "slides": [
    {"type": "cover", "tag": "FÖRDERUNG", "title": "3 Fördertöpfe für [KI im Betrieb]", "sub": "Wischen Sie durch →"},
    {"type": "list", "eyebrow": "TOPF 1", "title": "INQA-Coaching", "items": ["…", "…"], "numbered": false},
    {"type": "versus", "title": "…", "before": "…", "after": "…"},
    {"type": "stat", "value": "80 %", "label": "…"},
    {"type": "quote", "text": "…", "author": "…"},
    {"type": "cta", "badge": "Bis zu 80 % gefördert", "title": "Kostenloses [Erstgespräch.]", "sub": "…", "button": "bettersorted.de  →"}
  ]
}
[Wort] im Text = blau hervorgehoben. Ein Einzelbild ist einfach ein Karussell mit einer Slide.
"""
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
NAVY = (28, 22, 49); BLUE = (63, 148, 198); SKY = (108, 207, 246)
MUTED = (84, 82, 104); BG = (244, 249, 252)
FD = "/usr/share/fonts/opentype/inter/"
def F(name, size): return ImageFont.truetype(FD + name, size)
SIZES = {"portrait": (1080, 1350), "square": (1080, 1080), "story": (1080, 1920)}
ML = 90

def load_logo(height):
    a = np.asarray(Image.open(os.path.join(HERE, "assets", "logo.jpeg")).convert("RGB")).astype(np.float32)
    alpha = np.clip((255 - a.min(axis=2)) / 190.0, 0, 1)
    rgb = np.where(alpha[..., None] > 0.01, (a - 255 * (1 - alpha[..., None])) / np.maximum(alpha[..., None], 0.01), 255)
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8), "RGBA")
    im = im.crop(im.getbbox())
    return im.resize((int(im.width * height / im.height), height), Image.LANCZOS)

def background(W, H, seed):
    img = Image.new("RGB", (W, H), BG)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(seed)
    for col, a in ((SKY, 120), (BLUE, 60), (SKY, 80)):
        cx, cy = rng.integers(0, W), rng.integers(0, H); r = int(rng.integers(320, 520))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (a,))
    lay = lay.filter(ImageFilter.GaussianBlur(150)); img.paste(lay, (0, 0), lay)
    net = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(net); c = BLUE + (24,)
    ox, oy = W - 260, H - 330
    for nx, ny in ((ox + 300, oy - 230), (ox + 340, oy), (ox + 300, oy + 230)):
        d.line((ox, oy, nx, ny), fill=c, width=12)
        d.ellipse((nx - 40, ny - 40, nx + 40, ny + 40), outline=c, width=14)
    img.paste(net, (0, 0), net)
    return img.convert("RGBA")

def tokens(markup):
    out, hi = [], False
    for w in markup.split(" "):
        if w.startswith("["): hi = True; w = w[1:]
        end = "]" in w
        out.append((w.replace("]", ""), hi))
        if end: hi = False
    return out

def text_block(markup, font, maxw, color=NAVY, hcolor=BLUE, lh=1.15):
    toks = tokens(markup); sp = font.getlength(" ")
    lines, cur, cw = [], [], 0
    for w, hi in toks:
        wl = font.getlength(w)
        if cur and cw + sp + wl > maxw: lines.append(cur); cur, cw = [], 0
        cw = cw + (sp if cur else 0) + wl; cur.append((w, hi))
    if cur: lines.append(cur)
    asc, desc = font.getmetrics(); lhp = int((asc + desc) * lh)
    im = Image.new("RGBA", (maxw + 40, lhp * len(lines) + desc + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        x = 0
        for w, hi in ln:
            d.text((x, i * lhp), w, font=font, fill=hcolor if hi else color); x += font.getlength(w) + sp
    bb = im.getbbox()
    return im.crop((0, 0, im.width, (bb[3] + 6) if bb else im.height))

def fit_font(markup, name, size, maxw, minsize=48):
    while size > minsize and max(F(name, size).getlength(w) for w, _ in tokens(markup)) > maxw - 20: size -= 4
    return F(name, size)

def pill(text, font, fg, bg, padx=28, pady=14, outline=None):
    asc, desc = font.getmetrics(); w = int(font.getlength(text) + 2 * padx); h = asc + desc + 2 * pady - 8
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=bg, outline=outline, width=3 if outline else 0)
    d.text((padx, pady - 4), text, font=font, fill=fg); return im

def card(w, h, fill=(255, 255, 255, 205), border=None):
    pad = 40; im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 12, pad + w, pad + h + 12), 34, fill=NAVY + (28,))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(im); d.rounded_rectangle((pad, pad, pad + w, pad + h), 34, fill=fill, outline=border or (255, 255, 255, 240), width=4 if border else 3)
    return im, pad

def icon(size, num=None, cross=False):
    s = size * 4; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, s - 1, s - 1), fill=(MUTED if cross else BLUE) + (255,))
    if cross:
        d.line((s * .32, s * .32, s * .68, s * .68), fill="white", width=int(s * .1)); d.line((s * .68, s * .32, s * .32, s * .68), fill="white", width=int(s * .1))
    elif num is None:
        d.line([(s * .28, s * .52), (s * .44, s * .68), (s * .73, s * .35)], fill="white", width=int(s * .1), joint="curve")
    else:
        f = F("Inter-Bold.otf", int(s * .55)); asc, desc = f.getmetrics()
        d.text(((s - f.getlength(str(num))) / 2, (s - asc - desc) / 2), str(num), font=f, fill="white")
    return im.resize((size, size), Image.LANCZOS)

def chrome(img, i, n, logo):
    W, H = img.size; d = ImageDraw.Draw(img)
    img.alpha_composite(logo, (ML, 70))
    f = F("Inter-SemiBold.otf", 30)
    if n > 1:
        s = f"{i}/{n}"; d.text((W - ML - f.getlength(s), 88), s, font=f, fill=MUTED)
        # Punkte unten
        dot, gap = 12, 14; tw = n * dot + (n - 1) * gap; x = (W - tw) // 2
        for k in range(n):
            col = BLUE if k == i - 1 else (200, 214, 226)
            d.ellipse((x, H - 70, x + dot, H - 70 + dot), fill=col); x += dot + gap
    else:
        s = "bettersorted.de"; d.text((W - ML - f.getlength(s), 88), s, font=f, fill=MUTED)

def place_column(img, blocks, top, bottom):
    """blocks: Liste (Image, x_offset, gap_after). Vertikal zentriert zwischen top und bottom."""
    total = sum(b[0].height + b[2] for b in blocks) - (blocks[-1][2] if blocks else 0)
    y = top + max(0, (bottom - top - total) // 2)
    for im, xo, gap in blocks:
        img.alpha_composite(im, (ML + xo, y)); y += im.height + gap

def slide(spec, W, H, i, n, logo):
    img = background(W, H, seed=i * 7 + 3)
    CW = W - 2 * ML; t = spec["type"]; blocks = []
    if t == "cover":
        if spec.get("tag"): blocks.append((pill(spec["tag"], F("Inter-Bold.otf", 34), BLUE, (255, 255, 255, 220), outline=SKY + (255,)), 0, 34))
        blocks.append((text_block(spec["title"], fit_font(spec["title"], "InterDisplay-Bold.otf", 112, CW), CW), 0, 48))
        if spec.get("sub"): blocks.append((text_block(spec["sub"], F("Inter-Medium.otf", 44), CW - 40, color=MUTED, lh=1.3), 0, 0))
    elif t == "list":
        if spec.get("eyebrow"): blocks.append((pill(spec["eyebrow"], F("Inter-SemiBold.otf", 30), (255, 255, 255), BLUE + (255,), padx=22, pady=12), 0, 24))
        blocks.append((text_block(spec["title"], fit_font(spec["title"], "InterDisplay-Bold.otf", 76, CW), CW), 0, 34))
        for k, it in enumerate(spec["items"]):
            txt = text_block(it, F("Inter-Medium.otf", 42), CW - 150, lh=1.25)
            h = max(txt.height, 60) + 56; c, pad = card(CW, h)
            c.alpha_composite(icon(60, num=k + 1 if spec.get("numbered") else None), (pad + 30, pad + 28))
            c.alpha_composite(txt, (pad + 118, pad + 28 + max(0, (60 - txt.height) // 2)))
            blocks.append((c, -pad, 18 - 2 * pad))
        if spec.get("note"):
            blocks[-1] = (blocks[-1][0], blocks[-1][1], -12)
            blocks.append((text_block(spec["note"], F("Inter-Medium.otf", 36), CW, color=MUTED, lh=1.3), 0, 0))
    elif t == "versus":
        blocks.append((text_block(spec["title"], fit_font(spec["title"], "InterDisplay-Bold.otf", 76, CW), CW), 0, 34))
        for k, (lab, txt_, col) in enumerate((("VORHER", spec["before"], MUTED), (spec.get("after_label", "MIT KI"), spec["after"], BLUE))):
            lp = pill(lab, F("Inter-Bold.otf", 28), (255, 255, 255), col + (255,), padx=20, pady=10)
            txt = text_block(txt_, F("Inter-SemiBold.otf", 46), CW - 90, color=NAVY if k else MUTED, lh=1.25)
            h = lp.height + txt.height + 90
            c, pad = card(CW, h, fill=(255, 255, 255, 140 if k == 0 else 230), border=BLUE + (255,) if k else None)
            c.alpha_composite(lp, (pad + 40, pad + 34)); c.alpha_composite(txt, (pad + 40, pad + 34 + lp.height + 22))
            blocks.append((c, -pad, 26 - 2 * pad))
    elif t == "stat":
        v = spec["value"]; size = 230
        while F("InterDisplay-Bold.otf", size).getlength(v) > CW and size > 100: size -= 8
        f = F("InterDisplay-Bold.otf", size); asc, desc = f.getmetrics()
        im = Image.new("RGBA", (int(f.getlength(v)) + 20, asc + desc), (0, 0, 0, 0)); ImageDraw.Draw(im).text((0, 0), v, font=f, fill=BLUE)
        blocks.append((im, -6, 10)); blocks.append((Image.new("RGBA", (120, 10), BLUE + (255,)), 0, 36))
        blocks.append((text_block(spec["label"], F("Inter-Medium.otf", 50), CW - 40, color=MUTED, lh=1.3), 0, 0))
    elif t == "quote":
        q = F("InterDisplay-Bold.otf", 200); qi = Image.new("RGBA", (140, 160), (0, 0, 0, 0)); ImageDraw.Draw(qi).text((0, -40), "„", font=q, fill=SKY)
        blocks.append((qi, 0, 0)); blocks.append((text_block(spec["text"], F("InterDisplay-SemiBold.otf", 58), CW, lh=1.3), 0, 36))
        if spec.get("author"): blocks.append((text_block("— " + spec["author"], F("Inter-SemiBold.otf", 38), CW, color=MUTED), 0, 0))
    elif t == "cta":
        if spec.get("badge"): blocks.append((pill(spec["badge"], F("Inter-Bold.otf", 38), (255, 255, 255), BLUE + (255,), padx=32, pady=16), 0, 34))
        blocks.append((text_block(spec.get("title", "Kostenloses [Erstgespräch.]"), fit_font(spec.get("title", "Kostenloses [Erstgespräch.]"), "InterDisplay-Bold.otf", 104, CW), CW), 0, 30))
        blocks.append((text_block(spec.get("sub", "30 Minuten. Wir sehen uns Ihre Abläufe an und sagen offen, ob sich KI lohnt."), F("Inter-Medium.otf", 42), CW - 40, color=MUTED, lh=1.3), 0, 50))
        btn = pill(spec.get("button", "bettersorted.de  →"), F("Inter-Bold.otf", 48), (255, 255, 255), NAVY + (255,), padx=44, pady=26)
        blocks.append((btn, 0, 40))
        blocks.append((text_block(spec.get("trust", "BAFA-zugelassen · Autorisierter INQA-Coach · Schwerin"), F("Inter-SemiBold.otf", 30), CW, color=MUTED), 0, 0))
    else:
        raise ValueError("Unbekannter Slide-Typ: " + t)
    place_column(img, blocks, 200, H - 130)
    chrome(img, i, n, logo)
    return img.convert("RGB")

def main(spec_path, out_dir):
    spec = json.load(open(spec_path, encoding="utf-8"))
    W, H = SIZES[spec.get("format", "portrait")]
    os.makedirs(out_dir, exist_ok=True); logo = load_logo(60)
    n = len(spec["slides"]); files = []
    for i, s in enumerate(spec["slides"], 1):
        p = os.path.join(out_dir, f"{spec['slug']}-{i:02d}.png"); slide(s, W, H, i, n, logo).save(p, optimize=True); files.append(p); print(p)
    if n > 1:
        pdf = os.path.join(out_dir, f"{spec['slug']}.pdf")
        ims = [Image.open(f).convert("RGB") for f in files]; ims[0].save(pdf, save_all=True, append_images=ims[1:], resolution=144); print(pdf)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "out")
