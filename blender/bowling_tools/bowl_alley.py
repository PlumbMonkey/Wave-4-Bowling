"""Alley 1 - The Spectral Lounge (reference: art/reference/alley_lounge.webp).

Five lanes in a mahogany hall: gothic masking arches glowing violet over the
pins, gargoyle columns carrying pointed arches over the lanes, candle
chandeliers, ghost glass at the far end, velvet seating in the aisles.
Lane 0 is the one you play; its pins and colliders come from Godot.

Markers named LGT_* are exported with the GLB; games/bowling/scripts/alley_theme.gd
turns them into Godot lights.
"""
import bpy, bmesh, math
from mathutils import Vector
from bowl_common import (col, wipe, new_obj, shade_auto, box, revolve, tube, arch_outline,
                         wall_with_openings, wall_mapper, pbr, mat, load_png, empty, pin_spots,
                         LANE_HALF, LANE_LEN, DECK_END, PIT_END, GUTTER_W, CAPPING_TOP, APPROACH,
                         GX, PITCH, LANES, HALL_X, HALL_Y0, HALL_Y1, CEIL, BLOCK_X, COLUMN_X,
                         COLUMN_YS, BALL_R, SQ3_2, TAU)
import bowl_balls
from bowl_textures import MASK_W, MASK_SPRING, MASK_H

PFX = "BWL_"
MASK_Y = 19.00               # front face of the masking unit
MASK_Z0, MASK_Z1 = 0.95, 3.00
ARCH_Z = 1.18                # bottom of the glowing arch panels
PIN_PROFILE = [(0.0, 0.0), (0.0258, 0.0), (0.0365, 0.019), (0.0500, 0.057), (0.0605, 0.114),
               (0.0565, 0.165), (0.0435, 0.210), (0.0327, 0.234), (0.03045, 0.239),
               (0.0277, 0.247), (0.0254, 0.254), (0.0228, 0.262),
               (0.0240, 0.292), (0.0300, 0.330), (0.0318, 0.346), (0.0280, 0.365),
               (0.0160, 0.378), (0.0, 0.381)]
CHANDELIERS = [(0.0, 3.5, 4.9), (0.0, 11.0, 4.9), (-3.0, 7.2, 5.1), (3.0, 7.2, 5.1),
               (0.0, 16.0, 5.1)]


