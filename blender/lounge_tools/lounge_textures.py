"""Bake every Lounge texture to PNG with numpy.

Real image files rather than node trees so they survive glTF export. Arrays are
(H, W, C) with row 0 at the BOTTOM of the image, which is Blender's pixel order.
"""
import bpy, os, math
import numpy as np
from lounge_common import (TEX_DIR, FLOOR_BOUNDS, COMPASS_C, DOOR_W, SQ3_2)

G = np.float32


# ------------------------------------------------------------------ noise ---
def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def _upsample(a, H, W):
    h, w = a.shape
    yi = np.linspace(0.0, h - 1.0, H)
    xi = np.linspace(0.0, w - 1.0, W)
    y0 = np.floor(yi).astype(int); y1 = np.minimum(y0 + 1, h - 1)
    x0 = np.floor(xi).astype(int); x1 = np.minimum(x0 + 1, w - 1)
    fy = _smooth(yi - y0)[:, None].astype(G)
    fx = _smooth(xi - x0)[None, :].astype(G)
    top = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    bot = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return top * (1 - fy) + bot * fy


def fbm(H, W, octaves=6, base=3, seed=0, aspect=1.0):
    """aspect > 1 stretches features horizontally."""
    rng = np.random.default_rng(seed)
    out = np.zeros((H, W), dtype=G)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        n = base * (2 ** o)
        ny = max(int(n * H / W), 2)
        nx = max(int(n / aspect), 2)
        out += amp * _upsample(rng.random((ny, nx)).astype(G), H, W)
        norm += amp
        amp *= 0.52
    return out / norm


def norm01(a):
    lo, hi = float(a.min()), float(a.max())
    return ((a - lo) / (hi - lo + 1e-9)).astype(G)


def grid(H, W):
    v, u = np.meshgrid(np.linspace(0, 1, H, dtype=G),
                       np.linspace(0, 1, W, dtype=G), indexing='ij')
    return u, v


def lerp(a, b, t):
    a = np.asarray(a, dtype=G); b = np.asarray(b, dtype=G)
    return a + (b - a) * t[..., None]


def cover(d, aa):
    """Anti-aliased coverage from a signed distance (negative = inside)."""
    return np.clip(0.5 - d / aa, 0.0, 1.0).astype(G)


def over(rgb, col, alpha):
    col = np.asarray(col, dtype=G)
    if col.ndim == 1:
        col = col[None, None, :]
    return rgb * (1 - alpha[..., None]) + col * alpha[..., None]


# ------------------------------------------------------------ 2D SDFs -------
def sd_circle(x, y, cx, cy, r):
    return np.hypot(x - cx, y - cy) - r


def sd_segment(x, y, ax, ay, bx, by):
    px, py = x - ax, y - ay
    dx, dy = bx - ax, by - ay
    h = np.clip((px * dx + py * dy) / (dx * dx + dy * dy), 0.0, 1.0)
    return np.hypot(px - dx * h, py - dy * h)


def sd_box(x, y, cx, cy, hx, hy, rot=0.0, r=0.0):
    c, s = math.cos(-rot), math.sin(-rot)
    px, py = (x - cx) * c - (y - cy) * s, (x - cx) * s + (y - cy) * c
    qx, qy = np.abs(px) - hx + r, np.abs(py) - hy + r
    return (np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
            + np.minimum(np.maximum(qx, qy), 0) - r)


def sd_tri(x, y, pts):
    """Signed distance to a convex polygon (counter-clockwise points)."""
    d = np.full(x.shape, 1e9, dtype=G)
    pos = np.ones(x.shape, dtype=bool)
    neg = np.ones(x.shape, dtype=bool)
    n = len(pts)
    for i in range(n):
        ax, ay = pts[i]; bx, by = pts[(i + 1) % n]
        d = np.minimum(d, sd_segment(x, y, ax, ay, bx, by))
        cr = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        pos &= cr >= 0
        neg &= cr <= 0
    return np.where(pos | neg, -d, d)


def suit(x, y, cx, cy, s, kind):
    """Signed distance to a playing-card suit, *s* = overall height."""
    X, Y = (x - cx) / s, (y - cy) / s
    if kind == 'heart':
        d = np.minimum(sd_circle(X, Y, -0.22, 0.12, 0.26),
                       sd_circle(X, Y, 0.22, 0.12, 0.26))
        d = np.minimum(d, sd_tri(X, Y, [(-0.46, 0.05), (0.0, -0.5), (0.46, 0.05)]))
    elif kind == 'spade':
        d = np.minimum(sd_circle(X, Y, -0.22, -0.06, 0.25),
                       sd_circle(X, Y, 0.22, -0.06, 0.25))
        d = np.minimum(d, sd_tri(X, Y, [(0.0, 0.5), (-0.45, 0.02), (0.45, 0.02)]))
        d = np.minimum(d, sd_tri(X, Y, [(0.0, -0.1), (0.18, -0.5), (-0.18, -0.5)]))
    elif kind == 'club':
        d = np.minimum(sd_circle(X, Y, 0.0, 0.22, 0.2),
                       np.minimum(sd_circle(X, Y, -0.22, -0.08, 0.2),
                                  sd_circle(X, Y, 0.22, -0.08, 0.2)))
        d = np.minimum(d, sd_tri(X, Y, [(0.0, 0.0), (0.18, -0.5), (-0.18, -0.5)]))
    else:   # diamond
        d = (np.abs(X) / 0.36 + np.abs(Y) / 0.5 - 1.0) * 0.3
    return d * s


