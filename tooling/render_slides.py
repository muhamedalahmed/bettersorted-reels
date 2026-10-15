"""bettersorted – Karussell-/Bild-Generator, Design v2 „redaktionell“ (PNG + PDF).

Aufruf:
    python3 render_slides.py <spec.json> <ausgabeordner>

Designprinzipien (v2, Okt. 2026 – Mos Feedback „nicht KI-lastig, Logo kleiner“):
- flache Flächen statt Verläufe/Glas/Schatten; helles Papier (#F4F3EF) und Navy (#1C1631) im Wechsel
- klare Typografie (Inter Display), viel Weißraum, feine Linien statt Karten, keine Pillen/Emojis
- Logo klein (38 px) oben links; Fußzeile: bettersorted.de links, Seitenzahl „02 / 07“ rechts

Spec (Beispiel: content/karussell_beispiel.json):
{
  "slug": "…", "format": "portrait",      # portrait 1080x1350 | square 1080x1080 | story 1080x1920
  "slides": [
    {"type": "cover", "tag": "…", "title": "… [Wort] …", "sub": "…"},
    {"type": "list", "eyebrow": "…", "title": "…", "items": ["…"], "numbered": false, "note": "…"},
    {"type": "versus", "title": "…", "before": "…", "after": "…", "after_label": "MIT KI"},
    {"type": "stat", "value": "80 %", "label": "…"},
    {"type": "quote", "text": "…", "author": "…"},
    {"type": "cta", "badge": "…", "title": "…", "sub": "…", "button": "bettersorted.de", "trust": "…"}
  ]
}
Optional pro Slide: "theme": "dark" | "light" (Standard: cover/cta dunkel, Rest hell).
[Wort] = Akzentfarbe. Einzelbild = Spec mit einer Slide.
"""
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
NAVY = (28, 22, 49); BLUE = (63, 148, 198); SKY = (108, 207, 246)
PAPER = (244, 243, 239); INK = (28, 22, 49); GREY = (98, 96, 112); RULE = (214, 212, 205)
DARK_SUB = (190, 196, 210); DARK_RULE = (62, 56, 86)
FD = "/usr/share/fonts/opentype/inter/"
def F(name, size): return ImageFont.truetype(FD + name, size)
SIZES = {"portrait": (1080, 1350), "square": (1080, 1080), "story": (1080, 1920)}
ML = 96
LOGO_H = 38

def load_logo(height, on_dark=False):
    a = np.asarray(Image.open(os.path.join(HERE, "assets", "logo.jpeg")).convert("RGB")).astype(np.float32)
    alpha = np.clip((255 - a.min(axis=2)) / 190.0, 0, 1)
    rgb = np.where(alpha[..., None] > 0.01, (a - 255 * (1 - alpha[..., None])) / np.maximum(alpha[..., None], 0.01), 255)
    rgb = np.clip(rgb, 0, 255)
    if on_dark:  # dunkle Schrift -> weiß, Blau bleibt
        dark = rgb.max(axis=2) < 110
        rgb[dark] = 255
    im = Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")
    im = im.crop(im.getbbox())
    return im.resize((int(im.width * height / im.height), height), Image.LANCZOS)

def tokens(markup):
    out, hi = [], False
    for w in markup.split(" "):
        if w.startswith("["): hi = True; w = w[1:]
        end = "]" in w
        out.append((w.replace("]", ""), hi))
        if end: hi = False
    return out

def text_block(markup, font, maxw, color, hcolor, lh=1.12):
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
    return im.crop((0, 0, im.width, (bb[3] + 4) if bb else im.height))

def fit_font(markup, name, size, maxw, minsize=48):
    while size > minsize and max(F(name, size).getlength(w) for w, _ in tokens(markup)) > maxw - 10: size -= 4
    return F(name, size)