# ================================================================ helpers ===
def uv_quad(bm, pts, uvs, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
    vs = [bm.verts.new(p) for p in pts]
    bm.faces.new(vs)
    for v, t in zip(vs, uv):
        uvs[v] = t
    return vs


def set_uvs(bm, uvs):
    layer = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for loop in f.loops:
            if loop.vert in uvs:
                loop[layer].uv = uvs[loop.vert]


def world_uvs(ob, scale, axes=(0, 1)):
    me = ob.data
    layer = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            layer.data[li].uv = (co[axes[0]] * scale, co[axes[1]] * scale)


def dedupe(pts):
    out = []
    for p in pts:
        if not out or abs(out[-1][0] - p[0]) + abs(out[-1][1] - p[1]) > 1e-6:
            out.append(p)
    return out


def flame_card(bm, x, y, z, h, uvs):
    w = h * 0.5
    for a in (0.0, math.pi / 2):
        ca, sa = math.cos(a) * w, math.sin(a) * w
        uv_quad(bm, [(x - ca, y - sa, z), (x + ca, y + sa, z), (x + ca, y + sa, z + h),
                     (x - ca, y - sa, z + h)], uvs)


def candle(wax, fl, fuv, x, y, z, h=0.2, r=0.022):
    revolve(wax, [(r, 0.0), (r, h), (r * 0.6, h + 0.004), (0.0, h + 0.004)], 8, centre=(x, y, z))
    flame_card(fl, x, y, z + h + 0.004, max(0.07, h * 0.42), fuv)


# ============================================================= materials ===
def materials(tex):
    M = bowl_balls.materials(tex)
    mahog = load_png("LNG_Mahogany")
    M.update({
        "lane": pbr("BWL_LaneMat", base_img=tex["lane"], rough=0.05),
        "approach": pbr("BWL_ApproachMat", base_img=tex["approach"], rough=0.14),
        "marble": pbr("BWL_MarbleMat", base_img=tex["marble"], rough=0.10),
        "wood": pbr("BWL_Mahogany", base_img=mahog, rough=0.32),
        "wood_dk": mat("BWL_WoodDark", (0.035, 0.014, 0.010), rough=0.4),
        "plaster": mat("BWL_Plaster", (0.045, 0.030, 0.040), rough=0.85),
        "gilt": mat("BWL_Gilt", (0.80, 0.58, 0.24), metallic=1.0, rough=0.22),
        "brass": mat("BWL_Brass", (0.52, 0.34, 0.13), metallic=1.0, rough=0.32),
        "gutter": mat("BWL_Gutter", (0.05, 0.05, 0.06), metallic=0.9, rough=0.22),
        "pit": mat("BWL_PitBlack", (0.004, 0.003, 0.006), rough=0.95),
        "pitglow": pbr("BWL_PitGlowMat", base_img=tex["pit"], emit_img=tex["pit"], emit_str=1.6,
                       rough=0.9),
        "mask": pbr("BWL_MaskMat", base_img=tex["mask"], emit_img=tex["mask"], emit_str=2.2,
                    rough=0.4),
        "glass_c": pbr("BWL_GlassGhostMat", base_img=tex["glass_center"],
                       emit_img=tex["glass_center"], emit_str=2.6, rough=0.2),
        "glass_s": pbr("BWL_GlassSideMat", base_img=tex["glass_side"],
                       emit_img=tex["glass_side"], emit_str=2.2, rough=0.2),
        "portrait": pbr("BWL_PortraitMat", base_img=tex["portrait"], emit_img=tex["portrait"],
                        emit_str=1.2, rough=0.5),
        "banner": pbr("BWL_BannerMat", base_img=tex["banner"], rough=0.8),
        "velvet": pbr("BWL_Velvet", base_img=load_png("LNG_Velvet"), rough=0.72),
        "rug": pbr("BWL_Rug", base_img=load_png("LNG_RugRect"), rough=0.95),
        "column": mat("BWL_ColumnMarble", (0.040, 0.036, 0.045), rough=0.12),
        "stone": mat("BWL_GargoyleStone", (0.13, 0.12, 0.12), rough=0.75),
        "pin": mat("BWL_Pin", (0.90, 0.88, 0.84), rough=0.2),
        "pin_red": mat("BWL_PinStripe", (0.55, 0.02, 0.03), rough=0.3),
        "candle": mat("BWL_Candle", (0.80, 0.74, 0.60), rough=0.45, emit=(1.0, 0.7, 0.4),
                      emit_str=0.5),
        "flame": pbr("BWL_Flame", base_img=load_png("LNG_Flame"), emit_img=load_png("LNG_Flame"),
                     emit_str=12.0, alpha_from_base=True),
        "lantern": mat("BWL_LanternGlass", (0.9, 0.55, 0.2), rough=0.1, emit=(1.0, 0.6, 0.25),
                       emit_str=4.0),
        "orb": mat("BWL_Orb", (0.30, 0.10, 0.60), rough=0.05, emit=(0.54, 0.17, 0.89),
                   emit_str=3.0),
        "case_glass": mat("BWL_CaseGlass", (0.10, 0.10, 0.13), rough=0.03, alpha=0.18),
    })
    return M


# ================================================================= lanes ===
def pin_mesh(pins, stripes, x, y):
    revolve(pins, [(r, z) for r, z in PIN_PROFILE], 16, centre=(x, y, 0.0))
    # two red stripes on the narrow neck (matches bowling_pin.gd STRIPES)
    for (r0, z0), (r1, z1) in (((0.03045, 0.239), (0.0277, 0.247)), ((0.0254, 0.254), (0.0228, 0.262))):
        revolve(stripes, [(r0 + 0.0006, z0), (r1 + 0.0006, z1)], 16, centre=(x, y, 0.0))


def build_lanes(M, c):
    lane, appr, gut, wood, gilt, pit, glow = (bmesh.new() for _ in range(7))
    pins, stripes = bmesh.new(), bmesh.new()
    luv, auv, guv = {}, {}, {}
    profile = [(0.0, 0.0), (0.02, -0.045), (0.06, -0.06), (0.175, -0.06), (0.215, -0.045),
               (0.235, 0.0)]
    y_end = DECK_END
    for i in LANES:
        cx = i * PITCH
        uv_quad(lane, [(cx - LANE_HALF, 0, 0), (cx + LANE_HALF, 0, 0),
                       (cx + LANE_HALF, y_end, 0), (cx - LANE_HALF, y_end, 0)], luv)
        uv_quad(appr, [(cx - PITCH / 2, -APPROACH, 0), (cx + PITCH / 2, -APPROACH, 0),
                       (cx + PITCH / 2, 0, 0), (cx - PITCH / 2, 0, 0)], auv)
        for s in (-1, 1):
            # gutter channel, extruded along the lane
            r0 = [gut.verts.new((cx + s * (LANE_HALF + px), 0.0, pz)) for px, pz in profile]
            r1 = [gut.verts.new((cx + s * (LANE_HALF + px), y_end, pz)) for px, pz in profile]
            for k in range(len(profile) - 1):
                f = (r0[k], r0[k + 1], r1[k + 1], r1[k])
                gut.faces.new(f if s > 0 else f[::-1])
        # capping on this lane's right (and the far left edge), kickbacks, pit
        for edge in ([cx + PITCH / 2] + ([cx - PITCH / 2] if i == LANES[0] else [])):
            box(wood, edge, y_end * 0.5 - 0.3, CAPPING_TOP * 0.5, 0.24, y_end - 0.6, CAPPING_TOP)
            box(gilt, edge, y_end * 0.5 - 0.3, CAPPING_TOP + 0.004, 0.03, y_end - 0.6, 0.008)
            box(wood, edge, (17.6 + PIT_END) * 0.5, 0.30, 0.24, PIT_END - 17.6, 1.30)
            box(gilt, edge, (17.6 + PIT_END) * 0.5, 0.955, 0.26, PIT_END - 17.6, 0.03)
        box(pit, cx, (DECK_END + PIT_END) * 0.5, -0.375, 2 * GX, PIT_END - DECK_END, 0.05)
        box(pit, cx, DECK_END + 0.01, -0.18, 2 * LANE_HALF, 0.02, 0.36)
        uv_quad(glow, [(cx - GX, PIT_END, -0.35), (cx + GX, PIT_END, -0.35),
                       (cx + GX, PIT_END, 0.95), (cx - GX, PIT_END, 0.95)], guv)
        if i != 0:
            for x, y in pin_spots(cx):
                pin_mesh(pins, stripes, x, y)
    set_uvs(lane, {v: (t[0], t[1]) for v, t in luv.items()})
    set_uvs(appr, auv)
    set_uvs(glow, guv)
    new_obj(PFX + "Lanes", lane, c, [M["lane"]])
    new_obj(PFX + "Approach", appr, c, [M["approach"]])
    shade_auto(new_obj(PFX + "Gutters", gut, c, [M["gutter"]]), math.radians(50))
    new_obj(PFX + "Cappings", wood, c, [M["wood"]])
    new_obj(PFX + "CappingGilt", gilt, c, [M["gilt"]])
    new_obj(PFX + "Pits", pit, c, [M["pit"]])
    new_obj(PFX + "PitGlow", glow, c, [M["pitglow"]])
    shade_auto(new_obj(PFX + "SetPins", pins, c, [M["pin"]]), math.radians(60))
    shade_auto(new_obj(PFX + "SetPinStripes", stripes, c, [M["pin_red"]]), math.radians(60))


def build_masking(M, c):
    wood, gilt, panels = bmesh.new(), bmesh.new(), bmesh.new()
    puv = {}
    span = 2 * BLOCK_X
    box(wood, 0.0, MASK_Y + 0.18, (MASK_Z0 + MASK_Z1) * 0.5, span, 0.36, MASK_Z1 - MASK_Z0)
    box(wood, 0.0, MASK_Y - 0.02, MASK_Z1 + 0.06, span + 0.1, 0.12, 0.12)      # cornice
    box(gilt, 0.0, MASK_Y - 0.085, MASK_Z1 + 0.0, span + 0.1, 0.01, 0.03)
    box(gilt, 0.0, MASK_Y - 0.01, MASK_Z0 + 0.03, span, 0.02, 0.03)
    for i in LANES:
        cx = i * PITCH
        out = dedupe(arch_outline(MASK_W, 0.0, MASK_SPRING, 16))
        vs = [panels.verts.new((cx + x, MASK_Y - 0.012, ARCH_Z + z)) for x, z in out]
        panels.faces.new(vs)
        for v, (x, z) in zip(vs, out):
            puv[v] = ((x + MASK_W / 2) / MASK_W, z / MASK_H)
        path = [(cx + x, MASK_Y - 0.03, ARCH_Z + z) for x, z in
                dedupe(arch_outline(MASK_W + 0.08, 0.0, MASK_SPRING, 16))]
        tube(gilt, path, 0.03, sides=6, cap=False)
    for k in range(len(LANES) + 1):
        x = (LANES[0] - 0.5 + k) * PITCH
        revolve(wood, [(0.10, 0.0), (0.10, 0.25), (0.13, 0.30), (0.05, 0.75), (0.0, 0.85)], 8,
                centre=(x, MASK_Y + 0.02, MASK_Z1 + 0.12))
        revolve(gilt, [(0.0, 0.0), (0.04, 0.02), (0.0, 0.08)], 8,
                centre=(x, MASK_Y + 0.02, MASK_Z1 + 0.96))
    set_uvs(panels, puv)
    shade_auto(new_obj(PFX + "Masking", wood, c, [M["wood"]]))
    shade_auto(new_obj(PFX + "MaskingGilt", gilt, c, [M["gilt"]]))
    new_obj(PFX + "MaskArches", panels, c, [M["mask"]])


def ball_return(M, c, x, balls, wood, gilt, brass, lglass):
    """A gothic ball return on the approach: hood at the lane end, a rack of balls."""
    y0, y1 = -1.05, -3.10
    box(wood, x, (y0 + y1) * 0.5, 0.16, 0.46, abs(y1 - y0), 0.32)
    box(gilt, x, (y0 + y1) * 0.5, 0.325, 0.48, abs(y1 - y0), 0.012)
    for s in (-1, 1):
        tube(brass, [(x + s * 0.075, y1 + 0.05, 0.36), (x + s * 0.075, y0 - 0.35, 0.36)], 0.012,
             sides=6)
        tube(brass, [(x + s * 0.2, y1, 0.34), (x + s * 0.2, y0 - 0.3, 0.34)], 0.018, sides=6)
    # the hood: a carved cabinet with a pointed arch in front
    box(wood, x, y0 - 0.05, 0.48, 0.58, 0.55, 0.96)
    box(wood, x, y0 - 0.05, 0.98, 0.64, 0.6, 0.06)
    path = [(x + px, y0 - 0.335, 0.30 + pz) for px, pz in
            dedupe(arch_outline(0.36, 0.0, 0.18, 10))]
    tube(gilt, path, 0.015, sides=6, cap=False)
    lantern(brass, lglass, x, y0 - 0.05, 1.01)
    for k, kind in enumerate(balls):
        bowl_balls.build(kind, (x, y0 - 0.52 - k * 0.235, 0.36 + BALL_R - 0.03), c, M,
                         name="%sRack_%s_%d" % (PFX, kind, int(x * 10)))


def build_returns(M, c):
    wood, gilt, brass, lglass = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    ball_return(M, c, PITCH / 2, ["spectre", "p", "skull", "violet"], wood, gilt, brass, lglass)
    ball_return(M, c, -1.5 * PITCH, ["crimson", "emerald", "midnight", "violet"], wood, gilt, brass, lglass)
    ball_return(M, c, 2.5 * PITCH - 0.35, ["midnight", "crimson", "emerald"], wood, gilt, brass, lglass)
    shade_auto(new_obj(PFX + "Returns", wood, c, [M["wood"]]))
    new_obj(PFX + "ReturnGilt", gilt, c, [M["gilt"]])
    new_obj(PFX + "ReturnRails", brass, c, [M["brass"]])
    new_obj(PFX + "ReturnLanterns", lglass, c, [M["lantern"]])


# ================================================================== hall ===
SIDE_WINDOWS = [(0.5, 1.4, 3.7, 5.0), (7.0, 1.4, 3.7, 5.0), (13.5, 1.4, 3.7, 5.0)]
BACK_WINDOWS = [(0.0, 2.2, 3.4, 4.6, "c"), (-3.3, 1.6, 3.5, 4.7, "s"), (3.3, 1.6, 3.5, 4.7, "s")]


def build_shell(M, c):
    # floor: marble everywhere the lanes and approach don't cover
    fl = bmesh.new()
    for x0, x1, y0, y1 in ((-HALL_X, HALL_X, HALL_Y0, -APPROACH),
                           (-HALL_X, -BLOCK_X, -APPROACH, HALL_Y1),
                           (BLOCK_X, HALL_X, -APPROACH, HALL_Y1),
                           (-BLOCK_X, BLOCK_X, PIT_END, HALL_Y1)):
        fl.faces.new([fl.verts.new(p) for p in ((x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0))])
    ob = new_obj(PFX + "Floor", fl, c, [M["marble"]])
    world_uvs(ob, 0.5)

    walls = bmesh.new()
    for x, flip in ((HALL_X, False), (-HALL_X, True)):
        ops = [(y, w, s, sp) for y, w, s, sp in SIDE_WINDOWS]
        wall_with_openings(walls, wall_mapper('X', x, flip), HALL_Y0, HALL_Y1, CEIL, 0.4, ops)
    wall_with_openings(walls, wall_mapper('Y', HALL_Y1, False), -HALL_X, HALL_X, CEIL, 0.4,
                       [(x, w, s, sp) for x, w, s, sp, _ in BACK_WINDOWS])
    wall_with_openings(walls, wall_mapper('Y', HALL_Y0, True), -HALL_X, HALL_X, CEIL, 0.4, [])
    bmesh.ops.remove_doubles(walls, verts=walls.verts, dist=1e-5)
    new_obj(PFX + "Walls", walls, c, [M["plaster"]])

    # glazing
    gc, gs = bmesh.new(), bmesh.new()
    cu, su = {}, {}
    frames = bmesh.new()

    def pane(bm, uvs, to_world, u, w, sill, spring):
        h = spring - sill + w * SQ3_2
        out = dedupe(arch_outline(w, sill, spring, 14))
        vs = [bm.verts.new(to_world(u + x, z, 0.2)) for x, z in out]
        bm.faces.new(vs)
        for v, (x, z) in zip(vs, out):
            uvs[v] = ((x + w / 2) / w, (z - sill) / h)
        tube(frames, [to_world(u + x, z, -0.03) for x, z in out], 0.06, sides=6, cap=False)

    for x, flip in ((HALL_X, False), (-HALL_X, True)):
        tw = wall_mapper('X', x, flip)
        for y, w, s, sp in SIDE_WINDOWS:
            pane(gs, su, tw, y, w, s, sp)
    tw = wall_mapper('Y', HALL_Y1, False)
    for x, w, s, sp, kind in BACK_WINDOWS:
        pane(gc if kind == "c" else gs, cu if kind == "c" else su, tw, x, w, s, sp)
    set_uvs(gc, cu)
    set_uvs(gs, su)
    new_obj(PFX + "GlassGhost", gc, c, [M["glass_c"]])
    new_obj(PFX + "GlassSide", gs, c, [M["glass_s"]])
    shade_auto(new_obj(PFX + "WindowFrames", frames, c, [M["gilt"]]))

    # mahogany wainscot, dado rail, pilasters, cornice, coffered ceiling
    wood, gilt = bmesh.new(), bmesh.new()
    for x in (HALL_X - 0.04, -HALL_X + 0.04):
        box(wood, x, (HALL_Y0 + HALL_Y1) * 0.5, 0.75, 0.08, HALL_Y1 - HALL_Y0, 1.5)
        box(gilt, x - math.copysign(0.05, x), (HALL_Y0 + HALL_Y1) * 0.5, 1.5, 0.03,
            HALL_Y1 - HALL_Y0, 0.04)
        for y in range(-9, 21, 3):
            box(wood, x - math.copysign(0.05, x), y + 0.5, 0.75, 0.04, 0.06, 1.4)
        for y in (-6.5, -2.75, 3.75, 10.25, 17.0, 20.0):
            box(wood, x - math.copysign(0.08, x), y, CEIL * 0.5, 0.16, 0.36, CEIL)
        box(wood, x - math.copysign(0.12, x), (HALL_Y0 + HALL_Y1) * 0.5, CEIL - 0.25, 0.24,
            HALL_Y1 - HALL_Y0, 0.5)
    for y in (HALL_Y1 - 0.04, HALL_Y0 + 0.04):
        box(wood, 0.0, y, 0.75, 2 * HALL_X, 0.08, 1.5)
        box(wood, 0.0, y - math.copysign(0.12, y), CEIL - 0.25, 2 * HALL_X, 0.24, 0.5)
    ceil = bmesh.new()
    ceil.faces.new([ceil.verts.new(p) for p in ((-HALL_X, HALL_Y1, CEIL), (HALL_X, HALL_Y1, CEIL),
                                                  (HALL_X, HALL_Y0, CEIL), (-HALL_X, HALL_Y0, CEIL))])
    new_obj(PFX + "Ceiling", ceil, c, [M["wood_dk"]])
    for x in (-6.0, -3.0, 0.0, 3.0, 6.0):
        box(wood, x, (HALL_Y0 + HALL_Y1) * 0.5, CEIL - 0.15, 0.25, HALL_Y1 - HALL_Y0, 0.3)
    for y in range(-8, 22, 3):
        box(wood, 0.0, y, CEIL - 0.15, 2 * HALL_X, 0.25, 0.3)
    shade_auto(new_obj(PFX + "Panelling", wood, c, [M["wood"]]))
    new_obj(PFX + "PanelGilt", gilt, c, [M["gilt"]])


def gargoyle(bm, x, y, z, face):
    """A crouched, winged gargoyle - blocky, but it reads at column-top distance."""
    fx, fy = math.cos(face), math.sin(face)
    revolve(bm, [(0.0, 0.0), (0.16, 0.02), (0.20, 0.18), (0.15, 0.36), (0.08, 0.44),
                 (0.0, 0.46)], 10, centre=(x, y, z))
    hx, hy = x + fx * 0.14, y + fy * 0.14
    revolve(bm, [(0.0, 0.0), (0.08, 0.02), (0.10, 0.10), (0.07, 0.18), (0.0, 0.2)], 10,
            centre=(hx, hy, z + 0.36))
    for s in (-1, 1):
        px, py = -fy * s, fx * s
        tube(bm, [(hx + px * 0.05, hy + py * 0.05, z + 0.52),
                  (hx + px * 0.09 - fx * 0.05, hy + py * 0.09 - fy * 0.05, z + 0.64)], 0.018,
             sides=5)
        wing = [(x + px * 0.12, y + py * 0.12, z + 0.38),
                (x + px * 0.42 - fx * 0.15, y + py * 0.42 - fy * 0.15, z + 0.80),
                (x + px * 0.32 - fx * 0.2, y + py * 0.32 - fy * 0.2, z + 0.30)]
        bm.faces.new([bm.verts.new(p) for p in wing])
        tube(bm, [(x + px * 0.12 + fx * 0.1, y + py * 0.12 + fy * 0.1, z + 0.02),
                  (x + px * 0.1 + fx * 0.2, y + py * 0.1 + fy * 0.2, z + 0.0)], 0.035, sides=6)


def squashed_arch(p0, p1, z0, rise_scale, n=24):
    """A pointed arch from p0 to p1 (xy), springing at z0, flattened by rise_scale."""
    a, b = Vector(p0), Vector(p1)
    w = (b - a).length
    out = arch_outline(w, 0.0, 0.0, n)
    pts = []
    for u, z in out[1:-1]:
        t = (u + w / 2) / w
        q = a.lerp(b, t)
        pts.append((q.x, q.y, z0 + z * rise_scale))
    return pts


def build_columns(M, c):
    stone, gilt, wood, garg = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    top = 4.35
    for side in (-1, 1):
        x = side * COLUMN_X
        for y in COLUMN_YS:
            box(stone, x, y, 0.22, 0.78, 0.78, 0.44)
            revolve(stone, [(0.36, 0.44), (0.30, 0.56), (0.28, 0.60)], 8, centre=(x, y, 0.0))
            revolve(stone, [(0.27, 0.60), (0.24, 3.90)], 8, centre=(x, y, 0.0))
            for dz in (1.2, 2.6):
                revolve(gilt, [(0.25, 0.0), (0.26, 0.03), (0.25, 0.06)], 8, centre=(x, y, dz))
            revolve(stone, [(0.24, 3.90), (0.30, 4.05), (0.42, 4.25), (0.42, top)], 8,
                    centre=(x, y, 0.0))
            gargoyle(garg, x - side * 0.05, y, top, math.atan2(0.0, -side))
        # the arcade along the aisle and the arches across the lanes
        for y0, y1 in zip(COLUMN_YS, COLUMN_YS[1:]):
            tube(wood, squashed_arch((x, y0), (x, y1), top, 0.55), 0.13, sides=8, cap=False)
            tube(gilt, [(p[0] - side * 0.13, p[1], p[2] - 0.02) for p in
                        squashed_arch((x, y0), (x, y1), top, 0.55)], 0.025, sides=6, cap=False)
    for y in COLUMN_YS:
        pts = squashed_arch((-COLUMN_X, y), (COLUMN_X, y), top, 0.30, n=40)
        tube(wood, pts, 0.15, sides=8, cap=False)
        tube(gilt, [(p[0], p[1] - 0.15, p[2]) for p in pts], 0.025, sides=6, cap=False)
        tube(gilt, [(p[0], p[1] + 0.15, p[2]) for p in pts], 0.025, sides=6, cap=False)
    shade_auto(new_obj(PFX + "Columns", stone, c, [M["column"]]), math.radians(50))
    new_obj(PFX + "ColumnGilt", gilt, c, [M["gilt"]])
    shade_auto(new_obj(PFX + "Arches", wood, c, [M["wood"]]), math.radians(50))
    shade_auto(new_obj(PFX + "Gargoyles", garg, c, [M["stone"]]), math.radians(40))


# ================================================================= decor ===
def chandelier(brass, wax, fl, fuv, cx, cy, cz):
    tube(brass, [(cx, cy, cz + 0.6), (cx, cy, CEIL - 0.3)], 0.015, sides=5)
    revolve(brass, [(0.0, -0.45), (0.09, -0.35), (0.14, -0.1), (0.07, 0.25), (0.10, 0.45),
                    (0.04, 0.6), (0.0, 0.62)], 12, centre=(cx, cy, cz))
    for R, dz, n in ((0.85, 0.0, 12), (0.5, 0.42, 8)):
        ring = [(cx + R * math.cos(TAU * k / 32), cy + R * math.sin(TAU * k / 32), cz + dz)
                for k in range(33)]
        tube(brass, ring, 0.03, sides=6, cap=False)
        for k in range(n):
            a = TAU * (k + 0.5) / n
            px, py = cx + R * math.cos(a), cy + R * math.sin(a)
            arm = [(cx + (0.1 + (R - 0.1) * t / 6) * math.cos(a),
                    cy + (0.1 + (R - 0.1) * t / 6) * math.sin(a),
                    cz + dz + 0.12 - 0.22 * math.sin(t / 6 * math.pi)) for t in range(7)]
            tube(brass, arm, 0.016, sides=5)
            revolve(brass, [(0.0, 0.0), (0.045, 0.01), (0.045, 0.04)], 8, centre=(px, py, cz + dz))
            candle(wax, fl, fuv, px, py, cz + dz + 0.04, h=0.20)


def sconce(brass, wax, fl, fuv, x, y, z, nx):
    box(brass, x, y, z, 0.04, 0.12, 0.32)
    for off in (-0.16, 0.0, 0.16):
        tx, ty = x + nx * 0.24, y + off
        tube(brass, [(x, y, z - 0.05), (x + nx * 0.16, y + off * 0.6, z + 0.04), (tx, ty, z + 0.12)],
             0.012, sides=5)
        revolve(brass, [(0.0, 0.0), (0.04, 0.01), (0.04, 0.035)], 8, centre=(tx, ty, z + 0.12))
        candle(wax, fl, fuv, tx, ty, z + 0.15, h=0.16)


def candelabra(brass, wax, fl, fuv, x, y, h=1.8):
    revolve(brass, [(0.28, 0.0), (0.28, 0.05), (0.16, 0.1), (0.08, 0.22), (0.04, 0.3)], 12,
            centre=(x, y, 0.0))
    revolve(brass, [(0.03, 0.3), (0.03, h - 0.3), (0.06, h - 0.25), (0.035, h)], 10,
            centre=(x, y, 0.0))
    for dx in (-0.28, -0.14, 0.0, 0.14, 0.28):
        top = h + 0.14 - abs(dx) * 0.4
        if dx:
            tube(brass, [(x, y, h - 0.2), (x + dx * 0.6, y, h - 0.24), (x + dx, y, top - 0.05)],
                 0.014, sides=5)
        revolve(brass, [(0.0, 0.0), (0.045, 0.01), (0.045, 0.045)], 8, centre=(x + dx, y, top - 0.05))
        candle(wax, fl, fuv, x + dx, y, top, h=0.2)


def chesterfield(vel, gilt, x, y, length, face):
    """A straight tufted sofa centred at (x, y), facing along angle *face*."""
    fx, fy = math.cos(face), math.sin(face)
    sx, sy = -fy, fx
    rot = math.atan2(sy, sx)

    def at(a, b):
        return x + sx * a + fx * b, y + sy * a + fy * b
    px, py = at(0.0, 0.0)
    box(vel, px, py, 0.26, length, 0.85, 0.36, rot_z=rot)
    px, py = at(0.0, -0.36)
    box(vel, px, py, 0.62, length, 0.2, 0.72, rot_z=rot)
    for s in (-1, 1):
        ax, ay = at(s * (length / 2 + 0.05), 0.0)
        box(vel, ax, ay, 0.38, 0.18, 0.9, 0.6, rot_z=rot)
        a0 = at(s * (length / 2 + 0.05), -0.45)
        a1 = at(s * (length / 2 + 0.05), 0.42)
        tube(vel, [(a0[0], a0[1], 0.68), (a1[0], a1[1], 0.68)], 0.11, sides=10)
    for s in (-1, 1):
        for t in (-1, 1):
            fx_, fy_ = at(s * length / 2, t * 0.35)
            revolve(gilt, [(0.03, 0.0), (0.04, 0.05), (0.025, 0.08)], 8, centre=(fx_, fy_, 0.0))


def tub_chair(vel, gilt, x, y, face):
    revolve(vel, [(0.0, 0.08), (0.44, 0.08), (0.46, 0.42), (0.40, 0.48), (0.0, 0.50)], 20,
            centre=(x, y, 0.0))
    back = []
    a0 = face + math.radians(50)
    for k in range(21):
        a = a0 + math.radians(260) * k / 20
        back.append((x + 0.44 * math.cos(a), y + 0.44 * math.sin(a), 0.70))
    tube(vel, back, 0.12, sides=10)
    for k in range(4):
        a = face + math.pi / 4 + k * math.pi / 2
        revolve(gilt, [(0.03, 0.0), (0.04, 0.05), (0.025, 0.08)], 8,
                centre=(x + 0.36 * math.cos(a), y + 0.36 * math.sin(a), 0.0))


def round_table(wood, gilt, top_bm, x, y, r=0.35, h=0.68):
    revolve(top_bm, [(0.0, h - 0.035), (r, h - 0.035), (r, h), (0.0, h)], 24, centre=(x, y, 0.0))
    ring = [(x + r * math.cos(TAU * k / 32), y + r * math.sin(TAU * k / 32), h - 0.018)
            for k in range(33)]
    tube(gilt, ring, 0.016, sides=6, cap=False)
    revolve(wood, [(0.2, 0.0), (0.2, 0.04), (0.06, 0.12), (0.04, h * 0.5), (0.07, h * 0.6),
                   (0.04, h - 0.1), (0.14, h - 0.035)], 12, centre=(x, y, 0.0))


def lantern(brass, glass, x, y, z):
    revolve(brass, [(0.07, 0.0), (0.07, 0.02), (0.05, 0.03)], 8, centre=(x, y, z))
    revolve(glass, [(0.045, 0.03), (0.06, 0.08), (0.055, 0.18), (0.035, 0.21)], 10,
            centre=(x, y, z))
    revolve(brass, [(0.04, 0.21), (0.06, 0.23), (0.02, 0.30), (0.0, 0.32)], 8, centre=(x, y, z))


def build_decor(M, c):
    brass, wax, fl, gilt, wood = (bmesh.new() for _ in range(5))
    vel, tops, glass, orb, case, rug, banner, port = (bmesh.new() for _ in range(8))
    fuv, buv, puv, ruv = {}, {}, {}, {}
    c_lights = []

    for cx, cy, cz in CHANDELIERS:
        chandelier(brass, wax, fl, fuv, cx, cy, cz)
    for side in (-1, 1):
        wx = side * (HALL_X - 0.08)
        for y in (-7.0, -2.0, 4.0, 10.5, 17.5):
            sconce(brass, wax, fl, fuv, wx, y, 2.35, -side)
            c_lights.append((wx - side * 0.3, y, 2.6))
        for y in (-4.2, 19.0):
            candelabra(brass, wax, fl, fuv, side * 5.6, y)
            c_lights.append((side * 5.6, y, 1.95))

    # banners on the lane faces of the middle columns
    for side in (-1, 1):
        for y in COLUMN_YS[1:4]:
            x = side * (COLUMN_X - 0.30)
            top, bot, w = 4.0, 2.25, 0.62
            sh = 0.15 * (top - bot)
            rows = []
            for j in range(9):
                v = j / 8
                row = []
                for i in range(7):
                    u = i / 6
                    edge = bot + sh * abs(2 * u - 1)
                    z = edge + (top - edge) * v
                    vv = banner.verts.new((x - side * 0.02 * math.sin(u * math.pi * 2),
                                           y + side * (u - 0.5) * w, z))
                    buv[vv] = (u, (z - bot) / (top - bot))
                    row.append(vv)
                rows.append(row)
            for j in range(8):
                for i in range(6):
                    banner.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1],
                                      rows[j + 1][i]))
            tube(brass, [(x, y - w / 2 - 0.06, top + 0.04), (x, y + w / 2 + 0.06, top + 0.04)],
                 0.02, sides=6)

    # ghost portraits between the side windows
    for side in (-1, 1):
        x = side * (HALL_X - 0.1)
        for y in (3.75, 10.25):
            w, h, zc = 1.0, 1.35, 2.6
            uv_quad(port, [(x, y + side * w / 2, zc - h / 2), (x, y - side * w / 2, zc - h / 2),
                           (x, y - side * w / 2, zc + h / 2), (x, y + side * w / 2, zc + h / 2)],
                    puv)
            fr = [(x - side * 0.03, y - w / 2, zc - h / 2), (x - side * 0.03, y + w / 2, zc - h / 2),
                  (x - side * 0.03, y + w / 2, zc + h / 2), (x - side * 0.03, y - w / 2, zc + h / 2),
                  (x - side * 0.03, y - w / 2, zc - h / 2)]
            tube(gilt, fr, 0.06, sides=6, cap=False)

    # aisle seating, tables and lanterns
    chesterfield(vel, gilt, -6.8, -1.6, 1.9, 0.0)
    tub_chair(vel, gilt, -6.4, 1.2, 0.0)
    tub_chair(vel, gilt, 6.4, -2.4, math.pi)
    tub_chair(vel, gilt, 6.4, 0.4, math.pi)
    chesterfield(vel, gilt, -1.6, -8.4, 2.0, math.pi / 2)
    chesterfield(vel, gilt, 1.6, -8.4, 2.0, math.pi / 2)
    lanterns = [(-6.0, -3.6), (6.1, -1.0), (0.0, -7.4)]
    for x, y in lanterns:
        round_table(wood, gilt, tops, x, y)
        lantern(brass, glass, x, y, 0.68)
    # a trophy cabinet, and the gargoyle with his orb by the front
    box(wood, -7.55, 6.2, 0.45, 0.5, 1.7, 0.9)
    box(wood, -7.55, 6.2, 2.45, 0.5, 1.7, 0.08)
    box(case, -7.55, 6.2, 1.67, 0.46, 1.64, 1.44)
    for k, y in enumerate((5.65, 6.2, 6.75)):
        revolve(gilt, [(0.05, 0.0), (0.05, 0.02), (0.015, 0.05), (0.015, 0.14), (0.07, 0.2),
                       (0.09, 0.32), (0.0, 0.3)], 12, centre=(-7.55, y, 0.92 + (k % 2) * 0.72))
    revolve(wood, [(0.3, 0.0), (0.3, 0.1), (0.22, 0.16), (0.2, 1.0), (0.28, 1.08), (0.28, 1.14)],
            8, centre=(-5.3, -4.4, 0.0))
    gargoyle(bmesh_garg := bmesh.new(), -5.3, -4.25, 1.14, math.pi * 0.5 + 0.4)
    revolve(orb, [(0.0, 0.0)] + [(0.13 * math.sin(math.pi * t / 12),
                                  0.13 - 0.13 * math.cos(math.pi * t / 12)) for t in range(1, 12)]
            + [(0.0, 0.26)], 16, centre=(-5.3, -4.62, 1.14))
    # rugs
    for x, y, hw, hh in ((-6.3, -1.0, 1.1, 4.5), (6.3, -1.0, 1.1, 4.5), (0.0, -7.6, 3.2, 1.8)):
        uv_quad(rug, [(x - hw, y - hh, 0.008), (x + hw, y - hh, 0.008), (x + hw, y + hh, 0.008),
                      (x - hw, y + hh, 0.008)], ruv)

    set_uvs(fl, fuv)
    set_uvs(banner, buv)
    set_uvs(port, puv)
    set_uvs(rug, ruv)
    shade_auto(new_obj(PFX + "Brass", brass, c, [M["brass"]]))
    new_obj(PFX + "Candles", wax, c, [M["candle"]])
    new_obj(PFX + "Flames", fl, c, [M["flame"]])
    shade_auto(new_obj(PFX + "DecorGilt", gilt, c, [M["gilt"]]))
    shade_auto(new_obj(PFX + "DecorWood", wood, c, [M["wood"]]))
    shade_auto(new_obj(PFX + "TableTops", tops, c, [M["marble"]]))
    shade_auto(new_obj(PFX + "Velvet", vel, c, [M["velvet"]]), math.radians(40))
    new_obj(PFX + "LanternGlass", glass, c, [M["lantern"]])
    shade_auto(new_obj(PFX + "Orb", orb, c, [M["orb"]]), math.radians(80))
    shade_auto(new_obj(PFX + "FrontGargoyle", bmesh_garg, c, [M["stone"]]), math.radians(40))
    new_obj(PFX + "TrophyGlass", case, c, [M["case_glass"]])
    new_obj(PFX + "Rugs", rug, c, [M["rug"]])
    new_obj(PFX + "Banners", banner, c, [M["banner"]])
    new_obj(PFX + "Portraits", port, c, [M["portrait"]])
    return c_lights, lanterns


