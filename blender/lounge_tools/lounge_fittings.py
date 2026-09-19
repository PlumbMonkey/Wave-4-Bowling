"""Fixed fittings: fireplace + overmantel mirror, hooded statues, chandelier,
candelabras, sconces, spirit lanterns, banners and portraits."""
import bpy, bmesh, math
from mathutils import Vector, Matrix
from lounge_common import (col, wipe, new_obj, shade_auto, box, revolve, tube,
                           arch_outline, BACK_Y, BACK_HX, CEIL_Z, SQ3_2, TAU)

PFX = "LNG_"
Y0 = BACK_Y                   # room face of the fireplace wall
CHAND = (0.0, 3.2, 9.6)       # lowest ring of the chandelier


# ------------------------------------------------------------ primitives ----
def flame_card(bm, x, y, z, h=0.07, uvs=None):
    """Two crossed quads, textured with the flame."""
    w = h * 0.5
    for a in (0.0, math.pi / 2):
        ca, sa = math.cos(a) * w, math.sin(a) * w
        vs = [bm.verts.new((x - ca, y - sa, z)), bm.verts.new((x + ca, y + sa, z)),
              bm.verts.new((x + ca, y + sa, z + h)), bm.verts.new((x - ca, y - sa, z + h))]
        bm.faces.new(vs)
        if uvs is not None:
            for v, uv in zip(vs, ((0, 0), (1, 0), (1, 1), (0, 1))):
                uvs[v] = uv


def candle(wax, flames, fuv, x, y, z, h=0.20, r=0.022):
    revolve(wax, [(r, 0.0), (r, h), (r * 0.6, h + 0.004), (0.0, h + 0.004)], 8,
            centre=(x, y, z))
    flame_card(flames, x, y, z + h + 0.004, h=max(0.075, h * 0.42), uvs=fuv)


def apply_uvs(bm, uvs):
    layer = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for loop in f.loops:
            if loop.vert in uvs:
                loop[layer].uv = uvs[loop.vert]


def figure_profile(h, hood=False, flare=1.0):
    """(radius, z) of a robed figure - reads as a statue when revolved."""
    s = h / 1.9
    if hood:
        p = [(0.36 * flare, 0.00), (0.34 * flare, 0.10), (0.28, 0.45), (0.23, 0.85),
             (0.20, 1.10), (0.22, 1.30), (0.24, 1.42), (0.20, 1.50),
             (0.17, 1.56), (0.16, 1.72), (0.12, 1.84), (0.05, 1.92), (0.0, 1.94)]
    else:     # a slender gowned woman
        p = [(0.0, 0.0), (0.40 * flare, 0.0), (0.39 * flare, 0.05), (0.33 * flare, 0.20),
             (0.27, 0.42), (0.23, 0.64), (0.195, 0.86), (0.16, 1.02), (0.175, 1.14),
             (0.20, 1.25), (0.195, 1.33), (0.21, 1.39), (0.17, 1.45), (0.08, 1.49),
             (0.055, 1.54), (0.06, 1.60), (0.092, 1.645), (0.11, 1.70), (0.112, 1.76),
             (0.10, 1.82), (0.07, 1.87), (0.03, 1.895), (0.0, 1.90)]
    return [(r * s, z * s) for r, z in p]


# ============================================================== fireplace ==
FIRE_HW, FIRE_H, MANTEL_Z = 1.55, 1.90, 2.45     # opening half-width / height


