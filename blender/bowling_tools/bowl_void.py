"""Alley 2 - The Void (reference: art/reference/alley_void.webp).

The Lounge's mahogany hall, opened up at the far end: the back wall is one
great flattened arch onto deep space - a nebula, a spiral galaxy and a ringed
moon - and the masking over the pins is a gothic screen of open arches with
spires and a golden crescent, so you bowl toward the stars. Starfield ghost
glass down the sides, navy crescent banners, a star-painted vault, a compass
star in the black marble floor, and an astronomer's clutter of telescopes,
armillary spheres and globes in the aisles.

Collections BWL_VoidArt + BWL_VoidMarkers -> games/bowling/art/alleys/void.glb
"""
import bmesh, math
from bowl_common import (col, wipe, new_obj, shade_auto, box, revolve, tube, arch_outline,
                         wall_with_openings, pbr, mat, empty, LANES, PITCH, BLOCK_X, HALL_X,
                         HALL_Y1, CEIL, COLUMN_X, COLUMN_YS, TAU)
import bowl_alley as A
import bowl_hall as H
from bowl_textures import MASK_W, MASK_SPRING, MASK_H

PFX = A.PFX
SIDE_WINDOWS = A.SIDE_WINDOWS
SCREEN_TOP = A.MASK_Z1 + 0.30
NEBULA_R, NEBULA_CY, NEBULA_Z = 18.0, 12.0, (-1.0, 11.0)
PREVIEW = {"Mask": ('POINT', 45.0, (0.45, 0.55, 1.0), 0.4),
           "Pit": ('POINT', 25.0, (0.35, 0.45, 1.0), 0.3),
           "PinSpot": ('SPOT', 240.0, (0.80, 0.86, 1.0), 0.1),
           "Window": ('POINT', 70.0, (0.35, 0.40, 1.0), 0.8),
           "Nebula": ('POINT', 900.0, (0.50, 0.42, 1.0), 2.5),
           "Moon": ('POINT', 25.0, (1.0, 0.75, 0.4), 0.2),
           "Orb": ('POINT', 40.0, (0.35, 0.5, 1.0), 0.1)}


# ============================================================= materials ===
def materials(tex):
    M = A.materials(tex)
    M.update({
        "mask": pbr("BWL_VoidMaskMat", base_img=tex["void_mask"], emit_img=tex["void_mask"],
                    emit_str=1.3, rough=0.3, metallic=0.6, alpha_from_base=True),
        "glass_s": pbr("BWL_VoidGlassMat", base_img=tex["void_glass"], emit_img=tex["void_glass"],
                       emit_str=2.4, rough=0.2),
        "banner": pbr("BWL_VoidBannerMat", base_img=tex["void_banner"], rough=0.8,
                      alpha_from_base=True),
        "nebula": pbr("BWL_NebulaMat", base_img=tex["nebula"], emit_img=tex["nebula"],
                      emit_str=3.2, rough=1.0),
        "stars": pbr("BWL_StarVaultMat", base_img=tex["star_ceiling"], emit_img=tex["star_ceiling"],
                     emit_str=1.2, rough=0.8),
        "compass": pbr("BWL_CompassMat", base_img=tex["compass"], rough=0.08),
        "plaster": mat("BWL_VoidWall", (0.015, 0.016, 0.04), rough=0.8),
        "moon": mat("BWL_MoonGold", (0.85, 0.62, 0.26), metallic=1.0, rough=0.25,
                    emit=(1.0, 0.72, 0.35), emit_str=1.6),
        "lantern": mat("BWL_VoidLantern", (0.6, 0.7, 1.0), rough=0.1, emit=(0.55, 0.65, 1.0),
                       emit_str=4.0),
        "orb": mat("BWL_VoidOrb", (0.15, 0.25, 0.7), rough=0.05, emit=(0.35, 0.5, 1.0),
                   emit_str=3.0),
        "globe": mat("BWL_Globe", (0.03, 0.06, 0.20), rough=0.3, emit=(0.15, 0.25, 0.8),
                     emit_str=0.6),
        "lens": mat("BWL_Lens", (0.4, 0.6, 1.0), rough=0.02, emit=(0.4, 0.6, 1.0), emit_str=2.0),
    })
    return M


