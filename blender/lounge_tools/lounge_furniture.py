"""Loose furniture: the round rug and its ring of velvet sofas and tub chairs,
the ghost statue, occasional tables, candle jars and fringed lamps."""
import bpy, bmesh, math
from mathutils import Vector
from lounge_common import (col, wipe, new_obj, shade_auto, box, revolve, tube,
                           RUG_C, RUG_R, TAU)
from lounge_fittings import candle, apply_uvs, figure_profile

PFX = "LNG_"
SEAT_C = (RUG_C[0], RUG_C[1] + 0.35)       # the sofas curve round this point


# ---------------------------------------------------------------- helpers ---
def capped_revolve(bm, profile, seg, a0, span, centre, uvs=None, uscale=1.0,
                   vscale=1.0):
    """Revolve a closed (r, z) profile through *span* and cap both ends.
    UVs: u runs along the arc (metres at the profile's first radius), v along
    the profile's length."""
    cx, cy, cz = centre
    loops = []
    for s in range(seg + 1):
        t = a0 + span * s / seg
        loops.append([bm.verts.new((cx + r * math.cos(t), cy + r * math.sin(t), cz + z))
                      for r, z in profile])
    n = len(profile)
    acc = [0.0]
    for i in range(1, n):
        acc.append(acc[-1] + math.dist(profile[i - 1], profile[i]))
    for s in range(seg):
        a, b = loops[s], loops[s + 1]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(loops[0][::-1])
    bm.faces.new(loops[-1])
    if uvs is not None:
        R = max(r for r, _ in profile)
        for s, lp in enumerate(loops):
            arc = R * span * s / seg
            for i, v in enumerate(lp):
                uvs[v] = (arc * uscale, acc[i] * vscale)
    return loops


def pos_on(cent, r, ang):
    return (cent[0] + r * math.cos(ang), cent[1] + r * math.sin(ang))


def feet(bm, pts, z=0.0, h=0.08, r=0.035):
    for x, y in pts:
        revolve(bm, [(r, 0.0), (r * 1.3, h * 0.6), (r * 0.9, h)], 8, centre=(x, y, z))


# ================================================================== rugs ===
def build_rugs(M, c):
    bm = bmesh.new()
    uvs = {}
    n = 64
    cx, cy = RUG_C
    centre = bm.verts.new((cx, cy, 0.012))
    uvs[centre] = (0.5, 0.5)
    ring = []
    for k in range(n):
        a = TAU * k / n
        v = bm.verts.new((cx + RUG_R * math.cos(a), cy + RUG_R * math.sin(a), 0.012))
        uvs[v] = (0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a))
        ring.append(v)
    for k in range(n):
        bm.faces.new((centre, ring[k], ring[(k + 1) % n]))
    apply_uvs(bm, uvs)
    new_obj(PFX + "RugRound", bm, c, [M["rug"]])

    bm = bmesh.new()
    uvs = {}
    for x, y, rot in ((-7.1, -1.7, 0.35), (7.1, -1.7, -0.35)):
        hw, hh = 1.7, 1.15
        ca, sa = math.cos(rot), math.sin(rot)
        vs = []
        for (u, v) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            px, py = u * hw, v * hh
            vv = bm.verts.new((x + px * ca - py * sa, y + px * sa + py * ca, 0.010))
            uvs[vv] = ((u + 1) * 0.5, (v + 1) * 0.5)
            vs.append(vv)
        bm.faces.new(vs)
    apply_uvs(bm, uvs)
    new_obj(PFX + "RugCorners", bm, c, [M["rug_rect"]])


# ================================================================ seating ==
SOFA_PROFILE = [            # (radius from SEAT_C, z) - closed loop
    (2.30, 0.10), (2.30, 0.36), (2.36, 0.46), (2.50, 0.49), (2.95, 0.50),
    (3.02, 0.62), (3.04, 0.95), (3.12, 1.04), (3.24, 1.02), (3.30, 0.90),
    (3.30, 0.10)]
SOFA_ARCS = ((math.radians(118), math.radians(84)),     # left:  118..202 deg
             (math.radians(-22), math.radians(84)))     # right: -22..62 deg

TUB_SEAT = [(0.0, 0.26), (0.46, 0.26), (0.48, 0.42), (0.44, 0.48), (0.0, 0.50)]
TUB_BACK = [(0.44, 0.10), (0.44, 0.48), (0.46, 0.80), (0.52, 0.86), (0.60, 0.84),
            (0.62, 0.10)]