# ------------------------------------------------------------------ save ----
def save(name, rgb, alpha=None):
    H, W = rgb.shape[:2]
    a = np.ones((H, W), dtype=G) if alpha is None else alpha.astype(G)
    px = np.concatenate([np.clip(rgb, 0, 1).astype(G), a[..., None]], axis=2)
    img = bpy.data.images.get(name)
    if img and tuple(img.size) != (W, H):
        bpy.data.images.remove(img)
        img = None
    if img is None:
        img = bpy.data.images.new(name, W, H, alpha=True)
    img.colorspace_settings.name = 'sRGB'          # BEFORE pixels (5.2 wipes them)
    img.pixels.foreach_set(px.ravel().astype(G))
    os.makedirs(TEX_DIR, exist_ok=True)
    path = os.path.join(TEX_DIR, name + ".png")
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    img.filepath = path
    img.reload()
    return img


# =============================================================== surfaces ===
def marble_floor(ppm=150):
    """The whole hall floor in one image: diagonal checker of charcoal and
    blue-grey marble, brass-lined, with a compass-star medallion."""
    x0, y0, x1, y1 = FLOOR_BOUNDS
    W = int((x1 - x0) * ppm) // 16 * 16
    H = int((y1 - y0) * ppm) // 16 * 16
    u, v = grid(H, W)
    X = x0 + u * (x1 - x0)
    Y = y0 + v * (y1 - y0)

    # veined marble field
    n1 = fbm(H, W, 7, 5, seed=3)
    n2 = fbm(H, W, 6, 9, seed=8)
    vein = np.abs(np.sin((X * 0.9 + Y * 0.55) * 2.2 + n1 * 11.0))
    vein = (1.0 - vein) ** 14
    vein2 = (1.0 - np.abs(np.sin((X * -0.4 + Y * 1.0) * 3.1 + n2 * 9.0))) ** 22

    # diagonal tiles 1.35 m
    T = 1.35
    a = (X + Y) / (T * math.sqrt(2.0))
    b = (X - Y) / (T * math.sqrt(2.0))
    ia, ib = np.floor(a), np.floor(b)
    checker = ((ia + ib) % 2).astype(G)
    fa, fb = a - ia, b - ib
    edge = np.minimum(np.minimum(fa, 1 - fa), np.minimum(fb, 1 - fb)) * T
    rng = np.random.default_rng(12)
    tile_tone = rng.uniform(0.85, 1.12, 4096).astype(G)[
        ((ia * 31 + ib * 17) % 4096).astype(int)]

    dark = lerp((0.030, 0.031, 0.036), (0.070, 0.072, 0.082), n1)
    light = lerp((0.150, 0.160, 0.185), (0.235, 0.245, 0.275), n2)
    rgb = lerp(dark, light, checker * 0.0) * (1 - checker[..., None]) \
        + light * checker[..., None]
    rgb *= tile_tone[..., None]
    rgb = over(rgb, (0.36, 0.37, 0.41), np.clip(vein * 0.45 + vein2 * 0.25, 0, 1)
               * (0.35 + 0.65 * checker))
    rgb = over(rgb, (0.20, 0.20, 0.23), np.clip(vein * 0.35, 0, 1) * (1 - checker))
    grout = cover(edge - 0.012, 0.006)
    rgb = over(rgb, (0.020, 0.018, 0.017), grout)

    # compass medallion
    cx, cy = COMPASS_C
    dx, dy = X - cx, Y - cy
    r = np.hypot(dx, dy)
    th = np.arctan2(dy, dx)
    diamond = (np.abs(dx) + np.abs(dy)) - 2.35
    rgb = over(rgb, (0.050, 0.052, 0.060), cover(diamond, 0.01))
    for w0 in (0.0, -0.10):
        ring = np.abs(diamond - w0) - 0.018
        rgb = over(rgb, (0.55, 0.42, 0.20), cover(ring, 0.008))
    disc = r - 1.25
    rgb = over(rgb, (0.105, 0.110, 0.125), cover(disc, 0.01))
    for rr in (1.25, 1.12, 0.42):
        rgb = over(rgb, (0.62, 0.47, 0.22), cover(np.abs(r - rr) - 0.02, 0.008))
    # 8-point star: long points on the axes, short on the diagonals
    for k in range(8):
        ang = k * math.pi / 4
        L = 1.08 if k % 2 == 0 else 0.66
        wdt = 0.20 if k % 2 == 0 else 0.15
        tip = (math.cos(ang) * L, math.sin(ang) * L)
        l = (math.cos(ang + math.pi / 2) * wdt, math.sin(ang + math.pi / 2) * wdt)
        tri = [(0.0, 0.0), (tip[0], tip[1]), (l[0], l[1])]
        tri2 = [(0.0, 0.0), (-l[0], -l[1]), (tip[0], tip[1])]
        for t, col in ((tri, (0.70, 0.54, 0.26)), (tri2, (0.38, 0.29, 0.14))):
            pts = [(p[0], p[1]) for p in t]
            # ensure CCW
            area = sum(pts[i][0] * pts[(i + 1) % 3][1] - pts[(i + 1) % 3][0] * pts[i][1]
                       for i in range(3))
            if area < 0:
                pts = pts[::-1]
            rgb = over(rgb, col, cover(sd_tri(dx, dy, pts), 0.008))
    rgb = over(rgb, (0.75, 0.60, 0.30), cover(r - 0.06, 0.006))
    return save("LNG_Floor", rgb)


