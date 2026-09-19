"""The hall itself: floor, walls with door and window openings, emblem
tympana, columns, the gallery balcony and its balustrade, ceiling."""
import bpy, bmesh, math
from mathutils import Vector
from lounge_common import (
    col, wipe, new_obj, shade_auto, box, revolve, tube, arch_outline, SQ3_2,
    wall_with_openings, WALLS, DOORS, FLOOR_POLY, FLOOR_BOUNDS, WALL_T, CEIL_Z,
    GALLERY_Z, BALC_D, DOOR_W, DOOR_SPRING, DOOR_INNER_W, BACK_HX, BACK_Y,
    SIDE_X, DIAG_Y, FRONT_Y, wall_frame, seg_mapper, door_u)

PFX = "LNG_"

WINDOW_SILL, WINDOW_SPRING = 9.6, 12.6        # blue lancets
STORM = (3.2, 9.0, 12.0)                      # the central violet window


def windows(name):
    L = wall_frame(name)[3]
    if name == "Back":
        return [(L * 0.5, STORM[0], STORM[1], STORM[2], "storm"),
                (BACK_HX - 5.6, 1.8, WINDOW_SILL, WINDOW_SPRING, "blue"),
                (BACK_HX + 5.6, 1.8, WINDOW_SILL, WINDOW_SPRING, "blue")]
    if name in ("DiagL", "DiagR"):
        return [(L * 0.5, 1.8, WINDOW_SILL, WINDOW_SPRING, "blue")]
    if name in ("SideL", "SideR"):
        return [(4.0, 1.8, WINDOW_SILL, WINDOW_SPRING, "blue"),
                (9.0, 1.8, WINDOW_SILL, WINDOW_SPRING, "blue")]
    return []


def doors(name):
    return [(door_u(d), d[2], d[3]) for d in DOORS if d[0] == name]


def set_uvs(ob, fn):
    me = ob.data
    layer = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            layer.data[li].uv = fn(me.vertices[me.loops[li].vertex_index].co)
    return ob


def wall_uv(name, scale=1.0 / 3.6):
    p0, d, n, L = wall_frame(name)

    def fn(co):
        rel = Vector(co) - p0
        return (rel.dot(d) * scale + rel.dot(n) * scale, co.z * scale)
    return fn


def _dedupe(pts):
    out = []
    for p in pts:
        if not out or abs(out[-1][0] - p[0]) + abs(out[-1][1] - p[1]) > 1e-6:
            out.append(p)
    return out


def _panel(bm, to_world, uc, outline, depth, uv_fn=None, uvs=None):
    vs = [bm.verts.new(to_world(uc + x, z, depth)) for x, z in outline]
    f = bm.faces.new(vs)
    if uvs is not None and uv_fn:
        for v, (x, z) in zip(vs, outline):
            uvs[v] = uv_fn(x, z)
    return f


def _apply_uv_dict(bm, uvs):
    layer = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for loop in f.loops:
            if loop.vert in uvs:
                loop[layer].uv = uvs[loop.vert]


# ================================================================ floor ====
def build_floor(M, c):
    bm = bmesh.new()
    bm.faces.new([bm.verts.new((x, y, 0.0)) for x, y in FLOOR_POLY])
    ob = new_obj(PFX + "Floor", bm, c, [M["floor"]])
    x0, y0, x1, y1 = FLOOR_BOUNDS
    set_uvs(ob, lambda co: ((co.x - x0) / (x1 - x0), (co.y - y0) / (y1 - y0)))
    return ob


# ================================================================ walls ====
def build_walls(M, c):
    for name, _, _ in WALLS:
        ops = [(u, DOOR_W, 0.0, DOOR_SPRING) for u, _, _ in doors(name)]
        ops += [(u, w, s, sp) for u, w, s, sp, _ in windows(name)]
        L = wall_frame(name)[3]
        bm = bmesh.new()
        wall_with_openings(bm, seg_mapper(name), 0.0, L, CEIL_Z, WALL_T, ops,
                           nu=2, per_arch=10)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        ob = new_obj(PFX + "Wall_" + name, bm, c, [M["stone"]])
        set_uvs(ob, wall_uv(name))


