"""Cut the real recordings in audio_src/ into the game's "recorded" pin-sound set.

    audio_src/ball roll and strike.mp3  -> audio/rec_crash_1.wav, rec_crash_2.wav
    audio_src/pin setter.wav            -> audio/rec_pinsetter_1..3.wav

Needs ffmpeg on the PATH (to decode the mp3). The recordings are Gregg's
(sourced from Freesound, CC0); audio_src/ has a .gdignore so Godot skips it.
"""
import os, subprocess, tempfile
import numpy as np
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "audio_src")
OUT = os.path.join(HERE, "..", "audio")
SR = 44100


def load(name):
    tmp = os.path.join(tempfile.gettempdir(), "cut_rec.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(SRC, name), "-ac", "1",
                    "-ar", str(SR), tmp], check=True)
    sr, x = wavfile.read(tmp)
    return x.astype(np.float64) / 32768.0


def rms_db(x, win=0.02):
    w = int(SR * win)
    n = len(x) // w
    return 20 * np.log10(np.sqrt(np.mean(x[:n * w].reshape(n, w) ** 2, axis=1)) + 1e-9), w


def save(name, x, fade_out=0.25, peak=0.89):
    n = len(x)
    f_in = int(0.003 * SR)
    f_out = min(int(fade_out * SR), n // 2)
    x = x.copy()
    x[:f_in] *= np.linspace(0, 1, f_in)
    x[-f_out:] *= np.linspace(1, 0, f_out) ** 1.5
    x = x / (np.abs(x).max() + 1e-9) * peak
    wavfile.write(os.path.join(OUT, name + ".wav"), SR, (x * 32767).astype(np.int16))
    print("  %-18s %.2fs" % (name, n / SR))


def onset(x, start, thresh=0.25):
    seg = np.abs(x[start:])
    i = int(np.argmax(seg > thresh * seg.max()))
    return max(start, start + i - int(0.006 * SR))


def strike():
    x = load("ball roll and strike.mp3")
    db, w = rms_db(x)
    t0 = onset(x, 0)
    # the first rack runs until the quietest moment before the second burst
    lo, hi = int(1.8 * SR / w), int(2.4 * SR / w)
    gap = (lo + int(np.argmin(db[lo:hi]))) * w
    save("rec_crash_1", x[t0:gap], 0.35)
    t1 = onset(x, gap)
    save("rec_crash_2", x[t1:], 0.3)


def pinsetter(count=3, length=3.0):
    x = load("pin setter.wav")
    db, w = rms_db(x, 0.05)
    # the loudest onsets (a jump of 8 dB or more), at least `length` apart
    jumps = np.diff(db)
    cands = [k for k in range(len(jumps)) if jumps[k] > 6.0 and db[k + 1] > -32]
    cands.sort(key=lambda k: -db[k + 1])
    picks = []
    for k in cands:
        if len(picks) == count:
            break
        s = (k + 1) * w - int(0.05 * SR)
        if s + int(length * SR) <= len(x) and all(abs(s - p) > length * SR for p in picks):
            picks.append(s)
    for i, s in enumerate(sorted(picks)):
        save("rec_pinsetter_%d" % (i + 1), x[s:s + int(length * SR)], 0.6, peak=0.7)


if __name__ == "__main__":
    strike()
    pinsetter()