def stone_wall():
    """Dark ashlar, 1024 px = 3.6 m square, tiles in both directions."""
    H = W = 1024
    u, v = grid(H, W)
    rows = 8
    row = np.clip(np.floor(v * rows), 0, rows - 1)
    off = (row % 2) * 0.5
    cols = 4
    uu = u * cols + off
    col = np.floor(uu) % cols
    fu, fv = uu - np.floor(uu), v * rows - row
    rng = np.random.default_rng(5)
    tone = rng.uniform(0.75, 1.2, (rows, cols)).astype(G)[row.astype(int), col.astype(int)]
    n = fbm(H, W, 7, 6, seed=21)
    n2 = fbm(H, W, 5, 3, seed=22)
    base = lerp((0.060, 0.052, 0.056), (0.135, 0.122, 0.122), n)
    base *= tone[..., None]
    base = lerp(base, base * np.array((0.9, 0.85, 1.12), dtype=G), n2)
    d = np.minimum(np.minimum(fu, 1 - fu) * (3.6 / cols),
                   np.minimum(fv, 1 - fv) * (3.6 / rows))
    mortar = cover(d - 0.012, 0.01)
    rgb = over(base, (0.025, 0.022, 0.022), mortar)
    bevel = np.clip(d / 0.05, 0, 1)
    rgb *= (0.78 + 0.22 * bevel)[..., None]
    return save("LNG_Stone", rgb)


def mahogany():
    H, W = 1024, 256
    u, v = grid(H, W)
    n = fbm(H, W, 6, 4, seed=31, aspect=0.1)
    fine = fbm(H, W, 7, 30, seed=32, aspect=0.08)
    ring = 0.5 + 0.5 * np.sin(u * 60.0 + n * 14.0)
    t = np.clip(0.45 * ring + 0.55 * fine, 0, 1)
    rgb = lerp((0.040, 0.016, 0.010), (0.140, 0.058, 0.034), t)
    return save("LNG_Mahogany", rgb)


def lane_maple():
    H, W = 1024, 256
    u, v = grid(H, W)
    boards = 12
    b = np.clip(np.floor(u * boards), 0, boards - 1)
    rng = np.random.default_rng(41)
    tone = rng.uniform(0.85, 1.15, boards).astype(G)[b.astype(int)]
    fine = fbm(H, W, 6, 40, seed=42, aspect=0.05)
    rgb = lerp((0.36, 0.20, 0.09), (0.60, 0.38, 0.19), fine) * tone[..., None]
    fu = u * boards - b
    rgb *= (0.8 + 0.2 * np.clip(np.minimum(fu, 1 - fu) * 40, 0, 1))[..., None]
    # target arrows near v = 0.25
    X, Y = (u - 0.5) * 1.05, v * 18.0
    for k in range(-3, 4):
        ax = k * 0.14
        d = sd_tri(X, Y, [(ax - 0.035, 4.2), (ax + 0.035, 4.2), (ax, 4.55)])
        rgb = over(rgb, (0.05, 0.02, 0.02), cover(d, 0.004))
    return save("LNG_Lane", rgb)


def velvet_tufted():
    H = W = 512
    u, v = grid(H, W)
    n = fbm(H, W, 5, 8, seed=51)
    a = (u + v) * 3.0
    b = (u - v) * 3.0
    fa, fb = a - np.floor(a), b - np.floor(b)
    cell = np.minimum(np.minimum(fa, 1 - fa), np.minimum(fb, 1 - fb))   # 0 at seams
    puff = np.clip(cell * 3.2, 0, 1) ** 0.6
    ca, cb = np.abs(fa - 0.5), np.abs(fb - 0.5)
    button = cover(np.hypot(ca * 0.5, cb * 0.5) - 0.018, 0.01)
    button = cover(np.hypot(u * 6 - np.round(u * 6), v * 6 - np.round(v * 6)) - 0.05, 0.03)
    base = lerp((0.080, 0.006, 0.012), (0.34, 0.028, 0.040), puff * (0.8 + 0.2 * n))
    rgb = over(base, (0.25, 0.18, 0.08), button)
    return save("LNG_Velvet", rgb)


