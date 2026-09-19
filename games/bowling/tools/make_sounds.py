"""Synthesise every Phantom Bowling sound into ../audio/*.wav.

    python tools/make_sounds.py

No samples, no licences: rumble and clatter are shaped noise plus modal
resonances (a pin rings at a handful of frequencies), the stingers are additive
organ tones and bell partials through a synthetic hall reverb. The loops are
built to wrap seamlessly (their periodic parts fit the buffer exactly).
"""
import os, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audio")
rng = np.random.default_rng(1947)


# ------------------------------------------------------------------ tools ---
def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def bandnoise(n, lo, hi, order=4):
    x = rng.standard_normal(n)
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lowpass(x, fc, order=4):
    return signal.sosfilt(signal.butter(order, fc, btype="low", fs=SR, output="sos"), x)


def highpass(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, btype="high", fs=SR, output="sos"), x)


def periodic_noise(n, lo, hi, tilt=-1.0):
    """Noise whose spectrum sits in [lo, hi] - periodic, so it loops perfectly."""
    f = np.fft.rfftfreq(n, 1 / SR)
    mag = np.where((f >= lo) & (f <= hi), np.maximum(f, 1.0) ** (tilt / 2), 0.0)
    ph = rng.uniform(0, 2 * np.pi, f.size)
    x = np.fft.irfft(mag * np.exp(1j * ph), n)
    return x / (np.abs(x).max() + 1e-9)


def modes(dur, freqs, decays, amps, jitter=0.0):
    t = t_axis(dur)
    out = np.zeros_like(t)
    for f, d, a in zip(freqs, decays, amps):
        f = f * (1 + rng.uniform(-jitter, jitter))
        out += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / d)
    return out


def env(n, tau, attack=0.0015):
    t = np.arange(n) / SR
    a = np.clip(t / attack, 0, 1) if attack > 0 else 1.0
    return a * np.exp(-t / tau)


