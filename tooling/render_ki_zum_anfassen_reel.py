"""bettersorted - Reel "KI zum Anfassen heute Abend" (9:16, 20 s, 30 fps), design v4.
Scenes: hook with count-up numbers -> screenshot 1 (Google) -> screenshot 2 (Google AI) -> automaisa Hub -> CTA.
Usage: python3 render_ki_zum_anfassen_reel.py <shot_google.png> <shot_ai.png> <out.mp4>
"""
import sys, os, subprocess
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_slides import F, load_logo, motif, soft_tint, PAPER, INK, GREY, BLUE, RULE, HERE

W, H, FPS, DUR = 1080, 1920, 30, 20.0
ML = 48


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def fade(t, a, b, fin=0.35, fout=0.3):
    """Alpha for an element visible from a to b."""
    if t < a or t > b + fout:
        return 0.0
    ai = ease((t - a) / fin)
    ao = 1.0 if t <= b else 1 - (t - b) / fout
    return ai * ao


def paste(fr, im, x, y, a=1.0, dy=0):
    if a <= 0.01:
        return
    if a < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    fr.alpha_composite(im, (int(x), int(y + dy)))


def card(w, h, r=28, a=245):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=(255, 255, 255, a), outline=(214, 228, 238, 255), width=2)
    return im, d


def fmt(n):
    return f"{int(round(n)):,}".replace(",", ".")


def text_center(d, cx, y, s, font, fill):
    d.text((cx, y), s, font=font, fill=fill, anchor="mm")


def shot_card(path, label):
    """Screenshot in a white card with a small label on top."""
    s = Image.open(path).convert("RGBA")
    cw = W - 2 * ML
    sw = cw - 40
    sh = int(s.height * sw / s.width)
    s = s.resize((sw, sh), Image.LANCZOS)
    im, d = card(cw, sh + 120, 28, 250)
    d.text((24, 40), label, font=F("Inter-SemiBold.otf", 30), fill=BLUE, anchor="lm")
    im.alpha_composite(s, (20, 80))
    return im