# ================================================================ textiles ===
def round_rug():
    H = W = 2048
    u, v = grid(H, W)
    X, Y = u * 2 - 1, v * 2 - 1
    r = np.hypot(X, Y)
    th = np.arctan2(Y, X)
    n = fbm(H, W, 6, 20, seed=61)
    red = np.array((0.23, 0.020, 0.030), dtype=G)
    navy = np.array((0.025, 0.030, 0.075), dtype=G)
    cream = np.array((0.55, 0.42, 0.28), dtype=G)
    gold = np.array((0.50, 0.33, 0.10), dtype=G)
    rgb = np.zeros((H, W, 3), dtype=G) + red

    # field motif: petals
    petal = 0.5 + 0.5 * np.cos(th * 16) * np.cos(r * 38)
    field = (r > 0.26) & (r < 0.62)
    rgb[field] = lerp(red, navy, (petal > 0.72).astype(G))[field]
    rgb[field] = over(rgb, cream, ((petal > 0.93) & field).astype(G) * 0.8)[field]

    # centre medallion
    med = r < 0.26
    star = 0.5 + 0.5 * np.cos(th * 8)
    rgb[med] = lerp(navy, red, ((r < 0.10 + 0.12 * star) & med).astype(G))[med]
    rgb = over(rgb, cream, cover(np.abs(r - 0.26) - 0.006, 0.003))
    rgb = over(rgb, gold, cover(r - 0.03, 0.004))

    # borders
    for rr, w, c in ((0.64, 0.015, gold), (0.70, 0.010, cream),
                     (0.905, 0.010, cream), (0.955, 0.020, gold)):
        rgb = over(rgb, c, cover(np.abs(r - rr) - w, 0.003))
    band = (r > 0.715) & (r < 0.89)
    motif = 0.5 + 0.5 * np.cos(th * 48) * np.cos((r - 0.80) * 60)
    bandcol = lerp(navy, red, (motif > 0.55).astype(G))
    bandcol = over(bandcol, cream, (motif > 0.92).astype(G) * 0.7)
    rgb[band] = bandcol[band]
    outer = (r > 0.975)
    rgb[outer] = red

    # wear and pile
    rgb *= (0.78 + 0.35 * n)[..., None]
    alpha = cover(r - 0.999, 0.003)
    return save("LNG_RugRound", rgb, alpha)


def rect_rug():
    H, W = 1024, 1536
    u, v = grid(H, W)
    X, Y = (u - 0.5) * 3.0, (v - 0.5) * 2.0
    n = fbm(H, W, 6, 20, seed=66)
    red = np.array((0.20, 0.018, 0.028), dtype=G)
    navy = np.array((0.025, 0.030, 0.070), dtype=G)
    cream = np.array((0.52, 0.40, 0.27), dtype=G)
    edge = np.minimum(1.5 - np.abs(X), 1.0 - np.abs(Y))
    rgb = np.zeros((H, W, 3), dtype=G) + red
    border = edge < 0.22
    motif = 0.5 + 0.5 * np.cos(X * 40) * np.cos(Y * 40)
    rgb[border] = lerp(navy, red, (motif > 0.6).astype(G))[border]
    for e in (0.03, 0.22):
        rgb = over(rgb, cream, cover(np.abs(edge - e) - 0.008, 0.003))
    med = (np.abs(X) / 1.0 + np.abs(Y) / 0.55) - 1.0
    rgb = over(rgb, navy, cover(med, 0.004))
    rgb = over(rgb, cream, cover(np.abs(med) - 0.02, 0.003))
    rgb *= (0.78 + 0.35 * n)[..., None]
    return save("LNG_RugRect", rgb)