# ================================================================ masking ===
def build_masking(M, c):
    """A gothic screen of open arches: the nebula shows through every one."""
    wood, gilt, panels, moon = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    puv = {}
    z0 = A.MASK_Z0
    sill, spring = A.ARCH_Z - z0, A.ARCH_Z - z0 + MASK_SPRING
    wall_with_openings(wood, lambda u, z, d: (u, A.MASK_Y + d, z + z0), -BLOCK_X, BLOCK_X,
                       SCREEN_TOP - z0, 0.3, [(i * PITCH, MASK_W, sill, spring) for i in LANES])
    span = 2 * BLOCK_X
    box(wood, 0.0, A.MASK_Y - 0.02, SCREEN_TOP + 0.06, span + 0.1, 0.12, 0.12)       # cornice
    box(gilt, 0.0, A.MASK_Y - 0.085, SCREEN_TOP, span + 0.1, 0.01, 0.03)
    box(gilt, 0.0, A.MASK_Y - 0.01, z0 + 0.03, span, 0.02, 0.03)
    for i in LANES:
        cx = i * PITCH
        out = A.dedupe(arch_outline(MASK_W, 0.0, MASK_SPRING, 16))
        vs = [panels.verts.new((cx + x, A.MASK_Y - 0.012, A.ARCH_Z + z)) for x, z in out]
        panels.faces.new(vs)
        for v, (x, z) in zip(vs, out):
            puv[v] = ((x + MASK_W / 2) / MASK_W, z / MASK_H)
        path = [(cx + x, A.MASK_Y - 0.03, A.ARCH_Z + z) for x, z in
                A.dedupe(arch_outline(MASK_W + 0.08, 0.0, MASK_SPRING, 16))]
        tube(gilt, path, 0.03, sides=6, cap=False)
        if i:                                                   # a small moon over each side arch
            H.crescent(moon, (cx, A.MASK_Y - 0.09, SCREEN_TOP - 0.14), 0.11)
    # spires at every lane boundary, tallest in the middle
    for k in range(len(LANES) + 1):
        x = (LANES[0] - 0.5 + k) * PITCH
        tall = 1.3 + 0.5 * (1.0 - abs(x) / (2.5 * PITCH))
        base = SCREEN_TOP + 0.12
        revolve(wood, [(0.13, 0.0), (0.13, 0.45), (0.17, 0.50), (0.09, 0.56), (0.07, 0.62),
                       (0.0, tall)], 8, centre=(x, A.MASK_Y + 0.05, base))
        revolve(gilt, [(0.0, 0.0), (0.045, 0.03), (0.0, 0.12)], 8, centre=(x, A.MASK_Y + 0.05, base + tall))
        for s in (-1, 1):                                       # little flanking pinnacles
            revolve(wood, [(0.05, 0.0), (0.05, 0.25), (0.0, 0.62)], 6,
                    centre=(x + s * 0.24, A.MASK_Y + 0.05, base))
    # the great gable over the middle lane, with its crescent
    zb, apex, hw = SCREEN_TOP + 0.12, SCREEN_TOP + 1.75, 0.88
    for d, flip in ((-0.02, False), (0.14, True)):
        vs = [wood.verts.new(p) for p in ((-hw, A.MASK_Y + d, zb), (hw, A.MASK_Y + d, zb),
                                         (0.0, A.MASK_Y + d, apex))]
        wood.faces.new(vs[::-1] if flip else vs)
    for s in (-1, 1):
        tube(gilt, [(s * hw, A.MASK_Y - 0.04, zb), (0.0, A.MASK_Y - 0.04, apex)], 0.028, sides=6)
    mz = zb + 0.62
    ring = [(0.40 * math.cos(TAU * k / 40), A.MASK_Y - 0.05, mz + 0.40 * math.sin(TAU * k / 40))
            for k in range(41)]
    tube(gilt, ring, 0.022, sides=6, cap=False)
    H.crescent(moon, (0.0, A.MASK_Y - 0.06, mz), 0.30)
    revolve(gilt, [(0.0, 0.0), (0.05, 0.04), (0.0, 0.18)], 8, centre=(0.0, A.MASK_Y + 0.05, apex - 0.02))
    A.set_uvs(panels, puv)
    shade_auto(new_obj(PFX + "Masking", wood, c, [M["wood"]]), math.radians(50))
    shade_auto(new_obj(PFX + "MaskingGilt", gilt, c, [M["gilt"]]))
    new_obj(PFX + "MaskArches", panels, c, [M["mask"]])
    new_obj(PFX + "Moons", moon, c, [M["moon"]])


