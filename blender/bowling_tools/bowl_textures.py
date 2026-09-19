"""Numpy-baked textures for the Phantom Bowling art. Row 0 = image bottom.

The ball textures are equirectangular: pixel (u, v) is the direction
lon = 2*pi*u, lat = pi*(v - 0.5), matching bowl_balls.sphere(). Designs are
painted by projecting each direction onto the ball's front (-Y) hemisphere,
so they don't stretch.
"""
import math
import numpy as np
from lounge_textures import (fbm, norm01, grid, lerp, cover, over, sd_circle,  # noqa: F401
                             sd_segment, sd_box, sd_tri, save, _upsample, _voronoi_lead, G)
from bowl_common import (LANE_HALF, DECK_END, PITCH, LANE_LEN, PIN_SPACING, ROW_SPACING,
                         SQ3_2)

BOARD = 2 * LANE_HALF / 39.0
MAPLE_LO = (0.55, 0.36, 0.18)
MAPLE_HI = (0.78, 0.57, 0.32)


def board_x(b):
    return (20.0 - b) * BOARD


# ================================================================ wood ======
def _boards(H, W, width_m, seed, n_boards):
    u, v = grid(H, W)
    grain = _upsample(fbm(max(H // 32, 8), W, 6, 16, seed), H, W)
    fine = _upsample(fbm(max(H // 12, 8), W, 5, 60, seed + 1), H, W)
    b = np.clip(np.floor(u * n_boards), 0, n_boards - 1).astype(int)
    rng = np.random.default_rng(seed + 2)
    tone = rng.uniform(0.84, 1.14, n_boards).astype(G)[b]
    t = np.clip(0.55 * grain + 0.45 * fine, 0, 1)
    rgb = lerp(MAPLE_LO, MAPLE_HI, t) * tone[..., None]
    fu = u * n_boards - np.floor(u * n_boards)
    seam = cover(np.minimum(fu, 1 - fu) * (width_m / n_boards) - 0.0006, 0.0006)
    return u, v, over(rgb, (0.22, 0.12, 0.06), seam * 0.8)


def lane():
    """One lane from the foul line to the end of the pin deck."""
    W, H = 384, 6144
    u, v, rgb = _boards(H, W, 2 * LANE_HALF, 11, 39)
    X = (u - 0.5) * 2 * LANE_HALF
    Y = v * DECK_END
    ink = (0.10, 0.04, 0.03)
    for b in (5, 10, 15, 20, 25, 30, 35):
        tip = 3.66 + (4 - abs(b - 20) / 5.0) * 0.305
        x = board_x(b)
        d = sd_tri(X, Y, [(x - 0.013, tip - 0.16), (x + 0.013, tip - 0.16), (x, tip)])
        rgb = over(rgb, ink, cover(d, 0.002))
    for b in (3, 5, 8, 11, 14, 26, 29, 32, 35, 37):
        rgb = over(rgb, ink, cover(sd_circle(X, Y, board_x(b), 2.134, 0.007), 0.002))
    for b in (10, 30):                                   # range finders at 34-40 ft
        rgb = over(rgb, ink, cover(sd_box(X, Y, board_x(b), 11.28, 0.004, 0.9), 0.002) * 0.6)
    deck = Y > LANE_LEN - 0.2
    rgb[deck] *= 1.06
    for row in range(4):
        for k in range(row + 1):
            x = (k - row * 0.5) * PIN_SPACING
            y = LANE_LEN + row * ROW_SPACING
            rgb = over(rgb, (0.16, 0.08, 0.05), cover(sd_circle(X, Y, x, y, 0.029), 0.002))
    return save("BWL_Lane", rgb)


def approach():
    W, H = 640, 1664
    u, v, rgb = _boards(H, W, PITCH, 21, 65)
    X = (u - 0.5) * PITCH
    Y = -4.6 + v * 4.6
    ink = (0.10, 0.05, 0.03)
    for yy in (-3.66, -4.47):
        for b in (3, 5, 8, 11, 14, 20, 26, 29, 32, 35, 37):
            rgb = over(rgb, ink, cover(sd_circle(X, Y, board_x(b), yy, 0.008), 0.002))
    foul = (np.abs(Y + 0.012) < 0.012) & (np.abs(X) < LANE_HALF)
    rgb[foul] = (0.02, 0.02, 0.02)
    return save("BWL_Approach", rgb)


def marble():
    """Black marble tiles, 1024 px = 2 m, 2 x 2 tiles with brass joints."""
    S = 1024
    u, v = grid(S, S)
    n1 = fbm(S, S, 7, 4, seed=31)
    n2 = fbm(S, S, 6, 7, seed=32)
    vein = (1.0 - np.abs(np.sin((u * 3.1 + v * 1.7) * 6.0 + n1 * 12.0))) ** 18
    vein2 = (1.0 - np.abs(np.sin((u * -1.3 + v * 2.2) * 5.0 + n2 * 10.0))) ** 26
    rgb = lerp((0.020, 0.020, 0.024), (0.070, 0.068, 0.080), n2)
    rgb = over(rgb, (0.55, 0.48, 0.40), np.clip(vein * 0.55 + vein2 * 0.3, 0, 1))
    tu, tv = (u * 2) % 1.0, (v * 2) % 1.0
    edge = np.minimum(np.minimum(tu, 1 - tu), np.minimum(tv, 1 - tv)) * 1.0
    rgb = over(rgb, (0.45, 0.33, 0.14), cover(edge - 0.004, 0.002))
    return save("BWL_Marble", rgb)


# ============================================================ glowing bits ==
def _pin_sdf(X, Y, cx, base, hgt):
    prof = [(0.0, 0.12), (0.1, 0.16), (0.33, 0.22), (0.55, 0.14), (0.68, 0.085),
            (0.79, 0.10), (0.90, 0.105), (0.97, 0.07), (1.0, 0.0)]
    ts = np.array([p[0] for p in prof]); rs = np.array([p[1] for p in prof])
    t = np.clip((Y - base) / hgt, 0, 1)
    rr = np.interp(t, ts, rs) * hgt * 0.95
    inside_y = (Y >= base) & (Y <= base + hgt)
    return np.where(inside_y, np.abs(X - cx) - rr,
                    np.maximum(np.maximum(base - Y, Y - base - hgt), np.abs(X - cx)))


MASK_W, MASK_SPRING = 1.30, 0.50
MASK_H = MASK_SPRING + MASK_W * SQ3_2


def mask_arch():
    """The glowing gothic arch on the masking unit over each lane's pins."""
    S = 1024
    u, v = grid(S, S)
    X, Y = (u - 0.5) * MASK_W, v * MASK_H
    n = fbm(S, S, 6, 5, seed=41)
    glow = np.clip(1.0 - np.hypot(X / 0.75, (Y - 0.25) / 1.2), 0, 1)
    rgb = lerp((0.05, 0.01, 0.10), (0.62, 0.30, 1.00), glow ** 1.5 * (0.75 + 0.35 * n))
    w = MASK_W
    hw = np.where(Y < MASK_SPRING, w * 0.5,
                  np.sqrt(np.clip(w * w - (Y - MASK_SPRING) ** 2, 0, None)) - w * 0.5)
    edge = np.minimum(hw - np.abs(X), Y)
    gold = (0.85, 0.62, 0.26)
    for e0, t in ((0.035, 0.018), (0.09, 0.006)):
        rgb = over(rgb, gold, cover(np.abs(edge - e0) - t, 0.003))
    # trefoil in the head of the arch
    cy = MASK_SPRING + 0.62
    for k in range(3):
        a = math.pi / 2 + k * math.tau / 3
        c = sd_circle(X, Y, 0.10 * math.cos(a), cy + 0.10 * math.sin(a), 0.085)
        rgb = over(rgb, gold, cover(np.abs(c) - 0.008, 0.003))
    rgb = over(rgb, gold, cover(np.abs(sd_circle(X, Y, 0.0, cy, 0.22)) - 0.012, 0.003))
    # pin-and-ball emblem low in the arch
    for cx in (-0.07, 0.07):
        d = _pin_sdf(X, Y, cx, 0.10, 0.36)
        rgb = over(rgb, (0.95, 0.90, 1.0), cover(d, 0.003))
    rgb = over(rgb, (0.12, 0.03, 0.22), cover(sd_circle(X, Y, 0.0, 0.14, 0.07), 0.003))
    rgb = over(rgb, gold, cover(np.abs(sd_circle(X, Y, 0.0, 0.14, 0.07)) - 0.006, 0.003))
    return save("BWL_MaskArch", rgb, cover(-edge, 0.003))


def pit_glow():
    H, W = 512, 256
    u, v = grid(H, W)
    n = fbm(H, W, 6, 4, seed=51)
    t = np.clip(1.0 - v * 1.3 + (n - 0.5) * 0.5, 0, 1)
    return save("BWL_PitGlow", lerp((0.01, 0.0, 0.02), (0.42, 0.16, 0.85), t ** 2))


def ghost_lancet(name, w_m, jamb, seed, palette):
    """Stained glass with a pale spectral woman standing in it."""
    rise = w_m * SQ3_2
    h_m = jamb + rise
    W = 512
    H = int(W * h_m / w_m) // 16 * 16
    u, v = grid(H, W)
    X, Y = (u - 0.5) * w_m, v * h_m
    rng = np.random.default_rng(seed)
    pts = np.stack([rng.uniform(-w_m / 2, w_m / 2, 150), rng.uniform(0, h_m, 150)], 1).astype(G)
    lead, cell = _voronoi_lead(X, Y, pts)
    pal = np.array(palette, dtype=G)
    rgb = pal[rng.integers(0, len(pal), 150)][cell] * rng.uniform(0.6, 1.2, (150, 1)).astype(G)[cell]
    rgb *= (0.7 + 0.5 * fbm(H, W, 5, 6, seed=seed + 1))[..., None]
    # the figure: bell gown, narrow waist, head, arms lifted to the shoulders
    bot, top = 0.25, jamb + rise * 0.15
    s = np.clip((top - Y) / (top - bot), 0, 1)
    gown = np.abs(X) - (0.07 * w_m + 0.19 * w_m * s ** 1.6)
    gown = np.where((Y > bot) & (Y < top), gown, 1.0)
    head_y = top + 0.14 * w_m
    head = sd_circle(X, Y, 0.0, head_y, 0.075 * w_m)
    arms = np.minimum(sd_segment(X, Y, -0.08 * w_m, top - 0.05, -0.2 * w_m, top + 0.25) - 0.02,
                      sd_segment(X, Y, 0.08 * w_m, top - 0.05, 0.2 * w_m, top + 0.25) - 0.02)
    body = np.minimum(np.minimum(gown, head), arms)
    halo = np.exp(-np.clip(body, 0, None) / (0.08 * w_m))
    ghost = (0.70, 0.92, 1.00)
    rgb = lerp(rgb, ghost, np.clip(halo * 0.55, 0, 1))
    rgb = over(rgb, ghost, cover(body, 0.01) * 0.9)
    trac = np.abs(np.abs(X) - w_m * 0.25) - 0.018
    trac = np.where(np.abs(X) < w_m * 0.4, trac, 1.0)
    dark = np.minimum(lead - 0.008, np.where(body < 0.02, 1.0, trac))
    rgb = over(rgb, (0.01, 0.01, 0.015), cover(dark, 0.005))
    return save(name, rgb)


def ghost_portrait():
    H, W = 768, 576
    u, v = grid(H, W)
    X, Y = u - 0.5, (v - 0.5) * 1.33
    n = fbm(H, W, 6, 5, seed=61)
    rgb = lerp((0.012, 0.012, 0.03), (0.05, 0.06, 0.11), n)
    gown = np.abs(X) - (0.06 + 0.26 * np.clip((0.1 - Y) / 0.75, 0, 1) ** 1.4)
    gown = np.where((Y < 0.1) & (Y > -0.65), gown, 1.0)
    head = sd_circle(X, Y, 0.0, 0.2, 0.075)
    body = np.minimum(gown, head)
    halo = np.exp(-np.clip(body, 0, None) / 0.07)
    rgb = lerp(rgb, (0.35, 0.65, 1.0), np.clip(halo * 0.6, 0, 1))
    rgb = over(rgb, (0.62, 0.86, 1.0), cover(body, 0.01) * 0.75)
    vign = 1.0 - np.clip(np.hypot(X, Y / 1.2) * 1.1, 0, 1) ** 2
    return save("BWL_GhostPortrait", rgb * (0.4 + 0.6 * vign)[..., None])


def banner_pin():
    H, W = 1280, 512
    u, v = grid(H, W)
    X, Y = (u - 0.5) * 1.2, v * 3.0
    n = fbm(H, W, 6, 10, seed=71, aspect=0.4)
    fold = 0.5 + 0.5 * np.sin(u * math.tau * 3.0 + n * 2.0)
    rgb = lerp((0.10, 0.008, 0.02), (0.38, 0.03, 0.06), fold * 0.6 + n * 0.4)
    gold = (0.70, 0.50, 0.20)
    edge = np.minimum(0.6 - np.abs(X), Y - 0.45 * np.abs(X) / 0.6)
    rgb = over(rgb, gold, cover(np.abs(edge - 0.06) - 0.014, 0.004))
    rgb = over(rgb, gold, cover(_pin_sdf(X, Y, 0.0, 1.05, 1.15), 0.004))
    rgb = over(rgb, (0.38, 0.03, 0.06), cover(np.abs(Y - 1.84) - 0.02, 0.004)
               * cover(_pin_sdf(X, Y, 0.0, 1.05, 1.15), 0.004))
    ball = sd_circle(X, Y, 0.0, 0.78, 0.2)
    rgb = over(rgb, gold, cover(ball, 0.004))
    for hx, hy in ((-0.06, 0.86), (0.06, 0.86), (0.0, 0.72)):
        rgb = over(rgb, (0.2, 0.02, 0.03), cover(sd_circle(X, Y, hx, hy, 0.028), 0.004))
    fl = sd_circle(X, Y, 0.0, 2.55, 0.07)
    for s in (-1, 1):
        fl = np.minimum(fl, sd_segment(X, Y, 0.0, 2.55, s * 0.2, 2.75) - 0.03)
    rgb = over(rgb, gold, cover(fl, 0.004))
    return save("BWL_BannerPin", rgb, cover(-edge, 0.003))


# ================================================================= balls ====
BALL_W, BALL_H = 2048, 1024


def ball_dirs(W=BALL_W, H=BALL_H):
    u, v = grid(H, W)
    lon = u * math.tau
    lat = (v - 0.5) * math.pi
    D = np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], -1)
    return D.astype(G)


def wave_noise(D, n=28, fmin=2.0, fmax=9.0, seed=0):
    """Smooth, seam-free noise on the sphere: a sum of random plane waves."""
    rng = np.random.default_rng(seed)
    out = np.zeros(D.shape[:2], dtype=G)
    for i in range(n):
        k = rng.normal(size=3)
        k /= np.linalg.norm(k)
        f = fmin * (fmax / fmin) ** (i / max(n - 1, 1))
        out += np.sin((D @ k.astype(G)) * f + rng.uniform(0, math.tau)) / (1 + i * 0.15)
    return norm01(out)


def sphere_voronoi(D, n, seed, chunk=128):
    """Edge metric of a Voronoi tiling on the sphere (small = on a crack)."""
    rng = np.random.default_rng(seed)
    P = rng.normal(size=(n, 3))
    P = (P / np.linalg.norm(P, axis=1, keepdims=True)).astype(G)
    H = D.shape[0]
    out = np.zeros(D.shape[:2], dtype=G)
    for r0 in range(0, H, chunk):
        dots = D[r0:r0 + chunk] @ P.T
        top2 = np.partition(dots, -2, axis=2)[..., -2:]
        out[r0:r0 + chunk] = top2[..., 1] - top2[..., 0]
    return out


# finger holes, clear of the front designs: two fingers on top, thumb behind
HOLES = [((0.16, 0.35, 1.0), 0.10), ((-0.16, 0.35, 1.0), 0.10), ((0.0, 1.3, 1.0), 0.12)]


def paint_holes(D, rgb):
    for (hx, hy, hz), r in HOLES:
        h = np.array([hx, hy, hz], dtype=G)
        h /= np.linalg.norm(h)
        ang = np.arccos(np.clip(D @ h, -1, 1))
        rgb = over(rgb, (0.25, 0.25, 0.27), cover(np.abs(ang - r) - 0.012, 0.004))
        rgb = over(rgb, (0.006, 0.006, 0.008), cover(ang - r + 0.006, 0.004))
    return rgb


def front(D):
    """(a, b, facing): coordinates on the -Y hemisphere, seen from the front."""
    return D[..., 0], D[..., 2], -D[..., 1]


def ball_spectre():
    """The Spectre: a hooded reaper in obsidian, split by glowing lava cracks."""
    D = ball_dirs()
    a, b, f = front(D)
    heat = wave_noise(D, seed=3)
    crack = sphere_voronoi(D, 120, seed=5)
    lava_line = cover(crack - 0.004, 0.003)
    halo = np.exp(-crack / 0.012) * (0.3 + 0.7 * heat)
    base = lerp((0.012, 0.010, 0.010), (0.06, 0.03, 0.02), heat)
    base = over(base, (0.55, 0.14, 0.02), lava_line)
    emit = lerp((0, 0, 0), (1.0, 0.30, 0.03), np.clip(lava_line * 0.7 + halo * 0.2, 0, 1) * (0.35 + heat * 0.6))

    # the reaper, on the front face
    shoulder = 0.20
    hw = np.where(b > shoulder, 0.42 * np.sqrt(np.clip((0.82 - b) / (0.82 - shoulder), 0, 1)),
                  0.42 + (shoulder - b) * 0.65)
    fig = np.where((f > 0.1) & (b < 0.82), np.abs(a) - hw, 1.0)
    fig_in = cover(fig, 0.004)
    folds = 0.5 + 0.5 * np.sin(a * 24 + 2.5 * np.sin(b * 5.0) + heat * 4)
    robe = lerp((0.015, 0.012, 0.012), (0.10, 0.06, 0.05), folds * np.clip(0.6 - b, 0, 1))
    base = lerp(base, robe, cover(fig + 0.01, 0.004))
    emit = lerp(emit, emit * 0.0, fig_in)
    rim = cover(np.abs(fig) - 0.012, 0.01) * (f > 0.1)
    emit = over(emit, (1.0, 0.45, 0.08), rim)
    base = over(base, (0.60, 0.18, 0.03), rim)
    ember = np.clip((folds - 0.8) * 5, 0, 1) * fig_in * np.clip(0.3 - b, 0, 1) * 1.5
    emit = over(emit, (0.9, 0.25, 0.02), np.clip(ember, 0, 1) * 0.6)
    face = ((a / 0.20) ** 2 + ((b - 0.24) / 0.26) ** 2) - 1.0
    face_in = cover(face * 0.1, 0.004) * (f > 0.1)
    base = lerp(base, (0.0, 0.0, 0.0), face_in)
    emit = lerp(emit, (0.25, 0.03, 0.0), face_in * np.clip(0.2 - (b - 0.24), 0, 1))
    for s in (-1, 1):
        ex, ey = s * 0.075, 0.25
        ca, sa = math.cos(s * 0.35), math.sin(s * 0.35)
        lx = (a - ex) * ca + (b - ey) * sa
        ly = -(a - ex) * sa + (b - ey) * ca
        eye = ((lx / 0.048) ** 2 + (ly / 0.020) ** 2) - 1.0
        e_in = cover(eye * 0.02, 0.003) * (f > 0.1)
        glow = np.exp(-np.clip(eye, 0, None) * 0.9) * (f > 0.1) * 0.5
        base = over(base, (1.0, 0.75, 0.25), e_in)
        emit = over(emit, (1.0, 0.72, 0.18), np.clip(e_in + glow * face_in, 0, 1))
    base = paint_holes(D, base)
    emit = paint_holes(D, emit) * (base.sum(-1, keepdims=True) > 0.03)
    return save("BWL_BallSpectre", base), save("BWL_BallSpectreEmit", emit)


def ball_p():
    """The P: black marble, violet lightning, and a raised silver gothic P."""
    D = ball_dirs()
    a, b, f = front(D)
    n1 = wave_noise(D, seed=11)
    n2 = wave_noise(D, n=36, fmin=4, fmax=18, seed=12)
    n3 = wave_noise(D, n=40, fmin=10, fmax=40, seed=14)
    vein = (1.0 - np.abs(np.sin(n1 * 9.0 + n3 * 7.0))) ** 30
    bolt = (1.0 - np.abs(np.sin(n2 * 8.0 + n3 * 9.0))) ** 70
    base = lerp((0.015, 0.014, 0.018), (0.06, 0.055, 0.07), n2)
    base = over(base, (0.42, 0.40, 0.46), vein * 0.6)
    violet = (0.54, 0.17, 0.89)
    base = over(base, (0.30, 0.10, 0.55), bolt)
    emit = lerp((0, 0, 0), violet, np.clip(bolt * 1.6, 0, 1))

    # the monogram
    stem = sd_box(a, b, -0.19, 0.00, 0.115, 0.52, r=0.02)
    spike = sd_tri(a, b, [(-0.305, -0.50), (-0.075, -0.50), (-0.19, -0.84)])
    cap = sd_tri(a, b, [(-0.33, 0.50), (-0.05, 0.50), (-0.19, 0.72)])
    outer = sd_circle(a, b, 0.04, 0.24, 0.37)
    inner = sd_circle(a, b, 0.04, 0.24, 0.17)
    bowl = np.maximum(np.maximum(outer, -inner), -(a + 0.10))
    tail = sd_tri(a, b, [(0.08, -0.08), (0.34, -0.06), (0.46, -0.30)])
    cross = (np.abs(a) / 0.80 + np.abs(b + 0.02) / 0.11 - 1.0) * 0.1
    glyph = np.minimum.reduce([stem, spike, cap, bowl, tail, cross])
    glyph = np.where(f > 0.25, glyph, 1.0)
    counter = np.where((f > 0.25) & (a > -0.10), inner, 1.0)
    inlay = cover(counter, 0.004)
    base = lerp(base, (0.12, 0.03, 0.22), inlay)
    emit = lerp(emit, (0.45, 0.12, 0.85), inlay * (0.4 + 0.6 * wave_noise(D, seed=13)))
    g_in = cover(glyph, 0.003)
    shade = np.clip(0.55 + b * 0.5 + (n2 - 0.5) * 0.3, 0, 1)
    silver = lerp((0.30, 0.30, 0.34), (0.78, 0.78, 0.82), shade)
    base = lerp(base, silver, g_in)
    emit = emit * (1 - g_in[..., None])
    line = cover(np.abs(glyph) - 0.011, 0.003) * (f > 0.25)
    base = over(base, (0.05, 0.05, 0.06), line)
    base = paint_holes(D, base)
    emit = paint_holes(D, emit)
    orm = np.stack([np.ones_like(a), 0.07 + 0.30 * g_in, g_in * 0.9], -1)
    return (save("BWL_BallP", base), save("BWL_BallPEmit", emit), save("BWL_BallPORM", orm))


def skull():
    """Bone texture for the skull inside the clear resin ball."""
    D = ball_dirs(1024, 512)
    a, b, f = front(D)
    n = wave_noise(D, seed=21)
    n2 = wave_noise(D, n=30, fmin=6, fmax=24, seed=22)
    base = lerp((0.36, 0.30, 0.21), (0.70, 0.62, 0.47), n * 0.6 + 0.4)
    base = over(base, (0.30, 0.24, 0.16), ((1 - np.abs(np.sin(n2 * 20))) ** 40) * 0.6)
    emit = np.zeros_like(base)
    front_ = f > 0.05
    for s in (-1, 1):
        sock = (((a - s * 0.33) / 0.27) ** 2 + ((b - 0.10) / 0.25) ** 2) - 1.0
        rim = cover(np.abs(sock * 0.1) - 0.012, 0.006) * front_
        base = over(base, (0.36, 0.30, 0.20), rim)
        s_in = cover(sock * 0.1, 0.004) * front_
        base = lerp(base, (0.02, 0.015, 0.02), s_in)
        deep = np.clip(1.0 - (((a - s * 0.34) / 0.12) ** 2 + ((b - 0.08) / 0.10) ** 2), 0, 1)
        emit = over(emit, (0.55, 0.20, 1.00), deep * front_)
    nose = sd_tri(a, b, [(-0.08, -0.20), (0.08, -0.20), (0.0, 0.0)])
    base = lerp(base, (0.03, 0.02, 0.02), cover(np.where(front_, nose, 1.0), 0.004))
    teeth = (b < -0.36) & (b > -0.58) & front_ & (np.abs(a) < 0.38)
    gap = np.abs(((a + 0.38) / 0.076) % 1.0 - 0.5) > 0.43
    base[teeth] = (0.80, 0.74, 0.58)
    base[teeth & gap] = (0.05, 0.03, 0.02)
    base[(np.abs(b + 0.47) < 0.012) & (np.abs(a) < 0.38) & front_] = (0.08, 0.05, 0.03)
    return save("BWL_Skull", base), save("BWL_SkullEmit", emit)


def build():
    out = {"lane": lane(), "approach": approach(), "marble": marble(),
           "mask": mask_arch(), "pit": pit_glow(),
           "glass_center": ghost_lancet("BWL_GlassGhost", 2.2, 1.5, 81,
                                        [(0.06, 0.08, 0.45), (0.20, 0.08, 0.55), (0.35, 0.12, 0.75),
                                         (0.08, 0.18, 0.70), (0.45, 0.20, 0.85), (0.12, 0.05, 0.35)]),
           "glass_side": ghost_lancet("BWL_GlassSide", 1.6, 1.4, 83,
                                      [(0.10, 0.06, 0.40), (0.28, 0.10, 0.62), (0.08, 0.14, 0.60),
                                       (0.40, 0.18, 0.80)]),
           "portrait": ghost_portrait(), "banner": banner_pin()}
    out["spectre"] = ball_spectre()
    out["p"] = __import__("bowl_ball_p").ball_p2()      # v2: forged blackletter P (bowl_ball_p.py)
    out["skull"] = skull()
    return out