def banner():
    H, W = 1280, 512
    u, v = grid(H, W)
    X, Y = (u - 0.5) * 1.2, v * 3.0            # metres: 1.2 wide, 3 tall
    n = fbm(H, W, 6, 10, seed=71, aspect=0.4)
    fold = 0.5 + 0.5 * np.sin(u * TAU * 3.0 + n * 2.0)
    rgb = lerp((0.10, 0.008, 0.015), (0.36, 0.030, 0.045), fold * 0.6 + n * 0.4)
    gold = (0.62, 0.44, 0.17)
    # border, following the pointed bottom (point at y = 0, shoulders at 0.45)
    bot = Y - (0.45 * np.abs(X) / 0.6)
    edge = np.minimum(0.6 - np.abs(X), bot)
    rgb = over(rgb, gold, cover(np.abs(edge - 0.06) - 0.014, 0.004))
    # flared cross
    cx, cy = 0.0, 1.85
    arm = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    for ax, ay in arm:
        L = 0.62 if ay == -1 else 0.36
        d = sd_segment(X, Y, cx, cy, cx + ax * L, cy + ay * L) - 0.035
        rgb = over(rgb, gold, cover(d, 0.004))
        rgb = over(rgb, gold, cover(sd_circle(X, Y, cx + ax * L, cy + ay * L, 0.07), 0.004))
    rgb = over(rgb, gold, cover(np.abs(sd_circle(X, Y, cx, cy, 0.17)) - 0.02, 0.004))
    # fleur below
    rgb = over(rgb, gold, cover(sd_circle(X, Y, 0.0, 0.62, 0.07), 0.004))
    for s in (-1, 1):
        d = sd_segment(X, Y, 0.0, 0.62, s * 0.18, 0.80) - 0.03
        rgb = over(rgb, gold, cover(d, 0.004))
    rgb = over(rgb, gold, cover(np.abs(Y - 2.72) - 0.02, 0.004)
               * (np.abs(X) < 0.5))
    return save("LNG_Banner", rgb, cover(-edge, 0.003))


def portrait(seed, name):
    H, W = 768, 576
    u, v = grid(H, W)
    X, Y = (u - 0.5), (v - 0.5) * 1.33
    n = fbm(H, W, 6, 5, seed=seed)
    rgb = lerp((0.018, 0.012, 0.010), (0.090, 0.060, 0.040), n)
    body = ((X / 0.40) ** 2 + ((Y + 0.72) / 0.52) ** 2) - 1.0
    rgb = over(rgb, (0.030, 0.025, 0.030), cover(body * 0.2, 0.01))
    head = ((X / 0.14) ** 2 + ((Y - 0.05) / 0.19) ** 2) - 1.0
    face = lerp((0.30, 0.22, 0.16), (0.46, 0.36, 0.26), norm01(-X - Y * 0.5))
    rgb = over(rgb, face, cover(head * 0.08, 0.006))
    collar = sd_tri(X, Y, [(-0.12, -0.18), (0.0, -0.36), (0.12, -0.18)])
    rgb = over(rgb, (0.40, 0.36, 0.30), cover(collar, 0.006))
    vign = 1.0 - np.clip(np.hypot(X, Y / 1.2) * 1.1, 0, 1) ** 2
    rgb *= (0.5 + 0.5 * vign)[..., None]
    return save(name, rgb)


# =============================================================== glass ======
def _voronoi_lead(X, Y, pts, chunk=64):
    """Distance to the nearest Voronoi edge, row-chunked to save memory."""
    H, W = X.shape
    out = np.zeros((H, W), dtype=G)
    cell = np.zeros((H, W), dtype=np.int32)
    px, py = pts[:, 0][None, None, :], pts[:, 1][None, None, :]
    for r0 in range(0, H, chunk):
        xs = X[r0:r0 + chunk, :, None]; ys = Y[r0:r0 + chunk, :, None]
        d = np.hypot(xs - px, ys - py)
        idx = np.argpartition(d, 1, axis=2)[..., :2]
        d1 = np.take_along_axis(d, idx[..., :1], 2)[..., 0]
        d2 = np.take_along_axis(d, idx[..., 1:2], 2)[..., 0]
        out[r0:r0 + chunk] = (d2 - d1) * 0.5
        cell[r0:r0 + chunk] = idx[..., 0]
    return out, cell


def lancet(name, palette, w_m=1.8, seed=81, storm=False):
    """A pointed lancet window. The UV box is the window's bounding box."""
    rise = w_m * SQ3_2
    h_m = 3.0 + rise                       # jamb height 3.0 below the spring
    W = 512
    H = int(W * h_m / w_m) // 16 * 16
    u, v = grid(H, W)
    X, Y = (u - 0.5) * w_m, v * h_m
    rng = np.random.default_rng(seed)
    pts = np.stack([rng.uniform(-w_m / 2, w_m / 2, 170),
                    rng.uniform(0, h_m, 170)], 1).astype(G)
    lead, cell = _voronoi_lead(X, Y, pts)
    pal = np.array(palette, dtype=G)
    cols = pal[rng.integers(0, len(pal), 170)] * rng.uniform(0.6, 1.25, (170, 1)).astype(G)
    rgb = cols[cell]
    n = fbm(H, W, 5, 6, seed=seed + 1)
    if storm:
        neb = fbm(H, W, 7, 3, seed=seed + 2)
        rgb = lerp((0.08, 0.02, 0.22), (0.55, 0.28, 0.85), norm01(neb) ** 1.8)
        # a lightning thread
        path = 0.08 * np.sin(Y * 5.0 + 1.0) + 0.05 * fbm(H, W, 4, 6, seed=seed + 3)
        bolt = np.where(Y > h_m * 0.35, np.abs(X - path - 0.15), 1.0)
        rgb = over(rgb, (0.95, 0.85, 1.0), cover(bolt - 0.012, 0.01) * (Y < h_m * 0.85))
        lead = lead * 3.0                                   # fewer, lighter leads
    rgb *= (0.75 + 0.5 * n)[..., None]
    # tracery: central mullion, transoms, a rosette in the head
    trac = np.abs(X) - 0.028
    for ty in (1.0, 2.0, 3.0):
        trac = np.minimum(trac, np.abs(Y - ty) - 0.022)
    ros_c = 3.0 + rise * 0.45
    trac = np.minimum(trac, np.abs(np.hypot(X, Y - ros_c) - w_m * 0.22) - 0.025)
    for k in range(6):
        a = k * math.pi / 3
        trac = np.minimum(trac, np.abs(np.hypot(X - math.cos(a) * w_m * 0.11,
                                                Y - ros_c - math.sin(a) * w_m * 0.11)
                                       - w_m * 0.10) - 0.012)
    dark = np.minimum(lead - 0.010, trac)
    rgb = over(rgb, (0.010, 0.010, 0.014), cover(dark, 0.006))
    return save(name, rgb)


