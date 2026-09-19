"""The P ball, second version (reference: art/reference/balls_reaper_owl_logo.webp).

A blackletter P forged in dark steel - pointed flag, spiked foot, a broken-arc
bowl, a sword-like crossbar with diamond tips and a curling tail - raised off
black marble shot through with glowing violet lightning. The relief is a
normal map baked from the glyph's height field, so the letter catches light
along its bevels; the counter of the bowl is a recessed violet glow.

Returns (base, emit, orm, normal) images, 2048 x 1024 equirect.
"""
import math
import numpy as np
from lounge_textures import lerp, cover, over, save, G, norm01
from bowl_textures import (ball_dirs, wave_noise, front, paint_holes, sd_circle, sd_tri, BALL_W,
                           BALL_H)

BALL_R = 0.1085
RELIEF = 0.0028                  # metres the letter stands proud


def sd_poly(a, b, pts):
    """Signed distance to a polygon (negative inside), vectorised."""
    P = np.array(pts, dtype=np.float64)
    d = np.full(a.shape, np.inf)
    s = np.ones(a.shape)
    n = len(P)
    for i in range(n):
        vi, vj = P[i], P[i - 1]
        ex, ey = vj - vi
        wx, wy = a - vi[0], b - vi[1]
        t = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0.0, 1.0)
        dx, dy = wx - ex * t, wy - ey * t
        d = np.minimum(d, dx * dx + dy * dy)
        c1 = b >= vi[1]
        c2 = b < vj[1]
        c3 = ex * wy > ey * wx
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s = np.where(flip, -s, s)
    return s * np.sqrt(d)


def glyph_sdf(a, b):
    stem = sd_poly(a, b, [(-0.31, 0.55), (-0.09, 0.55), (-0.11, -0.44), (-0.29, -0.44)])
    foot = sd_poly(a, b, [(-0.31, -0.42), (-0.09, -0.42), (-0.17, -0.62), (-0.25, -0.90), (-0.30, -0.60)])
    flag = sd_poly(a, b, [(-0.46, 0.60), (-0.09, 0.53), (-0.06, 0.66), (-0.22, 0.82)])
    bowl_o = sd_poly(a, b, [(-0.12, 0.66), (0.20, 0.66), (0.40, 0.52), (0.45, 0.26), (0.30, 0.04),
                           (-0.12, 0.04)])
    counter = sd_poly(a, b, [(-0.02, 0.52), (0.17, 0.52), (0.29, 0.42), (0.31, 0.26), (0.21, 0.15),
                             (-0.02, 0.15)])
    bowl = np.maximum(bowl_o, -counter)
    # crossbar: a long blade with diamond tips and a boss where it crosses the stem
    bar = sd_poly(a, b, [(-0.72, 0.035), (0.62, 0.035), (0.62, -0.035), (-0.72, -0.035)])
    tips = np.minimum(sd_poly(a, b, [(-0.86, 0.0), (-0.72, 0.08), (-0.62, 0.0), (-0.72, -0.08)]),
                      sd_poly(a, b, [(0.76, 0.0), (0.62, 0.08), (0.52, 0.0), (0.62, -0.08)]))
    boss = sd_poly(a, b, [(-0.20, 0.14), (-0.06, 0.0), (-0.20, -0.14), (-0.34, 0.0)])
    # the tail: a curl sweeping down from the bowl and back up into a point
    r = np.hypot(a - 0.30, b + 0.24)
    ang = np.arctan2(b + 0.24, a - 0.30)
    ring = np.abs(r - 0.21) - (0.022 + 0.042 * np.clip((ang + 2.6) / 4.2, 0, 1))
    tail = np.where((ang > -2.7) & (ang < 1.9), ring, 1.0)
    tail_tip = sd_tri(a, b, [(0.09, -0.31), (0.21, -0.29), (0.03, -0.48)])
    g = np.minimum.reduce([stem, foot, flag, bowl, bar, tips, boss, tail, tail_tip])
    return g, counter