def eyebrow(text, color, line_color):
    f = F("Inter-SemiBold.otf", 28)
    txt = " ".join(text.upper())  # Sperrung
    txt = text.upper()
    w = int(64 + f.getlength(txt) + 40); asc, desc = f.getmetrics()
    im = Image.new("RGBA", (w + 20, asc + desc + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    y = (asc + desc) // 2
    d.line((0, y, 44, y), fill=line_color, width=3)
    x = 64
    for ch in txt:
        d.text((x, 0), ch, font=f, fill=color); x += f.getlength(ch) + 2.5
    return im.crop((0, 0, int(x) + 4, im.height))

def rule(w, color, thick=2):
    im = Image.new("RGBA", (w, thick), color + (255,)); return im

def place(img, blocks, top, bottom, center):
    total = sum(b[0].height + b[2] for b in blocks) - (blocks[-1][2] if blocks else 0)
    y = top + (max(0, (bottom - top - total) // 2) if center else 0)
    for im, xo, gap in blocks:
        img.alpha_composite(im, (ML + xo, y)); y += im.height + gap

def list_rows(items, numbered, CW, c):
    rows = []
    fnum = F("InterDisplay-SemiBold.otf", 40); ftxt = F("Inter-Medium.otf", 42)
    indent = 96 if numbered else 52
    for k, it in enumerate(items):
        txt = text_block(it, ftxt, CW - indent, c["ink"], c["acc"], lh=1.28)
        h = txt.height + 56
        row = Image.new("RGBA", (CW, h + 2), (0, 0, 0, 0)); d = ImageDraw.Draw(row)
        d.line((0, 0, CW, 0), fill=c["rule"], width=2)
        if numbered:
            d.text((0, 26), f"{k + 1:02d}", font=fnum, fill=c["acc"])
        else:
            d.rectangle((0, 46, 14, 60), fill=c["acc"])
        row.alpha_composite(txt, (indent, 28))
        if k == len(items) - 1: d.line((0, h, CW, h), fill=c["rule"], width=2)
        rows.append(row)
    return rows

def slide(spec, W, H, i, n, logos):
    t = spec["type"]
    theme = spec.get("theme") or ("dark" if t in ("cover", "cta") else "light")
    dark = theme == "dark"
    c = dict(bg=NAVY if dark else PAPER, ink=(255, 255, 255) if dark else INK, sub=DARK_SUB if dark else GREY,
             acc=SKY if dark else BLUE, rule=DARK_RULE if dark else RULE)
    img = Image.new("RGBA", (W, H), c["bg"] + (255,))
    CW = W - 2 * ML; blocks = []; center = t in ("cover", "stat", "cta", "quote")
    if t == "cover":
        if spec.get("tag"): blocks.append((eyebrow(spec["tag"], c["acc"], c["acc"]), 0, 40))
        blocks.append((text_block(spec["title"], fit_font(spec["title"], "InterDisplay-Bold.otf", 116, CW), CW, c["ink"], c["acc"], lh=1.04), 0, 44))
        if spec.get("sub"): blocks.append((text_block(spec["sub"], F("Inter-Regular.otf", 42), CW - 60, c["sub"], c["acc"], lh=1.35), 0, 0))
    elif t == "list":
        if spec.get("eyebrow"): blocks.append((eyebrow(spec["eyebrow"], c["acc"], c["acc"]), 0, 28))
        blocks.append((text_block(spec["title"], fit_font(spec["title"], "InterDisplay-Bold.otf", 80, CW), CW, c["ink"], c["acc"], lh=1.06), 0, 56))
        for r in list_rows(spec["items"], spec.get("numbered"), CW, c): blocks.append((r, 0, 0))
        if spec.get("note"):
            blocks[-1] = (blocks[-1][0], 0, 36)
            blocks.append((text_block(spec["note"], F("Inter-Regular.otf", 32), CW, c["sub"], c["acc"], lh=1.35), 0, 0))
    elif t == "versus":
        if spec.get("eyebrow"): blocks.append((eyebrow(spec["eyebrow"], c["acc"], c["acc"]), 0, 28))
        blocks.append((text_block(spec["title"], fit_font(spec["title"], "InterDisplay-Bold.otf", 80, CW), CW, c["ink"], c["acc"], lh=1.06), 0, 64))
        for k, (lab, txt_) in enumerate(((spec.get("before_label", "VORHER"), spec["before"]), (spec.get("after_label", "MIT KI"), spec["after"]))):
            col = c["sub"] if k == 0 else c["acc"]
            lab_im = eyebrow(lab, col, col)
            txt = text_block(txt_, F("InterDisplay-SemiBold.otf", 50), CW - 40, c["sub"] if k == 0 else c["ink"], c["acc"], lh=1.2)
            h = lab_im.height + 22 + txt.height
            blk = Image.new("RGBA", (CW, h), (0, 0, 0, 0))
            blk.alpha_composite(lab_im, (0, 0)); blk.alpha_composite(txt, (0, lab_im.height + 22))
            blocks.append((blk, 0, 34))
            if k == 0: blocks.append((rule(CW, c["rule"]), 0, 34))
    elif t == "stat":
        if spec.get("eyebrow"): blocks.append((eyebrow(spec["eyebrow"], c["acc"], c["acc"]), 0, 30))
        v = spec["value"]; size = 240
        while F("InterDisplay-Bold.otf", size).getlength(v) > CW and size > 100: size -= 8
        f = F("InterDisplay-Bold.otf", size); asc, desc = f.getmetrics()
        im = Image.new("RGBA", (int(f.getlength(v)) + 20, asc + desc), (0, 0, 0, 0)); ImageDraw.Draw(im).text((0, 0), v, font=f, fill=c["acc"])
        im = im.crop((0, 0, im.width, im.getbbox()[3] + 10))
        blocks.append((im, -8, 36)); blocks.append((rule(120, c["acc"], 4), 0, 40))
        blocks.append((text_block(spec["label"], F("Inter-Regular.otf", 48), CW - 40, c["ink"], c["acc"], lh=1.32), 0, 0))
    elif t == "quote":
        blocks.append((rule(120, c["acc"], 4), 0, 44))
        blocks.append((text_block(spec["text"], F("InterDisplay-SemiBold.otf", 62), CW, c["ink"], c["acc"], lh=1.25), 0, 40))
        if spec.get("author"): blocks.append((text_block(spec["author"], F("Inter-Medium.otf", 36), CW, c["sub"], c["acc"]), 0, 0))
    elif t == "cta":
        if spec.get("badge"): blocks.append((eyebrow(spec["badge"], c["acc"], c["acc"]), 0, 40))
        title = spec.get("title", "Kostenloses [Erstgespräch.]")
        blocks.append((text_block(title, fit_font(title, "InterDisplay-Bold.otf", 104, CW), CW, c["ink"], c["acc"], lh=1.05), 0, 36))
        blocks.append((text_block(spec.get("sub", "30 Minuten. Wir sehen uns Ihre Abläufe an und sagen offen, ob sich KI lohnt."), F("Inter-Regular.otf", 42), CW - 40, c["sub"], c["acc"], lh=1.35), 0, 56))
        bf = F("Inter-SemiBold.otf", 44); label = spec.get("button", "bettersorted.de")
        bw = int(bf.getlength(label) + 2 * 44 + 50); asc, desc = bf.getmetrics(); bh = asc + desc + 44
        btn = Image.new("RGBA", (bw, bh), (0, 0, 0, 0)); d = ImageDraw.Draw(btn)
        d.rounded_rectangle((0, 0, bw - 1, bh - 1), 8, fill=c["acc"])
        d.text((44, 18), label, font=bf, fill=NAVY if dark else (255, 255, 255))
        ax = bw - 64; ay = bh // 2
        d.line((ax, ay, ax + 26, ay), fill=NAVY if dark else (255, 255, 255), width=4)
        d.line((ax + 14, ay - 12, ax + 26, ay), fill=NAVY if dark else (255, 255, 255), width=4)
        d.line((ax + 14, ay + 12, ax + 26, ay), fill=NAVY if dark else (255, 255, 255), width=4)
        blocks.append((btn, 0, 44))
        blocks.append((text_block(spec.get("trust", "BAFA-zugelassen · Autorisierter INQA-Coach · Schwerin"), F("Inter-Regular.otf", 30), CW, c["sub"], c["acc"]), 0, 0))
    else:
        raise ValueError("Unbekannter Slide-Typ: " + t)
    top = 230 if not center else 200
    place(img, blocks, top, H - 160, center)
    # Kopf & Fuß
    logo = logos["dark" if dark else "light"]
    img.alpha_composite(logo, (ML, 84))
    d = ImageDraw.Draw(img); f = F("Inter-Medium.otf", 28)
    d.line((ML, H - 110, W - ML, H - 110), fill=c["rule"], width=2)
    d.text((ML, H - 90), "bettersorted.de", font=f, fill=c["sub"])
    if n > 1:
        s = f"{i:02d} / {n:02d}"; d.text((W - ML - f.getlength(s), H - 90), s, font=f, fill=c["sub"])
    return img.convert("RGB")

def main(spec_path, out_dir):
    spec = json.load(open(spec_path, encoding="utf-8"))
    W, H = SIZES[spec.get("format", "portrait")]
    os.makedirs(out_dir, exist_ok=True)
    logos = {"light": load_logo(LOGO_H), "dark": load_logo(LOGO_H, on_dark=True)}
    n = len(spec["slides"]); files = []
    for i, s in enumerate(spec["slides"], 1):
        p = os.path.join(out_dir, f"{spec['slug']}-{i:02d}.png"); slide(s, W, H, i, n, logos).save(p, optimize=True); files.append(p); print(p)
    if n > 1:
        pdf = os.path.join(out_dir, f"{spec['slug']}.pdf")
        ims = [Image.open(f).convert("RGB") for f in files]; ims[0].save(pdf, save_all=True, append_images=ims[1:], resolution=144); print(pdf)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "out")
