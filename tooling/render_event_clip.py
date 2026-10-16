"""bettersorted – Event-Clip aus Handyvideo: Schnitt (Pausen/Versprecher raus, Punch-in-Zooms),
Kopfzeile mit Logo, Untertitel mit Hervorhebung, Einblendungen synchron zur Rede, Abspann.
Aufruf: python3 render_event_clip.py <spec.json> <out.mp4>
Alle Zeiten in der Spec sind Zeiten im Quellvideo; das Skript rechnet sie auf den Schnitt um."""
import sys, os, json, subprocess, tempfile
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_slides import F, load_logo, motif, soft_tint, tokens, PAPER, INK, GREY, BLUE, HERE

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(HERE)
ZONE_FX = 1395      # Mitte der Einblendungen (auf dem Pult)
ZONE_CAP = 1640     # Mitte der Untertitel

def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3

def build_map(segs):
    out, o = [], 0.0
    for a, b, z in segs: out.append((a, b, o)); o += b - a
    return out, o
def s2o(t, m):
    for a, b, o in m:
        if t <= b: return o + max(0.0, t - a)
    a, b, o = m[-1]; return o + (b - a)

def card(w, h, r=26, a=238):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=(255, 255, 255, a), outline=(214, 228, 238, 255), width=2)
    return im, d

def rich_center(markup, font, maxw, lh):
    toks = tokens(markup); sp = font.getlength(" "); lines, cur, cw = [], [], 0
    for w, hi in toks:
        wl = font.getlength(w)
        if cur and cw + sp + wl > maxw: lines.append((cur, cw)); cur, cw = [], 0
        cw += (sp if cur else 0) + wl; cur.append((w, hi))
    lines.append((cur, cw)); return lines

def caption_img(markup):
    f = F("InterDisplay-Bold.otf", 54); lh = 70
    lines = rich_center(markup, f, 900, lh); bw = int(max(c for _, c in lines)) + 64; bh = len(lines) * lh + 40
    im, d = card(bw, bh, 22, 240)
    for i, (ln, cw) in enumerate(lines):
        x = (bw - cw) / 2; y = 20 + i * lh + lh / 2
        for w, hi in ln:
            d.text((x, y), w, font=f, fill=BLUE if hi else INK, anchor="lm"); x += f.getlength(w) + f.getlength(" ")
    return im

def header_img(spec):
    im, d = card(W - 96, 248, 28, 240)
    im.alpha_composite(load_logo(52), (40, 24))
    d.text((40, 90), spec["title"], font=F("InterDisplay-Bold.otf", 52), fill=INK)
    d.text((40, 156), spec["speaker"], font=F("Inter-SemiBold.otf", 30), fill=BLUE)
    d.text((40, 196), spec["event"], font=F("Inter-Regular.otf", 30), fill=GREY)
    return im

def badge_img(big, small):
    fb, fs = F("InterDisplay-Bold.otf", 76), F("Inter-Medium.otf", 32)
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    w = int(max(tmp.textlength(big, font=fb), tmp.textlength(small, font=fs))) + 120
    im, d = card(w, 178, 28, 245)
    d.rounded_rectangle((26, 30, 34, 148), radius=4, fill=BLUE)
    d.text((62, 22), big, font=fb, fill=BLUE); d.text((64, 118), small, font=fs, fill=GREY)
    return im

def pill_img(text, check=False):
    f = F("Inter-SemiBold.otf", 36); tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    pad = 74 if check else 34; w = int(tmp.textlength(text, font=f)) + pad + 34
    im, d = card(w, 72, 36, 245)
    if check:
        d.ellipse((20, 16, 60, 56), fill=BLUE)
        d.line((30, 37, 37, 44, 50, 28), fill=(255, 255, 255), width=5, joint="curve")
    d.text((pad, 36), text, font=f, fill=INK, anchor="lm")
    return im

def paste(fr, im, x, y, a, dy=0):
    if a <= 0.01: return
    if a < 1:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    fr.alpha_composite(im, (int(x), int(y + dy)))

def fade_window(t, a, b, fin=0.32, fout=0.22):
    if t < a or t > b + fout: return 0.0, 1.0
    ai = ease((t - a) / fin); ao = 1.0 if t <= b else 1 - (t - b) / fout
    return ai * ao, ai