# ======================================================= lights + cameras ===
def build_markers(c, candle_spots, lanterns):
    """LGT_* empties become Godot lights (see alley_theme.gd)."""
    k = 0
    for x, y, z in CHANDELIERS:
        empty("LGT_Chandelier_%d" % k, (x, y, z + 0.1), c); k += 1
    for i, (x, y, z) in enumerate(candle_spots):
        empty("LGT_Candle_%d" % i, (x, y, z), c)
    for i, (x, y) in enumerate(lanterns):
        empty("LGT_Lantern_%d" % i, (x, y, 0.85), c)
    for i in LANES:
        cx = i * PITCH
        empty("LGT_Mask_%d" % (i + 2), (cx, MASK_Y - 0.35, 1.5), c)
        empty("LGT_Pit_%d" % (i + 2), (cx, PIT_END - 0.25, 0.25), c)
        empty("LGT_PinSpot_%d" % (i + 2), (cx, 17.2, 2.7), c, target=(cx, 18.75, 0.1))
    for i, (x, y, z) in enumerate([(HALL_X - 1.0, yy, 4.6) for yy, *_ in SIDE_WINDOWS]
                                  + [(-HALL_X + 1.0, yy, 4.6) for yy, *_ in SIDE_WINDOWS]
                                  + [(xx, HALL_Y1 - 1.2, 4.6) for xx, *_ in BACK_WINDOWS]):
        empty("LGT_Window_%d" % i, (x, y, z), c)
    empty("LGT_Orb", (-5.3, -4.62, 1.3), c)
    empty("LGT_Approach", (0.2, -1.2, 2.6), c)
    empty("LGT_Lantern_ret", (PITCH / 2, -1.1, 1.25), c)