def build_fireplace(M, c):
    stone, gilt, soot, marble = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    y = Y0
    px = FIRE_HW + 0.25                              # pier centres
    for s in (-1, 1):
        box(stone, s * px, y - 0.32, MANTEL_Z / 2, 0.50, 0.64, MANTEL_Z)
        box(stone, s * px, y - 0.34, 0.12, 0.64, 0.72, 0.24)
        for zz in (0.9, 1.6):
            box(gilt, s * px, y - 0.65, zz, 0.30, 0.02, 0.04)
        revolve(gilt, [(0.0, 0.0), (0.13, 0.03), (0.09, 0.18), (0.0, 0.24)], 10,
                centre=(s * px, y - 0.44, MANTEL_Z + 0.14))
    box(stone, 0.0, y - 0.32, FIRE_H + (MANTEL_Z - FIRE_H) / 2, 2 * px,
        0.58, MANTEL_Z - FIRE_H)
    box(stone, 0.0, y - 0.42, MANTEL_Z + 0.07, 2 * px + 1.0, 0.86, 0.14)
    box(gilt, 0.0, y - 0.86, MANTEL_Z + 0.07, 2 * px + 1.02, 0.02, 0.06)
    box(gilt, 0.0, y - 0.62, FIRE_H + 0.05, 2 * FIRE_HW, 0.02, 0.05)
    # the firebox
    box(soot, 0.0, y - 0.02, FIRE_H / 2, 2 * FIRE_HW, 0.04, FIRE_H)
    for s in (-1, 1):
        box(soot, s * (FIRE_HW - 0.03), y - 0.32, FIRE_H / 2, 0.06, 0.60, FIRE_H)
    box(soot, 0.0, y - 0.32, FIRE_H - 0.02, 2 * FIRE_HW, 0.60, 0.04)
    # hearth
    box(marble, 0.0, y - 1.05, 0.03, 2 * px + 1.1, 1.5, 0.06)
    box(marble, 0.0, y - 0.32, 0.04, 2 * FIRE_HW, 0.62, 0.08)
    shade_auto(new_obj(PFX + "Fireplace", stone, c, [M["trim_lt"]]))
    new_obj(PFX + "FireplaceGilt", gilt, c, [M["gilt"]])
    new_obj(PFX + "Firebox", soot, c, [M["soot"]])
    new_obj(PFX + "Hearth", marble, c, [M["hearth"]])

    iron, logs, fl = bmesh.new(), bmesh.new(), bmesh.new()
    fuv = {}
    for i in range(9):
        x = -0.8 + i * 0.2
        tube(iron, [(x, y - 0.62, 0.10), (x, y - 0.62, 0.34), (x, y - 0.18, 0.38)],
             0.018, sides=6)
    tube(iron, [(-0.9, y - 0.62, 0.32), (0.9, y - 0.62, 0.32)], 0.02, sides=6)
    for (x0, x1, yy, z) in ((-0.75, 0.70, y - 0.40, 0.22), (-0.60, 0.80, y - 0.55, 0.32),
                            (-0.40, 0.45, y - 0.32, 0.40), (-0.2, 0.7, y - 0.45, 0.46)):
        tube(logs, [(x0, yy, z), (x1, yy + 0.05, z + 0.03)], 0.08, sides=8)
    for i, (x, sc) in enumerate(((-0.55, 0.70), (-0.25, 0.95), (0.05, 1.10), (0.35, 0.85),
                                 (0.62, 0.60), (-0.75, 0.45), (0.15, 0.70), (-0.40, 0.55))):
        flame_card(fl, x, y - 0.45 + (i % 3) * 0.08, 0.32, h=sc, uvs=fuv)
    apply_uvs(fl, fuv)
    new_obj(PFX + "Grate", iron, c, [M["iron"]])
    new_obj(PFX + "Logs", logs, c, [M["embers"]])
    new_obj(PFX + "FireFlames", fl, c, [M["flame"]])


def build_mirror(M, c):
    gilt, glass = bmesh.new(), bmesh.new()
    y = Y0 - 0.10
    x0, x1, z0, z1 = -1.05, 1.05, 2.95, 5.35
    # frame: a rectangular body with a pointed crest, built as tubes
    w = x1 - x0
    body = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1), (x0, y, z0)]
    tube(gilt, body, 0.11, sides=8, cap=False)
    tube(gilt, [(x0 - 0.16, y, z0 - 0.16), (x1 + 0.16, y, z0 - 0.16),
                (x1 + 0.16, y, z1), (x0 - 0.16, y, z1), (x0 - 0.16, y, z0 - 0.16)],
         0.05, sides=6, cap=False)
    crest = [(x, y, z) for x, z in arch_outline(w + 0.1, z1, z1, 14)]
    tube(gilt, crest, 0.09, sides=8, cap=False)
    apex = z1 + (w + 0.1) * SQ3_2
    revolve(gilt, [(0.0, 0.0), (0.18, 0.08), (0.10, 0.22), (0.13, 0.30),
                   (0.04, 0.42), (0.0, 0.46)], 12, centre=(0.0, y, apex - 0.05))
    for s in (-1, 1):
        revolve(gilt, [(0.0, 0.0), (0.14, 0.05), (0.08, 0.3), (0.0, 0.36)], 10,
                centre=(s * (w * 0.5 + 0.16), y, z1 - 0.02))
    # glass fills the body and the crest
    arc = arch_outline(w, z1, z1, 14)
    pts = [(x0, z0), (x1, z0), (x1, z1)] + arc[::-1] + [(x0, z1)]
    ded = []
    for p in pts:
        if not ded or abs(ded[-1][0] - p[0]) + abs(ded[-1][1] - p[1]) > 1e-5:
            ded.append(p)
    glass.faces.new([glass.verts.new((x, y + 0.02, z)) for x, z in ded])
    shade_auto(new_obj(PFX + "MirrorFrame", gilt, c, [M["gilt"]]))
    new_obj(PFX + "MirrorGlass", glass, c, [M["mirror"]])