def hall(x, decay=1.8, wet=0.35, pre=0.02):
    """A synthetic hall: exponentially decaying, darkening noise as the IR."""
    n = int(decay * 3 * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 6.9 / decay)
    ir = lowpass(ir, 5200)
    ir[: int(pre * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    y = signal.fftconvolve(x, ir)
    y = np.concatenate([y, np.zeros(max(0, len(x) + n - len(y)))])[: len(x) + n]
    dry = np.concatenate([x, np.zeros(n)])
    return dry * (1 - wet * 0.5) + y * wet


def trim_tail(x, thresh=1e-4):
    idx = np.where(np.abs(x) > thresh * np.abs(x).max())[0]
    return x[: idx[-1] + 1] if idx.size else x


def fade(x, fin=0.002, fout=0.02):
    n_in, n_out = int(fin * SR), int(fout * SR)
    x = x.copy()
    if n_in:
        x[:n_in] *= np.linspace(0, 1, n_in)
    if n_out:
        x[-n_out:] *= np.linspace(1, 0, n_out)
    return x


def save(name, x, peak=0.89):
    os.makedirs(OUT, exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    x = x / (np.abs(x).max() + 1e-9) * peak
    wavfile.write(os.path.join(OUT, name + ".wav"), SR, (x * 32767).astype(np.int16))
    print("  %-16s %5.2fs" % (name, len(x) / SR))


# ================================================================= lane =====
def roll_loop(dur=3.0):
    """The ball on maple: a low, grainy rumble with a faint board rhythm."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    rumble = periodic_noise(n, 35, 320, tilt=-1.6)
    body = periodic_noise(n, 300, 1400, tilt=-1.0) * 0.18
    hiss = periodic_noise(n, 2500, 7000, tilt=0.0) * 0.03
    seams = 1.0 + 0.18 * np.sin(2 * np.pi * 14.0 * t)      # 42 cycles in 3 s - loops clean
    return (rumble + body) * seams + hiss


def gutter_loop(dur=2.0):
    """A hollow, metallic channel rattle."""
    n = int(dur * SR)
    x = periodic_noise(n, 200, 2600, tilt=-0.6)
    # comb filter = the channel's ringing (applied circularly so it still loops)
    d = int(0.0034 * SR)
    for _ in range(3):
        x = x + 0.55 * np.roll(x, d)
    t = np.arange(n) / SR
    rattle = np.zeros(n)
    for k in range(18):
        i = rng.integers(0, n - 2000)
        rattle[i:i + 1500] += env(1500, 0.004) * rng.uniform(0.3, 1.0) * \
            np.sin(2 * np.pi * rng.uniform(1800, 3400) * np.arange(1500) / SR)
    return x / np.abs(x).max() + rattle * 0.5 + 0.15 * np.sin(2 * np.pi * 60 * t) * 0.0


def release_thump():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * (66 - 16 * t) * t) * np.exp(-t / 0.10)
    thump += np.sin(2 * np.pi * 132 * t) * np.exp(-t / 0.05) * 0.5
    knock = bandnoise(n, 150, 900) * env(n, 0.016) * 0.8
    return fade(thump + knock, 0.0005)


def pit_thud():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    x = lowpass(rng.standard_normal(n), 220) * env(n, 0.14, 0.004) * 3
    x += np.sin(2 * np.pi * 52 * t) * np.exp(-t / 0.18) * 0.7
    return fade(x, 0.001, 0.1)


# ================================================================== pins ====
# A pin is hard maple in a plastic (Surlyn) coat. Hit it and three things
# sound together: a very short, bright click from the coat, the wood ringing
# like a free bar (overtones at 1 : 2.76 : 5.40 : 8.93 of the fundamental, a
# few hundred Hz, dying in tens of milliseconds), and the hollow ring of the
# shell up around 2 kHz. How HARD the contact is sets how bright it sounds:
# each hit is the ringing convolved with a half-sine contact pulse - shorter
# pulse, harder hit, more top end.
PIN_RATIOS = (1.0, 2.756, 5.404, 8.933)


def pin_ring(dur, strength=1.0, f1=None, damp=1.0):
    t = t_axis(dur)
    f1 = f1 or rng.uniform(640, 860)
    x = np.zeros_like(t)
    for r, d, a in zip(PIN_RATIOS, (0.060, 0.034, 0.020, 0.012), (0.45, 0.85, 0.75, 0.45)):
        f = f1 * r * (1 + rng.uniform(-0.025, 0.025))
        x += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / (d * damp))
    fs = rng.uniform(1900, 2700)                      # the plastic shell
    x += 1.0 * np.sin(2 * np.pi * fs * t) * np.exp(-t / (0.028 * damp))
    x += 0.55 * np.sin(2 * np.pi * fs * 1.52 * t) * np.exp(-t / (0.016 * damp))
    x += 0.30 * np.sin(2 * np.pi * fs * 2.13 * t) * np.exp(-t / (0.010 * damp))
    return x * strength


def contact(x, width_ms):
    """Excite a resonator with a half-sine contact pulse of the given width."""
    n = max(2, int(width_ms * 1e-3 * SR))
    pulse = np.sin(np.pi * np.arange(n) / n)
    return signal.fftconvolve(x, pulse / pulse.sum())[: len(x)]


def click(n, amp, lo=3000, hi=12000, tau=0.0012):
    return bandnoise(n, lo, hi) * env(n, tau, 0.0001) * amp


def place(out, x, at, gain=1.0):
    i = int(at * SR)
    if i >= len(out):
        return
    m = min(len(x), len(out) - i)
    out[i:i + m] += x[:m] * gain


def pin_pin(k):
    """Two pins clacking together - the bright, woody TOCK."""
    dur = 0.38
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = contact(pin_ring(dur) + pin_ring(dur, 0.8), rng.uniform(0.12, 0.22))
    x += click(n, rng.uniform(0.9, 1.3), 2000, 10000, 0.0015)
    # the weight behind the clack: a short low thock
    thock = np.sin(2 * np.pi * rng.uniform(150, 210) * t) * np.exp(-t / 0.028)
    thock += 0.6 * np.sin(2 * np.pi * rng.uniform(95, 125) * t) * np.exp(-t / 0.04)
    thock += lowpass(rng.standard_normal(n), 300) * env(n, 0.016, 0.0004) * 3.0
    x += contact(thock, 0.6) * 1.25
    return fade(x, 0.0002, 0.04)


def ball_pin(k):
    """The ball driving through a pin: the heavy ball's low THOCK under the
    pin's crack, and often a second pin going off a hair later."""
    dur = 0.6
    n = int(dur * SR)
    t = np.arange(n) / SR
    ball = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, d, a in
               ((rng.uniform(48, 58), 0.13, 1.5), (rng.uniform(62, 78), 0.11, 2.0),
                (rng.uniform(125, 165), 0.07, 1.8),
                (rng.uniform(420, 520), 0.025, 0.4), (rng.uniform(950, 1250), 0.012, 0.25)))
    ball += lowpass(rng.standard_normal(n), 260) * env(n, 0.026, 0.0005) * 4.2
    x = contact(pin_ring(dur, 1.3) + ball * 1.5, rng.uniform(0.18, 0.3))
    x += click(n, 1.5, 1800, 10000, 0.0022)
    if rng.random() < 0.7:
        place(x, contact(pin_ring(0.35, 0.6), 0.35) + click(int(0.35 * SR), 0.4),
              rng.uniform(0.006, 0.022))
    return fade(x, 0.0002, 0.05)


def pin_lane(k):
    """A pin slapping onto the maple, then bouncing once or twice."""
    dur = 0.55
    n = int(dur * SR)
    t = np.arange(n) / SR

    def slap(gain):
        m = int(0.3 * SR)
        tt = np.arange(m) / SR
        thud = bandnoise(m, 130, 700) * env(m, 0.018, 0.0004)
        body = np.sin(2 * np.pi * rng.uniform(90, 130) * tt) * np.exp(-tt / 0.032)
        boom = np.sin(2 * np.pi * rng.uniform(58, 74) * tt) * np.exp(-tt / 0.05)
        ring = pin_ring(0.3, 0.9, damp=0.7)
        return contact(thud * 1.3 + body * 1.5 + boom * 0.9 + ring, rng.uniform(0.35, 0.6)) * gain + \
            click(m, 0.8 * gain, 1500, 8000, 0.002)
    x = np.zeros(n)
    at, g = 0.0, 1.0
    for _ in range(rng.integers(2, 4)):
        place(x, slap(g), at)
        at += rng.uniform(0.045, 0.11) * g
        g *= rng.uniform(0.3, 0.5)
    return fade(x, 0.0003, 0.05)


def pin_kick(k):
    """A pin cracking into the kickback panel beside the deck."""
    dur = 0.5
    n = int(dur * SR)
    t = np.arange(n) / SR
    panel = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, d, a in
                ((rng.uniform(85, 105), 0.08, 0.9), (rng.uniform(200, 260), 0.08, 1.0),
                 (rng.uniform(420, 520), 0.04, 0.5)))
    x = contact(pin_ring(dur, 1.0) + panel * 0.9, 0.3) + click(n, 1.0, 1800, 9000, 0.002)
    return fade(x, 0.0002, 0.05)


def pin_pit(k):
    """A pin tumbling into the pit - muffled by the cushion."""
    x = lowpass(pin_lane(k), 1400) * 0.8
    n = len(x)
    x += lowpass(rng.standard_normal(n), 160) * env(n, 0.09, 0.004) * 2.8
    return fade(x, 0.0005, 0.08)


def crash(k):
    """The rack going: one heavy ball hit, then a storm of clacks that thins
    out over a second - pins off pins, pins off the deck and the kickbacks,
    pins sliding and dropping into the pit. The individual contacts still
    play on top of this in the game; this is the body of the sound."""
    dur = 1.1
    n = int(dur * SR)
    x = np.zeros(n)
    place(x, ball_pin(k), 0.0, 1.2)
    tt0 = np.arange(n) / SR
    x += (np.sin(2 * np.pi * 58 * tt0) * np.exp(-tt0 / 0.17) * 2.3
          + np.sin(2 * np.pi * 44 * tt0) * np.exp(-tt0 / 0.14) * 1.2
          + lowpass(rng.standard_normal(n), 180) * env(n, 0.07, 0.001) * 4.0)
    density = (90, 120, 150)[k % 3]
    t = 0.004
    while t < 0.8:
        rate = density * np.exp(-t / 0.14) + 4 * np.exp(-t / 0.30)
        t += rng.exponential(1.0 / rate)
        g = rng.uniform(0.25, 0.9) * np.exp(-t / 0.30)
        kind = rng.random()
        if kind < 0.58:
            place(x, pin_pin(k), t, g)
        elif kind < 0.86:
            place(x, pin_lane(k), t, g * 0.9)
        else:
            place(x, pin_kick(k), t, g * 0.8)
    for _ in range(rng.integers(3, 6)):                 # pins dropping into the pit
        place(x, pin_pit(k), rng.uniform(0.25, 0.6), rng.uniform(0.2, 0.4))
    tt = np.arange(n) / SR                              # the scrape of pins sliding
    x += bandnoise(n, 400, 3200, 2) * np.exp(-tt / 0.18) * np.clip(tt / 0.05, 0, 1) * 0.07
    return fade(x, 0.0003, 0.15)


def pinsetter():
    """The machine: a motor spins up, the sweep clanks down, pins rattle into the rack."""
    dur = 2.8
    n = int(dur * SR)
    t = np.arange(n) / SR
    speed = np.interp(t, [0, 0.4, 2.2, 2.8], [0.2, 1.0, 1.0, 0.1])
    f0 = 92 * (0.7 + 0.3 * speed)
    ph = 2 * np.pi * np.cumsum(f0) / SR
    motor = sum(np.sin(ph * h) / h for h in (1, 2, 3, 5)) * speed
    motor = lowpass(motor, 900) * 0.35 + lowpass(rng.standard_normal(n), 400) * 0.08 * speed
    x = motor
    for at, weight in ((0.35, 1.0), (1.25, 0.8), (2.15, 1.0)):
        i = int(at * SR)
        m = n - i
        clunk = bandnoise(m, 120, 700) * env(m, 0.05) * weight
        clunk += modes(m / SR, [410, 930, 1720], [0.08, 0.05, 0.03], [0.5, 0.35, 0.2])[:m] * weight
        x[i:] += clunk
    for k in range(9):
        i = int(rng.uniform(1.35, 2.0) * SR)
        c = pin_pin(k)[: n - i] * rng.uniform(0.15, 0.35)
        x[i:i + len(c)] += c
    return fade(x, 0.05, 0.3)


# ============================================================== stingers ====
def organ(freqs, dur, attack=0.35, release=0.8, tremolo=5.2):
    t = t_axis(dur)
    x = np.zeros_like(t)
    for f in freqs:
        for h, a in ((1, 1.0), (2, 0.45), (3, 0.22), (4, 0.12), (6, 0.05)):
            for det in (-0.003, 0.003):
                x += a * np.sin(2 * np.pi * f * h * (1 + det) * t)
    amp = np.clip(t / attack, 0, 1) * np.clip((dur - t) / release, 0, 1)
    return x * amp * (1 + 0.12 * np.sin(2 * np.pi * tremolo * t))


def bell(f, dur, decay=1.4):
    t = t_axis(dur)
    parts = ((1.0, 1.0), (2.76, 0.5), (5.40, 0.28), (8.93, 0.14), (0.5, 0.25))
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * r ** 0.5 / decay) for r, a in parts)


