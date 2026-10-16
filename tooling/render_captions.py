"""Brennt Untertitel + Kopfzeile in ein Hochkant-Video (1080x1920).
Aufruf: python3 render_captions.py <spec.json> <in.mp4> <out.mp4>"""
import sys, os, json, subprocess, tempfile
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_slides import F, load_logo, INK, BLUE

W, H = 1080, 1920
def wrap(text, font, maxw, d):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur); return lines

def caption_png(text, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = F("InterDisplay-Bold.otf", 56); lines = wrap(text, f, 880, d)
    lh = 72; bh = len(lines) * lh + 44; y0 = 1180 - bh // 2
    bw = max(d.textlength(l, font=f) for l in lines) + 64
    d.rounded_rectangle(((W - bw) / 2, y0, (W + bw) / 2, y0 + bh), radius=22, fill=(255, 255, 255, 235))
    for i, l in enumerate(lines):
        d.text((W / 2, y0 + 22 + i * lh + lh / 2), l, font=f, fill=INK, anchor="mm")
    im.save(path)

def head_png(spec, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((48, 70, W - 48, 310), radius=26, fill=(255, 255, 255, 235))
    logo = load_logo(60); im.alpha_composite(logo, (88, 100))
    d.text((88, 184), spec["top"], font=F("InterDisplay-Bold.otf", 50), fill=INK)
    d.text((88, 250), spec["speaker"], font=F("Inter-SemiBold.otf", 32), fill=BLUE)
    im.save(path)

def main(spec_path, src, out):
    spec = json.load(open(spec_path, encoding="utf-8"))
    tmp = tempfile.mkdtemp()
    head_png(spec, f"{tmp}/head.png")
    inputs, chain, last = ["-i", src, "-i", f"{tmp}/head.png"], "[0:v][1:v]overlay=0:0[v0]", "v0"
    for i, (a, b, t) in enumerate(spec["captions"]):
        p = f"{tmp}/c{i}.png"; caption_png(t, p); inputs += ["-i", p]
        chain += f";[{last}][{i+2}:v]overlay=0:0:enable='between(t,{a},{b})'[v{i+1}]"; last = f"v{i+1}"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", chain, "-map", f"[{last}]", "-map", "0:a",
                    "-c:v", "libx264", "-crf", "21", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", out], check=True)

if __name__ == "__main__":
    main(*sys.argv[1:4])