# ================================================================ statues ==
def build_statues(M, c):
    bronze, stone = bmesh.new(), bmesh.new()
    for s in (-1, 1):
        x = s * 2.45
        # pointed niche
        out = arch_outline(1.05, 3.05, 5.00, 10)
        box(stone, x, Y0 - 0.25, 3.00, 0.9, 0.50, 0.16)          # bracket shelf
        revolve(stone, [(0.40, 0.0), (0.30, -0.30), (0.12, -0.55), (0.0, -0.62)], 12,
                centre=(x, Y0 - 0.28, 2.92))
        tube(stone, [(x + px, Y0 - 0.06, pz) for px, pz in out], 0.07, sides=6,
             cap=False)
        revolve(bronze, figure_profile(1.95, hood=True), 20, centre=(x, Y0 - 0.32, 3.08))
        # folded hands - a short bar in front of the chest
        tube(bronze, [(x - 0.12, Y0 - 0.52, 4.30), (x + 0.12, Y0 - 0.52, 4.30)], 0.06,
             sides=8)
    shade_auto(new_obj(PFX + "Statues", bronze, c, [M["statue"]]))
    shade_auto(new_obj(PFX + "Niches", stone, c, [M["trim_lt"]]))


# ============================================================ chandelier ===
def build_chandelier(M, c):
    brass, wax, fl = bmesh.new(), bmesh.new(), bmesh.new()
    fuv = {}
    cx, cy, cz = CHAND
    # chain to the ceiling rose
    for k in range(int((CEIL_Z - 0.6 - (cz + 2.4)) / 0.14)):
        z = cz + 2.4 + k * 0.14
        a = (k % 2) * math.pi / 2
        tube(brass, [(cx + math.cos(a) * 0.04, cy + math.sin(a) * 0.04, z),
                     (cx - math.cos(a) * 0.04, cy - math.sin(a) * 0.04, z + 0.12)],
             0.012, sides=4)
    revolve(brass, [(0.0, -0.35), (0.10, -0.25), (0.16, 0.0), (0.09, 0.4), (0.13, 0.8),
                    (0.07, 1.3), (0.12, 1.8), (0.05, 2.2), (0.08, 2.4), (0.0, 2.45)],
            16, centre=(cx, cy, cz))
    # a bowl and pendant finial under the lowest tier
    revolve(brass, [(0.0, -0.95), (0.06, -0.90), (0.10, -0.75), (0.30, -0.55),
                    (0.48, -0.35), (0.52, -0.22), (0.44, -0.18), (0.14, -0.10)], 20,
            centre=(cx, cy, cz))
    tiers = ((2.10, 0.0, 20), (1.45, 0.80, 14), (0.85, 1.50, 8))
    for R, dz, n in tiers:
        z = cz + dz
        ring = [(cx + R * math.cos(TAU * k / 48), cy + R * math.sin(TAU * k / 48), z)
                for k in range(49)]
        tube(brass, ring, 0.05, sides=8, cap=False)
        for k in range(n):
            a = TAU * (k + 0.5) / n
            px, py = cx + R * math.cos(a), cy + R * math.sin(a)
            # scrolled arm from the stem out to the ring
            arm = []
            for t in range(11):
                f = t / 10
                rr = 0.14 + (R - 0.14) * min(1.0, f * 1.12)
                dip = -0.30 * math.sin(min(1.0, f * 1.12) * math.pi * 0.85)
                arm.append((cx + rr * math.cos(a), cy + rr * math.sin(a),
                            z + 0.28 + dip - 0.30 * f + (0.18 * (f - 0.9) / 0.1 if f > 0.9 else 0)))
            tube(brass, arm, 0.032, sides=6)
            revolve(brass, [(0.0, 0.0), (0.06, 0.02), (0.07, 0.06), (0.03, 0.08),
                            (0.03, 0.10)], 8, centre=(px, py, z + 0.02))
            candle(wax, fl, fuv, px, py, z + 0.12, h=0.30, r=0.028)
        # crystal-ish drops under each ring
        for k in range(n * 2):
            a = TAU * k / (n * 2)
            revolve(brass, [(0.0, 0.0), (0.025, -0.05), (0.0, -0.13)], 5,
                    centre=(cx + R * math.cos(a), cy + R * math.sin(a), z - 0.02))
    apply_uvs(fl, fuv)
    shade_auto(new_obj(PFX + "Chandelier", brass, c, [M["brass"]]))
    new_obj(PFX + "ChandelierCandles", wax, c, [M["candle"]])
    new_obj(PFX + "ChandelierFlames", fl, c, [M["flame"]])


