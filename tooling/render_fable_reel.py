"""bettersorted - Reel "Claude Fable 5.2 ist da" (9:16, 20 s, 30 fps), design v4.
Scenes: hook -> what it can do (3 cards) -> numbers -> classification for SMEs -> CTA.
Facts checked against anthropic.com (announcement of Nov 9, 2026).
Usage: python3 render_fable_reel.py <out.mp4> [stills_dir]
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


def paste(fr, im, a=1.0, dy=0):
    if a <= 0.01:
        return
    if a < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    fr.alpha_composite(im, (0, int(dy)))


def card(w, h, r=22, a=250):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=(255, 255, 255, a), outline=(214, 228, 238, 255), width=2)
    return im, d


def list_card(num, title, sub):
    cw = W - 2 * ML
    im, d = card(cw, 200)
    d.text((40, 100), num, font=F("InterDisplay-Bold.otf", 60), fill=BLUE, anchor="lm")
    d.text((150, 76), title, font=F("Inter-SemiBold.otf", 44), fill=INK, anchor="lm")
    d.text((150, 134), sub, font=F("Inter-Regular.otf", 32), fill=GREY, anchor="lm")
    return im


def stat_card(value, label1, label2):
    cw = W - 2 * ML
    im, d = card(cw, 300)
    d.text((40, 120), value, font=F("InterDisplay-Bold.otf", 120), fill=BLUE, anchor="lm")
    d.text((40, 220), label1, font=F("Inter-SemiBold.otf", 38), fill=INK, anchor="lm")
    d.text((40, 268), label2, font=F("Inter-Regular.otf", 30), fill=GREY, anchor="lm")
    return im


def tag(d, cx, y, s):
    f = F("Inter-SemiBold.otf", 32)
    tw = d.textlength(s, font=f)
    d.rounded_rectangle((cx - tw / 2 - 28, y - 32, cx + tw / 2 + 28, y + 32), radius=14,
                        fill=(255, 255, 255), outline=(214, 228, 238), width=2)
    d.text((cx, y), s, font=f, fill=BLUE, anchor="mm")


def main(out, stills=None):
    bg = Image.new("RGBA", (W, H), PAPER + (255,))
    bg.alpha_composite(soft_tint(W, H))
    bg.alpha_composite(motif(W, H, False))
    logo = load_logo(44)
    f_foot = F("Inter-Medium.otf", 30)
    f_big = F("InterDisplay-Bold.otf", 112)
    f_h1 = F("InterDisplay-Bold.otf", 78)
    f_h2 = F("InterDisplay-Bold.otf", 64)
    f_sub = F("Inter-Regular.otf", 42)
    f_semi = F("Inter-SemiBold.otf", 40)

    cards = [list_card("01", "Programmiert tagelang", "auch große, unklare Software-Projekte"),
             list_card("02", "Führt 1.000+ KI-Agenten", "plant, verteilt, prüft eigene Ergebnisse"),
             list_card("03", "Baut echte Hardware", "Platinen entwerfen, Roboter steuern")]
    stats = [stat_card("30 Std.", "1.000 Fable-Agenten formalisieren", "den Beweis von Fermats letztem Satz"),
             stat_card("bis 30 %", "schnellere Antworten als Fable 5.1", "und 20 % günstiger (8 $ statt 10 $ / Mio. Tokens)")]

    T_HOOK = (0.0, 4.4)
    T_CAN = (4.4, 9.8)
    T_NUM = (9.8, 14.4)
    T_KMU = (14.4, 17.2)
    T_CTA = (17.2, 20.0)

    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", os.path.join(HERE, "assets", "sound.wav"), "-t", str(DUR),
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-af", "volume=0.8,afade=t=out:st=19.2:d=0.8", "-shortest", out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    n = int(DUR * FPS)
    for i in range(n):
        t = i / FPS
        fr = bg.copy()
        d = ImageDraw.Draw(fr)
        fr.alpha_composite(logo, (ML, 56))
        d.line((ML, H - 110, W - ML, H - 110), fill=RULE, width=2)
        d.text((ML, H - 70), "bettersorted.de", font=f_foot, fill=GREY, anchor="lm")
        d.text((W - ML, H - 70), "KI-News · Nov. 2026", font=f_foot, fill=GREY, anchor="rm")

        # hook
        a = fade(t, *T_HOOK)
        if a > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            tag(ld, W // 2, 620, "NEU SEIT 9. NOVEMBER")
            ld.text((W // 2, 800), "Claude", font=f_big, fill=INK, anchor="mm")
            ld.text((W // 2, 930), "Fable 5.2", font=F("InterDisplay-Bold.otf", 150), fill=BLUE, anchor="mm")
            ld.text((W // 2, 1060), "ist da.", font=f_big, fill=INK, anchor="mm")
            ld.text((W // 2, 1210), "Das stärkste Claude-Modell,", font=f_sub, fill=GREY, anchor="mm")
            ld.text((W // 2, 1270), "das du nutzen kannst.", font=f_sub, fill=GREY, anchor="mm")
            paste(fr, lay, a, (1 - ease((t - T_HOOK[0]) / 0.4)) * 30)

        # what it can do - cards appear one by one
        a = fade(t, *T_CAN)
        if a > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ld.text((ML, 420), "WAS ES KANN", font=F("Inter-SemiBold.otf", 32), fill=BLUE, anchor="lm")
            ld.text((ML, 510), "Gebaut für die", font=f_h1, fill=INK, anchor="lm")
            ld.text((ML, 600), "richtig harten Fälle", font=f_h1, fill=BLUE, anchor="lm")
            paste(fr, lay, a, (1 - ease((t - T_CAN[0]) / 0.4)) * 30)
            for k, c in enumerate(cards):
                start = T_CAN[0] + 0.5 + k * 0.6
                ca = min(a, ease((t - start) / 0.4)) if t >= start else 0
                if ca > 0:
                    cl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    cl.alpha_composite(c, (ML, 720 + k * 240))
                    paste(fr, cl, ca, (1 - ease((t - start) / 0.4)) * 40)

        # numbers
        a = fade(t, *T_NUM)
        if a > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ld.text((ML, 420), "IN ZAHLEN", font=F("Inter-SemiBold.otf", 32), fill=BLUE, anchor="lm")
            ld.text((ML, 510), "Schneller, günstiger,", font=f_h1, fill=INK, anchor="lm")
            ld.text((ML, 600), "schlauer", font=f_h1, fill=BLUE, anchor="lm")
            paste(fr, lay, a, (1 - ease((t - T_NUM[0]) / 0.4)) * 30)
            for k, c in enumerate(stats):
                start = T_NUM[0] + 0.4 + k * 0.8
                ca = min(a, ease((t - start) / 0.4)) if t >= start else 0
                if ca > 0:
                    cl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    cl.alpha_composite(c, (ML, 730 + k * 350))
                    paste(fr, cl, ca, (1 - ease((t - start) / 0.4)) * 40)

        # classification for SMEs
        a = fade(t, *T_KMU)
        if a > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ld.text((W // 2, 620), "Und für deinen Betrieb?", font=f_semi, fill=GREY, anchor="mm")
            ld.text((W // 2, 760), "Spitzen-KI für", font=f_h1, fill=INK, anchor="mm")
            ld.text((W // 2, 860), "die harten Fälle.", font=f_h1, fill=INK, anchor="mm")
            ld.text((W // 2, 1010), "Sensible Daten?", font=f_h2, fill=BLUE, anchor="mm")
            ld.text((W // 2, 1100), "Lieber lokale Open-Source-KI.", font=f_h2, fill=BLUE, anchor="mm")
            ld.text((W // 2, 1230), "Im eigenen Haus · DSGVO-konform", font=f_sub, fill=GREY, anchor="mm")
            paste(fr, lay, a, (1 - ease((t - T_KMU[0]) / 0.4)) * 30)

        # CTA
        a = fade(t, T_CTA[0], T_CTA[1], fout=0.0)
        if a > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            tag(ld, W // 2, 600, "Bis zu 80 % gefördert")
            ld.text((W // 2, 760), "Welche KI passt", font=f_h1, fill=INK, anchor="mm")
            ld.text((W // 2, 860), "zu deinem Betrieb?", font=f_h1, fill=BLUE, anchor="mm")
            ld.text((W // 2, 970), "Wir sortieren das mit dir.", font=f_sub, fill=GREY, anchor="mm")
            bw, bh = 560, 110
            ld.rounded_rectangle((W // 2 - bw // 2, 1060, W // 2 + bw // 2, 1060 + bh), radius=55, fill=INK)
            ld.text((W // 2, 1060 + bh // 2), "bettersorted.de →", font=F("Inter-SemiBold.otf", 44), fill=(255, 255, 255), anchor="mm")
            ld.text((W // 2, 1250), "BAFA-zugelassen · Autorisierter INQA-Coach · Schwerin", font=F("Inter-Regular.otf", 30), fill=GREY, anchor="mm")
            paste(fr, lay, a, (1 - ease((t - T_CTA[0]) / 0.4)) * 30)

        enc.stdin.write(fr.convert("RGB").tobytes())
        if stills and i in (90, 260, 400, 470, 560):
            fr.convert("RGB").save(os.path.join(stills, f"still_{i:03d}.png"))
    enc.stdin.close()
    enc.wait()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