def strike():
    """A ghostly organ swell under a bright bell - D minor, resolving up."""
    x = organ([146.83, 174.61, 220.0, 293.66], 2.6) * 0.18
    b = bell(1174.66, 2.6) * 0.5
    b2 = np.concatenate([np.zeros(int(0.18 * SR)), bell(1479.98, 2.42)])[: len(b)] * 0.4
    return trim_tail(hall(x + b + b2, decay=2.4, wet=0.45))


def spare():
    a = bell(880.0, 1.6)
    b = np.concatenate([np.zeros(int(0.16 * SR)), bell(1318.5, 1.44)])[: len(a)]
    return trim_tail(hall((a + b) * 0.5, decay=1.8, wet=0.4))


def gutter_sting():
    """A theremin sighing down."""
    t = t_axis(1.6)
    f = 700 * (0.3 ** (t / 1.6)) * (1 + 0.012 * np.sin(2 * np.pi * 6.0 * t))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.clip(t / 0.08, 0, 1) * np.clip((1.6 - t) / 0.5, 0, 1)
    return trim_tail(hall(x * 0.6, decay=2.0, wet=0.5))


def final():
    x = organ([110.0, 164.81, 220.0, 261.63, 329.63], 3.6, attack=0.6, release=1.4) * 0.16
    return trim_tail(hall(x + bell(659.25, 3.6, 2.0) * 0.35, decay=3.0, wet=0.5))