# ========================================================== candelabras ====
CANDELABRA_SITES = [(-2.55, 6.95), (2.55, 6.95), (-3.55, 6.85), (3.55, 6.85),
                    (-8.0, 6.3), (8.0, 6.3)]
SCONCE_SITES = []      # filled from the columns in build()


def candelabra(brass, wax, fl, fuv, x, y, h=1.85):
    revolve(brass, [(0.30, 0.0), (0.30, 0.05), (0.18, 0.10), (0.10, 0.22),
                    (0.05, 0.30)], 12, centre=(x, y, 0.0))
    revolve(brass, [(0.035, 0.30), (0.035, h - 0.3), (0.07, h - 0.25),
                    (0.04, h - 0.18), (0.04, h)], 10, centre=(x, y, 0.0))
    arms = ((0.0, 0.0), (0.30, 0.0), (-0.30, 0.0), (0.17, 0.0), (-0.17, 0.0))
    for i, (dx, _) in enumerate(arms):
        top = h + (0.18 if i == 0 else (0.02 if abs(dx) > 0.2 else 0.10))
        if dx:
            tube(brass, [(x, y, h - 0.2), (x + dx * 0.6, y, h - 0.25), (x + dx, y, top - 0.06)],
                 0.016, sides=5)
        revolve(brass, [(0.0, 0.0), (0.05, 0.01), (0.05, 0.05), (0.03, 0.06)], 8,
                centre=(x + dx, y, top - 0.06))
        candle(wax, fl, fuv, x + dx, y, top, h=0.22)


def build_candelabras(M, c, sconce_sites):
    brass, wax, fl = bmesh.new(), bmesh.new(), bmesh.new()
    fuv = {}
    for x, y in CANDELABRA_SITES:
        candelabra(brass, wax, fl, fuv, x, y)
    for x, y, z, nx, ny in sconce_sites:
        # a back plate and three cups on a curved bracket
        box(brass, x, y, z, 0.12, 0.04, 0.34)
        for k, off in enumerate((-0.2, 0.0, 0.2)):
            tx, ty = x + nx * 0.28 + (-ny) * off, y + ny * 0.28 + nx * off
            tube(brass, [(x, y, z - 0.05), (x + nx * 0.18 + (-ny) * off * 0.6,
                                            y + ny * 0.18 + nx * off * 0.6, z + 0.05),
                         (tx, ty, z + 0.12)], 0.015, sides=5)
            revolve(brass, [(0.0, 0.0), (0.05, 0.01), (0.05, 0.04)], 8,
                    centre=(tx, ty, z + 0.12))
            candle(wax, fl, fuv, tx, ty, z + 0.16, h=0.18)
    apply_uvs(fl, fuv)
    shade_auto(new_obj(PFX + "Candelabras", brass, c, [M["brass"]]))
    new_obj(PFX + "CandelabraCandles", wax, c, [M["candle"]])
    new_obj(PFX + "CandelabraFlames", fl, c, [M["flame"]])


# ======================================================== spirit lanterns ==
LANTERN_SITES = [(-7.35, 7.05), (7.35, 7.05)]


def build_lanterns(M, c):
    wood, brass, spirit = bmesh.new(), bmesh.new(), bmesh.new()
    for x, y in LANTERN_SITES:
        box(wood, x, y, 0.55, 0.62, 0.50, 1.10)
        box(brass, x, y, 1.12, 0.70, 0.56, 0.04)
        revolve(brass, [(0.14, 0.0), (0.16, 0.05), (0.10, 0.10), (0.12, 0.18)], 10,
                centre=(x, y, 1.14))
        # a small phantom figure standing in a blue flame
        revolve(spirit, [(0.0, 0.0), (0.10, 0.03), (0.07, 0.18), (0.05, 0.32),
                         (0.07, 0.40), (0.03, 0.48), (0.0, 0.50)], 10,
                centre=(x, y, 1.32))
    new_obj(PFX + "LanternCabinets", wood, c, [M["wood"]])
    new_obj(PFX + "LanternBrass", brass, c, [M["brass"]])
    new_obj(PFX + "SpiritFlames", spirit, c, [M["spirit"]])