def sofa(vel, wood, gilt, a0, span):
    uvs = {}
    capped_revolve(vel, SOFA_PROFILE, 28, a0, span, (*SEAT_C, 0.0), uvs=uvs,
                   uscale=1 / 0.9, vscale=1 / 0.9)
    apply_uvs(vel, uvs)
    # rolled arms at both ends
    for ang in (a0, a0 + span):
        tng = Vector((-math.sin(ang), math.cos(ang), 0.0))
        side = 1 if ang == a0 else -1
        path = []
        for i in range(9):
            r = 2.28 + (3.28 - 2.28) * i / 8
            x, y = pos_on(SEAT_C, r, ang)
            path.append((x + tng.x * side * 0.10, y + tng.y * side * 0.10, 0.70))
        tube(vel, path, 0.13, sides=10)
        mx, my = pos_on(SEAT_C, 2.79, ang)
        box(vel, mx + tng.x * side * 0.10, my + tng.y * side * 0.10, 0.38, 1.0, 0.20,
            0.62, rot_z=ang)
    # gilt base rail and feet
    rail = []
    for s in range(29):
        a = a0 + span * s / 28
        x, y = pos_on(SEAT_C, 2.28, a)
        rail.append((x, y, 0.12))
    tube(gilt, rail, 0.03, sides=6)
    fp = [pos_on(SEAT_C, r, a0 + span * f) for f in (0.02, 0.5, 0.98)
          for r in (2.36, 3.2)]
    feet(wood, fp)
    # throw cushions
    for f in (0.25, 0.72):
        a = a0 + span * f
        x, y = pos_on(SEAT_C, 2.85, a)
        box(vel, x, y, 0.72, 0.16, 0.48, 0.42, rot_z=a)


def tub_chair(vel, gilt, wood, x, y, face):
    """Round club chair; *face* is the direction the sitter looks."""
    uvs = {}
    revolve(vel, TUB_SEAT, 20, centre=(x, y, 0.0))
    back_a0 = face + math.radians(55)
    capped_revolve(vel, TUB_BACK, 24, back_a0, math.radians(250), (x, y, 0.0),
                   uvs=uvs, uscale=1 / 0.9, vscale=1 / 0.9)
    apply_uvs(vel, uvs)
    ring = [(x + 0.47 * math.cos(TAU * k / 32), y + 0.47 * math.sin(TAU * k / 32), 0.12)
            for k in range(33)]
    tube(gilt, ring, 0.025, sides=6, cap=False)
    feet(wood, [(x + 0.42 * math.cos(face + a), y + 0.42 * math.sin(face + a))
                for a in (0.8, 2.3, 3.9, 5.5)])


def build_seating(M, c):
    vel, wood, gilt = bmesh.new(), bmesh.new(), bmesh.new()
    for a0, span in SOFA_ARCS:
        sofa(vel, wood, gilt, a0, span)
    # two tub chairs closing the ring, facing the ghost
    for ang in (math.radians(248), math.radians(292)):
        x, y = pos_on(SEAT_C, 2.85, ang)
        tub_chair(vel, gilt, wood, x, y, ang + math.pi)
    # foreground chairs by the corner rugs
    for x, y in ((-6.6, -1.4), (6.6, -1.4)):
        face = math.atan2(SEAT_C[1] - y, SEAT_C[0] - x)
        tub_chair(vel, gilt, wood, x, y, face)
    shade_auto(new_obj(PFX + "Sofas", vel, c, [M["velvet"]]), math.radians(40))
    new_obj(PFX + "SofaFeet", wood, c, [M["gilt"]])
    shade_auto(new_obj(PFX + "SofaTrim", gilt, c, [M["gilt"]]))


# ========================================================= tables, lamps ===
def round_table(wood, top, gilt, x, y, r, h, pedestal=True):
    revolve(top, [(0.0, h), (r, h), (r, h - 0.035), (0.0, h - 0.035)][::-1], 28,
            centre=(x, y, 0.0))
    ring = [(x + r * math.cos(TAU * k / 40), y + r * math.sin(TAU * k / 40), h - 0.02)
            for k in range(41)]
    tube(gilt, ring, 0.018, sides=6, cap=False)
    if pedestal:
        revolve(wood, [(r * 0.55, 0.0), (r * 0.55, 0.04), (0.10, 0.12), (0.05, 0.30),
                       (0.08, h * 0.6), (0.05, h - 0.12), (r * 0.4, h - 0.04)], 14,
                centre=(x, y, 0.0))


def candle_jar(wax, glass_bm, fl, fuv, x, y, z):
    candle(wax, fl, fuv, x, y, z + 0.01, h=0.07, r=0.035)
    revolve(glass_bm, [(0.05, 0.0), (0.055, 0.02), (0.055, 0.16), (0.05, 0.17)], 10,
            centre=(x, y, z))


def fringed_lamp(brass, shade, x, y, z, big=False):
    s = 1.35 if big else 1.0
    revolve(brass, [(0.13 * s, 0.0), (0.13 * s, 0.03), (0.05 * s, 0.08), (0.03, 0.2),
                    (0.09 * s, 0.32 * s), (0.06 * s, 0.42 * s), (0.02, 0.48 * s),
                    (0.02, 0.62 * s)], 12, centre=(x, y, z))
    revolve(shade, [(0.30 * s, 0.50 * s), (0.34 * s, 0.53 * s), (0.18 * s, 0.78 * s),
                    (0.10 * s, 0.80 * s)], 20, centre=(x, y, z))
    # fringe: a short skirt of thin strips
    revolve(shade, [(0.30 * s, 0.50 * s), (0.30 * s, 0.44 * s)], 40, centre=(x, y, z))


