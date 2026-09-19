"""Alley 3 - The Crypt (reference: art/reference/alley_neon.webp).

A blacklight crypt: polished black stone lanes whose markings glow under UV,
cyan neon run along every gutter, stone walls hung with glowing murals (a
castle under a violet moon, ghosts in the mist), sigil banners on the pillars,
torches flickering on the columns, static laser beams criss-crossing the vault,
and over the masking, the ghost bride between two great gargoyles. The ball
racks glow like sweets.

Collections BWL_CryptArt + BWL_CryptMarkers -> games/bowling/art/alleys/crypt.glb
"""
import bmesh, math
from bowl_common import (col, wipe, new_obj, shade_auto, box, revolve, tube, arch_outline, pbr,
                         mat, load_png, empty, LANES, PITCH, GX, CAPPING_TOP, LANE_LEN, HALL_X,
                         HALL_Y1, CEIL, COLUMN_X, COLUMN_YS, SQ3_2)
import bowl_alley as A
import bowl_hall as H
from bowl_textures import MASK_W, MASK_SPRING

PFX = A.PFX
# no chandeliers down the middle: they'd hang in front of the ghost bride
CHANDELIERS = [ch for ch in A.CHANDELIERS if ch[0] != 0.0 or ch[1] < 8.0]
BRIDE_W = 2.5
BRIDE_Z = A.MASK_Z1 + 0.14
MURALS = ((-2.45, 3.45), (4.05, 9.95), (10.55, 16.7))
MURAL_Z = (1.70, 4.65)
TORCH_Z = 2.05
LASERS = (((-7.7, 18.5, 6.4), (3.8, -3.0, 3.1), "v"), ((7.7, 17.0, 6.5), (-4.5, 4.0, 2.6), "v"),
          ((-7.7, 5.5, 6.2), (7.7, 15.5, 3.4), "g"), ((7.7, 1.5, 6.4), (-2.5, 15.0, 5.2), "g"),
          ((0.0, HALL_Y1 - 0.2, 6.6), (-7.7, -5.0, 4.2), "v"))
PREVIEW = {"Chandelier": ('POINT', 170.0, (1.0, 0.62, 0.36), 0.6),
           "Mask": ('POINT', 60.0, (0.62, 0.30, 1.0), 0.4),
           "Pit": ('POINT', 30.0, (0.45, 0.30, 1.0), 0.3),
           "PinSpot": ('SPOT', 230.0, (0.55, 0.65, 1.0), 0.1),
           "Window": ('POINT', 120.0, (0.45, 0.22, 1.0), 1.0),
           "Torch": ('POINT', 55.0, (1.0, 0.48, 0.18), 0.15),
           "Neon": ('POINT', 18.0, (0.10, 0.80, 1.0), 0.2),
           "Bride": ('POINT', 45.0, (0.20, 0.90, 1.0), 0.5),
           "Orb": ('POINT', 40.0, (0.6, 0.25, 1.0), 0.1)}
GLOW_BALLS = {"violet": (0.55, 0.15, 1.0), "emerald": (0.15, 1.0, 0.45),
              "crimson": (1.0, 0.35, 0.10), "midnight": (0.15, 0.45, 1.0)}