def main(spec_path, out):
    spec = json.load(open(spec_path, encoding="utf-8"))
    src = os.path.join(ROOT, spec["source"]); segs = spec["segments"]
    m, total = build_map(segs); od = spec["outro"]["duration"]
    tmp = tempfile.mkdtemp(); base = f"{tmp}/base.mp4"
    # 1) Schnitt + Punch-in
    fc, cat = [], ""
    for i, (a, b, z) in enumerate(segs):
        v = f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS"
        if z != 1.0:
            cw, ch = int(W / z) // 2 * 2, int(H / z) // 2 * 2
            v += f",crop={cw}:{ch}:{int(600 * (1 - 1 / z))}:{int(300 * (1 - 1 / z))},scale={W}:{H}"
        fc.append(v + f",fps={FPS},format=yuv420p[v{i}]")
        fc.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={b - a - 0.03:.3f}:d=0.03[a{i}]")
        cat += f"[v{i}][a{i}]"
    fc.append(f"{cat}concat=n={len(segs)}:v=1:a=1[v][a]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "pcm_s16le", f"{tmp}/base.mov"], check=True)
    # 2) Ebenen vorbereiten
    header = header_img(spec)
    caps = [(s2o(a, m), s2o(b, m), caption_img(t)) for a, b, t in spec["captions"]]
    fx = []
    for e in spec["effects"]:
        if e["type"] == "badge":
            fx.append(("single", s2o(e["t"], m), s2o(e["end"], m), badge_img(e["big"], e["small"])))
        else:
            fx.append((e["type"], [s2o(t, m) for t, _ in e["items"]], s2o(e["end"], m),
                       [pill_img(x, e["type"] == "checks") for _, x in e["items"]]))
    # Abspann
    outro = Image.new("RGBA", (W, H), PAPER + (255,)); outro.alpha_composite(soft_tint(W, H)); outro.alpha_composite(motif(W, H, False, strong=True))
    o_logo = load_logo(120)
    o_l1 = F("InterDisplay-Bold.otf", 64); o_l2 = F("Inter-Regular.otf", 44); o_url = F("Inter-SemiBold.otf", 40)
    # 3) Frames rendern
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", f"{tmp}/base.mov", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-crf", "19", "-preset", "slow", "-pix_fmt", "yuv420p", f"{tmp}/video.mp4"], stdin=subprocess.PIPE)
    n_main, last = 0, None
    while True:
        raw = dec.stdout.read(W * H * 3)
        if len(raw) < W * H * 3: break
        t = n_main / FPS; fr = Image.frombytes("RGB", (W, H), raw).convert("RGBA")
        a = ease(t / 0.5); paste(fr, header, 48, 36, a, -(1 - a) * 40)
        for ca, cb, im in caps:
            if ca - 0.01 <= t < cb:
                al = min(1.0, (t - ca) / 0.12 + 0.35); paste(fr, im, (W - im.width) / 2, ZONE_CAP - im.height / 2, al)
                break
        for kind, ts, end, ims in fx:
            if kind == "single":
                al, ai = fade_window(t, ts, end)
                paste(fr, ims, (W - ims.width) / 2, ZONE_FX - ims.height / 2, al, (1 - ai) * 30)
            elif kind == "pills":
                rows, row, rw = [], [], 0
                for im in ims:
                    if row and rw + im.width + 16 > W - 96: rows.append((row, rw)); row, rw = [], 0
                    rw += (16 if row else 0) + im.width; row.append(im)
                rows.append((row, rw)); k = 0; y0 = ZONE_FX - (len(rows) * 88 - 16) / 2
                for r, (row, rw) in enumerate(rows):
                    x = (W - rw) / 2
                    for im in row:
                        al, ai = fade_window(t, ts[k], end); paste(fr, im, x, y0 + r * 88, al, (1 - ai) * 24); x += im.width + 16; k += 1
            else:  # checks
                y0 = ZONE_FX - (len(ims) * 84 - 12) / 2; mw = max(im.width for im in ims)
                for k, im in enumerate(ims):
                    al, ai = fade_window(t, ts[k], end); paste(fr, im, (W - mw) / 2, y0 + k * 84, al, 0); 
                    if 0 < ai < 1: pass
        last = fr; enc.stdin.write(fr.convert("RGB").tobytes()); n_main += 1
    dec.wait()
    n_out = int(od * FPS)
    for i in range(n_out):
        t = i / FPS; fr = outro.copy()
        a = ease((t - 0.05) / 0.45); paste(fr, o_logo, (W - o_logo.width) / 2, 700, a, (1 - a) * 30)
        d = ImageDraw.Draw(fr)
        a2 = ease((t - 0.3) / 0.45); a3 = ease((t - 0.55) / 0.45)
        txt = Image.new("RGBA", (W, 300), (0, 0, 0, 0)); td = ImageDraw.Draw(txt)
        td.text((W / 2, 40), spec["outro"]["line1"], font=o_l1, fill=INK, anchor="mm")
        td.text((W / 2, 112), spec["outro"]["line2"], font=o_l2, fill=GREY, anchor="mm")
        paste(fr, txt, 0, 900, a2, (1 - a2) * 24)
        u = Image.new("RGBA", (W, 80), (0, 0, 0, 0)); ImageDraw.Draw(u).text((W / 2, 40), spec["outro"]["url"], font=o_url, fill=BLUE, anchor="mm")
        paste(fr, u, 0, 1120, a3, (1 - a3) * 16)
        if t < 0.35 and last is not None:  # Überblendung vom letzten Videobild
            fr = Image.blend(last, fr, ease(t / 0.35))
        enc.stdin.write(fr.convert("RGB").tobytes())
    enc.stdin.close(); enc.wait()
    # 4) Ton: Rede + Hausmusik im Abspann, normalisiert
    dur = n_main / FPS + od
    music = os.path.join(HERE, "assets", "sound.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{tmp}/video.mp4", "-i", f"{tmp}/base.mov", "-i", music, "-filter_complex",
                    f"[1:a]apad[sp];[2:a]volume=0.35,afade=t=in:d=0.3,afade=t=out:st={od - 0.7:.2f}:d=0.7,adelay={int(n_main / FPS * 1000)}|{int(n_main / FPS * 1000)}[mu];"
                    f"[sp][mu]amix=inputs=2:duration=longest:normalize=0,atrim=0:{dur:.2f},loudnorm=I=-14:TP=-1.5:LRA=11[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out], check=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