def stat_card(title, old, new, unit, big_new):
    """Before/after card: old (grey, small) -> new (blue, big)."""
    cw = W - 2 * ML
    im, d = card(cw, 330, 28, 250)
    d.text((40, 52), title, font=F("Inter-SemiBold.otf", 32), fill=GREY, anchor="lm")
    d.text((40, 150), "vorher", font=F("Inter-Regular.otf", 28), fill=GREY, anchor="lm")
    d.text((40, 200), old, font=F("InterDisplay-Bold.otf", 64), fill=GREY, anchor="lm")
    d.text((cw // 2 - 10, 200), "→", font=F("InterDisplay-Bold.otf", 64), fill=BLUE, anchor="mm")
    d.text((cw // 2 + 70, 150), "jetzt", font=F("Inter-Regular.otf", 28), fill=GREY, anchor="lm")
    d.text((cw // 2 + 70, 215), new, font=F("InterDisplay-Bold.otf", big_new), fill=BLUE, anchor="lm")
    d.text((40, 290), unit, font=F("Inter-Regular.otf", 28), fill=GREY, anchor="lm")
    return im


def main(shot_google, shot_ai, out):
    # static background
    bg = Image.new("RGBA", (W, H), PAPER + (255,))
    bg.alpha_composite(soft_tint(W, H))
    bg.alpha_composite(motif(W, H, False))
    logo = load_logo(44)
    f_foot = F("Inter-Medium.otf", 30)
    f_hook = F("InterDisplay-Bold.otf", 150)
    f_h1 = F("InterDisplay-Bold.otf", 78)
    f_h2 = F("InterDisplay-Bold.otf", 64)
    f_sub = F("Inter-Regular.otf", 42)
    f_semi = F("Inter-SemiBold.otf", 40)

    img1 = shot_card(shot_google, "GOOGLE SEARCH CONSOLE · letzte 28 Tage vs. davor")
    img2 = shot_card(shot_ai, "GOOGLE SEARCH CONSOLE · KI-Funktionen")

    # time windows (seconds)
    T_HOOK = (0.0, 4.4)
    T_S1 = (4.4, 9.4)
    T_S2 = (9.4, 14.2)
    T_HUB = (14.2, 17.2)
    T_CTA = (17.2, 20.0)

    dec_cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
               "-i", "-", "-i", os.path.join(HERE, "assets", "sound.wav"), "-t", str(DUR),
               "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-af", "volume=0.8,afade=t=out:st=19.2:d=0.8", "-shortest", out]
    enc = subprocess.Popen(dec_cmd, stdin=subprocess.PIPE)

    n = int(DUR * FPS)
    for i in range(n):
        t = i / FPS
        fr = bg.copy()
        d = ImageDraw.Draw(fr)
        # header logo + footer
        fr.alpha_composite(logo, (ML, 56))
        d.line((ML, H - 110, W - ML, H - 110), fill=RULE, width=2)
        d.text((ML, H - 70), "bettersorted.de", font=f_foot, fill=GREY, anchor="lm")
        d.text((W - ML, H - 70), "KI zum Anfassen · heute 18:30", font=f_foot, fill=GREY, anchor="rm")

        # --- hook: count-up of impressions
        a = fade(t, *T_HOOK)
        if a > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            k = ease((t - 0.3) / 2.2)
            val = 11802 + (59135 - 11802) * k
            ld.text((W // 2, 640), "Google-Impressionen", font=f_semi, fill=GREY, anchor="mm")
            ld.text((W // 2, 760), "11.802", font=F("InterDisplay-Bold.otf", 110), fill=GREY, anchor="mm")
            ld.text((W // 2, 880), "↓", font=F("InterDisplay-Bold.otf", 90), fill=BLUE, anchor="mm")
            ld.text((W // 2, 1050), fmt(val), font=f_hook, fill=BLUE, anchor="mm")
            ld.text((W // 2, 1200), "in nur 28 Tagen", font=f_h2, fill=INK, anchor="mm")
            paste(fr, lay, 0, 0, a, (1 - ease((t - T_HOOK[0]) / 0.4)) * 30)

        # --- screenshot 1 + stats
        a = fade(t, *T_S1)
        if a > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            lay.alpha_composite(img1, (ML, 360))
            sc = stat_card("Google-Suche (Web)", "11.802", "59.135", "Impressionen · Klicks: 112 → 436", 84)
            lay.alpha_composite(sc, (ML, 360 + img1.height + 40))
            paste(fr, lay, 0, 0, a, (1 - ease((t - T_S1[0]) / 0.4)) * 40)

        # --- screenshot 2 + stats
        a = fade(t, *T_S2)
        if a > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            lay.alpha_composite(img2, (ML, 360))
            sc = stat_card("KI-Funktionen in der Google-Suche", "1.386", "9.599", "Auftritte in den letzten 28 Tagen", 100)
            lay.alpha_composite(sc, (ML, 360 + img2.height + 40))
            paste(fr, lay, 0, 0, a, (1 - ease((t - T_S2[0]) / 0.4)) * 40)

        # --- automaisa Hub
        a = fade(t, *T_HUB)
        if a > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ld.text((W // 2, 700), "Seit 4 Wochen arbeitet", font=f_h1, fill=INK, anchor="mm")
            ld.text((W // 2, 800), "unser", font=f_h1, fill=INK, anchor="mm")
            ld.text((W // 2, 920), "automaisa Hub", font=F("InterDisplay-Bold.otf", 110), fill=BLUE, anchor="mm")
            ld.text((W // 2, 1040), "mit.", font=f_h1, fill=INK, anchor="mm")
            ld.text((W // 2, 1200), "Heute zeigen wir dir, wie.", font=f_sub, fill=GREY, anchor="mm")
            paste(fr, lay, 0, 0, a, (1 - ease((t - T_HUB[0]) / 0.4)) * 30)

        # --- CTA
        a = fade(t, T_CTA[0], T_CTA[1], fout=0.0)
        if a > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ld.text((W // 2, 560), "KI zum Anfassen", font=F("InterDisplay-Bold.otf", 108), fill=INK, anchor="mm")
            ld.text((W // 2, 690), "Heute · 18:30 Uhr", font=f_h1, fill=BLUE, anchor="mm")
            ld.text((W // 2, 790), "tisch Coworking, Schwerin", font=f_sub, fill=GREY, anchor="mm")
            ld.text((W // 2, 850), "Wittenburger Str. 16a/b", font=f_sub, fill=GREY, anchor="mm")
            bw, bh = 880, 120
            ld.rounded_rectangle((W // 2 - bw // 2, 980, W // 2 + bw // 2, 980 + bh), radius=60, fill=INK)
            ld.text((W // 2, 980 + bh // 2), "bettersorted.de/ki-zum-anfassen", font=F("Inter-SemiBold.otf", 42), fill=(255, 255, 255), anchor="mm")
            ld.text((W // 2, 1180), "Anmelden oder spontan vorbeikommen", font=f_semi, fill=INK, anchor="mm")
            ld.text((W // 2, 1260), "BAFA-gelistet · Autorisierter INQA-Coach · Schwerin", font=F("Inter-Regular.otf", 30), fill=GREY, anchor="mm")
            paste(fr, lay, 0, 0, a, (1 - ease((t - T_CTA[0]) / 0.4)) * 30)

        enc.stdin.write(fr.convert("RGB").tobytes())
        if i in (60, 200, 340, 460, 580):
            fr.convert("RGB").save(f"/tmp/claude-0/-home-claude/abbc8c35-d4e2-5b20-a60e-81a493483747/scratchpad/still_{i}.png")
    enc.stdin.close()
    enc.wait()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