# ============================================================= materials ===
def materials(tex):
    M = A.materials(tex)
    lane_b, lane_e = tex["crypt_lane"]
    appr_b, appr_e = tex["crypt_approach"]
    stone = load_png("LNG_Stone")
    M.update({
        "lane": pbr("BWL_CryptLaneMat", base_img=lane_b, emit_img=lane_e, emit_str=2.2, rough=0.05),
        "approach": pbr("BWL_CryptApproachMat", base_img=appr_b, emit_img=appr_e, emit_str=2.2,
                        rough=0.10),
        "wood": mat("BWL_Ebony", (0.022, 0.016, 0.028), rough=0.30),
        "wood_dk": mat("BWL_VaultStone", (0.018, 0.016, 0.024), rough=0.85),
        "gilt": mat("BWL_OldGilt", (0.42, 0.31, 0.15), metallic=1.0, rough=0.38),
        "plaster": pbr("BWL_CryptWallMat", base_img=stone, rough=0.8),
        "column": mat("BWL_CryptColumn", (0.035, 0.032, 0.045), rough=0.35),
        "stone": mat("BWL_CryptGargoyle", (0.07, 0.065, 0.08), rough=0.7),
        "mask": pbr("BWL_NeonMaskMat", base_img=tex["neon_mask"], emit_img=tex["neon_mask"],
                    emit_str=2.4, rough=0.4),
        "bride": pbr("BWL_BrideMat", base_img=tex["bride"], emit_img=tex["bride"], emit_str=2.4,
                     rough=0.4, alpha_from_base=True),
        "banner": pbr("BWL_SigilMat", base_img=tex["sigils"], emit_img=tex["sigils"], emit_str=2.0,
                      rough=0.6),
        "mural_a": pbr("BWL_MuralAMat", base_img=tex["mural_a"], emit_img=tex["mural_a"],
                       emit_str=1.5, rough=0.7),
        "mural_b": pbr("BWL_MuralBMat", base_img=tex["mural_b"], emit_img=tex["mural_b"],
                       emit_str=1.5, rough=0.7),
        "star_map": pbr("BWL_StarMapMat", base_img=tex["star_map"], emit_img=tex["star_map"],
                        emit_str=1.8, rough=0.3, alpha_from_base=True),
        "neon_c": mat("BWL_NeonCyan", (0.1, 0.8, 1.0), rough=0.3, emit=(0.1, 0.85, 1.0), emit_str=6.0),
        "neon_v": mat("BWL_NeonViolet", (0.6, 0.2, 1.0), rough=0.3, emit=(0.62, 0.22, 1.0), emit_str=6.0),
        "laser_v": mat("BWL_LaserViolet", (0.7, 0.2, 1.0), emit=(0.75, 0.25, 1.0), emit_str=14.0),
        "laser_g": mat("BWL_LaserGreen", (0.3, 1.0, 0.4), emit=(0.3, 1.0, 0.35), emit_str=14.0),
        "iron": mat("BWL_Iron", (0.05, 0.05, 0.055), metallic=0.8, rough=0.5),
        "lantern": mat("BWL_CryptLantern", (0.6, 0.3, 1.0), rough=0.1, emit=(0.65, 0.3, 1.0),
                       emit_str=4.0),
    })
    M["plain"] = {k: mat("BWL_BallGlow_" + k, tuple(v * 0.5 for v in rgb), rough=0.06, metallic=0.1,
                         emit=rgb, emit_str=1.6)
                  for k, rgb in GLOW_BALLS.items()}
    return M


# ================================================================== pieces ===
def build_bride(M, c):
    """The ghost bride's panel over the masking, flanked by two great gargoyles."""
    panel, neon, garg = bmesh.new(), bmesh.new(), bmesh.new()
    uvs = {}
    sp = MASK_SPRING * BRIDE_W / MASK_W
    h = sp + BRIDE_W * SQ3_2
    y = A.MASK_Y + 0.03
    out = A.dedupe(arch_outline(BRIDE_W, 0.0, sp, 20))
    vs = [panel.verts.new((x, y, BRIDE_Z + z)) for x, z in out]
    panel.faces.new(vs)
    for v, (x, z) in zip(vs, out):
        uvs[v] = ((x + BRIDE_W / 2) / BRIDE_W, z / h)
    A.set_uvs(panel, uvs)
    tube(neon, [(x, y - 0.03, BRIDE_Z + z) for x, z in
                A.dedupe(arch_outline(BRIDE_W + 0.12, 0.0, sp, 20))], 0.025, sides=6, cap=False)
    for s in (-1, 1):
        before = set(garg.verts)
        A.gargoyle(garg, 0.0, 0.0, 0.0, -math.pi / 2)
        for v in garg.verts:
            if v not in before:
                v.co = v.co * 1.9 + type(v.co)((s * 2.05, A.MASK_Y + 0.05, A.MASK_Z1 + 0.12))
        revolve(garg, [(0.30, 0.0), (0.30, 0.10), (0.26, 0.12)], 8,
                centre=(s * 2.05, A.MASK_Y + 0.05, A.MASK_Z1 + 0.02))
    new_obj(PFX + "BridePanel", panel, c, [M["bride"]])
    new_obj(PFX + "BrideNeon", neon, c, [M["neon_v"]])
    shade_auto(new_obj(PFX + "GreatGargoyles", garg, c, [M["stone"]]), math.radians(40))


def build_murals(M, c):
    a, b, frame = bmesh.new(), bmesh.new(), bmesh.new()
    ua, ub = {}, {}
    z0, z1 = MURAL_Z
    k = 0
    for side in (1, -1):
        x = side * (HALL_X - 0.09)
        for y0, y1 in MURALS:
            bm, uv = (a, ua) if k % 2 == 0 else (b, ub)
            if side > 0:
                pts = ((x, y1, z0), (x, y0, z0), (x, y0, z1), (x, y1, z1))
            else:
                pts = ((x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1))
            A.uv_quad(bm, pts, uv)
            fx = x - side * 0.02
            tube(frame, [(fx, y0, z0), (fx, y1, z0), (fx, y1, z1), (fx, y0, z1), (fx, y0, z0)],
                 0.022, sides=6, cap=False)
            k += 1
    A.set_uvs(a, ua)
    A.set_uvs(b, ub)
    new_obj(PFX + "MuralA", a, c, [M["mural_a"]])
    new_obj(PFX + "MuralB", b, c, [M["mural_b"]])
    new_obj(PFX + "MuralNeon", frame, c, [M["neon_v"]])


