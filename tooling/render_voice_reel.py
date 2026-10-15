"""bettersorted – Kurz-Reel (5–6 s) mit Sprecherstimme, Design v4 (hell, Logo-Motiv).

Aufruf:
    python3 render_voice_reel.py <spec.json> <out.mp4> [voice.mp3]

Ohne voice.mp3 wird nur die Hausmusik leise untergelegt (Vorschau).
Mit voice.mp3: Stimme vorne, Hausmusik bei -20 dB darunter; Videolänge = Stimme + 0,3 s.

Spec:
{
  "eyebrow": "LOKALE KI", "title": "Wo lokale KI [hilft]",
  "items": [{"t": 0.9, "title": "Dokumente", "sub": "…"}, …],   # t = Einblendzeit in s (zur Stimme passend)
  "punch_t": 2.9, "punch": "Ihre Daten bleiben [im Haus.]", "punch_sub": "…",
  "duration": 5.6
}
"""
import sys, os, json, subprocess
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_slides import (F, load_logo, motif, soft_tint, text_block, PAPER, INK, GREY, BLUE, SKY, RULE, ML, HERE)

W, H, FPS = 1080, 1920, 30
CW = W - 2 * ML

def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3

def card(title, sub, num):
    cw, ch = CW, 170
    im = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, cw - 1, ch - 1), radius=26, fill=(255, 255, 255, 245), outline=(214, 228, 238), width=2)
    d.text((44, 36), f"{num:02d}", font=F("InterDisplay-SemiBold.otf", 40), fill=BLUE)
    d.text((140, 30), title, font=F("InterDisplay-Bold.otf", 54), fill=INK)
    d.text((140, 98), sub, font=F("Inter-Regular.otf", 34), fill=GREY)
    return im

def main(spec_path, out, voice=None):
    spec = json.load(open(spec_path, encoding="utf-8"))
    dur = spec.get("duration", 5.6)
    if voice:
        vd = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", voice]).decode())
        dur = max(dur, vd + 0.3)
    # statischer Hintergrund
    bg = Image.new("RGBA", (W, H), PAPER + (255,))
    bg.alpha_composite(soft_tint(W, H)); bg.alpha_composite(motif(W, H, False, strong=True))
    logo = load_logo(44); bg.alpha_composite(logo, (ML, 110))
    d = ImageDraw.Draw(bg)
    d.line((ML, H - 150, W - ML, H - 150), fill=RULE, width=2)
    d.text((ML, H - 118), "bettersorted.de", font=F("Inter-Medium.otf", 32), fill=GREY)

    eb = F("Inter-SemiBold.otf", 32)
    eyebrow = Image.new("RGBA", (CW, 50), (0, 0, 0, 0)); ed = ImageDraw.Draw(eyebrow)
    ed.line((0, 22, 56, 22), fill=BLUE, width=4); ed.text((76, 4), spec["eyebrow"], font=eb, fill=BLUE)
    title = text_block(spec["title"], F("InterDisplay-Bold.otf", 108), CW, INK, BLUE, lh=1.04)
    cards = [card(it["title"], it["sub"], i + 1) for i, it in enumerate(spec["items"])]
    PW = 680  # links vom Logo-Motiv bleiben
    punch = text_block(spec["punch"], F("InterDisplay-Bold.otf", 80), PW, INK, BLUE, lh=1.06)
    psub = text_block(spec.get("punch_sub", ""), F("Inter-Regular.otf", 38), PW - 40, GREY, BLUE, lh=1.3) if spec.get("punch_sub") else None

    y_eb, y_title = 300, 370
    y_cards = y_title + title.height + 70
    y_punch = y_cards + len(cards) * 192 + 60

    def paste(frame, im, x, y, a, dy=0):
        if a <= 0: return
        if a < 1:
            im = im.copy(); al = im.getchannel("A").point(lambda v: int(v * a)); im.putalpha(al)
        frame.alpha_composite(im, (int(x), int(y + dy)))

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    music = os.path.join(HERE, "assets", "sound.wav")
    if voice:
        cmd += ["-i", voice, "-i", music, "-filter_complex",
                "[1:a]apad,volume=1.0[v];[2:a]volume=0.12,afade=t=out:st=%.2f:d=0.5[m];[v][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]" % (dur - 0.5),
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-i", music, "-filter_complex", "[1:a]volume=0.35,afade=t=out:st=%.2f:d=0.5[a]" % (dur - 0.5), "-map", "0:v", "-map", "[a]"]
    cmd += ["-t", f"{dur:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS; fr = bg.copy()
        a = ease(t / 0.4); paste(fr, eyebrow, ML, y_eb, a, (1 - a) * 20)
        a = ease((t - 0.08) / 0.45); paste(fr, title, ML, y_title, a, (1 - a) * 30)
        for k, (c, it) in enumerate(zip(cards, spec["items"])):
            a = ease((t - it["t"]) / 0.35); paste(fr, c, ML, y_cards + k * 192, a, (1 - a) * 40)
        a = ease((t - spec["punch_t"]) / 0.4); paste(fr, punch, ML, y_punch, a, (1 - a) * 30)
        if psub: a2 = ease((t - spec["punch_t"] - 0.25) / 0.4); paste(fr, psub, ML, y_punch + punch.height + 26, a2, (1 - a2) * 20)
        p.stdin.write(fr.convert("RGB").tobytes())
    p.stdin.close(); p.wait()

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
