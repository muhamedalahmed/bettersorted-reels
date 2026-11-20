# Build 9:16 Shorts from 4:5 carousel slides (crossfade + house sound).
import glob, os, subprocess, sys
from PIL import Image
PAPER = (245, 249, 252); DUR = 4.2; FADE = 0.5
snd = sys.argv[1]
for d in sorted(glob.glob('/home/claude/out_story/foerder-*')):
    slug = os.path.basename(d); fs = sorted(glob.glob(d + '/*.png'))
    frames = []
    for i, f in enumerate(fs):
        bg = Image.open(f).convert('RGB')
        p = f'{d}/v{i:02d}.jpg'; bg.save(p, quality=95); frames.append(p)
    n = len(frames); total = n * DUR - (n - 1) * FADE
    args = ['ffmpeg', '-y', '-loglevel', 'error']
    for p in frames: args += ['-loop', '1', '-t', str(DUR), '-framerate', '30', '-i', p]
    args += ['-stream_loop', '-1', '-i', snd]
    fc = []; last = '[0:v]'; off = DUR - FADE
    for i in range(1, n):
        out = f'[x{i}]'; fc.append(f'{last}[{i}:v]xfade=transition=fade:duration={FADE}:offset={off:.2f}{out}'); last = out; off += DUR - FADE
    fc.append(f'{last}format=yuv420p[v]')
    fc.append(f'[{n}:a]atrim=0:{total:.2f},afade=t=in:d=0.5,afade=t=out:st={total-1.2:.2f}:d=1.2,volume=0.8[a]')
    args += ['-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-c:a', 'aac', '-b:a', '160k', '-t', f'{total:.2f}', f'{d}/short.mp4']
    subprocess.run(args, check=True); print(slug, round(total, 1), 's')