# ===================================================== banners, portraits ==
def build_banners(M, c):
    """Crimson banners on the upper columns. The texture is 1.2 x 3 m with its
    point shoulders at 15% height, so the mesh uses the same proportion."""
    cloth, rods = bmesh.new(), bmesh.new()
    uvs = {}
    top, bot, w = 14.3, 10.0, 1.1
    H = top - bot
    sh = 0.15 * H
    cols, rows = 8, 12
    for x in (-3.55, 3.55):
        y = Y0 - 0.42
        grid = []
        for j in range(rows + 1):
            v = j / rows
            row = []
            for i in range(cols + 1):
                u = i / cols
                edge = bot + sh * abs(2.0 * u - 1.0)
                z = edge + (top - edge) * v
                vv = cloth.verts.new((x - w / 2 + w * u,
                                      y - 0.05 * math.sin(u * math.pi * 3.0), z))
                uvs[vv] = (u, (z - bot) / H)
                row.append(vv)
            grid.append(row)
        for j in range(rows):
            for i in range(cols):
                cloth.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1],
                                 grid[j + 1][i]))
        tube(rods, [(x - w / 2 - 0.12, y, top + 0.05), (x + w / 2 + 0.12, y, top + 0.05)],
             0.03, sides=8)
        for s in (-1, 1):
            revolve(rods, [(0.0, 0.0), (0.05, 0.02), (0.0, 0.10)], 8,
                    centre=(x + s * (w / 2 + 0.14), y, top))
    apply_uvs(cloth, uvs)
    new_obj(PFX + "Banners", cloth, c, [M["banner"]])
    new_obj(PFX + "BannerRods", rods, c, [M["brass"]])


def build_portraits(M, c):
    gilt = bmesh.new()
    for x, key in ((-7.05, "portrait_a"), (7.05, "portrait_b")):
        y = Y0 - 0.06
        w, h, zc = 1.15, 1.5, 12.0
        bm = bmesh.new()
        vs = [bm.verts.new((x - w / 2, y - 0.03, zc - h / 2)),
              bm.verts.new((x + w / 2, y - 0.03, zc - h / 2)),
              bm.verts.new((x + w / 2, y - 0.03, zc + h / 2)),
              bm.verts.new((x - w / 2, y - 0.03, zc + h / 2))]
        f = bm.faces.new(vs)
        layer = bm.loops.layers.uv.new("UVMap")
        for loop, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[layer].uv = uv
        new_obj(PFX + "Portrait_" + key[-1].upper(), bm, c, [M[key]])
        tube(gilt, [(x - w / 2, y - 0.06, zc - h / 2), (x + w / 2, y - 0.06, zc - h / 2),
                    (x + w / 2, y - 0.06, zc + h / 2), (x - w / 2, y - 0.06, zc + h / 2),
                    (x - w / 2, y - 0.06, zc - h / 2)], 0.08, sides=6, cap=False)
    shade_auto(new_obj(PFX + "PortraitFrames", gilt, c, [M["gilt"]]))


def build(M):
    c = col("LNG_Fittings", col("Lounge"))
    for pre in ("LNG_Fire", "LNG_Hearth", "LNG_Grate", "LNG_Logs", "LNG_Mirror",
                "LNG_Statues", "LNG_Niches", "LNG_Chandelier", "LNG_Candelabra",
                "LNG_Lantern", "LNG_Spirit", "LNG_Banner", "LNG_Portrait"):
        wipe(pre)
    build_fireplace(M, c)
    build_mirror(M, c)
    build_statues(M, c)
    build_chandelier(M, c)
    # sconces on the room face of every column, facing into the hall
    from lounge_shell import column_sites
    sconces = []
    for x, y, _ in column_sites():
        v = Vector((-x, 1.6 - y))
        v.normalize()
        sconces.append((x + v.x * 0.42, y + v.y * 0.42, 3.4, v.x, v.y))
    build_candelabras(M, c, sconces)
    build_lanterns(M, c)
    build_banners(M, c)
    build_portraits(M, c)
    return c
