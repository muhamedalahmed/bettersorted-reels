"""bettersorted - photo recap reel (9:16, 30 fps), design v4.
Event photos with slow zoom, white caption cards with blue highlights, light CTA end card.
Usage: python3 render_photo_reel.py <spec.json> <out.mp4>
Spec: {"scenes": [{"photo": path, "dur": s, "caption": "markup", "sub": "optional"}],
       "cta": {"dur": s, "eyebrow": "...", "title": "markup", "sub": "...", "button": "..."},
       "footer_right": "..."}
"""
import sys, os, json, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_slides import F, load_logo, motif, soft_tint, tokens, PAPER, INK, GREY, BLUE, RULE, NAVY, HERE

W, H, FPS = 1080, 1920, 30
ML = 56
XF = 0.4  # crossfade duration


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def card(w, h, r=28, a=244):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=(255, 255, 255, a), outline=(214, 228, 238, 255), width=2)
    return im, d


def wrap(markup, font, maxw):
    toks = tokens(markup)
    sp = font.getlength(" ")
    lines, cur, cw = [], [], 0
    for w, hi in toks:
        wl = font.getlength(w)
        if cur and cw + sp + wl > maxw:
            lines.append((cur, cw)); cur, cw = [], 0
        cw += (sp if cur else 0) + wl
        cur.append((w, hi))
    lines.append((cur, cw))
    return lines


def draw_lines(d, lines, font, x0, y0, lh, center_w=None):
    for i, (ln, cw) in enumerate(lines):
        x = x0 + ((center_w - cw) / 2 if center_w else 0)
        y = y0 + i * lh
        for w, hi in ln:
            d.text((x, y), w, font=font, fill=BLUE if hi else INK, anchor="lm")
            x += font.getlength(w) + font.getlength(" ")


def caption_card(markup, sub=None):
    f = F("InterDisplay-Bold.otf", 62)
    lh = 78
    maxw = W - 2 * ML - 88
    lines = wrap(markup, f, maxw)
    fs = F("Inter-Medium.otf", 34)
    sub_h = 64 if sub else 0
    cw = W - 2 * ML
    ch = len(lines) * lh + 76 + sub_h
    im, d = card(cw, ch)
    draw_lines(d, lines, f, 44, 38 + lh / 2, lh)
    if sub:
        d.text((44, 38 + len(lines) * lh + 30), sub, font=fs, fill=GREY, anchor="lm")
    return im


def prep_photo(path):
    """Return a 9:16 base image 12% larger than the frame, for the slow zoom."""
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    BW, BH = int(W * 1.12), int(H * 1.12)
    if im.width / im.height > 0.8:
        # landscape: blurred cover background + full photo as rounded card
        bg = ImageOps.fit(im, (BW, BH), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))
        bg = Image.blend(bg, Image.new("RGB", bg.size, NAVY), 0.35)
        pw = BW - 2 * 70
        ph = int(im.height * pw / im.width)
        p = im.resize((pw, ph), Image.LANCZOS)
        mask = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=28, fill=255)
        bg.paste(p, (70, int(BH * 0.40 - ph / 2)), mask)
        return bg
    return ImageOps.fit(im, (BW, BH), Image.LANCZOS, centering=(0.5, 0.45))


def zoom_frame(base, k):
    """k in [0,1]: zoom from 1.0 (crop of 1/1.12) to 1.06 relative."""
    s = 1.0 + 0.06 * k
    cw, ch = W / s, H / s
    cx, cy = base.width / 2, base.height / 2
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return base.resize((W, H), Image.BILINEAR, box=box)


