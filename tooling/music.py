"""Erzeugt einen eigenen, lizenzfreien 20-Sekunden-Track für alle Reels.
Ruhiger Lo-Fi/Corporate-Groove, 100 BPM, F-Dur, mit sanften Whooshes an den Szenenwechseln."""
import os
import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt
from scipy.io import wavfile

SR = 44100
DUR = 20.0
N = int(SR * DUR)
BPM = 100
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(7)

def hz(m): return 440 * 2 ** ((m - 69) / 12)
def env_adsr(n, a, d, s, r):
    t = np.arange(n) / SR
    e = np.ones(n) * s
    ai = int(a * SR); di = int(d * SR); ri = int(r * SR)
    e[:ai] = np.linspace(0, 1, ai) if ai else e[:ai]
    e[ai:ai + di] = np.linspace(1, s, len(e[ai:ai + di]))
    if ri: e[-ri:] *= np.linspace(1, 0, ri)
    return e
def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)
def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)

L = np.zeros(N); R = np.zeros(N)
def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= N: return
    sig = sig[: N - i]
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[i:i + len(sig)] += sig * gain * gl * 1.414
    R[i:i + len(sig)] += sig * gain * gr * 1.414

chords = [  # (Bass, Voicing)
    (41, [53, 57, 60, 64]),  # Fmaj7
    (45, [52, 55, 57, 60]),  # Am7
    (38, [50, 53, 57, 60]),  # Dm7
    (46, [50, 53, 57, 58]),  # Bbmaj7
]
BARS = 8

# Pad (weich, leicht verstimmt)
for b in range(BARS + 1):
    bass, notes = chords[b % 4]
    if b == BARS: bass, notes = chords[0]
    length = BAR + 0.8
    n = int(length * SR); t = np.arange(n) / SR
    for k, m in enumerate(notes):
        f = hz(m)
        for det, pan in ((-0.12, -0.6), (0.12, 0.6)):
            ff = f * 2 ** (det / 12 / 4)
            s = (np.sin(2 * np.pi * ff * t) + 0.25 * np.sin(2 * np.pi * 2 * ff * t) + 0.08 * np.sin(2 * np.pi * 3 * ff * t))
            e = env_adsr(n, 0.35, 0.6, 0.75, 0.9)
            add(lp(s * e, 1800), b * BAR, 0.05, pan)

# Bass
for b in range(BARS + 1):
    bass = chords[b % 4][0] if b < BARS else chords[0][0]
    for beat in ((0, 2) if b < BARS else (0,)):
        n = int(BEAT * 1.9 * SR); t = np.arange(n) / SR
        f = hz(bass)
        s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
        e = np.exp(-t * 2.2) * np.minimum(1, t / 0.01)
        add(lp(s * e, 400), b * BAR + beat * BEAT, 0.11)

# Arpeggio-Pluck mit Echo (ab Takt 2)
arp_l = np.zeros(N); arp_r = np.zeros(N)
pattern = [0, 2, 1, 3, 2, 1, 3, 2]
for b in range(0, BARS):
    notes = [m + 12 for m in chords[b % 4][1]]
    for i, p in enumerate(pattern):
        n = int(0.5 * SR); t = np.arange(n) / SR
        f = hz(notes[p])
        tri = 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * t))
        s = (0.7 * tri + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * 9) * np.minimum(1, t / 0.004)
        st = int((b * BAR + i * BEAT / 2) * SR)
        vel = 0.9 if i % 2 == 0 else 0.65
        seg = lp(s, 3500)[: N - st]
        pan = -0.35 if i % 2 else 0.35
        arp_l[st:st + len(seg)] += seg * vel * (1 - pan) / 2
        arp_r[st:st + len(seg)] += seg * vel * (1 + pan) / 2
# Ping-Pong-Echo (Achtel punktiert)
dly = int(BEAT * 0.75 * SR)
for k in range(1, 4):
    g = 0.35 ** k
    src_l, src_r = (arp_r, arp_l) if k % 2 else (arp_l, arp_r)
    arp_l[dly * k:] += src_l[:-dly * k] * g
    arp_r[dly * k:] += src_r[:-dly * k] * g
L += arp_l * 0.16; R += arp_r * 0.16

# Drums (ab Takt 3, letzter Takt ohne)
def kick():
    n = int(0.4 * SR); t = np.arange(n) / SR
    f = 45 + 75 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9)
def hat(dec=55):
    n = int(0.12 * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-t * dec)
def snap():
    n = int(0.25 * SR); t = np.arange(n) / SR
    s = sosfilt(butter(2, [900, 3500], "band", fs=SR, output="sos"), rng.standard_normal(n))
    return s * np.exp(-t * 22)
for b in range(2, BARS):
    for beat in range(4):
        t0 = b * BAR + beat * BEAT
        if beat in (0, 2): add(kick(), t0, 0.32)
        if beat == 2 and b % 2: add(kick(), t0 + BEAT * 0.75, 0.16)
        if beat in (1, 3): add(snap(), t0, 0.07)
        add(hat(), t0 + BEAT / 2, 0.045, 0.3)
        add(hat(80), t0, 0.022, -0.3)

# Whooshes an den Szenenwechseln (Video: 4.6 s, 10.2 s, 15.0 s)
for tc in (4.6, 10.2, 15.0):
    n = int(0.7 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    sweep = np.zeros(n)
    # gleitender Bandpass durch Blöcke
    blk = 512
    for i in range(0, n, blk):
        fc = 600 + 5000 * (i / n)
        seg = noise[i:i + blk]
        sweep[i:i + blk] = sosfilt(butter(2, [fc * 0.7, fc * 1.3], "band", fs=SR, output="sos"), seg)
    e = np.sin(np.pi * np.clip(t / 0.7, 0, 1)) ** 2
    add(sweep * e, tc - 0.45, 0.10, -0.4)
    add(sweep[::-1] * e, tc - 0.45, 0.06, 0.4)

# Hall
ir_n = int(1.6 * SR); ti = np.arange(ir_n) / SR
ir = rng.standard_normal(ir_n) * np.exp(-ti * 3.2); ir = lp(ir, 5000); ir /= np.sqrt(np.sum(ir ** 2))
wetL = fftconvolve(L, ir)[:N]; wetR = fftconvolve(R, ir[::-1].copy()[::-1])[:N]
L = L + 0.18 * wetL; R = R + 0.18 * wetR

# Master: Fade-in/out, sanfte Sättigung, Pegel
fade = np.ones(N)
fi = int(0.25 * SR); fo = int(1.8 * SR)
fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
L *= fade; R *= fade
st = np.vstack([L, R]).T
st = hp(st.T, 30).T
st = np.tanh(st * 1.3) / np.tanh(1.3)
st /= np.max(np.abs(st)) / 0.89
wavfile.write(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sound.wav"), SR, (st * 32767).astype(np.int16))
print("ok", st.shape)