def build_windows(M, c):
    bm_b, bm_s = bmesh.new(), bmesh.new()
    uv_b, uv_s = {}, {}
    frames = bmesh.new()
    for name, _, _ in WALLS:
        tw = seg_mapper(name)
        for u, w, sill, spring, kind in windows(name):
            h = spring - sill + w * SQ3_2
            out = _dedupe(arch_outline(w, sill, spring, 14))
            bm, uvs = (bm_s, uv_s) if kind == "storm" else (bm_b, uv_b)
            _panel(bm, tw, u, out, WALL_T * 0.5,
                   lambda x, z, w=w, sill=sill, h=h: ((x + w * 0.5) / w, (z - sill) / h),
                   uvs)
            # a thin stone frame just proud of the wall
            path = [tw(u + x, z, -0.04) for x, z in out]
            tube(frames, path, 0.07, sides=6, cap=False)
            sill_c = tw(u, sill - 0.08, -0.12)
            p0, d, n, L = wall_frame(name)
            box(frames, sill_c.x, sill_c.y, sill_c.z, w + 0.5, 0.30, 0.16,
                rot_z=math.atan2(d.y, d.x))
    _apply_uv_dict(bm_b, uv_b)
    _apply_uv_dict(bm_s, uv_s)
    new_obj(PFX + "Glass_Blue", bm_b, c, [M["glass_blue"]])
    new_obj(PFX + "Glass_Storm", bm_s, c, [M["glass_storm"]])
    shade_auto(new_obj(PFX + "WindowFrames", frames, c, [M["trim_lt"]]))


# ======================================================== door surrounds ===
EMB_MAT = {"bowling": "emb_bowling", "billiards": "emb_billiards",
           "golf": "emb_golf", "poker": "emb_poker"}


def build_doors(M, c):
    wood, gilt, trim = bmesh.new(), bmesh.new(), bmesh.new()
    for name, _, _ in WALLS:
        tw = seg_mapper(name)
        p0, d, n, L = wall_frame(name)
        yaw = math.atan2(d.y, d.x)
        for u, slug, tint in doors(name):
            # tympanum with the game's emblem
            bm = bmesh.new()
            uvs = {}
            out = _dedupe(arch_outline(DOOR_W, DOOR_SPRING, DOOR_SPRING, 16))
            rise = DOOR_W * SQ3_2
            _panel(bm, tw, u, out, 0.22,
                   lambda x, z: ((x + DOOR_W * 0.5) / DOOR_W, (z - DOOR_SPRING) / rise),
                   uvs)
            _apply_uv_dict(bm, uvs)
            ob = new_obj(PFX + "Emblem_" + slug, bm, c, [M[EMB_MAT[slug]]])
            ob["game"] = slug

            # jambs and lintel narrow the opening to the real door gap
            jw = (DOOR_W - DOOR_INNER_W) * 0.5
            for s in (-1, 1):
                p = tw(u + s * (DOOR_W * 0.5 - jw * 0.5), DOOR_SPRING * 0.5, WALL_T * 0.5)
                box(wood, p.x, p.y, p.z, jw, WALL_T + 0.12, DOOR_SPRING, rot_z=yaw)
            p = tw(u, DOOR_SPRING - 0.16, WALL_T * 0.5)
            box(wood, p.x, p.y, p.z, DOOR_W, WALL_T + 0.12, 0.32, rot_z=yaw)
            p = tw(u, DOOR_SPRING + 0.02, -0.04)
            box(gilt, p.x, p.y, p.z, DOOR_W + 0.1, 0.10, 0.06, rot_z=yaw)

            # gilt bead round the arch, heavier stone hood mould outside it
            path = [tw(u + x, z, -0.05) for x, z in
                    _dedupe(arch_outline(DOOR_W + 0.10, 0.0, DOOR_SPRING, 20))]
            tube(gilt, path, 0.055, sides=8, cap=False)
            path = [tw(u + x, z, -0.10) for x, z in
                    _dedupe(arch_outline(DOOR_W + 0.50, 0.0, DOOR_SPRING, 20))]
            tube(trim, path, 0.13, sides=8, cap=False)
            # finial at the apex
            apex = tw(u, DOOR_SPRING + (DOOR_W + 0.5) * SQ3_2 + 0.02, -0.10)
            revolve(trim, [(0.0, 0.0), (0.16, 0.05), (0.10, 0.22), (0.05, 0.36),
                           (0.0, 0.42)], 10, centre=tuple(apex))
            # threshold slab
            p = tw(u, 0.02, WALL_T * 0.5)
            box(trim, p.x, p.y, p.z, DOOR_INNER_W, WALL_T + 0.3, 0.04, rot_z=yaw)
    shade_auto(new_obj(PFX + "DoorJoinery", wood, c, [M["wood"]]))
    shade_auto(new_obj(PFX + "DoorGilt", gilt, c, [M["gilt"]]))
    shade_auto(new_obj(PFX + "DoorMoulds", trim, c, [M["trim"]]))