# ================================================================== space ===
def build_nebula(M, c):
    """A curved screen of deep space behind the open back arch."""
    bm, uvs = bmesh.new(), {}
    n = 48
    a0, a1 = -math.radians(62), math.radians(62)
    rows = []
    for zi, z in enumerate(NEBULA_Z):
        row = []
        for k in range(n + 1):
            a = a0 + (a1 - a0) * k / n
            v = bm.verts.new((NEBULA_R * math.sin(a), NEBULA_CY + NEBULA_R * math.cos(a), z))
            uvs[v] = (k / n, zi)
            row.append(v)
        rows.append(row)
    for k in range(n):
        bm.faces.new((rows[0][k], rows[0][k + 1], rows[1][k + 1], rows[1][k]))
    A.set_uvs(bm, uvs)
    new_obj(PFX + "Nebula", bm, c, [M["nebula"]])


# ================================================================= decor ===
def telescope(brass, wood, lens, x, y, face, tilt=0.5):
    """A brass refractor on a wooden tripod, looking out at *face* (radians)."""
    top = 1.05
    for k in range(3):
        a = face + TAU * k / 3 + 0.5
        tube(wood, [(x, y, top), (x + 0.38 * math.cos(a), y + 0.38 * math.sin(a), 0.0)], 0.022, sides=6)
    fx, fy, fz = math.cos(face) * math.cos(tilt), math.sin(face) * math.cos(tilt), math.sin(tilt)
    p0 = (x - fx * 0.45, y - fy * 0.45, top + 0.08 - fz * 0.45)
    p1 = (x + fx * 0.75, y + fy * 0.75, top + 0.08 + fz * 0.75)
    tube(brass, [p0, (x, y, top + 0.08)], 0.035, sides=10)
    tube(brass, [(x, y, top + 0.08), p1], 0.055, sides=10)
    tube(brass, [(p0[0] - fx * 0.12, p0[1] - fy * 0.12, p0[2] - fz * 0.12), p0], 0.018, sides=8)
    revolve(brass, [(0.0, 0.0), (0.05, 0.02), (0.05, 0.1)], 8, centre=(x, y, top - 0.05))
    tube(lens, [p1, (p1[0] + fx * 0.01, p1[1] + fy * 0.01, p1[2] + fz * 0.01)], 0.05, sides=10)


def armillary(brass, orb, x, y, z, r=0.28, stand=True):
    """Gilded rings round a glowing centre, on a turned stand."""
    if stand:
        revolve(brass, [(0.16, 0.0), (0.16, 0.04), (0.05, 0.1), (0.03, z - r - 0.1), (0.06, z - r - 0.05),
                        (0.02, z - r + 0.02)], 10, centre=(x, y, 0.0))
    n = 40
    for tilt, yaw in ((0.0, 0.0), (math.pi / 2, 0.0), (math.pi / 2, math.pi / 2),
                      (math.radians(23.4), 0.6)):
        pts = []
        for k in range(n + 1):
            a = TAU * k / n
            px, py, pz = r * math.cos(a), r * math.sin(a), 0.0
            py, pz = py * math.cos(tilt), py * math.sin(tilt)
            px, py = px * math.cos(yaw) - py * math.sin(yaw), px * math.sin(yaw) + py * math.cos(yaw)
            pts.append((x + px, y + py, z + pz))
        tube(brass, pts, 0.009 if tilt else 0.012, sides=5, cap=False)
    tube(brass, [(x, y, z - r - 0.04), (x, y, z + r + 0.04)], 0.006, sides=5)
    revolve(orb, [(0.0, -0.06)] + [(0.06 * math.sin(math.pi * t / 8), -0.06 * math.cos(math.pi * t / 8))
                                   for t in range(1, 8)] + [(0.0, 0.06)], 12, centre=(x, y, z))


def globe(brass, gl, x, y, z, r=0.22):
    revolve(brass, [(0.14, 0.0), (0.14, 0.03), (0.04, 0.08), (0.03, z - r - 0.02)], 10, centre=(x, y, 0.0))
    revolve(gl, [(0.0, -r)] + [(r * math.sin(math.pi * t / 12), -r * math.cos(math.pi * t / 12))
                               for t in range(1, 12)] + [(0.0, r)], 20, centre=(x, y, z))
    ring = [(x + (r + 0.03) * math.cos(TAU * k / 32), y, z + (r + 0.03) * math.sin(TAU * k / 32))
            for k in range(17)]
    tube(brass, ring, 0.012, sides=5, cap=False)