def cta_frame(spec, logo):
    fr = Image.new("RGBA", (W, H), PAPER + (255,))
    fr.alpha_composite(soft_tint(W, H))
    fr.alpha_composite(motif(W, H, False, strong=True))
    d = ImageDraw.Draw(fr)
    fr.alpha_composite(logo, (96, 120))
    d.text((96, 560), spec["eyebrow"].upper(), font=F("Inter-SemiBold.otf", 34), fill=BLUE, anchor="lm")
    ft = F("InterDisplay-Bold.otf", 92)
    lines = wrap(spec["title"], ft, W - 2 * 96 - 40)
    draw_lines(d, lines, ft, 96, 680, 108)
    y = 680 + len(lines) * 108 + 40
    fs = F("Inter-Regular.otf", 42)
    for ln, _ in wrap(spec["sub"], fs, W - 2 * 96 - 160):
        d.text((96, y), " ".join(w for w, _ in ln), font=fs, fill=GREY, anchor="lm"); y += 58
    y += 50
    fb = F("Inter-SemiBold.otf", 40)
    bw = int(fb.getlength(spec["button"])) + 88
    d.rounded_rectangle((96, y, 96 + bw, y + 96), radius=20, fill=NAVY)
    d.text((96 + bw / 2, y + 48), spec["button"], font=fb, fill=(255, 255, 255), anchor="mm")
    d.line((96, H - 150, W - 96, H - 150), fill=RULE, width=2)
    d.text((96, H - 105), "BAFA-zugelassen · Autorisierter INQA-Coach · Schwerin", font=F("Inter-Regular.otf", 30), fill=GREY, anchor="lm")
    return fr


def main(spec_path, out):
    spec = json.load(open(spec_path))
    logo = load_logo(44)
    logo_card, _ = card(logo.width + 48, logo.height + 36, 20, 240)
    logo_card.alpha_composite(logo, (24, 18))
    foot_f = F("Inter-Medium.otf", 30)

    scenes = []
    t = 0.0
    for sc in spec["scenes"]:
        scenes.append({"t0": t, "t1": t + sc["dur"], "base": prep_photo(sc["photo"]),
                       "cap": caption_card(sc["caption"], sc.get("sub"))})
        t += sc["dur"]
    cta_t0 = t
    dur = t + spec["cta"]["dur"]
    cta = cta_frame(spec["cta"], load_logo(52))

    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-stream_loop", "-1", "-i", os.path.join(HERE, "assets", "sound.wav"), "-t", f"{dur:.2f}",
           "-c:v", "libx264", "-crf", "19", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "160k",
           "-af", f"volume=0.8,afade=t=in:st=0:d=0.4,afade=t=out:st={dur - 1.0:.2f}:d=1.0", "-shortest", out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def scene_img(sc, tt):
        k = (tt - sc["t0"]) / (sc["t1"] - sc["t0"] + XF)
        fr = zoom_frame(sc["base"], k).convert("RGBA")
        fr.alpha_composite(logo_card, (ML, 64))
        # caption slides up shortly after the scene starts
        a = ease((tt - sc["t0"] - 0.15) / 0.45)
        if a > 0:
            c = sc["cap"]
            y = H - 230 - c.height + int((1 - a) * 60)
            if a < 1:
                c = c.copy(); c.putalpha(c.getchannel("A").point(lambda v: int(v * a)))
            fr.alpha_composite(c, (ML, y))
        d = ImageDraw.Draw(fr)
        d.text((W / 2, H - 120), spec.get("footer_right", "bettersorted.de"), font=foot_f, fill=(255, 255, 255), anchor="mm",
               stroke_width=2, stroke_fill=(28, 22, 49))
        return fr

    n = int(round(dur * FPS))
    for i in range(n):
        tt = i / FPS
        if tt >= cta_t0:
            fr = cta
            if tt < cta_t0 + XF:  # crossfade from last scene
                prev = scene_img(scenes[-1], tt)
                fr = Image.blend(prev, cta, ease((tt - cta_t0) / XF))
        else:
            idx = max(j for j, sc in enumerate(scenes) if sc["t0"] <= tt)
            fr = scene_img(scenes[idx], tt)
            if idx > 0 and tt < scenes[idx]["t0"] + XF:
                prev = scene_img(scenes[idx - 1], tt)
                fr = Image.blend(prev, fr, ease((tt - scenes[idx]["t0"]) / XF))
        enc.stdin.write(fr.convert("RGB").tobytes())
    enc.stdin.close()
    enc.wait()
    print("wrote", out, f"{dur:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
