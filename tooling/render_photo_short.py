"""bettersorted – photo recap short (9:16) in design v4 plus 4:5 photo crops for feed posts.
Usage: python3 render_photo_short.py <spec.json> <out_dir>
Spec: {"title", "subtitle", "photos": [{"src", "caption", "focus_y"}], "end": {"eyebrow", "title", "lines": [...]}}"""
import sys, os, json, subprocess, tempfile
from PIL import Image, ImageDraw, ImageOps
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_slides import F, load_logo, motif, soft_tint, PAPER, INK, GREY, BLUE, RULE, HERE

W, H, FPS = 1080, 1920, 30
PHOTO_SEC, END_SEC, FADE = 2.6, 3.6, 0.35
CARD_W = 936; CARD_H = int(CARD_W * 5 / 4)  # 4:5 photo card
CARD_X = (W - CARD_W) // 2; CARD_Y = 400


def crop45(path, focus_y=0.5, width=1080):
    """Auto-orient, crop to 4:5 around focus_y, drop all metadata (EXIF/GPS)."""
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    w, h = im.size
    if w / h > 0.8:  # too wide -> crop width
        nw = int(h * 0.8); x = (w - nw) // 2; im = im.crop((x, 0, x + nw, h))
    else:  # too tall -> crop height around focus
        nh = int(w / 0.8); y = int(max(0, min(h - nh, focus_y * h - nh / 2))); im = im.crop((0, y, w, y + nh))
    return im.resize((width, int(width * 1.25)), Image.LANCZOS)


def base():
    bg = Image.new("RGBA", (W, H), PAPER + (255,))
    bg.alpha_composite(soft_tint(W, H)); bg.alpha_composite(motif(W, H, False))
    bg.alpha_composite(load_logo(44), (72, 72))
    d = ImageDraw.Draw(bg)
    d.line((72, H - 120, W - 72, H - 120), fill=RULE, width=2)
    d.text((72, H - 78), "bettersorted.de", font=F("Inter-Medium.otf", 30), fill=GREY, anchor="lm")
    return bg


def header(bg, spec):
    d = ImageDraw.Draw(bg)
    d.text((72, 190), spec["title"], font=F("InterDisplay-Bold.otf", 74), fill=INK, anchor="lm")
    d.text((72, 275), spec["subtitle"], font=F("Inter-SemiBold.otf", 36), fill=BLUE, anchor="lm")


def rounded_mask(w, h, r=34):
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255); return m


def photo_frame(bg, photo, caption, t):
    im = bg.copy()
    z = 1.0 + 0.06 * t  # slow zoom
    pw, ph = int(CARD_W * z), int(CARD_H * z)
    p = photo.resize((pw, ph), Image.BILINEAR)
    p = p.crop(((pw - CARD_W) // 2, (ph - CARD_H) // 2, (pw - CARD_W) // 2 + CARD_W, (ph - CARD_H) // 2 + CARD_H))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((CARD_X - 3, CARD_Y - 3, CARD_X + CARD_W + 2, CARD_Y + CARD_H + 2), radius=37, fill=(214, 228, 238, 255))
    im.paste(p, (CARD_X, CARD_Y), rounded_mask(CARD_W, CARD_H))
    f = F("InterDisplay-Bold.otf", 50)
    d.text((W // 2, CARD_Y + CARD_H + 95), caption, font=f, fill=INK, anchor="mm")
    return im


def end_frame(spec):
    im = base(); d = ImageDraw.Draw(im); e = spec["end"]
    d.text((72, 640), e["eyebrow"].upper(), font=F("Inter-SemiBold.otf", 32), fill=BLUE, anchor="lm")
    y = 740
    for line in e["title"]:
        d.text((72, y), line, font=F("InterDisplay-Bold.otf", 92), fill=INK, anchor="lm"); y += 110
    y += 40
    for line in e["lines"]:
        d.text((72, y), line, font=F("Inter-Medium.otf", 40), fill=GREY, anchor="lm"); y += 62
    bx, by = 72, y + 50
    bf = F("Inter-SemiBold.otf", 36); label = e["button"]; bw = int(bf.getlength(label)) + 80
    d.rounded_rectangle((bx, by, bx + bw, by + 96), radius=48, fill=INK)
    d.text((bx + bw // 2, by + 48), label, font=bf, fill=(255, 255, 255), anchor="mm")
    return im


def main(spec_path, out_dir):
    spec = json.load(open(spec_path)); os.makedirs(out_dir, exist_ok=True)
    root = os.path.dirname(os.path.abspath(spec_path))
    photos = []
    for i, ph in enumerate(spec["photos"], 1):
        im = crop45(os.path.join(root, ph["src"]) if not os.path.isabs(ph["src"]) else ph["src"], ph.get("focus_y", 0.5))
        im.save(os.path.join(out_dir, f"foto{i:02d}.jpg"), quality=90)
        photos.append((im, ph["caption"]))
    bg = base(); header(bg, spec)
    end = end_frame(spec).convert("RGB")
    tmp = tempfile.mkdtemp(); n = 0
    prev = None
    for im, cap in photos:
        frames = int(PHOTO_SEC * FPS)
        for k in range(frames):
            fr = photo_frame(bg, im, cap, k / frames).convert("RGB")
            if prev is not None and k < FADE * FPS:
                fr = Image.blend(prev, fr, k / (FADE * FPS))
            fr.save(f"{tmp}/{n:05d}.jpg", quality=92); n += 1
        prev = fr
    for k in range(int(END_SEC * FPS)):
        fr = Image.blend(prev, end, k / (FADE * FPS)) if k < FADE * FPS else end
        fr.save(f"{tmp}/{n:05d}.jpg", quality=92); n += 1
    dur = n / FPS
    out = os.path.join(out_dir, "short.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/%05d.jpg",
                    "-stream_loop", "-1", "-i", os.path.join(HERE, "assets", "sound.wav"),
                    "-t", f"{dur:.2f}", "-af", f"afade=t=in:d=0.5,afade=t=out:st={dur - 1.2:.2f}:d=1.2,volume=0.8",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], check=True)
    end.save(os.path.join(out_dir, "end.png"))
    print(out, f"{dur:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