def build_tables(M, c):
    wood, top, gilt, marble = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    wax, glass, fl, brass, shade = (bmesh.new() for _ in range(5))
    fuv = {}
    gx, gy = SEAT_C[0], SEAT_C[1] + 0.25
    round_table(wood, top, gilt, gx, gy, 0.78, 0.78)                 # ghost plinth
    round_table(wood, top, gilt, SEAT_C[0], SEAT_C[1] - 1.35, 0.42, 0.46)  # coffee
    for ang in (math.radians(108), math.radians(208), math.radians(-28),
                math.radians(72)):
        x, y = pos_on(SEAT_C, 2.80, ang)
        round_table(wood, top, gilt, x, y, 0.30, 0.62)
        candle_jar(wax, glass, fl, fuv, x, y, 0.62)
    for s in (-1, 1):
        # a pair of candle jars on the ghost plinth
        candle_jar(wax, glass, fl, fuv, gx + s * 0.55, gy - 0.20, 0.78)
    # corner marble tables with a fringed lamp and a candle
    for s in (-1, 1):
        x, y = s * 7.55, -0.55
        round_table(wood, marble, gilt, x, y, 0.46, 0.70)
        fringed_lamp(brass, shade, x + s * 0.12, y + 0.12, 0.70)
        candle_jar(wax, glass, fl, fuv, x - s * 0.22, y - 0.18, 0.70)
        # tall standard lamp behind
        revolve(brass, [(0.22, 0.0), (0.22, 0.04), (0.08, 0.10), (0.03, 0.3),
                        (0.03, 1.55), (0.06, 1.6), (0.02, 1.7)], 12,
                centre=(s * 8.6, 0.6, 0.0))
        fringed_lamp(brass, shade, s * 8.6, 0.6, 1.25, big=True)
    apply_uvs(fl, fuv)
    new_obj(PFX + "TableBases", wood, c, [M["wood"]])
    new_obj(PFX + "TableTops", top, c, [M["wood"]])
    new_obj(PFX + "MarbleTops", marble, c, [M["marble"]])
    new_obj(PFX + "TableGilt", gilt, c, [M["gilt"]])
    new_obj(PFX + "JarCandles", wax, c, [M["candle"]])
    new_obj(PFX + "JarGlass", glass, c, [M["glass_jar"]])
    new_obj(PFX + "JarFlames", fl, c, [M["flame"]])
    shade_auto(new_obj(PFX + "LampBrass", brass, c, [M["brass"]]))
    shade_auto(new_obj(PFX + "LampShades", shade, c, [M["shade"]]))


# ============================================================ the ghost ====
def build_ghost(M, c):
    body, wisp = bmesh.new(), bmesh.new()
    x, y, z = SEAT_C[0], SEAT_C[1] + 0.25, 0.78
    prof = figure_profile(1.55, hood=False, flare=1.25)
    revolve(body, prof, 36, centre=(x, y, z))
    # arms raised, one reaching up and back
    sh = z + 1.55 * 1.40 / 1.9
    tube(body, [(x - 0.17, y, sh), (x - 0.27, y - 0.04, sh + 0.14),
                (x - 0.32, y - 0.07, sh + 0.36), (x - 0.27, y - 0.08, sh + 0.58),
                (x - 0.19, y - 0.06, sh + 0.72)], 0.032, sides=10)
    tube(body, [(x + 0.17, y, sh), (x + 0.24, y - 0.08, sh - 0.14),
                (x + 0.22, y - 0.18, sh - 0.30), (x + 0.12, y - 0.24, sh - 0.40)], 0.030,
         sides=10)
    # trailing hair / veil
    tube(body, [(x, y + 0.08, sh + 0.28), (x + 0.10, y + 0.22, sh + 0.05),
                (x + 0.16, y + 0.30, sh - 0.35), (x + 0.10, y + 0.34, sh - 0.70)], 0.05,
         sides=8)
    # spectral swirl rising around the skirt
    path = []
    for i in range(80):
        t = i / 79
        a = t * TAU * 2.25
        r = 0.55 - 0.35 * t
        path.append((x + r * math.cos(a), y + r * math.sin(a), z + 0.05 + t * 1.2))
    tube(wisp, path, 0.018, sides=6)
    path2 = [(p[0] * 0.9 + x * 0.1, p[1] * 0.9 + y * 0.1, p[2] + 0.12) for p in path[10:]]
    tube(wisp, path2, 0.010, sides=5)
    shade_auto(new_obj(PFX + "GhostStatue", body, c, [M["ghost"]]), math.radians(50))
    new_obj(PFX + "GhostWisps", wisp, c, [M["ghost_wisp"]])


def build(M):
    c = col("LNG_Furniture", col("Lounge"))
    for pre in ("LNG_Rug", "LNG_Sofa", "LNG_Table", "LNG_Marble", "LNG_Jar",
                "LNG_Lamp", "LNG_Ghost"):
        wipe(pre)
    build_rugs(M, c)
    build_seating(M, c)
    build_tables(M, c)
    build_ghost(M, c)
    return c