def build_extras(M, c):
    brass, wood, lens, orb, gl, cmp_ = (bmesh.new() for _ in range(6))
    cuv = {}
    H.disc(cmp_, cuv, (0.0, -6.3, 0.006), 1.75, n=64, facing='+Z')
    telescope(brass, wood, lens, -6.9, 3.2, math.radians(20), tilt=0.45)
    telescope(brass, wood, lens, 6.9, 8.6, math.radians(160), tilt=0.5)
    telescope(brass, wood, lens, -6.6, 15.0, math.radians(35), tilt=0.6)
    armillary(brass, orb, -5.7, 12.2, 1.25)
    armillary(brass, orb, 5.7, 4.6, 1.25)
    armillary(brass, orb, 5.9, -4.3, 1.1, r=0.24)
    # a star-chart cabinet with globes on the right wall
    box(wood, 7.55, 14.5, 0.5, 0.5, 2.4, 1.0)
    box(wood, 7.55, 14.5, 1.02, 0.56, 2.5, 0.05)
    for k, yy in enumerate((13.6, 14.5, 15.4)):
        globe(brass, gl, 7.55, yy, 1.3 + 0.05 * k, r=0.15 + 0.03 * (k % 2))
    # the chandeliers carry hanging gilt orbs
    for cx, cy, cz in A.CHANDELIERS:
        for k in range(4):
            a = TAU * k / 4 + 0.4
            px, py = cx + 0.55 * math.cos(a), cy + 0.55 * math.sin(a)
            drop = 0.45 + 0.2 * (k % 2)
            tube(brass, [(px, py, cz), (px, py, cz - drop)], 0.006, sides=4)
            revolve(orb, [(0.0, -0.07)] + [(0.07 * math.sin(math.pi * t / 8), -0.07 * math.cos(math.pi * t / 8))
                                           for t in range(1, 8)] + [(0.0, 0.07)], 10,
                    centre=(px, py, cz - drop - 0.07))
    A.set_uvs(cmp_, cuv)
    shade_auto(new_obj(PFX + "Astro", brass, c, [M["brass"]]))
    shade_auto(new_obj(PFX + "AstroWood", wood, c, [M["wood"]]))
    new_obj(PFX + "Lenses", lens, c, [M["lens"]])
    shade_auto(new_obj(PFX + "AstroOrbs", orb, c, [M["orb"]]), math.radians(80))
    shade_auto(new_obj(PFX + "Globes", gl, c, [M["globe"]]), math.radians(80))
    new_obj(PFX + "Compass", cmp_, c, [M["compass"]])


# ======================================================= lights + cameras ===
def build_markers(mk, candles, lanterns):
    A.build_markers(mk, candles, lanterns)
    for i, (x, y, z) in enumerate(((-3.2, 23.5, 4.5), (0.0, 25.0, 5.5), (3.2, 23.5, 4.5))):
        empty("LGT_Nebula_%d" % i, (x, y, z), mk)
    empty("LGT_Moon", (0.0, A.MASK_Y - 0.5, SCREEN_TOP + 0.75), mk)


def build(tex):
    root = col("BWL_Void")
    for pre in ("BWL_", "LGT_", "BALL_"):
        wipe(pre)
    M = materials(tex)
    c = col("BWL_VoidArt", root)
    A.build_lanes(M, c)
    build_masking(M, c)
    A.build_returns(M, c)
    H.floor(M, c)
    H.walls(M, c, SIDE_WINDOWS, back="open")
    H.glazing(M, c, SIDE_WINDOWS)
    H.panelling(M, c, back_wainscot=False, ceil_key="stars", ceil_scale=0.12)
    build_nebula(M, c)
    A.build_columns(M, c)
    candles, lanterns = A.build_decor(M, c, rugs=A.RUGS[:2])
    build_extras(M, c)
    mk = col("BWL_VoidMarkers", root)
    build_markers(mk, candles, lanterns)
    A.build_preview_lights(mk, col("BWL_PreviewLights"), PREVIEW,
                           shadows=("Chandelier", "PinSpot", "Nebula"))
    A.build_cameras(col("BWL_Cameras"))
    return root