# ================================================================ emblems ===
EMB_H = DOOR_W * SQ3_2          # tympanum height (spring -> apex)


def _emblem_canvas(tint, seed):
    S = 1024
    u, v = grid(S, S)
    X, Y = (u - 0.5) * DOOR_W, v * EMB_H
    n = fbm(S, S, 6, 6, seed=seed)
    if tint == 'green':
        lo, hi = (0.010, 0.040, 0.025), (0.050, 0.150, 0.085)
    else:
        lo, hi = (0.060, 0.008, 0.012), (0.220, 0.030, 0.035)
    glow = np.clip(1.0 - np.hypot(X / 1.6, (Y - 1.2) / 1.6), 0, 1)
    rgb = lerp(lo, hi, glow * 0.7 + n * 0.3)
    # arch-shaped gold border
    w = DOOR_W
    hw = np.sqrt(np.clip(w * w - Y * Y, 0, None)) - w * 0.5
    edge = np.minimum(hw - np.abs(X), Y) * 0.866
    return X, Y, rgb, edge


GOLD = (0.70, 0.50, 0.20)
GOLD_D = (0.36, 0.24, 0.08)
IVORY = (0.80, 0.70, 0.52)


def _gold(rgb, d, aa=0.006, shade=None):
    col = np.array(GOLD, dtype=G)[None, None, :]
    if shade is not None:
        col = lerp(GOLD_D, (0.92, 0.72, 0.36), shade)
    return over(rgb, col, cover(d, aa))


def _finish(rgb, edge):
    rgb = _gold(rgb, np.abs(edge - 0.10) - 0.018)
    rgb = _gold(rgb, np.abs(edge - 0.19) - 0.006)
    return rgb


def emblem_bowling():
    X, Y, rgb, edge = _emblem_canvas('red', 91)
    # radiating lines from the base centre
    th = np.arctan2(Y - 0.05, X)
    ray = np.abs(np.sin(th * 7.0)) * np.hypot(X, Y)
    keep = (th > 0.30) & (th < math.pi - 0.30)
    rgb = _gold(rgb, np.where(keep, ray - 0.010, 1.0))
    rgb = _gold(rgb, np.abs(np.hypot(X, Y - 0.05) - 1.35) - 0.012)
    prof = [(0.0, 0.12), (0.1, 0.16), (0.33, 0.22), (0.55, 0.14), (0.68, 0.085),
            (0.79, 0.10), (0.90, 0.105), (0.97, 0.07), (1.0, 0.0)]
    ts = np.array([p[0] for p in prof]); rs = np.array([p[1] for p in prof])
    for cx, tilt in ((-0.24, 0.10), (0.24, -0.10)):
        h0, hgt = 0.55, 1.70
        c, s = math.cos(tilt), math.sin(tilt)
        lx = (X - cx) * c + (Y - h0) * s
        ly = -(X - cx) * s + (Y - h0) * c
        t = np.clip(ly / hgt, 0, 1)
        rr = np.interp(t, ts, rs) * hgt * 0.95
        d = np.where((ly >= 0) & (ly <= hgt), np.abs(lx) - rr,
                     np.maximum(-ly, ly - hgt) + np.abs(lx) * 0)
        shade = np.clip(0.55 - lx / (rr + 1e-3) * 0.45, 0, 1)
        col = lerp((0.45, 0.36, 0.24), (0.95, 0.86, 0.66), shade)
        rgb = over(rgb, col, cover(d, 0.006))
        rgb = _gold(rgb, np.abs(d + 0.0) - 0.010)
        for sy in (0.66, 0.72):
            band = (np.abs(t - sy) < 0.018) & (d < 0)
            rgb = over(rgb, (0.55, 0.04, 0.05), band.astype(G))
    return save("LNG_EmbBowling", _finish(rgb, edge), cover(-edge, 0.004))