# ============================================================ ambience etc ==
def ambience(dur=24.0):
    """The hall at night: a low organ drone that breathes, wind at the glass,
    and candles ticking. Every periodic part fits 24 s exactly."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    drone = (np.sin(2 * np.pi * 55.0 * t) + 0.6 * np.sin(2 * np.pi * 82.5 * t)
             + 0.35 * np.sin(2 * np.pi * 110.0 * t) + 0.15 * np.sin(2 * np.pi * 165.0 * t))
    drone *= 0.55 + 0.45 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 12.0))
    wind = periodic_noise(n, 180, 900, tilt=-1.2)
    wind *= 0.35 + 0.65 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 8.0 + 1.0)) ** 2
    crackle = np.zeros(n)
    for _ in range(90):
        i = rng.integers(2000, n - 2000)
        m = rng.integers(200, 900)
        crackle[i:i + m] += bandnoise(m, 2000, 8000) * env(m, 0.002) * rng.uniform(0.2, 1.0)
    return drone * 0.35 + wind * 0.5 + crackle * 0.25


def whoosh():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    for i in range(0, n, 512):
        fc = 300 + 2200 * (i / n)
        seg = bandnoise(min(512 + 256, n - i), fc * 0.7, fc * 1.3, order=2)
        out[i:i + len(seg)] += seg * np.hanning(len(seg))
    return fade(out * np.sin(np.pi * t / 0.45) ** 2, 0.01, 0.05)


def replay_swell():
    n = int(1.0 * SR)
    t = np.arange(n) / SR
    x = hall(rng.standard_normal(int(0.05 * SR)) * 0.5, decay=0.9, wet=1.0)[:n][::-1]
    x = np.concatenate([x, np.zeros(max(0, n - len(x)))])[:n]
    boom = np.sin(2 * np.pi * 48 * t) * np.exp(-np.maximum(t - 0.85, 0) / 0.15) * (t > 0.85)
    return fade(x + boom * 0.8, 0.05, 0.05)


def select():
    t = t_axis(0.25)
    return fade(np.sin(2 * np.pi * 988 * t) * np.exp(-t / 0.06) +
                0.4 * np.sin(2 * np.pi * 1976 * t) * np.exp(-t / 0.03), 0.0005, 0.03)


def pins_only():
    """Just the pin contact families - the rest of the mix stays as it is.
    (The originals of these, from before the low-end pass, are the bone_*
    files, which the bone pin set plays.)"""
    for k in range(1, 7):
        save("ball_pin_%d" % k, ball_pin(k))
        save("pin_lane_%d" % k, pin_lane(k))
    for k in range(1, 9):
        save("pin_pin_%d" % k, pin_pin(k))
    for k in range(1, 5):
        save("pin_kick_%d" % k, pin_kick(k))
    for k in range(1, 4):
        save("pin_pit_%d" % k, pin_pit(k))
        save("crash_%d" % k, crash(k))


if __name__ == "__main__" and "--pins" in sys.argv:
    pins_only()
elif __name__ == "__main__":
    print("writing", os.path.normpath(OUT))
    save("roll_loop", roll_loop(), 0.8)
    save("gutter_loop", gutter_loop(), 0.8)
    save("release", release_thump())
    save("pit", pit_thud())
    for k in range(1, 7):
        save("ball_pin_%d" % k, ball_pin(k))
        save("pin_lane_%d" % k, pin_lane(k))
    for k in range(1, 9):
        save("pin_pin_%d" % k, pin_pin(k))
    for k in range(1, 5):
        save("pin_kick_%d" % k, pin_kick(k))
    for k in range(1, 4):
        save("pin_pit_%d" % k, pin_pit(k))
        save("crash_%d" % k, crash(k))
    save("pinsetter", pinsetter())
    save("strike", strike())
    save("spare", spare())
    save("gutter", gutter_sting())
    save("final", final())
    save("ambience_loop", ambience(), 0.7)
    save("whoosh", whoosh())
    save("replay", replay_swell())
    save("select", select())
