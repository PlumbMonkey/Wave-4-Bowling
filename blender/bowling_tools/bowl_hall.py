"""Hall pieces shared by the alleys after the Lounge (The Void, The Crypt).

The Lounge's build_shell is its own; these are the same hall made from parts,
so an alley can swap the back wall for open sky, drop the windows for murals,
or dress the walls in stone.
"""
import bmesh, math
from bowl_common import (new_obj, shade_auto, box, tube, arch_outline, wall_with_openings,
                         wall_mapper, APPROACH, PIT_END, HALL_X, HALL_Y0, HALL_Y1, CEIL, BLOCK_X,
                         SQ3_2, TAU)
from bowl_alley import PFX, dedupe, set_uvs, world_uvs, squashed_arch

OPEN_W, OPEN_SPRING, OPEN_RISE = 13.0, 4.2, 0.24      # The Void's great arch onto space


def box_uvs(ob, scale):
    """Box-project UVs (for stone): each face takes the two axes it faces across."""
    me = ob.data
    layer = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        n = poly.normal
        ax = (1, 2) if abs(n.x) >= max(abs(n.y), abs(n.z)) else \
            ((0, 2) if abs(n.y) >= abs(n.z) else (0, 1))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            layer.data[li].uv = (co[ax[0]] * scale, co[ax[1]] * scale)


def floor(M, c, key="marble", scale=0.5):
    fl = bmesh.new()
    for x0, x1, y0, y1 in ((-HALL_X, HALL_X, HALL_Y0, -APPROACH),
                           (-HALL_X, -BLOCK_X, -APPROACH, HALL_Y1),
                           (BLOCK_X, HALL_X, -APPROACH, HALL_Y1),
                           (-BLOCK_X, BLOCK_X, PIT_END, HALL_Y1)):
        fl.faces.new([fl.verts.new(p) for p in ((x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0))])
    ob = new_obj(PFX + "Floor", fl, c, [M[key]])
    world_uvs(ob, scale)
    return ob


def walls(M, c, side_windows, back_windows=(), back="wall", key="plaster", stone_scale=None):
    """Side, front and back walls. back = 'wall' | 'open' (a great arch onto the sky)."""
    bm = bmesh.new()
    for x, flip in ((HALL_X, False), (-HALL_X, True)):
        wall_with_openings(bm, wall_mapper('X', x, flip), HALL_Y0, HALL_Y1, CEIL, 0.4,
                           [(y, w, s, sp) for y, w, s, sp in side_windows])
    wall_with_openings(bm, wall_mapper('Y', HALL_Y0, True), -HALL_X, HALL_X, CEIL, 0.4, [])
    if back == "wall":
        wall_with_openings(bm, wall_mapper('Y', HALL_Y1, False), -HALL_X, HALL_X, CEIL, 0.4,
                           [(x, w, s, sp) for x, w, s, sp, *_ in back_windows])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    ob = new_obj(PFX + "Walls", bm, c, [M[key]])
    if stone_scale:
        box_uvs(ob, stone_scale)
    if back == "open":
        open_back(M, c, key, stone_scale)
    return ob


def open_back(M, c, key, stone_scale):
    """The back wall with one great flattened pointed arch cut through it."""
    bm = bmesh.new()
    hw = OPEN_W / 2
    arch = [(-hw, 0.0), (-hw, OPEN_SPRING)] + \
        [(p[0], p[2]) for p in squashed_arch((-hw, HALL_Y1), (hw, HALL_Y1), OPEN_SPRING, OPEN_RISE, n=32)] + \
        [(hw, OPEN_SPRING), (hw, 0.0)]
    for d in (0.0, 0.4):
        y = HALL_Y1 + d
        for (x0, z0), (x1, z1) in zip(arch, arch[1:]):
            if abs(x1 - x0) < 1e-6:
                continue
            q = [bm.verts.new(p) for p in ((x0, y, z0), (x1, y, z1), (x1, y, CEIL), (x0, y, CEIL))]
            bm.faces.new(q if d == 0.0 else q[::-1])
        for s in (-1, 1):
            q = [bm.verts.new(p) for p in ((s * hw, y, 0), (s * HALL_X, y, 0), (s * HALL_X, y, CEIL),
                                           (s * hw, y, CEIL))]
            bm.faces.new(q[::-1] if (s < 0) == (d == 0.0) else q)
    ob = new_obj(PFX + "BackWall", bm, c, [M[key]])
    if stone_scale:
        box_uvs(ob, stone_scale)
    # a carved and gilded surround on the arch
    path = [(x, HALL_Y1 - 0.05, z) for x, z in arch]
    tr, gl = bmesh.new(), bmesh.new()
    tube(tr, path, 0.22, sides=8, cap=False)
    tube(gl, [(x, y - 0.2, z) for x, y, z in path], 0.035, sides=6, cap=False)
    shade_auto(new_obj(PFX + "BackArch", tr, c, [M["wood"]]), math.radians(50))
    new_obj(PFX + "BackArchGilt", gl, c, [M["gilt"]])