def emblem_billiards():
    X, Y, rgb, edge = _emblem_canvas('green', 92)
    # crossed cues behind the rack
    for s in (-1, 1):
        a = (-s * 1.15, 0.45); b = (s * 0.95, 2.45)
        d = sd_segment(X, Y, *a, *b)
        t = np.clip(((X - a[0]) * (b[0] - a[0]) + (Y - a[1]) * (b[1] - a[1]))
                    / ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2), 0, 1)
        wdt = 0.045 - 0.028 * t
        rgb = over(rgb, lerp((0.25, 0.12, 0.05), (0.72, 0.55, 0.30), t), cover(d - wdt, 0.005))
        rgb = _gold(rgb, np.abs(d - wdt) - 0.006)
    # triangle rack
    cy, side = 1.30, 1.45
    hgt = side * SQ3_2
    tri = [(-side / 2, cy - hgt / 3), (side / 2, cy - hgt / 3), (0.0, cy + hgt * 2 / 3)]
    dtri = sd_tri(X, Y, tri)
    rgb = over(rgb, (0.02, 0.05, 0.03), cover(dtri, 0.006))
    rgb = _gold(rgb, np.abs(dtri) - 0.035)
    br = 0.105
    base_y = cy - hgt / 3 + 0.19
    k = 0
    for row in range(5):
        n = 5 - row
        for i in range(n):
            bx = (i - (n - 1) / 2) * br * 2.02
            by = base_y + row * br * 1.75
            d = sd_circle(X, Y, bx, by, br)
            shade = np.clip(0.7 - (X - bx) / br * 0.3 + (Y - by) / br * 0.3, 0, 1)
            rgb = over(rgb, lerp(GOLD_D, (0.98, 0.82, 0.45), shade), cover(d, 0.005))
            k += 1
    return save("LNG_EmbBilliards", _finish(rgb, edge), cover(-edge, 0.004))


def emblem_golf():
    X, Y, rgb, edge = _emblem_canvas('green', 93)
    for s in (-1, 1):
        a = (s * 1.00, 2.30); b = (-s * 0.62, 0.52)
        d = sd_segment(X, Y, *a, *b) - 0.030
        rgb = over(rgb, (0.70, 0.66, 0.60), cover(d, 0.005))
        rgb = _gold(rgb, np.abs(d) - 0.006)
        head = sd_box(X, Y, b[0] - s * 0.13, b[1] - 0.02, 0.19, 0.07,
                      rot=s * 0.25, r=0.05)
        rgb = over(rgb, (0.78, 0.74, 0.68), cover(head, 0.005))
        rgb = _gold(rgb, np.abs(head) - 0.008)
        grip = sd_segment(X, Y, *a, a[0] - s * 0.25, a[1] - 0.28) - 0.042
        rgb = over(rgb, (0.08, 0.05, 0.04), cover(grip, 0.005))
    cx, cy, R = 0.0, 1.62, 0.44
    d = sd_circle(X, Y, cx, cy, R)
    shade = np.clip(0.75 - (X - cx) / R * 0.35 + (Y - cy) / R * 0.35, 0, 1)
    rgb = over(rgb, lerp((0.45, 0.33, 0.14), (0.98, 0.84, 0.50), shade), cover(d, 0.005))
    dm = np.hypot((X * 14) - np.round(X * 14), (Y * 14) - np.round(Y * 14))
    rgb = over(rgb, (0.35, 0.25, 0.10), cover(dm - 0.17, 0.08) * cover(d + 0.03, 0.01) * 0.6)
    rgb = _gold(rgb, np.abs(d) - 0.012)
    tee = sd_tri(X, Y, [(-0.16, cy - R - 0.02), (0.16, cy - R - 0.02), (0.0, cy - R - 0.34)])
    rgb = _gold(rgb, tee)
    return save("LNG_EmbGolf", _finish(rgb, edge), cover(-edge, 0.004))


def emblem_poker():
    X, Y, rgb, edge = _emblem_canvas('red', 94)
    pivot = (0.0, 0.40)
    for ang, kind in ((0.42, 'heart'), (-0.42, 'club'), (0.0, 'spade')):
        c, s = math.cos(ang), math.sin(ang)
        lx = (X - pivot[0]) * c - (Y - pivot[1]) * s
        ly = (X - pivot[0]) * s + (Y - pivot[1]) * c
        d = sd_box(lx, ly, 0.0, 1.05, 0.40, 0.58, r=0.05)
        rgb = over(rgb, (0.03, 0.01, 0.01), cover(d - 0.03, 0.03) * 0.6)
        rgb = over(rgb, IVORY, cover(d, 0.005))
        rgb = _gold(rgb, np.abs(d + 0.04) - 0.010)
        sd = suit(lx, ly, 0.0, 1.05, 0.42, kind)
        col = (0.55, 0.03, 0.04) if kind == 'heart' else (0.05, 0.03, 0.03)
        rgb = over(rgb, col, cover(sd, 0.005) * cover(d, 0.005))
        for cx, cy in ((-0.28, 1.48), (0.28, 0.62)):
            rgb = over(rgb, col, cover(suit(lx, ly, cx, cy, 0.10, kind), 0.004)
                       * cover(d, 0.005))
    for cx, kind in ((-1.05, 'spade'), (1.05, 'club')):
        sd = suit(X, Y, cx, 0.62, 0.36, kind)
        rgb = _gold(rgb, sd)
    rgb = _gold(rgb, suit(X, Y, 0.0, 2.35, 0.24, 'diamond'))
    return save("LNG_EmbPoker", _finish(rgb, edge), cover(-edge, 0.004))


