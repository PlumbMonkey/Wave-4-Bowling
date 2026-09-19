"""Textures for Alley 2 (The Void) and Alley 3 (The Crypt). Row 0 = image bottom."""
import math
import numpy as np
from lounge_textures import (fbm, norm01, grid, lerp, cover, over, sd_circle, sd_segment,
                             sd_box, sd_tri, save, _upsample, _voronoi_lead, G)
from bowl_textures import (_boards, board_x, _pin_sdf, MASK_W, MASK_SPRING, MASK_H, BOARD,
                           ghost_lancet)
from bowl_common import LANE_HALF, DECK_END, PITCH, LANE_LEN, PIN_SPACING, ROW_SPACING

GOLD = (0.85, 0.64, 0.28)


def crescent_sd(X, Y, cx, cy, r, thick=0.72, off=(0.36, 0.14)):
    """Signed distance to a crescent moon (outer disc minus an offset disc)."""
    outer = sd_circle(X, Y, cx, cy, r)
    inner = sd_circle(X, Y, cx + off[0] * r, cy + off[1] * r, r * thick + 0.02 * r)
    return np.maximum(outer, -inner)


def star_field(H, W, seed, density=0.0015, size=1.2):
    rng = np.random.default_rng(seed)
    n = int(H * W * density)
    img = np.zeros((H, W), dtype=G)
    ys, xs = rng.integers(0, H, n), rng.integers(0, W, n)
    br = rng.power(3.0, n).astype(G)
    img[ys, xs] = br
    # a few bright stars with soft halos
    for _ in range(max(6, n // 400)):
        y, x = rng.integers(8, H - 8), rng.integers(8, W - 8)
        yy, xx = np.mgrid[-6:7, -6:7]
        halo = np.exp(-(xx ** 2 + yy ** 2) / (2.0 * size ** 2 * 2.2)).astype(G)
        spikes = (np.exp(-(yy ** 2) * 3) * np.exp(-np.abs(xx) / 3) +
                  np.exp(-(xx ** 2) * 3) * np.exp(-np.abs(yy) / 3)).astype(G) * 0.5
        img[y - 6:y + 7, x - 6:x + 7] += halo + spikes
    return np.clip(img, 0, 1.5)


# ================================================================ THE VOID ==
def nebula_backdrop():
    """The sky beyond the open back of The Void: nebula clouds, a spiral
    galaxy, a ringed moon and a thousand stars. Wraps round a curved screen."""
    H, W = 1024, 2048
    u, v = grid(H, W)
    n1 = norm01(fbm(H, W, 7, 3, seed=501))
    n2 = norm01(fbm(H, W, 7, 5, seed=502))
    n3 = norm01(fbm(H, W, 6, 9, seed=503))
    base = lerp((0.005, 0.006, 0.03), (0.05, 0.02, 0.14), v * 0.6 + n1 * 0.4)
    cloud_v = np.clip((n1 - 0.45) * 2.4, 0, 1) ** 1.4
    cloud_b = np.clip((n2 - 0.5) * 2.6, 0, 1) ** 1.6
    rgb = lerp(base, (0.55, 0.20, 0.85), cloud_v * 0.9)
    rgb = lerp(rgb, (0.15, 0.40, 1.00), cloud_b * 0.75)
    rgb = lerp(rgb, (1.0, 0.55, 0.85), np.clip((n3 - 0.72) * 4, 0, 1) * cloud_v * 0.6)
    # the spiral galaxy, upper right of centre
    X, Y = (u - 0.62) * 2.0 * 2.0, (v - 0.64) * 2.0
    c, s = math.cos(0.5), math.sin(0.5)
    Xr, Yr = X * c - Y * s, (X * s + Y * c) * 2.6
    r = np.hypot(Xr, Yr) + 1e-4
    th = np.arctan2(Yr, Xr)
    arms = 0.5 + 0.5 * np.cos(2 * th - 7.0 * np.log(r + 0.05))
    disc = np.exp(-r / 0.16) * (0.35 + 0.65 * arms ** 3) + np.exp(-r / 0.03) * 1.5
    rgb = rgb + disc[..., None] * np.array((0.95, 0.80, 1.0), dtype=G) * 0.9
    # a moon with a thin ring, upper left
    mX, mY = (u - 0.40) * 4.0, (v - 0.72) * 2.0
    moon = cover(np.hypot(mX, mY) - 0.10, 0.004)
    shade = np.clip(0.4 + (mX + mY) * 3.0, 0.1, 1)
    rgb = over(rgb, np.stack([shade * 0.75, shade * 0.72, shade * 0.85], -1), moon)
    ring = cover(np.abs(np.hypot(mX, mY * 3.5) - 0.17) - 0.004, 0.003) * (np.hypot(mX, mY) > 0.1 - 1e-3)
    rgb = over(rgb, (0.8, 0.75, 0.9), ring * 0.7)
    stars = star_field(H, W, 504, 0.0022)
    rgb = rgb + stars[..., None] * np.array((0.95, 0.92, 1.0), dtype=G)
    return save("BWL_Nebula", np.clip(rgb, 0, 1))


def void_mask():
    """The arch over each Void lane: gold tracery and a crescent moon, open
    in the middle (alpha) so the pins stand against the nebula."""
    S = 1024
    u, v = grid(S, S)
    X, Y = (u - 0.5) * MASK_W, v * MASK_H
    w = MASK_W
    hw = np.where(Y < MASK_SPRING, w * 0.5,
                  np.sqrt(np.clip(w * w - (Y - MASK_SPRING) ** 2, 0, None)) - w * 0.5)
    edge = np.minimum(hw - np.abs(X), Y)
    rgb = np.zeros((S, S, 3), dtype=G) + np.array(GOLD, dtype=G)
    alpha = np.zeros((S, S), dtype=G)
    for e0, t in ((0.03, 0.02), (0.085, 0.007)):
        alpha = np.maximum(alpha, cover(np.abs(edge - e0) - t, 0.003))
    cy = MASK_SPRING + 0.68
    moon = crescent_sd(X, Y, 0.0, cy, 0.13)
    alpha = np.maximum(alpha, cover(moon, 0.003))
    alpha = np.maximum(alpha, cover(np.abs(sd_circle(X, Y, 0.0, cy, 0.19)) - 0.008, 0.003))
    for k in range(8):                                  # little stars round the moon
        a = k * math.tau / 8 + 0.2
        sx, sy = 0.25 * math.cos(a), cy + 0.25 * math.sin(a)
        st = (np.abs(X - sx) / 0.015 + np.abs(Y - sy) / 0.03 - 1.0) * 0.015
        st = np.minimum(st, (np.abs(X - sx) / 0.03 + np.abs(Y - sy) / 0.015 - 1.0) * 0.015)
        alpha = np.maximum(alpha, cover(st, 0.002) * (Y > MASK_SPRING + 0.2))
    alpha *= (edge > -0.01)
    return save("BWL_VoidMask", rgb, alpha)


def star_glass():
    """Side windows onto open space, with a pale spectral figure in each."""
    return ghost_lancet("BWL_VoidGlass", 1.8, 2.6, 511,
                        [(0.02, 0.03, 0.12), (0.05, 0.05, 0.22), (0.10, 0.06, 0.30),
                         (0.03, 0.08, 0.28), (0.15, 0.08, 0.38)])


def void_banner():
    H, W = 1280, 512
    u, v = grid(H, W)
    X, Y = (u - 0.5) * 1.2, v * 3.0
    n = fbm(H, W, 6, 10, seed=521, aspect=0.4)
    fold = 0.5 + 0.5 * np.sin(u * math.tau * 3.0 + n * 2.0)
    rgb = lerp((0.01, 0.015, 0.06), (0.06, 0.08, 0.24), fold * 0.6 + n * 0.4)
    edge = np.minimum(0.6 - np.abs(X), Y - 0.45 * np.abs(X) / 0.6)
    rgb = over(rgb, GOLD, cover(np.abs(edge - 0.06) - 0.012, 0.004))
    rgb = over(rgb, GOLD, cover(crescent_sd(X, Y, 0.0, 1.75, 0.34), 0.004))
    for k, (sx, sy, s) in enumerate(((0.28, 2.35, 0.06), (-0.25, 2.5, 0.04), (0.18, 1.1, 0.035),
                                     (-0.3, 1.2, 0.05), (0.0, 2.72, 0.03))):
        st = np.minimum((np.abs(X - sx) / s + np.abs(Y - sy) / (s * 2.2) - 1.0),
                        (np.abs(X - sx) / (s * 2.2) + np.abs(Y - sy) / s - 1.0)) * s
        rgb = over(rgb, GOLD, cover(st, 0.004))
    return save("BWL_VoidBanner", rgb, cover(-edge, 0.003))


def star_ceiling():
    """Vault panels: deep blue, gilded star-points and faint constellations."""
    S = 1024
    u, v = grid(S, S)
    n = fbm(S, S, 6, 4, seed=531)
    rgb = lerp((0.01, 0.012, 0.05), (0.03, 0.04, 0.12), n)
    stars = star_field(S, S, 532, 0.0012)
    rng = np.random.default_rng(533)
    lines = np.zeros((S, S), dtype=G)
    X, Y = u, v
    for _ in range(9):
        pts = rng.uniform(0.05, 0.95, (4, 2))
        for a, b in zip(pts, pts[1:]):
            lines = np.maximum(lines, cover(sd_segment(X, Y, *a, *b) - 0.0008, 0.0008))
    rgb = over(rgb, (0.55, 0.45, 0.25), lines * 0.35)
    rgb = rgb + stars[..., None] * np.array((1.0, 0.85, 0.5), dtype=G)
    return save("BWL_StarCeiling", np.clip(rgb, 0, 1))


def void_floor():
    """Black marble with gold veins, 2 m tiles, and a compass star inlay (its own
    texture on a disc mesh at the front of the hall)."""
    S = 1024
    u, v = grid(S, S)
    X, Y = (u - 0.5) * 2, (v - 0.5) * 2
    r = np.hypot(X, Y)
    th = np.arctan2(Y, X)
    n = fbm(S, S, 6, 6, seed=541)
    rgb = lerp((0.02, 0.02, 0.035), (0.07, 0.07, 0.10), n)
    for rr, w in ((0.97, 0.012), (0.90, 0.006), (0.40, 0.008)):
        rgb = over(rgb, GOLD, cover(np.abs(r - rr) - w, 0.003))
    for k in range(16):
        a = k * math.pi / 8
        L = 0.88 if k % 4 == 0 else (0.62 if k % 2 == 0 else 0.42)
        wdt = 0.10 if k % 4 == 0 else 0.06
        tip = (math.cos(a) * L, math.sin(a) * L)
        side = (math.cos(a + math.pi / 2) * wdt, math.sin(a + math.pi / 2) * wdt)
        for sgn, col in ((1, (0.90, 0.70, 0.32)), (-1, (0.48, 0.34, 0.14))):
            tri = [(0.0, 0.0), tip, (sgn * side[0], sgn * side[1])]
            rgb = over(rgb, col, cover(sd_tri(X, Y, tri), 0.003))
    alpha = cover(r - 0.999, 0.003)
    return save("BWL_Compass", rgb, alpha)


# =============================================================== THE CRYPT ==
def crypt_lane():
    """Polished dark stone laid in slabs, with the markings inlaid in a paint
    that glows under blacklight. Returns (base, emission)."""
    W, H = 384, 6144
    u, v = grid(H, W)
    X = (u - 0.5) * 2 * LANE_HALF
    Y = v * DECK_END
    n1 = _upsample(fbm(max(H // 24, 8), W, 6, 10, seed=551), H, W)
    n2 = _upsample(fbm(max(H // 12, 8), W, 6, 30, seed=552), H, W)
    rgb = lerp((0.035, 0.035, 0.045), (0.10, 0.10, 0.12), n1 * 0.7 + n2 * 0.3)
    vein = (1.0 - np.abs(np.sin(n1 * 18 + n2 * 11))) ** 30
    rgb = over(rgb, (0.38, 0.38, 0.44), vein * 0.5)
    # slab joints: across every 1.52 m, and three lengthwise seams
    across = np.abs(((Y / 1.524) % 1.0) - 0.5) > 0.498
    rgb[across] *= 0.35
    for sx in (-0.26, 0.0, 0.26):
        rgb[np.abs(X - sx) < 0.0015] *= 0.4
    emit = np.zeros_like(rgb)
    uv_cyan = np.array((0.10, 0.85, 1.0), dtype=G)
    uv_violet = np.array((0.60, 0.25, 1.0), dtype=G)
    for b in (5, 10, 15, 20, 25, 30, 35):
        tip = 3.66 + (4 - abs(b - 20) / 5.0) * 0.305
        x = board_x(b)
        d = sd_tri(X, Y, [(x - 0.013, tip - 0.16), (x + 0.013, tip - 0.16), (x, tip)])
        m = cover(d, 0.002)
        emit = over(emit, uv_cyan, m)
        rgb = over(rgb, (0.15, 0.6, 0.7), m)
    for b in (3, 5, 8, 11, 14, 26, 29, 32, 35, 37):
        m = cover(sd_circle(X, Y, board_x(b), 2.134, 0.008), 0.002)
        emit = over(emit, uv_violet, m)
    for row in range(4):
        for k in range(row + 1):
            x = (k - row * 0.5) * PIN_SPACING
            y = LANE_LEN + row * ROW_SPACING
            m = cover(np.abs(sd_circle(X, Y, x, y, 0.032)) - 0.003, 0.002)
            emit = over(emit, uv_violet, m)
    # thin glowing guide lines along both edges
    edge = cover(np.abs(np.abs(X) - (LANE_HALF - 0.012)) - 0.002, 0.0015)
    emit = over(emit, uv_cyan, edge * 0.8)
    return save("BWL_CryptLane", rgb), save("BWL_CryptLaneEmit", emit)


def crypt_approach():
    W, H = 640, 1664
    u, v = grid(H, W)
    X = (u - 0.5) * PITCH
    Y = -4.6 + v * 4.6
    n = fbm(H, W, 6, 8, seed=561)
    rgb = lerp((0.05, 0.05, 0.06), (0.13, 0.12, 0.14), n)
    for yy in (-1.5, -3.0):
        rgb[np.abs(Y - yy) < 0.004] *= 0.4
    rgb[np.abs(X) < 0.002] *= 0.4
    emit = np.zeros_like(rgb)
    for yy in (-3.66, -4.47):
        for b in (3, 5, 8, 11, 14, 20, 26, 29, 32, 35, 37):
            emit = over(emit, (0.6, 0.25, 1.0), cover(sd_circle(X, Y, board_x(b), yy, 0.009), 0.002))
    foul = (np.abs(Y + 0.012) < 0.012) & (np.abs(X) < LANE_HALF)
    emit[foul] = (0.1, 0.85, 1.0)
    return save("BWL_CryptApproach", rgb), save("BWL_CryptApproachEmit", emit)


def neon_mask(bride=False):
    """Crypt masking arch: black stone, violet/cyan neon borders and a glowing
    fleur-de-lis - or, with *bride*, the big panel over the masking with the
    ghost bride in it. Base and emission are the same image."""
    S = 1024
    u, v = grid(S, S)
    X, Y = (u - 0.5) * MASK_W, v * MASK_H
    w = MASK_W
    hw = np.where(Y < MASK_SPRING, w * 0.5,
                  np.sqrt(np.clip(w * w - (Y - MASK_SPRING) ** 2, 0, None)) - w * 0.5)
    edge = np.minimum(hw - np.abs(X), Y)
    n = fbm(S, S, 6, 5, seed=571)
    rgb = lerp((0.01, 0.005, 0.03), (0.06, 0.02, 0.14), n * np.clip(1 - np.hypot(X, Y - 0.6), 0, 1))
    cyan, violet, green = (0.15, 0.9, 1.0), (0.65, 0.25, 1.0), (0.35, 1.0, 0.45)
    rgb = over(rgb, violet, cover(np.abs(edge - 0.035) - 0.012, 0.004))
    rgb = over(rgb, cyan, cover(np.abs(edge - 0.08) - 0.004, 0.003))
    # fleur-de-lis
    fx, fy = 0.0, 0.22
    petal = np.minimum(sd_circle(X, Y, fx, fy + 0.14, 0.05),
                       np.minimum(sd_circle(X, Y, fx - 0.09, fy + 0.07, 0.045),
                                  sd_circle(X, Y, fx + 0.09, fy + 0.07, 0.045)))
    stem = sd_box(X, Y, fx, fy + 0.02, 0.12, 0.012)
    fleur = np.minimum(petal, stem)
    if not bride:
        rgb = over(rgb, green, cover(np.abs(fleur) - 0.006, 0.003))
        return save("BWL_NeonMask", rgb, cover(-edge, 0.003))
    # the ghost bride, filling the arch: head and veil near the apex, a long
    # flared gown dissolving into mist at the hem, arms folded at the waist
    top, hem = MASK_SPRING + 0.86, 0.08
    s = np.clip((top - Y) / (top - hem), 0, 1)
    # silhouette half-widths up the figure: hem, skirt, waist, bodice, shoulders, neck
    prof_y = [hem, top - 0.50, top - 0.30, top - 0.14, top - 0.05, top - 0.01, top + 0.03]
    prof_w = [0.34, 0.11, 0.055, 0.075, 0.085, 0.05, 0.018]
    hw = np.interp(Y, prof_y, prof_w)
    gown = np.where((Y > hem) & (Y < top + 0.03), np.abs(X) - hw, 1.0)
    shoulders = sd_segment(X, Y, -0.055, top - 0.045, 0.055, top - 0.045) - 0.03
    head = sd_circle(X, Y, 0.0, top + 0.065, 0.042)
    veil_s = np.clip((top + 0.1 - Y) / 0.75, 0, 1)
    veil = np.abs(X) - (0.05 + 0.17 * veil_s ** 1.2)
    vfade = np.clip((Y - (top - 0.75)) / 0.45, 0, 1) * np.clip((top + 0.12 - Y) / 0.06, 0, 1)
    body = np.minimum(np.minimum(gown, head), shoulders)
    fade = np.clip((Y - hem) / 0.45, 0, 1) ** 1.3                    # the hem dissolves
    wisp = 0.55 + 0.45 * norm01(fbm(S, S, 5, 9, seed=572))
    halo = np.exp(-np.clip(body, 0, None) / 0.06) * fade
    rgb = lerp(rgb, cyan, np.clip(halo * 0.5, 0, 1))
    rgb = over(rgb, (0.55, 0.95, 1.0), cover(veil, 0.02) * vfade * 0.4 * wisp)
    rgb = over(rgb, (0.80, 1.0, 1.0), cover(body, 0.004) * fade * wisp * 0.9)
    # folds down the gown
    folds = (0.5 + 0.5 * np.cos(X / (hw + 1e-3) * 7.0)) * cover(body, 0.004) * s
    rgb = lerp(rgb, (0.25, 0.70, 0.85), np.clip(folds * 0.35 * fade, 0, 1))
    # hollow eyes
    for sx in (-0.016, 0.016):
        eye = ((X - sx) / 0.008) ** 2 + ((Y - top - 0.068) / 0.011) ** 2 - 1.0
        rgb = over(rgb, (0.04, 0.18, 0.26), cover(eye * 0.008, 0.002) * 0.7)
    return save("BWL_BridePanel", rgb, cover(-edge, 0.003))


def crypt_mural(seed, name):
    """A blacklight mural: a castle on a crag under a huge moon, mist, and
    spectral figures - neon line and glow on black."""
    H, W = 1024, 2048
    u, v = grid(H, W)
    X, Y = u * 2.0, v
    rng = np.random.default_rng(seed)
    n = fbm(H, W, 6, 5, seed=seed)
    rgb = lerp((0.005, 0.005, 0.02), (0.03, 0.02, 0.10), n)
    mx, my = rng.uniform(1.25, 1.6), 0.72
    moon = np.hypot(X - mx, Y - my)
    rgb = lerp(rgb, (0.55, 0.3, 1.0), np.exp(-np.clip(moon - 0.16, 0, None) / 0.08) * 0.55)
    rgb = over(rgb, (0.85, 0.75, 1.0), cover(moon - 0.16, 0.004))
    crag = 0.18 + 0.14 * np.exp(-((X - mx) / 0.45) ** 2) + 0.03 * np.sin(X * 11 + seed)
    rgb = over(rgb, (0.02, 0.01, 0.05), cover(Y - crag, 0.004))
    rgb = over(rgb, (0.55, 0.25, 1.0), cover(np.abs(Y - crag) - 0.002, 0.002) * 0.8)
    wall = sd_box(X, Y, mx, 0.36, 0.36, 0.06)
    merlons = np.where(np.abs(((X - mx) / 0.03) % 1.0 - 0.5) < 0.25, sd_box(X, Y, mx, 0.43, 0.36, 0.012), 1.0)
    wall = np.minimum(wall, merlons)
    rgb = over(rgb, (0.02, 0.01, 0.05), cover(wall, 0.003))
    rgb = over(rgb, (0.15, 0.9, 1.0), cover(np.abs(wall) - 0.002, 0.002) * 0.8)
    # castle: towers with pointed roofs on the crag
    for k in range(7):
        tx = mx - 0.35 + k * 0.11 + rng.uniform(-0.02, 0.02)
        base = 0.18 + 0.14 * math.exp(-((tx - mx) / 0.45) ** 2)
        th = rng.uniform(0.10, 0.26)
        tw = rng.uniform(0.018, 0.035)
        tower = sd_box(X, Y, tx, base + th / 2, tw, th / 2)
        roof = sd_tri(X, Y, [(tx - tw * 1.3, base + th), (tx + tw * 1.3, base + th),
                             (tx, base + th + tw * 3.2)])
        shape = np.minimum(tower, roof)
        rgb = over(rgb, (0.02, 0.01, 0.05), cover(shape, 0.003))
        rgb = over(rgb, (0.15, 0.9, 1.0), cover(np.abs(shape) - 0.0025, 0.002))
        for wy in np.arange(base + 0.03, base + th - 0.02, 0.05):
            rgb = over(rgb, (1.0, 0.7, 0.3), cover(sd_box(X, Y, tx, wy, 0.004, 0.008), 0.002))
    # mist and spectral figures
    mist = np.clip((fbm(H, W, 6, 7, seed=seed + 1) - 0.45) * 3, 0, 1) * np.clip(0.35 - Y, 0, 1) * 2.5
    rgb = lerp(rgb, (0.2, 0.7, 0.9), np.clip(mist, 0, 1) * 0.55)
    for k in range(3):
        gx = (0.25, 0.7, 1.88)[k] + rng.uniform(-0.05, 0.05)
        gy, gh = 0.10, rng.uniform(0.30, 0.42)
        s = np.clip((gy + gh - Y) / gh, 0, 1)
        gown = np.where(Y < gy + gh, np.abs(X - gx) - (0.012 + 0.06 * s ** 1.4), 1.0)
        head = sd_circle(X, Y, gx, gy + gh + 0.025, 0.022)
        body = np.minimum(gown, head)
        fade = np.clip((Y - gy) / (gh * 0.7), 0, 1) ** 1.5
        rgb = lerp(rgb, (0.2, 0.95, 1.0), np.clip(np.exp(-np.clip(body, 0, None) / 0.03) * fade * 0.35, 0, 1))
        rgb = over(rgb, (0.7, 1.0, 1.0), cover(body, 0.004) * fade * 0.45)
    rgb = over(rgb, (0.65, 0.25, 1.0), cover(np.abs(np.minimum(np.minimum(u, 1 - u) * 2, np.minimum(v, 1 - v))) - 0.012, 0.004))
    return save(name, np.clip(rgb, 0, 1))


def sigil_strip():
    """Glowing sigils for the lane faces of the crypt pillars: moon, sun, eye, rune circle."""
    H, W = 1024, 256
    u, v = grid(H, W)
    X, Y = (u - 0.5) * 0.3, v * 1.2
    n = fbm(H, W, 5, 6, seed=581)
    rgb = lerp((0.01, 0.01, 0.02), (0.05, 0.04, 0.07), n)
    cyan, green = (0.15, 0.9, 1.0), (0.35, 1.0, 0.45)
    rgb = over(rgb, cyan, cover(np.abs(np.abs(X) - 0.13) - 0.004, 0.002))
    rgb = over(rgb, cyan, cover(crescent_sd(X, Y, 0.0, 1.02, 0.07), 0.002))
    sun = np.abs(sd_circle(X, Y, 0.0, 0.72, 0.045)) - 0.005
    for k in range(12):
        a = k * math.tau / 12
        sun = np.minimum(sun, sd_segment(X, Y, 0.065 * math.cos(a), 0.72 + 0.065 * math.sin(a),
                                         0.095 * math.cos(a), 0.72 + 0.095 * math.sin(a)) - 0.004)
    rgb = over(rgb, green, cover(sun, 0.002))
    eye = np.maximum(np.abs(X) / 0.09 + np.abs(Y - 0.42) / 0.04 - 1.0, -1.0) * 0.03
    rgb = over(rgb, cyan, cover(np.abs(eye) - 0.003, 0.002))
    rgb = over(rgb, cyan, cover(sd_circle(X, Y, 0.0, 0.42, 0.016), 0.002))
    rc = np.abs(sd_circle(X, Y, 0.0, 0.14, 0.08)) - 0.004
    for k in range(6):
        a = k * math.tau / 6 + 0.3
        rc = np.minimum(rc, sd_segment(X, Y, 0.0, 0.14, 0.08 * math.cos(a), 0.14 + 0.08 * math.sin(a)) - 0.003)
    rgb = over(rgb, green, cover(rc, 0.002))
    return save("BWL_Sigils", rgb)


def star_map_glass():
    """The vault window: a round star map glowing blue and violet."""
    S = 1024
    u, v = grid(S, S)
    X, Y = u * 2 - 1, v * 2 - 1
    r = np.hypot(X, Y)
    th = np.arctan2(Y, X)
    n = fbm(S, S, 6, 5, seed=591)
    rgb = lerp((0.02, 0.05, 0.25), (0.25, 0.10, 0.55), n)
    stars = star_field(S, S, 592, 0.002)
    rgb = rgb + stars[..., None] * 0.8
    for rr in (0.35, 0.62, 0.96):
        rgb = over(rgb, (0.1, 0.9, 1.0), cover(np.abs(r - rr) - 0.008, 0.004))
    spokes = np.abs(np.sin(th * 6)) * r
    rgb = over(rgb, (0.1, 0.9, 1.0), cover(spokes - 0.006, 0.004) * (r > 0.35) * (r < 0.96))
    rgb = over(rgb, (0.9, 0.95, 1.0), cover(crescent_sd(X, Y, 0.0, 0.0, 0.22), 0.004))
    return save("BWL_StarMap", np.clip(rgb, 0, 1), cover(r - 0.999, 0.004))


def build_void():
    return {"nebula": nebula_backdrop(), "void_mask": void_mask(), "void_glass": star_glass(),
            "void_banner": void_banner(), "star_ceiling": star_ceiling(), "compass": void_floor()}


def build_crypt():
    lane_b, lane_e = crypt_lane()
    appr_b, appr_e = crypt_approach()
    return {"crypt_lane": (lane_b, lane_e), "crypt_approach": (appr_b, appr_e),
            "neon_mask": neon_mask(), "bride": neon_mask(True), "mural_a": crypt_mural(601, "BWL_MuralA"),
            "mural_b": crypt_mural(602, "BWL_MuralB"), "sigils": sigil_strip(),
            "star_map": star_map_glass()}