# ================================================================ columns ===
def column_sites():
    """(x, y, yaw) - yaw turns local +Y to face out through the wall."""
    sites = []
    corners = [(-BACK_HX, BACK_Y), (BACK_HX, BACK_Y),
               (-SIDE_X, DIAG_Y), (SIDE_X, DIAG_Y)]
    for x, y in corners:
        a = math.atan2(-x, y - 0.0)
        sites.append((x, y, 0.0))
    for x in (-3.55, 3.55):
        sites.append((x, BACK_Y, 0.0))
    for x in (-SIDE_X, SIDE_X):
        sites.append((x, -2.5, 0.0))
    return sites


def build_columns(M, c):
    stone, gold = bmesh.new(), bmesh.new()
    base = [(0.50, 0.0), (0.50, 0.32), (0.44, 0.38), (0.44, 0.48), (0.38, 0.54),
            (0.34, 0.62)]
    cap = [(0.34, 0.0), (0.36, 0.06), (0.46, 0.30), (0.56, 0.42), (0.56, 0.55),
           (0.40, 0.58)]
    for x, y, _ in column_sites():
        revolve(stone, base, 16, centre=(x, y, 0.0))
        revolve(stone, [(0.30, 0.62), (0.30, 7.10)], 16, centre=(x, y, 0.0))
        for dx, dy in ((0.33, 0.0), (-0.33, 0.0), (0.0, -0.33), (0.0, 0.33),
                       (0.23, -0.23), (-0.23, -0.23), (0.23, 0.23), (-0.23, 0.23)):
            revolve(stone, [(0.085, 0.62), (0.085, 7.10)], 8,
                    centre=(x + dx, y + dy, 0.0))
        revolve(stone, cap, 16, centre=(x, y, 7.08))
        revolve(gold, [(0.335, 0.0), (0.345, 0.04), (0.335, 0.08)], 16,
                centre=(x, y, 7.06))
        # upper order above the gallery
        revolve(stone, [(0.26, 9.1), (0.26, 15.2)], 16, centre=(x, y, 0.0))
        revolve(stone, [(0.34, 0.0), (0.34, 0.25), (0.28, 0.32)], 16,
                centre=(x, y, 8.85))
        revolve(stone, cap, 16, centre=(x, y, 15.15))
    shade_auto(new_obj(PFX + "Columns", stone, c, [M["trim"]]))
    shade_auto(new_obj(PFX + "ColumnRings", gold, c, [M["gilt"]]))


# ========================================================== the gallery ====
def gallery_polyline():
    return [(-SIDE_X, FRONT_Y), (-SIDE_X, DIAG_Y), (-BACK_HX, BACK_Y),
            (BACK_HX, BACK_Y), (SIDE_X, DIAG_Y), (SIDE_X, FRONT_Y)]