def build_neon(M, c):
    """Cyan neon along every gutter, a violet bar at the foul line, and the lasers."""
    cyan, violet, lv, lg, iron = (bmesh.new() for _ in range(5))
    for i in LANES:
        cx = i * PITCH
        for s in (-1, 1):
            x = cx + s * (GX + 0.012)
            tube(cyan, [(x, 0.15, CAPPING_TOP + 0.012), (x, LANE_LEN - 0.4, CAPPING_TOP + 0.012)],
                 0.011, sides=6)
    tube(violet, [(-2.5 * PITCH, -0.02, 0.012), (2.5 * PITCH, -0.02, 0.012)], 0.008, sides=6)
    for p0, p1, kind in LASERS:
        tube(lv if kind == "v" else lg, [p0, p1], 0.007, sides=5)
        box(iron, p0[0] - math.copysign(0.08, p0[0]) if abs(p0[0]) > 1 else p0[0], p0[1], p0[2],
            0.16, 0.16, 0.16)
    new_obj(PFX + "NeonCyan", cyan, c, [M["neon_c"]])
    new_obj(PFX + "NeonViolet", violet, c, [M["neon_v"]])
    new_obj(PFX + "LasersViolet", lv, c, [M["laser_v"]])
    new_obj(PFX + "LasersGreen", lg, c, [M["laser_g"]])
    shade_auto(new_obj(PFX + "LaserHeads", iron, c, [M["iron"]]))


def build_torches(M, c):
    iron, fl = bmesh.new(), bmesh.new()
    fuv, spots = {}, []
    for side in (-1, 1):
        for y in COLUMN_YS:
            x0 = side * (COLUMN_X + 0.22)
            tx = side * (COLUMN_X + 0.40)
            tube(iron, [(x0, y, TORCH_Z - 0.18), (tx, y, TORCH_Z)], 0.018, sides=6)
            box(iron, x0, y, TORCH_Z - 0.2, 0.04, 0.12, 0.2)
            revolve(iron, [(0.0, -0.12), (0.03, -0.1), (0.075, 0.05), (0.09, 0.12), (0.07, 0.12)],
                    8, centre=(tx, y, TORCH_Z))
            A.flame_card(fl, tx, y, TORCH_Z + 0.08, 0.34, fuv)
            spots.append((tx, y, TORCH_Z + 0.35))
    A.set_uvs(fl, fuv)
    shade_auto(new_obj(PFX + "Torches", iron, c, [M["iron"]]))
    new_obj(PFX + "TorchFlames", fl, c, [M["flame"]])
    return spots


def build_vault(M, c):
    bm, uvs = bmesh.new(), {}
    H.disc(bm, uvs, (0.0, 8.0, CEIL - 0.32), 2.4, n=64, facing='-Z')
    A.set_uvs(bm, uvs)
    new_obj(PFX + "StarMap", bm, c, [M["star_map"]])
    ring = bmesh.new()
    tube(ring, [(2.45 * math.cos(math.tau * k / 64), 8.0 + 2.45 * math.sin(math.tau * k / 64), CEIL - 0.32)
                for k in range(65)], 0.03, sides=6, cap=False)
    new_obj(PFX + "StarMapNeon", ring, c, [M["neon_c"]])


# ======================================================= lights + cameras ===
def build_markers(mk, candles, lanterns, torches):
    A.build_markers(mk, candles, lanterns, CHANDELIERS)
    for i, p in enumerate(torches):
        empty("LGT_Torch_%d" % i, p, mk)
    k = 0
    for x in (-(GX + 0.012), GX + 0.012):                   # on the neon beside the player's lane
        for y in (3.5, 11.0):
            empty("LGT_Neon_%d" % k, (x, y, CAPPING_TOP + 0.05), mk)
            k += 1
    empty("LGT_Bride", (0.0, A.MASK_Y - 0.6, BRIDE_Z + 1.4), mk)


def build(tex):
    root = col("BWL_Crypt")
    for pre in ("BWL_", "LGT_", "BALL_"):
        wipe(pre)
    M = materials(tex)
    c = col("BWL_CryptArt", root)
    A.build_lanes(M, c)
    A.build_masking(M, c)
    build_bride(M, c)
    A.build_returns(M, c)
    H.floor(M, c)
    H.walls(M, c, (), back="wall", stone_scale=0.4)
    H.panelling(M, c)
    build_vault(M, c)
    A.build_columns(M, c)
    candles, lanterns = A.build_decor(M, c, portraits=False, chandeliers=CHANDELIERS)
    build_murals(M, c)
    build_neon(M, c)
    torches = build_torches(M, c)
    mk = col("BWL_CryptMarkers", root)
    build_markers(mk, candles, lanterns, torches)
    A.build_preview_lights(mk, col("BWL_PreviewLights"), PREVIEW,
                           shadows=("Chandelier", "PinSpot"))
    A.build_cameras(col("BWL_Cameras"))
    return root