PREVIEW = {"Chandelier": ('POINT', 320.0, (1.0, 0.66, 0.34), 0.6),
           "Candle": ('POINT', 35.0, (1.0, 0.58, 0.26), 0.15),
           "Lantern": ('POINT', 18.0, (1.0, 0.6, 0.3), 0.1),
           "Mask": ('POINT', 60.0, (0.62, 0.35, 1.0), 0.4),
           "Pit": ('POINT', 25.0, (0.6, 0.3, 1.0), 0.3),
           "PinSpot": ('SPOT', 220.0, (0.9, 0.86, 1.0), 0.1),
           "Window": ('POINT', 90.0, (0.45, 0.4, 1.0), 0.8),
           "Orb": ('POINT', 40.0, (0.6, 0.25, 1.0), 0.1),
           "Approach": ('POINT', 120.0, (1.0, 0.7, 0.45), 0.5)}


def build_preview_lights(markers_col, c):
    """Real Blender lights at the markers, for EEVEE previews only (not exported)."""
    wipe("BWLLGT_")
    for ob in list(markers_col.objects):
        if not ob.name.startswith("LGT_"):
            continue
        kind = ob.name.split("_")[1]
        typ, energy, color, size = PREVIEW[kind]
        d = bpy.data.lights.new("BWLLGT_" + ob.name, typ)
        d.energy, d.color = energy, color
        d.shadow_soft_size = size
        d.use_shadow = kind in ("Chandelier", "PinSpot", "Window")
        if kind == "Candle":
            d.specular_factor = 0.1
        lo = bpy.data.objects.new("BWLLGT_" + ob.name, d)
        lo.location = ob.location
        if "target" in ob:
            v = Vector(ob["target"]) - ob.location
            lo.rotation_euler = v.to_track_quat('-Z', 'Y').to_euler()
            d.spot_size = math.radians(55)
            d.spot_blend = 0.5
        c.objects.link(lo)