def offset_polyline(pts, dist):
    """Offset to the right of travel (into the room for this polyline)."""
    P = [Vector((x, y)) for x, y in pts]
    segs = []
    for a, b in zip(P, P[1:]):
        t = (b - a).normalized()
        nrm = Vector((t.y, -t.x))
        segs.append((a + nrm * dist, t))
    out = [segs[0][0]]
    for (a1, t1), (a2, t2) in zip(segs, segs[1:]):
        den = t1.x * t2.y - t1.y * t2.x
        s = ((a2.x - a1.x) * t2.y - (a2.y - a1.y) * t2.x) / den
        out.append(a1 + t1 * s)
    last_a, last_t = segs[-1]
    end = P[-1] + Vector((last_t.y, -last_t.x)) * dist
    out.append(end)
    return out


def build_gallery(M, c):
    outer = [Vector(p) for p in gallery_polyline()]
    inner = offset_polyline(gallery_polyline(), BALC_D)
    z1, z0 = GALLERY_Z, GALLERY_Z - 0.38
    bm = bmesh.new()
    ot = [bm.verts.new((p.x, p.y, z1)) for p in outer]
    it = [bm.verts.new((p.x, p.y, z1)) for p in inner]
    ob_ = [bm.verts.new((p.x, p.y, z0)) for p in outer]
    ib = [bm.verts.new((p.x, p.y, z0)) for p in inner]
    for i in range(len(outer) - 1):
        bm.faces.new((ot[i], ot[i + 1], it[i + 1], it[i]))
        bm.faces.new((ib[i], ib[i + 1], ob_[i + 1], ob_[i]))
        bm.faces.new((it[i], it[i + 1], ib[i + 1], ib[i]))
    slab = new_obj(PFX + "GallerySlab", bm, c, [M["trim"]])

    # fascia mouldings and corbels under the slab
    mould, wood, gilt = bmesh.new(), bmesh.new(), bmesh.new()
    for a, b in zip(inner, inner[1:]):
        t = (b - a); L = t.length; t.normalize()
        nrm = Vector((t.y, -t.x))
        yaw = math.atan2(t.y, t.x)
        mid = (a + b) * 0.5
        for dz, hgt, proud in ((z0 - 0.06, 0.14, 0.08), (z1 - 0.04, 0.10, 0.05)):
            p = mid + nrm * proud * 0.5
            box(mould, p.x, p.y, dz, L + 0.1, 0.12 + proud, hgt, rot_z=yaw)
        p = mid + nrm * 0.02
        box(gilt, p.x, p.y, z0 + 0.14, L, 0.05, 0.04, rot_z=yaw)
        n_c = max(1, int(L / 1.6))
        for k in range(n_c):
            q = a + t * (L * (k + 0.5) / n_c) - nrm * 0.35
            box(mould, q.x, q.y, z0 - 0.35, 0.22, 0.75, 0.55, rot_z=yaw)

        # balustrade, set back 0.12 from the edge
        edge_a = a - nrm * 0.12
        rail_mid = mid - nrm * 0.12
        box(wood, rail_mid.x, rail_mid.y, z1 + 1.02, L + 0.12, 0.17, 0.09, rot_z=yaw)
        box(mould, rail_mid.x, rail_mid.y, z1 + 0.06, L, 0.20, 0.12, rot_z=yaw)
        nb = int((L - 0.3) / 0.22)
        for k in range(nb):
            q = edge_a + t * (0.15 + (L - 0.3) * (k + 0.5) / nb)
            revolve(mould, BALUSTER, 6, centre=(q.x, q.y, z1 + 0.12))
    for p in inner:
        q = p
        box(wood, q.x, q.y, z1 + 0.58, 0.26, 0.26, 1.16)
        revolve(gilt, [(0.0, 0.0), (0.09, 0.02), (0.07, 0.12), (0.0, 0.18)], 8,
                centre=(q.x, q.y, z1 + 1.16))
    shade_auto(new_obj(PFX + "GalleryMoulds", mould, c, [M["trim"]]))
    shade_auto(new_obj(PFX + "GalleryRail", wood, c, [M["wood"]]))
    shade_auto(new_obj(PFX + "GalleryGilt", gilt, c, [M["gilt"]]))
    return slab