# ============================================================ misc bits =====
def flame():
    H, W = 512, 256
    u, v = grid(H, W)
    X, Y = (u - 0.5) * 2, v
    width = 0.55 * np.clip(np.sin(np.clip(Y, 0, 1) * math.pi), 0, 1) ** 0.8 * (1.0 - Y * 0.35)
    width = np.where(Y < 0.18, 0.55 * np.sqrt(np.clip(Y / 0.18, 0, 1)) * 0.9, width)
    d = np.abs(X) / (width + 1e-4)
    core = np.clip(1.0 - d, 0, 1)
    t = np.clip(core * (1.2 - Y * 0.6), 0, 1)
    rgb = lerp((0.85, 0.20, 0.02), (1.00, 0.92, 0.65), t ** 1.4)
    alpha = np.clip(core * 2.2, 0, 1) * np.clip((1 - Y) * 3, 0, 1)
    return save("LNG_Flame", rgb, alpha)


def golf_screen():
    H, W = 576, 1024
    u, v = grid(H, W)
    X, Y = u, v
    sky = lerp((0.020, 0.030, 0.090), (0.10, 0.16, 0.34), np.clip(1.4 - Y * 1.4, 0, 1))
    n = fbm(H, W, 5, 4, seed=101)
    rgb = sky * (0.85 + 0.3 * n)[..., None]
    rgb = over(rgb, (0.95, 0.95, 0.85), cover(np.hypot((X - 0.78) * 1.78, Y - 0.78) - 0.06, 0.004))
    rgb = over(rgb, (0.35, 0.40, 0.55), cover(np.hypot((X - 0.78) * 1.78, Y - 0.78) - 0.14, 0.08) * 0.35)
    hill1 = 0.42 + 0.06 * np.sin(X * 7.0) + 0.03 * np.sin(X * 17 + 1)
    hill2 = 0.30 + 0.04 * np.sin(X * 5.0 + 2.0)
    rgb = over(rgb, (0.020, 0.060, 0.050), cover(Y - hill1, 0.003))
    rgb = over(rgb, (0.050, 0.170, 0.080), cover(Y - hill2, 0.003))
    fair = np.abs(X - 0.5 - (0.3 - Y) * 0.8) - (0.02 + (0.3 - Y) * 0.9)
    rgb = over(rgb, (0.12, 0.34, 0.14), cover(fair, 0.004) * (Y < hill2))
    rgb = over(rgb, (0.85, 0.85, 0.80), cover(sd_segment(X * 1.78, Y, 0.62 * 1.78, 0.33,
                                                          0.62 * 1.78, 0.40) - 0.003, 0.002))
    rgb = over(rgb, (0.80, 0.10, 0.10), cover(sd_tri(X * 1.78, Y, [(0.62 * 1.78, 0.40),
               (0.62 * 1.78, 0.375), (0.645 * 1.78, 0.3875)]), 0.002))
    return save("LNG_GolfScreen", rgb)


TAU = math.tau


def build():
    return {
        "floor": marble_floor(), "stone": stone_wall(), "wood": mahogany(),
        "lane": lane_maple(), "velvet": velvet_tufted(),
        "rug_round": round_rug(), "rug_rect": rect_rug(),
        "banner": banner(),
        "portrait_a": portrait(111, "LNG_PortraitA"),
        "portrait_b": portrait(222, "LNG_PortraitB"),
        "glass_blue": lancet("LNG_GlassBlue",
                             [(0.05, 0.12, 0.60), (0.08, 0.22, 0.85), (0.10, 0.08, 0.45),
                              (0.25, 0.10, 0.60), (0.04, 0.30, 0.70), (0.06, 0.16, 0.72),
                              (0.05, 0.12, 0.60), (0.08, 0.22, 0.85), (0.30, 0.08, 0.55),
                              (0.80, 0.55, 0.15), (0.60, 0.08, 0.10)], 1.8, 81),
        "glass_storm": lancet("LNG_GlassStorm", [(0.4, 0.2, 0.8)], 3.2, 85, storm=True),
        "emb_bowling": emblem_bowling(), "emb_billiards": emblem_billiards(),
        "emb_golf": emblem_golf(), "emb_poker": emblem_poker(),
        "flame": flame(), "golf_screen": golf_screen(),
    }