def ball_p2():
    D = ball_dirs()
    a, b, f = front(D)
    H, W = a.shape
    n1 = wave_noise(D, seed=21)
    n2 = wave_noise(D, n=36, fmin=4, fmax=18, seed=22)
    n3 = wave_noise(D, n=40, fmin=10, fmax=40, seed=24)
    n4 = wave_noise(D, n=24, fmin=2, fmax=6, seed=25)

    # --- black marble with violet storm light
    base = lerp((0.008, 0.008, 0.012), (0.035, 0.032, 0.045), n2 * 0.6 + n4 * 0.4)
    vein = (1.0 - np.abs(np.sin(n1 * 8.0 + n3 * 6.0))) ** 40
    base = over(base, (0.30, 0.29, 0.34), vein * 0.35)
    # lightning: the ridges of a warped noise field, made jagged by a finer one
    n5 = wave_noise(D, n=48, fmin=5, fmax=14, seed=27)
    n6 = wave_noise(D, n=60, fmin=25, fmax=70, seed=28)
    ridge = 1.0 - np.abs(2.0 * norm01(n5 + 0.35 * n3 + 0.12 * n6) - 1.0)
    bolt = np.clip(ridge, 0, 1) ** 45
    halo = np.clip(ridge, 0, 1) ** 9
    cloud = np.clip((n4 - 0.55) * 3.0, 0, 1) ** 1.5
    violet = np.array((0.58, 0.20, 1.0), dtype=G)
    base = over(base, (0.22, 0.07, 0.42), np.clip(halo * 0.5 + cloud * 0.4, 0, 1))
    base = over(base, (0.70, 0.45, 1.0), bolt)
    emit = violet * np.clip(bolt * 1.4 + halo * 0.18 + cloud * 0.10, 0, 1)[..., None]

    # --- the letter
    k = 1.32                                                  # the letter fills the face of the ball
    g, counter = glyph_sdf(a / k, (b + 0.04) / k)
    g, counter = g * k, counter * k
    on_front = f > 0.3
    g = np.where(on_front, g, 1.0)
    counter = np.where(on_front, counter, 1.0)
    bevel = 0.028
    hgt = np.clip(-g / bevel, 0.0, 1.0)
    hgt = hgt * hgt * (3 - 2 * hgt)                              # rounded chamfer
    groove = cover(np.abs(g + 0.045) - 0.004, 0.003)            # an engraved line inset along the edge
    hgt = hgt - groove * 0.35
    # the counter: a recessed violet glow
    inlay = cover(counter, 0.004)
    hgt = hgt - inlay * 0.5 * cover(counter + 0.01, 0.01)
    metal_in = cover(g, 0.002)

    # lighting cue baked into the colour: light from upper left
    gy, gx = np.gradient(hgt)
    lit = np.clip(0.5 + (-gx * 0.7 + gy * 0.7) * 26.0, 0, 1)
    brushed = norm01(wave_noise(D, n=60, fmin=30, fmax=90, seed=26))
    steel = lerp((0.24, 0.24, 0.28), (0.74, 0.74, 0.80), np.clip(0.35 + 0.35 * brushed + 0.3 * lit - 0.2, 0, 1))
    steel = lerp(steel, (0.05, 0.05, 0.06), groove * 0.8)            # grime in the groove
    edge = cover(np.abs(g) - 0.006, 0.003) * on_front
    steel = lerp(steel, (0.80, 0.80, 0.86), edge * lit * 0.6)        # a catch-light on the lit edges
    base = lerp(base, steel, metal_in)
    # soot around the letter where it meets the marble
    soot = np.clip(1.0 - np.clip(g, 0, None) / 0.035, 0, 1) * (1 - metal_in) * on_front
    base = base * (1.0 - 0.6 * soot)[..., None]
    base = lerp(base, (0.10, 0.02, 0.20), inlay)
    emit = emit * (1.0 - metal_in)[..., None]
    swirl = 0.45 + 0.55 * norm01(n3)
    emit = lerp(emit, violet * 0.9, np.clip(inlay * swirl, 0, 1))

    # --- normal map from the height field (u around the ball, v up)
    z = hgt * RELIEF
    lat = np.linspace(-math.pi / 2, math.pi / 2, H)[:, None]
    px_u = math.tau * BALL_R / W * np.maximum(np.cos(lat), 0.05)
    px_v = math.pi * BALL_R / H
    dzdv, dzdu = np.gradient(z)
    nrm = np.stack([-dzdu / px_u, -dzdv / px_v, np.ones_like(z)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)

    base = paint_holes(D, base)
    emit = paint_holes(D, emit)
    rough = 0.05 + 0.23 * metal_in + brushed * 0.08 * metal_in
    orm = np.stack([np.ones_like(a), rough, metal_in * 0.95], -1)
    return (save("BWL_BallP", base), save("BWL_BallPEmit", emit), save("BWL_BallPORM", orm),
            save("BWL_BallPNormal", nrm * 0.5 + 0.5))