BALUSTER = [(0.050, 0.0), (0.050, 0.07), (0.030, 0.11), (0.066, 0.30),
            (0.030, 0.52), (0.022, 0.62), (0.036, 0.74), (0.046, 0.79),
            (0.046, 0.86)]


# ============================================================ ceiling ======
def build_ceiling(M, c):
    bm = bmesh.new()
    bm.faces.new([bm.verts.new((x, y, CEIL_Z)) for x, y in FLOOR_POLY[::-1]])
    new_obj(PFX + "Ceiling", bm, c, [M["ceiling"]])

    beams, gilt = bmesh.new(), bmesh.new()
    for y in (-6.0, -3.0, 0.0, 3.0, 6.0):
        box(beams, 0.0, y, CEIL_Z - 0.2, SIDE_X * 2, 0.34, 0.40)
    for x in (-9.0, -6.0, -3.0, 0.0, 3.0, 6.0, 9.0):
        box(beams, x, -0.5, CEIL_Z - 0.2, 0.34, 17.0, 0.40)
    # cornice along every wall
    for name, _, _ in WALLS:
        p0, d, n, L = wall_frame(name)
        mid = p0 + d * (L * 0.5) - n * 0.14
        yaw = math.atan2(d.y, d.x)
        box(beams, mid.x, mid.y, CEIL_Z - 0.55, L + 0.4, 0.30, 0.50, rot_z=yaw)
        mid2 = p0 + d * (L * 0.5) - n * 0.30
        box(gilt, mid2.x, mid2.y, CEIL_Z - 0.80, L + 0.4, 0.04, 0.05, rot_z=yaw)
    # ceiling rose over the chandelier
    revolve(gilt, [(1.1, 0.0), (0.9, -0.08), (0.5, -0.14), (0.2, -0.26),
                   (0.0, -0.30)], 24, centre=(0.0, 3.2, CEIL_Z - 0.40))
    shade_auto(new_obj(PFX + "CeilingBeams", beams, c, [M["wood"]]))
    shade_auto(new_obj(PFX + "CeilingGilt", gilt, c, [M["gilt"]]))


def build_skirting(M, c):
    bm = bmesh.new()
    for name, _, _ in WALLS:
        p0, d, n, L = wall_frame(name)
        yaw = math.atan2(d.y, d.x)
        cuts = sorted((u - DOOR_W * 0.5 - 0.1, u + DOOR_W * 0.5 + 0.1)
                      for u, _, _ in doors(name))
        spans, cur = [], 0.0
        for lo, hi in cuts:
            spans.append((cur, lo)); cur = hi
        spans.append((cur, L))
        for lo, hi in spans:
            if hi - lo < 0.05:
                continue
            mid = p0 + d * ((lo + hi) * 0.5) - n * 0.04
            box(bm, mid.x, mid.y, 0.16, hi - lo, 0.09, 0.32, rot_z=yaw)
    new_obj(PFX + "Skirting", bm, c, [M["trim"]])


def build(M):
    c = col("LNG_Shell", col("Lounge"))
    for pre in ("LNG_Floor", "LNG_Wall_", "LNG_Glass_", "LNG_WindowFrames",
                "LNG_Emblem_", "LNG_Door", "LNG_Column", "LNG_Gallery",
                "LNG_Ceiling", "LNG_Skirting"):
        wipe(pre)
    build_floor(M, c)
    build_walls(M, c)
    build_windows(M, c)
    build_doors(M, c)
    build_columns(M, c)
    build_gallery(M, c)
    build_ceiling(M, c)
    build_skirting(M, c)
    return c