def build_cameras(c):
    wipe("BWLCAM_")

    def cam(name, loc, target, fov_v=None, lens=None):
        d = bpy.data.cameras.new("BWLCAM_" + name)
        if fov_v:
            d.sensor_fit = 'VERTICAL'
            d.angle_y = math.radians(fov_v)
        if lens:
            d.lens = lens
        d.clip_start, d.clip_end = 0.05, 200.0
        ob = bpy.data.objects.new("BWLCAM_" + name, d)
        ob.location = loc
        v = Vector(target) - Vector(loc)
        ob.rotation_euler = v.to_track_quat('-Z', 'Y').to_euler()
        c.objects.link(ob)
        return ob
    aim = cam("Aim", (0.07, -2.7, 1.45), (0.03, 15.0, 0.15), fov_v=58)   # = Godot's aim camera
    cam("Hall", (0.0, -9.4, 2.4), (0.0, 20.0, 1.3), lens=16)
    cam("Pins", (0.95, 15.9, 0.75), (0.0, 18.7, 0.15), fov_v=58)
    cam("Aisle", (-6.8, -6.0, 1.7), (-2.0, 12.0, 1.4), lens=20)
    bpy.context.scene.camera = aim


def build(tex):
    root = col("BWL_Lounge")
    for pre in ("BWL_", "LGT_", "BALL_"):
        wipe(pre)
    M = materials(tex)
    c = col("BWL_LoungeArt", root)
    build_lanes(M, c)
    build_masking(M, c)
    build_returns(M, c)
    build_shell(M, c)
    build_columns(M, c)
    candles, lanterns = build_decor(M, c)
    mk = col("BWL_LoungeMarkers", root)
    build_markers(mk, candles, lanterns)
    build_preview_lights(mk, col("BWL_PreviewLights"))
    build_cameras(col("BWL_Cameras"))
    return root