def glazing(M, c, side_windows, back_windows=(), glass_side="glass_s", glass_back="glass_c"):
    gc, gs, frames = bmesh.new(), bmesh.new(), bmesh.new()
    cu, su = {}, {}

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
        for y, w, s, sp in side_windows:
            pane(gs, su, tw, y, w, s, sp)
    tw = wall_mapper('Y', HALL_Y1, False)
    for x, w, s, sp, kind in back_windows:
        pane(gc if kind == "c" else gs, cu if kind == "c" else su, tw, x, w, s, sp)
    set_uvs(gc, cu)
    set_uvs(gs, su)
    if back_windows:
        new_obj(PFX + "GlassBack", gc, c, [M[glass_back]])
    else:
        gc.free()
    new_obj(PFX + "GlassSide", gs, c, [M[glass_side]])
    shade_auto(new_obj(PFX + "WindowFrames", frames, c, [M["gilt"]]))


def panelling(M, c, back_wainscot=True, ceil_key="wood_dk", ceil_scale=None, beams=True):
    """Wainscot, dado, pilasters, cornice and the ceiling - as in the Lounge."""
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
    for y in ((HALL_Y1 - 0.04, HALL_Y0 + 0.04) if back_wainscot else (HALL_Y0 + 0.04,)):
        box(wood, 0.0, y, 0.75, 2 * HALL_X, 0.08, 1.5)
        box(wood, 0.0, y - math.copysign(0.12, y), CEIL - 0.25, 2 * HALL_X, 0.24, 0.5)
    ceil = bmesh.new()
    ceil.faces.new([ceil.verts.new(p) for p in ((-HALL_X, HALL_Y1, CEIL), (HALL_X, HALL_Y1, CEIL),
                                                  (HALL_X, HALL_Y0, CEIL), (-HALL_X, HALL_Y0, CEIL))])
    ob = new_obj(PFX + "Ceiling", ceil, c, [M[ceil_key]])
    if ceil_scale:
        world_uvs(ob, ceil_scale)
    if beams:
        for x in (-6.0, -3.0, 0.0, 3.0, 6.0):
            box(wood, x, (HALL_Y0 + HALL_Y1) * 0.5, CEIL - 0.15, 0.25, HALL_Y1 - HALL_Y0, 0.3)
        for y in range(-8, 22, 3):
            box(wood, 0.0, y, CEIL - 0.15, 2 * HALL_X, 0.25, 0.3)
    shade_auto(new_obj(PFX + "Panelling", wood, c, [M["wood"]]))
    new_obj(PFX + "PanelGilt", gilt, c, [M["gilt"]])


def disc(bm, uvs, centre, r, n=48, facing='-Y'):
    """A flat textured disc (UV 0..1 over its bounding square)."""
    cx, cy, cz = centre
    vs = []
    for k in range(n):
        a = TAU * k / n
        u, v = math.cos(a), math.sin(a)
        if facing == '-Y':
            p = (cx + u * r, cy, cz + v * r)
        elif facing == '-Z':
            p = (cx + u * r, cy - v * r, cz)
        else:                                    # '+Z'
            p = (cx + u * r, cy + v * r, cz)
        vv = bm.verts.new(p)
        uvs[vv] = (0.5 + 0.5 * u, 0.5 + 0.5 * v)
        vs.append(vv)
    bm.faces.new(vs)
    return vs


def crescent_outline(r, thick=0.72, off=(0.36, 0.14), n=96):
    """2D outline of a crescent (outer disc minus an offset inner disc), CCW."""
    ri = r * thick + 0.02 * r
    ci = (off[0] * r, off[1] * r)
    outer = [(r * math.cos(TAU * k / n), r * math.sin(TAU * k / n)) for k in range(n)]
    keep = [math.hypot(p[0] - ci[0], p[1] - ci[1]) > ri for p in outer]
    start = next(k for k in range(n) if keep[k] and not keep[k - 1])
    arc = []
    k = start
    while keep[k % n]:
        arc.append(outer[k % n])
        k += 1
    inner = [(ci[0] + ri * math.cos(TAU * j / n), ci[1] + ri * math.sin(TAU * j / n)) for j in range(n)]
    ins = [j for j in range(n) if math.hypot(*inner[j]) < r]
    # walk the inner arc back from the end of the outer arc to its start
    end = arc[-1]
    j0 = min(ins, key=lambda j: math.hypot(inner[j][0] - end[0], inner[j][1] - end[1]))
    back, j = [], j0
    while (j % n) in ins and len(back) < n:
        back.append(inner[j % n])
        j -= 1
    if len(back) < 3:
        back, j = [], j0
        while (j % n) in ins and len(back) < n:
            back.append(inner[j % n])
            j += 1
    return arc + back


def crescent(bm, centre, r, facing_deg=0.0, **kw):
    """A flat crescent moon standing upright at *centre*, facing -Y (rotated by facing_deg)."""
    cx, cy, cz = centre
    ca, sa = math.cos(math.radians(facing_deg)), math.sin(math.radians(facing_deg))
    vs = [bm.verts.new((cx + u * ca, cy + u * sa, cz + v)) for u, v in crescent_outline(r, **kw)]
    bm.faces.new(vs)
